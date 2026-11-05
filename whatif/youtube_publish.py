"""Resumable YouTube uploads with verified channel identity and private journals.

No upload occurs without an explicitly cleared manifest and --publish. The old
read-only connector is unchanged. Provider errors and session URLs stay private.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from . import media, youtube as yt
from .store import digest, identifier

UPLOAD_SCOPE = 'https://www.googleapis.com/auth/youtube.upload'
UPLOAD_URL = 'https://www.googleapis.com/upload/youtube/v3/videos'
CHUNK_BYTES = 2 * 1024 * 1024
VIDEO_ID = re.compile(r'[A-Za-z0-9_-]{11}\Z')


class UploadError(RuntimeError):
    pass


def private_directory(path):
    path = Path(path)
    if path.is_symlink():
        raise UploadError('Private state directory must not be a symlink')
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    if path.stat().st_mode & 0o077:
        raise UploadError('Private upload state requires directory mode 0700')
    return path


def require_upload_scope(credentials):
    needed = [yt.READ_SCOPE, UPLOAD_SCOPE]
    granted = getattr(credentials, 'granted_scopes', None)
    if not credentials.has_scopes(needed) or (granted is not None and not set(needed).issubset(granted)):
        raise UploadError('Read-only consent cannot upload; grant youtube.readonly and youtube.upload')


def connect(store, client_file, expected_id):
    yt.require_channel_id(expected_id)
    config = yt.client_config(client_file)
    Flow, _, _, Session = yt.sdk()
    with store.lock('ifverse-anime'):
        if store.path('ifverse-anime').exists():
            raise UploadError('Connection exists; preserve it and verify it before reconnecting')
        flow = Flow.from_client_config(config, scopes=[yt.READ_SCOPE, UPLOAD_SCOPE], autogenerate_code_verifier=True)
        credentials = flow.run_local_server(host='127.0.0.1', port=8765, open_browser=False,
            timeout_seconds=300, access_type='offline', prompt='consent select_account',
            authorization_prompt_message='Open this Google consent URL on the machine running this command:\n{url}',
            success_message='Consent received. Return to the terminal.')
        require_upload_scope(credentials)
        channel = yt.select_channel(yt.owned_channels(credentials, Session), expected_id=expected_id)
        if yt.normalized_handle(channel.get('handle', '')) != 'ifverse_anime' or not credentials.refresh_token:
            raise UploadError('Expected ifverse_anime with offline authorization; nothing saved')
        record = {'schema_version': 1, 'connection': 'ifverse-anime', 'channel': channel,
                  'verified_at': yt.now(), 'credentials': json.loads(credentials.to_json())}
        store.save('ifverse-anime', record)
    return {'status': 'upload_connection_saved', 'channel_id': channel['id'], 'handle': channel['handle']}


def verified_session(store, expected_id):
    yt.require_channel_id(expected_id)
    _, Credentials, Request, Session = yt.sdk()
    with store.lock('ifverse-anime'):
        record = store.load('ifverse-anime')
        if record['channel']['id'] != expected_id:
            raise UploadError('Saved connection belongs to a different channel')
        credentials = Credentials.from_authorized_user_info(record['credentials'])
        require_upload_scope(credentials)
        if not credentials.valid:
            credentials.refresh(Request())
        channel = yt.select_channel(yt.owned_channels(credentials, Session), expected_id=expected_id)
        if yt.normalized_handle(channel.get('handle', '')) != 'ifverse_anime':
            raise UploadError('Verified channel is not @ifverse_anime')
        record.update(channel=channel, verified_at=yt.now(), credentials=json.loads(credentials.to_json()))
        store.save('ifverse-anime', record)
    return Session(credentials)


def preflight(item, root, registry):
    """Actual source/editorial decisions must be supplied, never inferred from FFmpeg."""
    identifier(item['id'])
    matches = [t for t in registry['topics'] if t['id'] == item['id']]
    if len(matches) != 1:
        raise UploadError('Episode must have one durable topic reservation')
    topic = matches[0]
    review = item.get('review', {})
    if item.get('publication_clearance') != 'cleared' or review.get('source_use') != 'approved' or review.get('audiovisual') != 'approved':
        raise UploadError('Source-use and actual audiovisual review are pending')
    if not review.get('reviewed_by') or not review.get('evidence'):
        raise UploadError('Record the real reviewer and evidence; do not invent review')
    if review.get('audience') not in ('not_made_for_kids', 'made_for_kids') or type(review.get('synthetic_disclosure')) is not bool:
        raise UploadError('Audience and synthetic-disclosure decisions are required')
    root = Path(root).resolve(); video = (root / item['video']).resolve()
    if not video.is_relative_to(root / 'artifacts') or not video.is_file():
        raise UploadError('Video must be a completed artifact under this repository')
    fingerprint = digest(video)
    if fingerprint != item.get('video_sha256') or fingerprint != topic.get('video_sha256'):
        raise UploadError('Manifest, topic registry and actual video must have the same SHA-256')
    metadata = item['metadata']
    title, description = metadata.get('title'), metadata.get('description')
    if not isinstance(title, str) or not 1 <= len(title) <= 100 or any(x in title for x in '<>\n\r'):
        raise UploadError('Invalid upload title')
    if not isinstance(description, str) or len(description.encode()) > 5000 or any(c in description for c in '<>'):
        raise UploadError('Invalid upload description')
    probe = media.probe(video); duration = float(probe['format']['duration'])
    track = next((s for s in probe['streams'] if s['codec_type'] == 'video'), {})
    if not 60 <= duration <= 180 or track.get('width', 0) * 16 != track.get('height', 0) * 9 or not track:
        raise UploadError('Upload must be a vertical Short of at least 60 and at most 180 seconds')
    if not any(s['codec_type'] == 'audio' for s in probe['streams']):
        raise UploadError('Short must include audio')
    media.command(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(video),'-f','null','-'])
    body = {'snippet': {'title': title, 'description': description, 'categoryId': '24', 'defaultLanguage': 'en'},
            'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': review['audience'] == 'made_for_kids',
                       'containsSyntheticMedia': review['synthetic_disclosure']}}
    tags = metadata.get('tags', [])
    if not isinstance(tags,list) or not all(isinstance(t,str) and t and not any(c in t for c in '<>\n\r') for t in tags) or sum(len(t)+3 for t in tags) > 500:
        raise UploadError('Invalid or excessive metadata tags')
    body['snippet'].update(tags=tags, defaultAudioLanguage='en')
    metadata_hash = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return video, fingerprint, metadata_hash, body


def checked_session_url(url):
    u = urlsplit(url)
    if u.scheme != 'https' or u.hostname != 'www.googleapis.com' or u.port not in (None, 443) or u.username or u.password or u.fragment or u.path != '/upload/youtube/v3/videos':
        raise UploadError('Unexpected resumable-upload endpoint; no media sent')
    return url


def completed(response, state, save):
    try:
        value = response.json()
        video_id = value['id']
        if not VIDEO_ID.fullmatch(video_id) or value['snippet']['channelId'] != state['verified_channel_id']:
            raise ValueError('Identity mismatch')
        privacy = value['status']['privacyStatus']
        if privacy not in ('private', 'public', 'unlisted'):
            raise ValueError('Unknown privacy')
    except Exception:
        state['state'] = 'upload_unknown'; save(state)
        raise UploadError('Final response could not be verified; reconcile channel before retrying') from None
    state.update(state='complete', video_id=video_id, actual_privacy=privacy,
                 provider_upload_status=value['status'].get('uploadStatus', 'unknown'),
                 published_at=datetime.now(timezone.utc).isoformat())
    state.pop('session_url', None); save(state)
    return public_receipt(state)


def public_receipt(state):
    return {k: state[k] for k in ('id', 'video_id', 'video_sha256', 'metadata_sha256', 'verified_channel_id',
                                  'actual_privacy', 'published_at', 'provider_upload_status') if k in state} | {
        'publicly_posted': state.get('actual_privacy') == 'public' and state.get('provider_upload_status') == 'processed',
        'url': 'https://www.youtube.com/shorts/' + state['video_id']}


def verify_uploaded(session, receipt):
    """Confirm status without another insert; processing/private is not public success."""
    response = session.get('https://www.googleapis.com/youtube/v3/videos',
                           params={'part': 'snippet,status', 'id': receipt['video_id']},
                           timeout=30, allow_redirects=False)
    if response.status_code != 200:
        raise UploadError('Upload has a receipt but final status check failed; do not reupload')
    items = response.json().get('items', [])
    if len(items) != 1 or items[0]['snippet']['channelId'] != receipt['verified_channel_id']:
        raise UploadError('Uploaded video channel could not be verified; do not reupload')
    status = items[0]['status']
    return {**receipt, 'actual_privacy': status['privacyStatus'],
            'provider_upload_status': status.get('uploadStatus', 'unknown'),
            'publicly_posted': status['privacyStatus'] == 'public' and status.get('uploadStatus') == 'processed'}


def upload(session, episode_id, video, video_hash, metadata_hash, body, expected_id, state_dir):
    """Resume the same session after uncertainty; never blindly start another upload."""
    identifier(episode_id); yt.require_channel_id(expected_id)
    folder = private_directory(state_dir); path = folder / (episode_id + '.json')
    with yt.file_lock(folder / ('.' + episode_id + '.lock')):
        if path.is_symlink() or (path.exists() and path.stat().st_mode & 0o077):
            raise UploadError('Private journal must be a regular owner-only file')
        def save(state): yt.atomic_json(path, state)
        total = video.stat().st_size
        state = json.loads(path.read_text()) if path.exists() else None
        expected = {'id': episode_id, 'video_sha256': video_hash, 'metadata_sha256': metadata_hash,
                    'verified_channel_id': expected_id, 'total_bytes': total}
        if state:
            if any(state.get(k) != v for k, v in expected.items()):
                raise UploadError('Saved operation has different media, metadata or channel')
            if state['state'] == 'complete':
                return public_receipt(state)
            if state['state'] in ('starting', 'initiation_unknown', 'upload_unknown') or not state.get('session_url'):
                raise UploadError('Delivery uncertain; reconcile the original operation before another upload')
            checked_session_url(state['session_url'])
            try:
                response = session.put(state['session_url'], headers={'Content-Length': '0', 'Content-Range': f'bytes */{total}'},
                                       data=b'', timeout=60, allow_redirects=False)
            except Exception:
                raise UploadError('Resume probe failed; session retained for reconciliation') from None
            if response.status_code in (200, 201):
                return completed(response, state, save)
            if response.status_code != 308:
                state['state'] = 'upload_unknown'; save(state)
                raise UploadError('Upload session unavailable; reconcile channel rather than create a duplicate')
            offset = acknowledged(response, total)
        else:
            state = {**expected, 'state': 'starting'}; save(state)
            try:
                response = session.post(UPLOAD_URL, params={'uploadType':'resumable','part':'snippet,status','notifySubscribers':'false'},
                                        json=body, headers={'X-Upload-Content-Type':'video/mp4', 'X-Upload-Content-Length':str(total)},
                                        timeout=60, allow_redirects=False)
                if response.status_code not in (200, 201):
                    raise UploadError('Provider refused upload initiation; check API quota, consent and project settings')
                state['session_url'] = checked_session_url(response.headers.get('Location', ''))
                state['state'] = 'uploading'; save(state); offset = 0
            except Exception:
                state['state'] = 'initiation_unknown'; save(state)
                raise UploadError('Upload initiation did not complete reliably; inspect private journal before retrying') from None
        with video.open('rb') as stream:
            while offset < total:
                stream.seek(offset); data = stream.read(min(CHUNK_BYTES, total-offset))
                state.update(state='chunk_inflight', next_offset=offset); save(state)
                try:
                    response = session.put(state['session_url'], data=data,
                        headers={'Content-Type':'video/mp4','Content-Length':str(len(data)),
                                 'Content-Range':f'bytes {offset}-{offset+len(data)-1}/{total}'},
                        timeout=120, allow_redirects=False)
                except Exception:
                    raise UploadError('Chunk response uncertain; resume this same session on the next attempt') from None
                if response.status_code in (200, 201):
                    return completed(response, state, save)
                if response.status_code != 308:
                    raise UploadError('Provider interrupted upload; preserve the session and reconcile before retry')
                new_offset = acknowledged(response, total)
                if new_offset <= offset or new_offset > offset + len(data):
                    raise UploadError('Invalid upload acknowledgement; session retained')
                offset = new_offset
                state.update(state='uploading', next_offset=offset); save(state)
        raise UploadError('No verified final response; resume probe required')


def acknowledged(response, total):
    value = response.headers.get('Range')
    if value is None:
        return 0
    match = re.fullmatch(r'bytes=0-(\d+)', value)
    if not match or not 0 <= int(match[1]) < total:
        raise UploadError('Invalid provider byte range')
    return int(match[1]) + 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--credentials-dir', default='private/youtube-publish')
    sub = p.add_subparsers(dest='operation', required=True)
    c = sub.add_parser('connect'); c.add_argument('--client-secrets', required=True); c.add_argument('--expected-channel-id', required=True)
    sub.add_parser('status')
    verify = sub.add_parser('verify', help='Check the saved upload authorization without posting')
    verify.add_argument('--expected-channel-id', required=True)
    args = p.parse_args(); store = yt.ConnectionStore(args.credentials_dir)
    try:
        if args.operation == 'connect':
            result = connect(store, args.client_secrets, args.expected_channel_id)
        elif args.operation == 'verify':
            with verified_session(store, args.expected_channel_id):
                result = {'status': 'verified_upload_connection', 'live_checked': True,
                          'channel_id': args.expected_channel_id, 'handle': '@ifverse_anime'}
        else:
            result = {'connections': store.cached(), 'live_checked': False,
                      'note': 'Cached identity only; publisher verifies scopes/channel at upload time'}
        print(json.dumps(result)); return 0
    except Exception:
        print(json.dumps({'status':'blocked','message':'No successful upload connection established; check private configuration. Credentials not printed.'})); return 1


if __name__ == '__main__':
    sys.exit(main())
