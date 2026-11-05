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
    from . import publishing_direct as direct
else:
    import publishing_direct as direct

PublishingError = direct.PublishingError
require = direct.require

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'private' / 'publishing'
PLATFORMS = ('youtube', 'facebook', 'tiktok', 'instagram', 'snapchat')
LIMITS = {'facebook': (4, 60), 'instagram': (3, 180), 'snapchat': (6, 60), 'tiktok': (3, 180)}
EPISODE = re.compile(r'[a-z0-9][a-z0-9_-]{0,100}')


def https(url):
    parsed = urlsplit(url)
    return parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password


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
    require(item['brand'] == 'ifverse_anime' and EPISODE.fullmatch(item['episode'])
            and item['platform'] in PLATFORMS, 'Invalid Ifverse episode or destination')
    date = datetime.fromisoformat(item['scheduled_for'])
    require(date.utcoffset() is not None, 'Specify an ISO 8601 schedule with UTC offset')
    require(isinstance(item['account_id'], str) and re.fullmatch(r'[A-Za-z0-9_-]{1,100}', item['account_id']),
            'Specify the verified platform account ID or TikTok handle without @')
    platform = item['platform']
    if platform == 'youtube':
        youtube_request(root, item)
    else:
        load_review(root, item)
        caption, title = item['caption'], item['title']
        require(isinstance(title, str) and 1 <= len(title) <= 100 and isinstance(caption, str)
                and len(caption.encode()) <= (160 if platform == 'snapchat' else 2200),
                'Invalid title or caption length')
    return date.astimezone(timezone.utc).isoformat()


def open_state(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS posts (
        episode TEXT NOT NULL, platform TEXT NOT NULL, account TEXT NOT NULL,
        scheduled TEXT NOT NULL, manifest TEXT NOT NULL, status TEXT NOT NULL,
        checkpoint TEXT, checkpoint_id TEXT, provider_id TEXT, url TEXT,
        PRIMARY KEY (episode, platform)
    )""")
    return db


def enqueue(db, root, items):
    if isinstance(items, dict):
        items = [items]
    require(isinstance(items, list) and 1 <= len(items) <= 5
            and len({item['episode'] for item in items}) == 1
            and len({item['platform'] for item in items}) == len(items),
            'Supply one episode with up to five distinct destinations')
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


def update_result(db, row, status, resource, url):
    if url and url.startswith('/') and not url.startswith('//') and row['platform'] == 'facebook':
        url = 'https://www.facebook.com' + url
    with db:
        db.execute('UPDATE posts SET status=?, provider_id=?, url=? WHERE episode=? AND platform=?',
                   (status, resource, url if url and https(url) else None, row['episode'], row['platform']))


def run_due(db, root, now):
    rows = list(db.execute("SELECT * FROM posts WHERE status IN ('queued','processing') AND scheduled<=? "
                           "ORDER BY scheduled, platform", (now.isoformat(),)))
    results = []
    for row in rows:
        key = (row['episode'], row['platform'])
        item = json.loads(row['manifest'])
        platform = row['platform']
        try:
            validate(root, item)
            data = read_video(root, item) if platform != 'youtube' and row['status'] == 'queued' else None
            if platform in ('facebook', 'instagram', 'snapchat'):
                provider = direct.client(platform)
                provider.verify(row['account'])
            elif platform == 'youtube':
                require(item['account_id'] == os.environ.get('IFVERSE_ANIME_CHANNEL_ID'),
                        'Configure the intended YouTube channel before publishing')
                subprocess.run([sys.executable, '-m', 'whatif.youtube_publish', 'verify',
                                '--expected-channel-id', row['account']], cwd=root, capture_output=True,
                               check=True, timeout=60)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            results.append({'platform': platform, 'episode': row['episode'], 'status': 'awaiting_setup_or_review'})
            continue

        with db:
            claimed = db.execute("UPDATE posts SET status='working' WHERE episode=? AND platform=? AND status=?",
                                 (*key, row['status'])).rowcount
        if not claimed:
            continue

        def checkpoint(phase, resource):
            with db:
                db.execute('UPDATE posts SET checkpoint=?, checkpoint_id=? WHERE episode=? AND platform=?',
                           (phase, resource, *key))

        try:
            if platform == 'tiktok':
                result = ('manual_action_required', None, 'https://www.tiktok.com/tiktokstudio/upload')
            elif platform == 'youtube':
                result = youtube(root, item)
            elif row['status'] == 'processing':
                result = provider.finish_instagram(row['provider_id'], checkpoint)
            else:
                result = provider.publish(item, data, checkpoint)
            update_result(db, row, *result)
            results.append({'platform': platform, 'episode': row['episode'], 'status': result[0]})
        except (OSError, ValueError, KeyError, TypeError, ImportError, subprocess.SubprocessError):
            with db:
                db.execute("UPDATE posts SET status='needs_reconciliation' WHERE episode=? AND platform=?", key)
            results.append({'platform': platform, 'episode': row['episode'], 'status': 'needs_reconciliation'})
    return results


def refresh(db):
    for row in list(db.execute("SELECT * FROM posts WHERE status='submitted' AND platform!='youtube'")):
        try:
            provider = direct.client(row['platform'])
            provider.verify(row['account'])
            status, url = provider.status(row['provider_id'])
            update_result(db, row, status, row['provider_id'], url)
        except (OSError, ValueError, KeyError, TypeError):
            print(f'Could not verify {row["episode"]} on {row["platform"]}', file=sys.stderr)


def dashboard(db, path, accounts):
    def table(headers, rows):
        head = ''.join(f'<th>{escape(label)}</th>' for label in headers)
        body = ''.join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows)
        return f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
    connections = []
    for platform in PLATFORMS:
        names = [accounts[platform]] if accounts and platform in accounts else []
        status = ', '.join(names) if names else ('Manual TikTok Studio' if platform == 'tiktok' else 'Use Check account')
        connections.append((escape(platform.title()), escape(status)))
    queue = []
    for row in db.execute('SELECT * FROM posts ORDER BY scheduled, platform'):
        label = 'Open TikTok Studio' if row['platform'] == 'tiktok' else 'Open post'
        link = f'<a href="{escape(row["url"])}">{label}</a>' if row['url'] else '—'
        local = datetime.fromisoformat(row['scheduled']).astimezone(timezone(timedelta(hours=8)))
        queue.append(tuple(escape(str(value)) for value in (
            row['episode'], row['platform'], local.strftime('%Y-%m-%d %H:%M'),
            row['status'].replace('_', ' '), row['provider_id'] or row['checkpoint_id'] or '—')) + (link,))
    accounts_table = table(('Destination', 'Account'), connections)
    queue_table = table(('Episode', 'Destination', 'Ulaanbaatar time', 'Status', 'Reference', 'Post'), queue)
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
    queue = commands.add_parser('queue')
    queue.add_argument('manifest', type=Path)
    commands.add_parser('run-due')
    commands.add_parser('watch')
    report = commands.add_parser('dashboard')
    report.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    try:
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
                    dashboard(db, STATE / 'dashboard.html', None)
                    if args.command == 'run-due':
                        return 0
                    time.sleep(60)
            else:
                if args.refresh:
                    refresh(db)
                path = STATE / 'dashboard.html'
                dashboard(db, path, None)
                print(path)
    except PublishingError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, KeyError, TypeError, ValueError, subprocess.SubprocessError, sqlite3.Error):
        print('Publishing command failed. Check private configuration and saved job state.', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == '__main__':
    sys.exit(main())
