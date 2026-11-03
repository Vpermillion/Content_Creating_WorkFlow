"""Publish only reviewed, hash-pinned batch artifacts; resume existing uploads."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from whatif import topics, youtube, youtube_publish as publish
from whatif.store import atomic_json, identifier


def load_request(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT / 'publish-requests') or path.suffix != '.json' or path.stat().st_size > 250_000:
        raise ValueError('Use a bounded reviewed JSON request under publish-requests/')
    request = json.loads(path.read_text()); identifier(request['id'])
    if request.get('schema_version') != 1 or request.get('channel') != 'ifverse_anime' or request.get('owner_requested_publication') is not True:
        raise ValueError('Explicit batch/channel publication scope is required')
    batch_path = (ROOT / request['batch']).resolve()
    if not batch_path.is_relative_to(ROOT / 'batch-requests'):
        raise ValueError('Batch must be a saved request')
    batch = json.loads(batch_path.read_text())
    allowed = {e['id'] for e in batch['episodes']}
    items = request['items']
    if not isinstance(items, list) or not 1 <= len(items) <= 10 or len({i['id'] for i in items}) != len(items):
        raise ValueError('Use one to ten distinct episodes')
    for item in items:
        identifier(item['id'])
        if item['id'] not in allowed:
            raise ValueError('Episode is outside the authorized production batch')
        if item.get('publication_clearance') != 'cleared' or item.get('review', {}).get('source_use') != 'approved' or item.get('review', {}).get('audiovisual') != 'approved':
            raise ValueError('Pending source-use/editorial review; no upload attempted')
        if not re.fullmatch(r'[a-f0-9]{40}', item.get('result_commit', '')):
            raise ValueError('Pin the exact completed result commit')
        if not re.fullmatch(r'[a-f0-9]{64}', item.get('video_sha256', '')):
            raise ValueError('Pin the final video SHA-256')
        if not re.fullmatch(re.escape('codex/results/' + item['id']) + r'(?:-r[23])?', item.get('result_branch','')):
            raise ValueError('Use the exact episode-specific result branch')
        if item.get('video', '').startswith('artifacts/' + item['id'] + '/') is not True:
            raise ValueError('Video must belong to this episode')
    return request


def fetch_result(item):
    branch = item['result_branch']
    subprocess.run(['git', 'fetch', '--quiet', '--depth=1', 'origin', 'refs/heads/' + branch], cwd=ROOT, check=True)
    commit = subprocess.check_output(['git','rev-parse','FETCH_HEAD'],cwd=ROOT,text=True).strip()
    if commit != item['result_commit']:
        raise ValueError('Result branch differs from reviewed commit')
    receipt_name = 'artifacts/' + item['id'] + '/batch-result.json'
    result = json.loads(subprocess.check_output(['git','show',commit+':'+receipt_name],cwd=ROOT))
    if result.get('status') != 'success' or result.get('video_sha256') != item['video_sha256']:
        raise ValueError('Saved result did not establish the expected video')
    expected_video = 'artifacts/' + item['id'] + '/' + result['video']
    if item['video'] != expected_video:
        raise ValueError('Manifest must select the final mixed video from its receipt')
    path = (ROOT / expected_video).resolve()
    if not path.is_relative_to(ROOT / 'artifacts' / item['id']):
        raise ValueError('Invalid artifact path')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as out:
        subprocess.run(['git','show',commit+':'+expected_video],cwd=ROOT,stdout=out,check=True)


def run(relative, expected_channel_id, execute=False):
    request = load_request(relative)
    registry_path = ROOT / 'channels/ifverse_anime-topics.json'
    registry = json.loads(registry_path.read_text())
    if not execute:
        return {'status':'planned','episodes':[i['id'] for i in request['items']],
                'uploaded':False,'note':'Plan only; --publish performs verified uploads'}
    youtube.require_channel_id(expected_channel_id)
    ready = []
    for item in request['items']:
        fetch_result(item)
        ready.append((item, publish.preflight(item, ROOT, registry)))
    session = publish.verified_session(youtube.ConnectionStore(ROOT / 'private/youtube-publish'), expected_channel_id)
    receipts = []
    try:
        for item, (video, fingerprint, metadata_hash, body) in ready:
            receipt = publish.upload(session,item['id'],video,fingerprint,metadata_hash,body,
                                     expected_channel_id,ROOT/'private/youtube-upload-state')
            receipt = publish.verify_uploaded(session, receipt)
            atomic_json(ROOT/'publication-receipts'/ (item['id']+'.json'),receipt)
            if receipt['publicly_posted']:
                topics.mark_published(registry_path,item['id'],receipt)
            # Nonpublic/processing receipts prevent blind reupload without claiming public success.
            receipts.append(receipt)
    finally:
        session.close()
    return {'status':'complete' if all(r['publicly_posted'] for r in receipts) else 'uploaded_status_pending',
            'receipts':receipts}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--request',required=True)
    p.add_argument('--expected-channel-id',default=os.environ.get('IFVERSE_ANIME_CHANNEL_ID'))
    p.add_argument('--publish',action='store_true');args=p.parse_args()
    try:
        result=run(args.request,args.expected_channel_id,args.publish)
        print(json.dumps(result));return 0 if result['status'] in ('planned','complete') else 2
    except Exception as exc:
        # Never echo SDK/provider exceptions that can contain tokens or session URLs.
        message=str(exc) if isinstance(exc,(publish.UploadError,ValueError)) else 'Check private configuration and saved receipts; do not blindly reupload'
        print(json.dumps({'status':'blocked','error_type':type(exc).__name__,'message':message}));return 1


if __name__=='__main__':
    sys.exit(main())
