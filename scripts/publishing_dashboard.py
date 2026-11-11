"""Local, subscription-free Ifverse publishing queue using platform APIs."""
import argparse
from contextlib import closing
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
import time
from urllib.parse import urlsplit

if __package__:
    from . import publishing_accounts as accounts
    from . import publishing_direct as direct
else:
    import publishing_accounts as accounts
    import publishing_direct as direct

PublishingError = direct.PublishingError
require = direct.require

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
STATE = ROOT / 'private' / 'publishing'
PLATFORMS = accounts.PLATFORMS
LIMITS = {'facebook': (4, 60), 'instagram': (3, 180), 'snapchat': (6, 60), 'tiktok': (3, 180)}
EPISODE = re.compile(r'[a-z0-9][a-z0-9_-]{0,100}')


def https(url):
    parsed = urlsplit(url)
    return parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password


def load_review(root, item):
    require(accounts.BRAND.fullmatch(item['brand']), 'Invalid brand')
    registry = json.loads((root / 'channels' / f'{item["brand"]}-topics.json').read_text(encoding='utf-8'))
    matches = [topic for topic in registry['topics'] if topic['id'] == item['episode']]
    require(len(matches) == 1, 'Select one episode from the topic registry')
    topic = matches[0]
    choice = topic.get('owner_topic_choice', {})
    require(topic.get('state') in ('rendered', 'uploaded_status_pending', 'published') and choice.get('status') == 'approved'
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
                    and (receipt.get('account_id') or receipt.get('verified_channel_id') or item['account_id'])
                    == item['account_id']
                    for receipt in topic.get('publication_receipts', [])),
            'The topic registry already contains a receipt for this destination')
    require(item['platform'] != 'youtube' or not topic.get('video_id')
            or topic.get('verified_channel_id', item['account_id']) != item['account_id'],
            'The topic registry already contains a YouTube upload for this account')
    return registry, topic


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
    return data



def youtube_request(root, item):
    path = (root / item['request']).resolve()
    require(path.is_relative_to(root / 'publish-requests') and path.is_file()
            and path.suffix == '.json' and path.stat().st_size <= 250_000, 'Use a local YouTube publish request')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == item['request_sha256'], 'YouTube request changed')
    request = json.loads(raw)
    require(request.get('items') and len(request['items']) == 1
            and request['items'][0]['id'] == item['episode'],
            'The YouTube request must target only the scheduled episode')
    return path


def validate(root, item):
    require(accounts.BRAND.fullmatch(item['brand']) and EPISODE.fullmatch(item['episode'])
            and item['platform'] in PLATFORMS, 'Invalid Ifverse episode or destination')
    if 'account' in item:
        accounts.resolve(root, item)
        require(item.get('owner_requested_publication') is True, 'Record the owner’s publishing authorization')
    else:
        require(item['brand'] == 'ifverse_anime', 'Choose a registered account for this brand')
    date = datetime.fromisoformat(item['scheduled_for'])
    require(date.utcoffset() is not None, 'Specify an ISO 8601 schedule with UTC offset')
    require(isinstance(item['account_id'], str) and re.fullmatch(r'[A-Za-z0-9_-]{1,100}', item['account_id']),
            'Specify the verified platform account ID or TikTok handle without @')
    platform = item['platform']
    if platform == 'youtube' and 'account' not in item:
        youtube_request(root, item)
    else:
        load_review(root, item)
        caption, title = item['caption'], item['title']
        require(isinstance(title, str) and 1 <= len(title) <= 100 and isinstance(caption, str)
                and len(caption.encode()) <= {'snapchat': 160, 'youtube': 5000}.get(platform, 2200),
                'Invalid title or caption length')
    return date.astimezone(timezone.utc).isoformat()


