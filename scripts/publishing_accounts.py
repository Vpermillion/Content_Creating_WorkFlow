"""Resolve public account bindings and load only the selected private grant."""
import json
import os
from pathlib import Path
import re
import sys

if __package__:
    from . import publishing_direct as direct
else:
    import publishing_direct as direct

ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ('youtube', 'facebook', 'tiktok', 'instagram', 'snapchat')
ALIAS = re.compile(r'[a-z0-9][a-z0-9-]{0,39}')
BRAND = re.compile(r'[a-z0-9][a-z0-9_]{0,39}')
ACCOUNT = re.compile(r'[A-Za-z0-9_-]{1,100}')


def registry(root):
    path = root / 'channels/publishing-accounts.json'
    if not path.exists():
        return {}
    accounts = json.loads(path.read_text(encoding='utf-8'))
    seen = set()
    for name, row in accounts.items():
        brand, platform, account = (row[key] for key in ('brand', 'platform', 'account_id'))
        direct.require(set(row) <= {'brand', 'platform', 'account_id', 'handle'}
                       and isinstance(row.get('handle', ''), str)
                       and ALIAS.fullmatch(name) and BRAND.fullmatch(brand) and platform in PLATFORMS
                       and ACCOUNT.fullmatch(account), 'Invalid publishing account binding')
        identity = (platform, account.casefold() if platform == 'tiktok' else account)
        direct.require(identity not in seen, 'A platform account must have one publishing alias')
        seen.add(identity)
    return accounts


def resolve(root, item):
    alias = item['account']
    row = registry(root).get(alias)
    direct.require(row is not None, 'Choose a registered publishing account alias')
    direct.require(all(item[field] == row[field] for field in ('brand', 'platform', 'account_id')),
                   'The registered account differs from the reviewed destination')
    return row


def grant(root, alias):
    payload = os.environ.get('IFVERSE_PUBLISH_ACCOUNTS')
    if payload is None:
        path = root / 'private/publishing/accounts.json'
        direct.require(path.is_file() and not path.is_symlink(), 'Configure the private publishing grants')
        if os.name == 'posix':
            direct.require(not path.stat().st_mode & 0o077, 'Set the private grants file to mode 0600')
        payload = path.read_text(encoding='utf-8')
    account = json.loads(payload).get(alias)
    direct.require(isinstance(account, dict), 'The selected account needs its own private grant')
    return account


def provider(root, alias, row):
    return direct.client(row['platform'], row['account_id'], grant(root, alias))


def youtube_session(root, alias, row):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from whatif import youtube, youtube_publish

    store = youtube.ConnectionStore(root / 'private/youtube-publish')
    if 'IFVERSE_PUBLISH_ACCOUNTS' in os.environ:
        record = grant(root, alias).get('youtube_connection', {})
        direct.require(record.get('connection') == alias and record.get('channel', {}).get('id') == row['account_id'],
                       'The private YouTube connection differs from the registered channel')
        with store.lock(alias):
            store.save(alias, record)
    return youtube_publish.verified_session(store, row['account_id'], alias, row.get('handle'))
