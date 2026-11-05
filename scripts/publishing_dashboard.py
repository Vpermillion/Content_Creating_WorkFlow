"""Schedule reviewed Ifverse shorts through Zernio and track each destination."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'private' / 'publishing'
PLATFORMS = ('youtube', 'facebook', 'tiktok', 'instagram', 'snapchat')
LIMITS = {'youtube': (3, 180), 'facebook': (3, 60), 'tiktok': (3, 180),
          'instagram': (3, 180), 'snapchat': (6, 60)}
ID = re.compile(r'[0-9a-f]{24}')


class PublishingError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PublishingError(message)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def https(url):
    parsed = urlsplit(url)
    return parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password


def request(url, method, headers, body=None):
    require(https(url), 'Expected an HTTPS provider URL')
    with build_opener(NoRedirect()).open(Request(url, body, headers, method=method), timeout=90) as response:
        return response.read(2_000_000)


class Provider:
    def __init__(self):
        self.key = os.environ.get('ZERNIO_API_KEY')
        self.profile = os.environ.get('ZERNIO_PROFILE_ID')
        require(self.key and ID.fullmatch(self.profile or ''), 'Set ZERNIO_API_KEY and ZERNIO_PROFILE_ID privately')

    def api(self, path, body=None, operation=None):
        headers = {'Authorization': f'Bearer {self.key}', 'Accept': 'application/json'}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        if operation:
            headers['Idempotency-Key'] = operation
        try:
            raw = request('https://zernio.com/api/v1/' + path, 'GET' if body is None else 'POST',
                          headers, None if body is None else json.dumps(body).encode())
        except HTTPError as error:
            raise PublishingError(f'Publishing provider returned HTTP {error.code}') from None
        return json.loads(raw)

    def accounts(self):
        query = urlencode({'profileId': self.profile, 'status': 'connected', 'limit': 50})
        rows = self.api('accounts?' + query)['accounts']
        return [{key: row.get(key) for key in ('_id', 'platform', 'username')}
                for row in rows if row.get('platform') in PLATFORMS]

    def connect(self, platform):
        url = self.api(f'connect/{platform}?' + urlencode({'profileId': self.profile}))['authUrl']
        require(https(url), 'OAuth URL is invalid')
        return url

    def upload(self, data):
        urls = self.api('media/presign', {'filename': 'reviewed-short.mp4', 'contentType': 'video/mp4',
                                          'size': len(data)})
        url = urls['uploadUrl']
        require((urlsplit(url).hostname or '').endswith('.r2.cloudflarestorage.com'),
                'Unexpected media upload host')
        request(url, 'PUT', {'Content-Type': 'video/mp4'}, data)
        require(https(urls['publicUrl']), 'Invalid hosted media URL')
        return urls['publicUrl']


def load_review(root, item):
    require(item['brand'] == 'ifverse_anime', 'This version uses the Ifverse anime topic registry')
    registry = json.loads((root / 'channels/ifverse_anime-topics.json').read_text(encoding='utf-8'))
    matches = [topic for topic in registry['topics'] if topic['id'] == item['episode']]
    require(len(matches) == 1, 'Select one episode from the topic registry')
    topic = matches[0]
    choice = topic.get('owner_topic_choice', {})
    require(topic.get('state') in ('rendered', 'published') and choice.get('status') == 'approved'
            and choice.get('selected_by') == 'owner' and choice.get('decision_reference') and choice.get('selected_at')
            and topic.get('script_sha256') and choice.get('script_sha256') == topic['script_sha256'],
            'Record the owner decision against the exact rendered script first')
    require(topic.get('video_sha256') and item['master_sha256'] == topic['video_sha256'],
            'Use the current selected master from the topic registry')
    review = item['review']
    require(review.get('source_use') == 'approved' and review.get('audiovisual') == 'approved'
            and review.get('reviewed_by') and review.get('evidence'), 'Publication review evidence is required')
    require(review.get('audience') in ('made_for_kids', 'not_made_for_kids')
            and type(review.get('synthetic_disclosure')) is bool, 'Complete audience and disclosure review')
    require(review.get('approved_video_sha256') == item['video_sha256'],
            'Approval must name the exact export hash')
    require(not any(receipt.get('platform', 'youtube') == item['platform']
                    for receipt in topic.get('publication_receipts', [])),
            'The topic registry already contains a receipt for this destination')
    return review


def read_video(root, item):
    path = (root / item['video']).resolve()
    require(path.is_relative_to(root / 'artifacts') and path.suffix.lower() == '.mp4'
            and path.is_file() and path.stat().st_size <= 100 * 1024 * 1024,
            'Use a repository artifact MP4 up to 100 MiB')
    data = path.read_bytes()
    require(len(data) <= 100 * 1024 * 1024 and hashlib.sha256(data).hexdigest() == item['video_sha256'],
            'Reviewed video hash mismatch')
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)],
                           capture_output=True, check=True, timeout=30)
    info = json.loads(probe.stdout)
    duration = float(info['format']['duration'])
    video = next((track for track in info['streams'] if track['codec_type'] == 'video'), {})
    low, high = LIMITS[item['platform']]
    require(low <= duration <= high and video.get('width', 0) >= 540
            and video['width'] * 16 == video['height'] * 9
            and any(track['codec_type'] == 'audio' for track in info['streams']),
            f'Expected a vertical {low}–{high} second export with audio')
    require(path.read_bytes() == data, 'Video changed while being inspected')
    return data, duration


def prepare(root, item, provider):
    platform = item['platform']
    account_id = item['account_id']
    require(platform in PLATFORMS and ID.fullmatch(account_id), 'Invalid platform or provider account ID')
    review = load_review(root, item)
    date = datetime.fromisoformat(item['scheduled_for'])
    require(date.utcoffset() is not None, 'Specify an ISO 8601 schedule with a UTC offset')
    caption, title = item['caption'], item['title']
    require(isinstance(title, str) and 1 <= len(title) <= 100 and isinstance(caption, str)
            and len(caption.encode()) <= (160 if platform == 'snapchat' else 2200),
            'Invalid title or caption length')
    data, duration = read_video(root, item)
    require(any(row['_id'] == account_id and row['platform'] == platform
                and row['username'] and row['username'].lstrip('@').casefold() == item['expected_username'].lstrip('@').casefold()
                for row in provider.accounts()), 'Connected account does not match the reviewed destination')
    target = {'platform': platform, 'accountId': account_id}
    payload = {'content': caption, 'platforms': [target],
               'scheduledFor': date.astimezone(timezone.utc).isoformat(), 'timezone': 'UTC'}
    if platform == 'youtube':
        target['platformSpecificData'] = {'title': title, 'visibility': 'public', 'categoryId': '24',
                                          'madeForKids': review['audience'] == 'made_for_kids',
                                          'containsSyntheticMedia': review['synthetic_disclosure']}
    if platform == 'facebook':
        target['platformSpecificData'] = {'contentType': 'reel', 'title': title}
    if platform == 'snapchat':
        target['platformSpecificData'] = {'contentType': 'spotlight'}
    if platform == 'tiktok':
        settings = item['tiktok']
        require(settings.get('content_preview_confirmed') is True and settings.get('express_consent_given') is True
                and settings.get('commercialContentType') in ('none', 'brand_organic', 'brand_content'),
                'Record the TikTok creator’s preview, express consent and disclosure decisions')
        creator = provider.api(f'accounts/{account_id}/tiktok/creator-info?mediaType=video')
        limits = creator['postingLimits']
        require(creator['creator']['canPostMore'] and duration <= limits['maxVideoDurationSec']
                and settings.get('privacy_level') in {option['value'] for option in creator['privacyLevels']},
                'The selected TikTok privacy, duration or posting allowance is unavailable')
        toggles = ('allow_comment', 'allow_duet', 'allow_stitch')
        for toggle in toggles:
            require(type(settings.get(toggle)) is bool
                    and (not settings[toggle] or limits['interactionSettings'][toggle]['enabled']),
                    f'Confirm an available TikTok setting for {toggle}')
        keys = (*toggles, 'privacy_level', 'commercialContentType', 'content_preview_confirmed', 'express_consent_given')
        payload['tiktokSettings'] = {key: settings[key] for key in keys}
        payload['tiktokSettings']['video_made_with_ai'] = review['synthetic_disclosure']
    return date, data, payload


def open_state(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS posts (
        episode TEXT, platform TEXT, account TEXT, scheduled TEXT, operation TEXT,
        provider_id TEXT, status TEXT, url TEXT, PRIMARY KEY (episode, platform)
    )""")
    return db