def open_state(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    create = """CREATE TABLE IF NOT EXISTS posts (
        episode TEXT NOT NULL, platform TEXT NOT NULL, account TEXT NOT NULL,
        scheduled TEXT NOT NULL, manifest TEXT NOT NULL, status TEXT NOT NULL,
        checkpoint TEXT, checkpoint_id TEXT, provider_id TEXT, url TEXT,
        PRIMARY KEY (episode, platform, account)
    )"""
    with db:
        db.execute('BEGIN IMMEDIATE')
        columns = db.execute('PRAGMA table_info(posts)').fetchall()
        legacy = columns and next(c['pk'] for c in columns if c['name'] == 'account') == 0
        if legacy:
            db.execute('ALTER TABLE posts RENAME TO posts_legacy')
        db.execute(create)
        if legacy:
            db.execute('INSERT INTO posts SELECT * FROM posts_legacy')
            db.execute('DROP TABLE posts_legacy')
    return db


def enqueue(db, root, items):
    if isinstance(items, dict):
        items = [items]
    require(isinstance(items, list) and 1 <= len(items) <= 25
            and len({item['episode'] for item in items}) == 1
            and len({item['brand'] for item in items}) == 1
            and len({(item['platform'], item['account_id']) for item in items}) == len(items),
            'Supply one episode with up to 25 distinct platform accounts')
    rows = [(item['episode'], item['platform'], item['account_id'], validate(root, item), json.dumps(item))
            for item in items]
    try:
        with db:
            db.executemany("""INSERT INTO posts (episode, platform, account, scheduled, manifest, status)
                              VALUES (?, ?, ?, ?, ?, 'queued')""", rows)
    except sqlite3.IntegrityError:
        raise PublishingError('A destination already has a job for this episode') from None
    return len(rows)


def youtube(root, item):
    require(item['account_id'] == os.environ.get('IFVERSE_ANIME_CHANNEL_ID'),
            'Configure the intended YouTube channel before publishing')
    path = youtube_request(root, item)
    proc = subprocess.run([sys.executable, str(root / 'scripts/youtube_upload_batch.py'),
                           '--request', str(path), '--expected-channel-id', item['account_id'], '--publish'],
                          cwd=root, capture_output=True, timeout=1800)
    try:
        receipt, = json.loads(proc.stdout)['receipts']
        require(proc.returncode in (0, 2), 'YouTube upload needs reconciliation')
        require(receipt['verified_channel_id'] == item['account_id'], 'Unexpected YouTube receipt')
        video = receipt['video_id']
        require(re.fullmatch(r'[A-Za-z0-9_-]{11}', video), 'Invalid YouTube video ID')
    except (KeyError, TypeError, ValueError):
        raise PublishingError('Check the existing YouTube upload journal before retrying') from None
    status = 'published' if receipt.get('publicly_posted') is True else 'submitted'
    return status, video, 'https://www.youtube.com/watch?v=' + video


def named_youtube_preflight(root, item):
    from whatif import youtube_publish

    registry, _ = load_review(root, item)
    return youtube_publish.preflight({
        'id': item['episode'], 'video': item['video'], 'video_sha256': item['video_sha256'],
        'publication_clearance': 'cleared', 'review': item['review'],
        'metadata': {'title': item['title'], 'description': item['caption'], 'tags': item.get('tags', [])},
    }, root, registry)


def youtube_result(session, receipt):
    from whatif import youtube_publish

    receipt = youtube_publish.verify_uploaded(session, receipt)
    status = 'published' if receipt['publicly_posted'] else 'submitted'
    if receipt['provider_upload_status'] in ('deleted', 'failed', 'rejected'):
        status = 'failed'
    return status, receipt['video_id'], receipt['url']


def named_youtube(root, item, session, prepared, checkpoint):
    from whatif import youtube_publish

    path, fingerprint, metadata_hash, body = prepared
    state = youtube_publish.private_directory(root / 'private/youtube-upload-state') / item['account_id']
    receipt = youtube_publish.upload(session, item['episode'], path, fingerprint, metadata_hash, body,
                                     item['account_id'], state)
    checkpoint('video_id', receipt['video_id'])
    return youtube_result(session, receipt)


def update_result(db, row, status, resource, url):
    if url and url.startswith('/') and not url.startswith('//') and row['platform'] == 'facebook':
        url = 'https://www.facebook.com' + url
    with db:
        db.execute('UPDATE posts SET status=?, provider_id=?, url=? WHERE episode=? AND platform=? AND account=?',
                   (status, resource, url if url and https(url) else None,
                    row['episode'], row['platform'], row['account']))


def run_due(db, root, now):
    rows = list(db.execute("SELECT * FROM posts WHERE status IN ('queued','processing') AND scheduled<=? "
                           "ORDER BY scheduled, platform", (now.isoformat(),)))
    results = []
    for row in rows:
        key = (row['episode'], row['platform'], row['account'])
        item = json.loads(row['manifest'])
        platform = row['platform']
        alias = item.get('account')
        session = None
        result_info = {'platform': platform, 'episode': row['episode'], 'account_id': row['account']}
        try:
            validate(root, item)
            data = read_video(root, item) if platform != 'youtube' and row['status'] == 'queued' else None
            binding = accounts.resolve(root, item) if alias else None
            if platform in ('facebook', 'instagram', 'snapchat'):
                provider = accounts.provider(root, alias, binding) if alias else direct.client(platform)
                provider.verify(row['account'])
            elif platform == 'youtube' and alias:
                prepared = named_youtube_preflight(root, item)
                session = accounts.youtube_session(root, alias, binding)
            elif platform == 'youtube':
                require(item['account_id'] == os.environ.get('IFVERSE_ANIME_CHANNEL_ID'),
                        'Configure the intended YouTube channel before publishing')
                subprocess.run([sys.executable, '-m', 'whatif.youtube_publish', 'verify',
                                '--expected-channel-id', row['account']], cwd=root, capture_output=True,
                               check=True, timeout=60)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, ImportError, subprocess.SubprocessError):
            results.append({**result_info, 'status': 'awaiting_setup_or_review'})
            continue

        def checkpoint(phase, resource):
            with db:
                db.execute('UPDATE posts SET checkpoint=?, checkpoint_id=? WHERE episode=? AND platform=? AND account=?',
                           (phase, resource, *key))

        try:
            with db:
                claimed = db.execute("UPDATE posts SET status='working' WHERE episode=? AND platform=? AND account=? AND status=?",
                                     (*key, row['status'])).rowcount
            if not claimed:
                continue
            if platform == 'tiktok':
                result = ('manual_action_required', None, 'https://www.tiktok.com/tiktokstudio/upload')
            elif session:
                result = named_youtube(root, item, session, prepared, checkpoint)
            elif platform == 'youtube':
                result = youtube(root, item)
            elif row['status'] == 'processing':
                result = provider.finish_instagram(row['provider_id'], checkpoint)
            else:
                result = provider.publish(item, data, checkpoint)
            update_result(db, row, *result)
            results.append({**result_info, 'status': result[0]})
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, ImportError, subprocess.SubprocessError):
            with db:
                db.execute("UPDATE posts SET status='needs_reconciliation' WHERE episode=? AND platform=? AND account=?", key)
            results.append({**result_info, 'status': 'needs_reconciliation'})
        finally:
            if session:
                session.close()
    return results


