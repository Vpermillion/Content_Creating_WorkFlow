"""Save one compact batch index and topic outcomes; metadata never rerenders."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.render_anime_batch import load_batch,result_branch
from whatif.topics import script_hash

SOURCE_BRANCH='codex/ifverse-workflow'
REGISTRY='channels/ifverse_anime-topics.json'


def git(*args,input=None,env=None):
    return subprocess.check_output(['git',*args],cwd=ROOT,input=input,env=env)


def collect(batch):
    records=[]
    for episode in batch['episodes']:
        branch=result_branch(batch,episode)
        found=git('ls-remote','origin','refs/heads/'+branch).decode().strip()
        if not found:
            records.append({'id':episode['id'],'status':'result_missing','branch':branch});continue
        commit=found.split()[0]
        git('fetch','--quiet','--depth=1','origin','refs/heads/'+branch)
        result=json.loads(git('show',commit+':artifacts/'+episode['id']+'/batch-result.json'))
        if result['id']!=episode['id'] or result['script_sha256']!=script_hash(episode['scenes']):
            raise ValueError('Saved result identity/script differs from the request')
        records.append({**result,'branch':branch,'commit':commit})
    return records


def merge_outcomes(registry,records):
    for result in records:
        entry=next(e for e in registry['topics'] if e['id']==result['id'])
        if entry['state']=='published' or entry.get('video_id'):continue
        if entry.get('sound_repair') and result.get('branch') != entry.get('result_branch'):continue
        if result.get('script_sha256')!=entry['script_sha256']:
            continue  # A later requested script revision must not be replaced.
        if result['status']=='success':
            entry.update(state='rendered',video_sha256=result['video_sha256'],
                         duration_seconds=result['duration_seconds'],result_branch=result['branch'],
                         result_commit=result['commit'],publication_clearance='not_established',
                         result_receipt='artifacts/'+entry['id']+'/batch-result.json')
        elif entry['state']!='rendered':
            entry.update(state='render_failed',last_error=result.get('error','Saved result not available'))
    return registry


def index_text(registry,goal):
    text=['# Ten Ifverse Anime Shorts — 61-second cuts','',
          'Each completed cut is 720×1280, English, with Michael narration, aligned burned-in captions and four phrase-anchored actual DubbingAI recording cues (community excerpt rights unverified). No piano is embedded; the owner will handle optional Meaningful Love - Silo music in YouTube.','',
          '**Publication:** this render job does not establish any YouTube uploads. Consult actual publication receipts and topic status. Source-use clearance and full listening/editorial approval are separate from rendering. A GitHub link is not a YouTube post.','',
          '| Topic | State | Length | Video | Posting details |','| --- | --- | --- | --- | --- |']
    for episode in goal['episodes']:
        entry=next(e for e in registry['topics'] if e['id']==episode['id'])
        base='https://github.com/Vpermillion/Content_Creating_WorkFlow/blob/'+entry.get('result_branch','codex/results/'+entry['id']+'-r2')+'/artifacts/'+entry['id']+'/'
        ready=entry['state'] in ('rendered','published','uploaded_status_pending')
        video='[MP4]('+base+entry.get('video_path','production/sound-effects/video-sfx.mp4')+')' if ready else 'Pending'
        packet='[Title, description, hashtags and settings]('+base+entry.get('posting_packet_path','post-settings.json')+')' if ready else 'Pending'
        duration=str(entry.get('duration_seconds','—'))+' s' if ready else '—'
        text.append('| '+episode['title'].replace('|','/')+' | '+entry['state']+' | '+duration+' | '+video+' | '+packet+' |')
    text += ['', 'Every result branch also preserves its script, English SRT, exact waveform/caption/source/mix receipts and a contact sheet. Earlier attempts remain versioned. The first 75-second engineering batch exposed a final-cue boundary issue and overly long scripts; the final scripts were shortened for 61 seconds and use frozen footage. Subsequent visual repairs retain the completed voice and caption timing.', '',
             '[Persistent topic registry](../channels/ifverse_anime-topics.json) · [Batch request](../batch-requests/ifverse-anime-ten-61s-20261103-01.json) · [Automation and upload setup](AUTOMATION.md)', '']
    return '\n'.join(text)


def finalize(relative,push=False):
    batch=load_batch(relative);records=collect(batch)
    goal_path=ROOT/batch.get('goal_batch',relative)
    if not goal_path.resolve().is_relative_to(ROOT/'batch-requests'):raise ValueError('Invalid goal batch path')
    goal=json.loads(goal_path.read_text())
    git('fetch','--quiet','--depth=1','origin','refs/heads/'+SOURCE_BRANCH)
    parent=git('rev-parse','FETCH_HEAD').decode().strip()
    registry=merge_outcomes(json.loads(git('show',parent+':'+REGISTRY)),records)
    summary={'id':batch['id'],'results':records,'uploaded_by_this_job':False,
             'publication_clearance':'not_established','publishing_connection':'not_assessed_by_render_job'}
    files={REGISTRY:(json.dumps(registry,indent=2)+'\n').encode(),
           'docs/BATCH_61S.md':index_text(registry,goal).encode(),
           'artifacts/batches/'+batch['id']+'/summary.json':(json.dumps(summary,indent=2)+'\n').encode()}
    for name,data in files.items():
        path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    if not push:return summary
    fd,index=tempfile.mkstemp(prefix='batch-summary-index-');os.close(fd);os.unlink(index)
    env=os.environ.copy();env['GIT_INDEX_FILE']=index
    env.update(GIT_AUTHOR_NAME='github-actions[bot]',GIT_AUTHOR_EMAIL='41898282+github-actions[bot]@users.noreply.github.com',
               GIT_COMMITTER_NAME='github-actions[bot]',GIT_COMMITTER_EMAIL='41898282+github-actions[bot]@users.noreply.github.com')
    try:
        git('read-tree',parent,env=env)
        for name,data in files.items():
            blob=git('hash-object','-w','--stdin',input=data).decode().strip()
            git('update-index','--add','--cacheinfo','100644,'+blob+','+name,env=env)
        tree=git('write-tree',env=env).decode().strip()
        commit=git('commit-tree',tree,'-p',parent,env=env,input=b'Record batch results and persistent topic history\n').decode().strip()
        subprocess.run(['git','push','origin',commit+':refs/heads/'+SOURCE_BRANCH],cwd=ROOT,check=True)
    finally:
        if Path(index).exists():Path(index).unlink()
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--batch',required=True);p.add_argument('--save-to-github',action='store_true');a=p.parse_args()
    summary=finalize(a.batch,a.save_to_github)
    print(json.dumps({'batch':summary['id'],'outcomes':{r['id']:r['status'] for r in summary['results']},'uploaded':False}))