def record_status(db, operation, post):
    provider_id = post.get('_id', '')
    require(ID.fullmatch(provider_id), 'Provider returned no valid post ID')
    row = db.execute('SELECT * FROM posts WHERE operation = ?', (operation,)).fetchone()
    require(row and (not row['provider_id'] or row['provider_id'] == provider_id), 'Provider ID mismatch')
    targets = post.get('platforms', [])
    require(len(targets) == 1 and targets[0].get('platform') == row['platform'], 'Unexpected provider destination')
    target = targets[0]
    account = target.get('accountId')
    if isinstance(account, dict):
        account = account.get('_id')
    require(account == row['account'], 'Provider response refers to a different account')
    url = target.get('platformPostUrl')
    status = target.get('status') or post.get('status') or 'unknown'
    if status == 'pending' and post.get('status') == 'scheduled':
        status = 'scheduled'
    if status == 'published' and not (url and https(url)):
        status = 'published_link_pending'
    with db:
        db.execute('UPDATE posts SET provider_id=?, status=?, url=? WHERE operation=?',
                   (provider_id, status, url if url and https(url) else None, operation))


def schedule(db, root, item, provider):
    date, data, payload = prepare(root, item, provider)
    require(date > datetime.now(timezone.utc) + timedelta(minutes=5), 'Schedule at least five minutes ahead')
    operation = str(uuid4())
    try:
        with db:
            db.execute('INSERT INTO posts VALUES (?, ?, ?, ?, ?, NULL, ?, NULL)',
                       (item['episode'], item['platform'], item['account_id'],
                        payload['scheduledFor'], operation, 'uploading_media'))
    except sqlite3.IntegrityError:
        raise PublishingError('A job already exists for this episode and account. Reconcile it before any retry.') from None
    try:
        payload['mediaItems'] = [{'type': 'video', 'url': provider.upload(data)}]
        require(date > datetime.now(timezone.utc) + timedelta(minutes=5), 'The scheduled time is now too close')
    except Exception:
        with db:
            db.execute('DELETE FROM posts WHERE operation=?', (operation,))
        raise
    with db:
        db.execute('UPDATE posts SET status=? WHERE operation=?', ('submission_needs_reconciliation', operation))
    post = provider.api('posts', payload, operation)['post']
    record_status(db, operation, post)
    return post['_id']