def refresh(db, root=ROOT):
    for row in list(db.execute("SELECT * FROM posts WHERE status='submitted'")):
        try:
            item = json.loads(row['manifest'])
            alias = item.get('account')
            binding = accounts.resolve(root, item) if alias else None
            if row['platform'] == 'youtube':
                if alias:
                    with accounts.youtube_session(root, alias, binding) as session:
                        update_result(db, row, *youtube_result(session, {
                            'video_id': row['provider_id'], 'verified_channel_id': row['account'], 'url': row['url'],
                        }))
                continue
            provider = accounts.provider(root, alias, binding) if alias else direct.client(row['platform'])
            provider.verify(row['account'])
            status, url = provider.status(row['provider_id'])
            update_result(db, row, status, row['provider_id'], url)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, ImportError):
            print(f'Could not verify {row["episode"]} on {row["platform"]}', file=sys.stderr)


def dashboard(db, path, bindings):
    def table(headers, rows):
        head = ''.join(f'<th>{escape(label)}</th>' for label in headers)
        body = ''.join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows)
        return f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
    connections = [tuple(escape(value) for value in (alias, row['brand'], row['platform'].title(),
                    row.get('handle') or row['account_id'])) for alias, row in sorted((bindings or {}).items())]
    queue = []
    for row in db.execute('SELECT * FROM posts ORDER BY scheduled, platform'):
        label = 'Open TikTok Studio' if row['platform'] == 'tiktok' else 'Open post'
        link = f'<a href="{escape(row["url"])}">{label}</a>' if row['url'] else '—'
        local = datetime.fromisoformat(row['scheduled']).astimezone(timezone(timedelta(hours=8)))
        queue.append(tuple(escape(str(value)) for value in (
            row['episode'], row['platform'], json.loads(row['manifest']).get('account', row['account']),
            local.strftime('%Y-%m-%d %H:%M'),
            row['status'].replace('_', ' '), row['provider_id'] or row['checkpoint_id'] or '—')) + (link,))
    accounts_table = table(('Alias', 'Brand', 'Platform', 'Account'), connections)
    queue_table = table(('Episode', 'Platform', 'Account', 'Ulaanbaatar time', 'Status', 'Reference', 'Post'), queue)
    path.write_text(f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport"
content="width=device-width,initial-scale=1"><title>Ifverse Publishing</title><style>
body{{background:#10151e;color:#edf1f9;font:16px system-ui;margin:3rem auto;max-width:1050px;padding:0 1rem}}
h1{{font-size:2.5rem}} h2{{margin-top:2rem}} p{{color:#aebed2}} table{{border-collapse:collapse;width:100%}}
th,td{{text-align:left;padding:.75rem;border-bottom:1px solid #354456}} a{{color:#7cd8ff}}
section{{overflow:auto}} code{{color:#b1e6d5}}</style><main><h1>Ifverse Publishing</h1>
<p>One queue for reviewed short-form videos. Times are local to Ulaanbaatar. Run the repository worker to process due jobs.</p>
<h2>Connections</h2>{accounts_table}<h2>Publishing queue</h2><section>{queue_table}</section>
<p>{'' if queue else 'No jobs have been scheduled.'}</p></main></html>''', encoding='utf-8')



def verify(platform, account):
    if platform == 'youtube':
        subprocess.run([sys.executable, '-m', 'whatif.youtube_publish', 'verify',
                        '--expected-channel-id', account], cwd=ROOT, check=True)
    elif platform == 'tiktok':
        print('TikTok Studio is a manual destination for this private workflow.')
    else:
        print(json.dumps({'platform': platform, 'account': account,
                          'identity': direct.client(platform).verify(account)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('verify')
    check.add_argument('platform', choices=PLATFORMS)
    check.add_argument('account')
    by_alias = commands.add_parser('verify-account')
    by_alias.add_argument('alias')
    commands.add_parser('accounts')
    queue = commands.add_parser('queue')
    queue.add_argument('manifest', type=Path)
    commands.add_parser('run-due')
    commands.add_parser('watch')
    report = commands.add_parser('dashboard')
    report.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'accounts':
            print(json.dumps(accounts.registry(ROOT), indent=2))
            return 0
        if args.command == 'verify-account':
            binding = accounts.registry(ROOT).get(args.alias)
            require(binding is not None, 'Choose a registered account alias')
            platform = binding['platform']
            if platform == 'youtube':
                with accounts.youtube_session(ROOT, args.alias, binding):
                    pass
            elif platform != 'tiktok':
                accounts.provider(ROOT, args.alias, binding).verify(binding['account_id'])
            print(json.dumps({'account': args.alias, 'status': 'manual' if platform == 'tiktok' else 'verified'}))
            return 0
        if args.command == 'verify':
            verify(args.platform, args.account)
            return 0
        with closing(open_state(STATE / 'direct-posts.sqlite3')) as db:
            if args.command == 'queue':
                require(args.manifest.stat().st_size <= 250_000, 'Manifest is too large')
                print(f'Queued {enqueue(db, ROOT, json.loads(args.manifest.read_text(encoding="utf-8-sig")))} destination(s)')
            elif args.command in ('watch', 'run-due'):
                while True:
                    for result in run_due(db, ROOT, datetime.now(timezone.utc)):
                        print(json.dumps(result), flush=True)
                    refresh(db)
                    dashboard(db, STATE / 'dashboard.html', accounts.registry(ROOT))
                    if args.command == 'run-due':
                        return 0
                    time.sleep(60)
            else:
                if args.refresh:
                    refresh(db)
                path = STATE / 'dashboard.html'
                dashboard(db, path, accounts.registry(ROOT))
                print(path)
    except PublishingError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, KeyError, TypeError, ValueError, RuntimeError, ImportError, subprocess.SubprocessError, sqlite3.Error):
        print('Publishing command failed. Check private configuration and saved job state.', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == '__main__':
    sys.exit(main())