def dashboard(db, path, accounts):
    def table(headers, rows):
        head = ''.join(f'<th>{escape(label)}</th>' for label in headers)
        body = ''.join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows)
        return f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
    connections = []
    for platform in PLATFORMS:
        names = [row['username'] or row['_id'] for row in accounts or [] if row['platform'] == platform]
        status = ', '.join(names) if names else ('Not checked' if accounts is None else 'No connected account')
        connections.append((escape(platform.title()), escape(status)))
    queue = []
    for row in db.execute('SELECT * FROM posts ORDER BY scheduled, platform'):
        link = f'<a href="{escape(row["url"])}">Open post</a>' if row['url'] else '—'
        local = datetime.fromisoformat(row['scheduled']).astimezone(timezone(timedelta(hours=8)))
        queue.append(tuple(escape(str(value)) for value in (
            row['episode'], row['platform'], local.strftime('%Y-%m-%d %H:%M'),
            row['status'].replace('_', ' '), row['provider_id'] or row['operation'])) + (link,))
    accounts_table = table(('Destination', 'Account'), connections)
    queue_table = table(('Episode', 'Destination', 'Ulaanbaatar time', 'Status', 'Reference', 'Post'), queue)
    path.write_text(f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport"
content="width=device-width,initial-scale=1"><title>Ifverse Publishing</title><style>
body{{background:#10151e;color:#edf1f9;font:16px system-ui;margin:3rem auto;max-width:1050px;padding:0 1rem}}
h1{{font-size:2.5rem}} h2{{margin-top:2rem}} p{{color:#aebed2}} table{{border-collapse:collapse;width:100%}}
th,td{{text-align:left;padding:.75rem;border-bottom:1px solid #354456}} a{{color:#7cd8ff}}
section{{overflow:auto}} code{{color:#b1e6d5}}</style><main><h1>Ifverse Publishing</h1>
<p>One queue for reviewed short-form videos. Refresh after account consent or provider updates.</p>
<h2>Connections</h2>{accounts_table}<h2>Publishing queue</h2><section>{queue_table}</section>
<p>{'' if queue else 'No jobs have been scheduled.'}</p></main></html>''', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('accounts')
    connect = commands.add_parser('connect')
    connect.add_argument('platform', choices=PLATFORMS)
    submit = commands.add_parser('schedule')
    submit.add_argument('manifest', type=Path, help='One reviewed job or a list of up to five destinations')
    submit.add_argument('--submit', action='store_true', required=True, help='Authorize the reviewed media transfer')
    report = commands.add_parser('dashboard')
    report.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'accounts':
            print(json.dumps(Provider().accounts(), indent=2))
        elif args.command == 'connect':
            print(Provider().connect(args.platform))
        else:
            with open_state(STATE / 'posts.sqlite3') as db:
                if args.command == 'schedule':
                    items = json.loads(args.manifest.read_text(encoding='utf-8'))
                    if isinstance(items, dict):
                        items = [items]
                    require(isinstance(items, list) and 1 <= len(items) <= 5
                            and len({item['episode'] for item in items}) == 1
                            and len({item['platform'] for item in items}) == len(items),
                            'Supply one episode with up to five distinct destinations')
                    provider = Provider()
                    failed = False
                    for item in items:
                        try:
                            print(json.dumps({'platform': item['platform'],
                                              'id': schedule(db, ROOT, item, provider)}))
                        except PublishingError as error:
                            failed = True
                            print(json.dumps({'platform': item['platform'], 'blocked': str(error)}))
                        except (OSError, KeyError, TypeError, ValueError, subprocess.SubprocessError):
                            failed = True
                            print(json.dumps({'platform': item['platform'], 'blocked': 'Check local files and reconcile provider state'}))
                    dashboard(db, STATE / 'dashboard.html', None)
                    return int(failed)
                else:
                    accounts = None
                    if args.refresh:
                        provider = Provider()
                        accounts = provider.accounts()
                        for row in db.execute('SELECT operation,provider_id FROM posts WHERE provider_id IS NOT NULL'):
                            try:
                                post = provider.api('posts/' + row['provider_id'])['post']
                                record_status(db, row['operation'], post)
                            except (ValueError, OSError, KeyError, TypeError):
                                print(f'Could not refresh post {row["provider_id"]}', file=sys.stderr)
                    path = STATE / 'dashboard.html'
                    dashboard(db, path, accounts)
                    print(path)
    except PublishingError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, KeyError, TypeError, ValueError, subprocess.SubprocessError, sqlite3.Error):
        print('Publishing request failed. Check private configuration and reconcile any existing job.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
