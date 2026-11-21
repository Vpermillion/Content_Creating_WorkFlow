"""Private durable reviewed drafts. One serialized worker per durable volume.

Provider adapters own reconciliation; an interrupted operation is never reset.
The API caller is trusted owner-only infrastructure, not a public client.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from uuid import uuid4

from scripts import publishing_accounts as accounts
from scripts.publishing_direct import require
from . import youtube

FORMATS = {'youtube': ('short',), 'instagram': ('reel', 'jpeg'),
           'facebook': ('reel', 'feed'), 'tiktok': ('studio',)}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Drafts:
    def __init__(self, directory, root, adapter):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        require(not self.directory.is_symlink() and not self.directory.stat().st_mode & 0o077,
                'Private state requires an owner-only directory')
        self.root, self.adapter = Path(root), adapter
        self.path = self.directory / 'drafts.sqlite'
        with self.db() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS drafts (
                id TEXT PRIMARY KEY, snapshot TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS deliveries (
                draft TEXT, alias TEXT, status TEXT NOT NULL, receipt TEXT NOT NULL,
                PRIMARY KEY(draft,alias));
                CREATE TABLE IF NOT EXISTS operations (
                identity TEXT PRIMARY KEY, draft TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tiktok_posts (
                provider_id TEXT PRIMARY KEY, draft TEXT NOT NULL, alias TEXT NOT NULL);''')
        os.chmod(self.path, 0o600)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def media(self, sha):
        require(isinstance(sha, str) and re.fullmatch('[0-9a-f]{64}', sha), 'Invalid media hash')
        return self.directory / 'media' / sha

    def put_media(self, data):
        require(0 < len(data) <= 100 * 1024 * 1024, 'Media must be between 1 byte and 100 MiB')
        sha = hashlib.sha256(data).hexdigest()
        folder = self.directory / 'media'
        folder.mkdir(mode=0o700, exist_ok=True)
        path = self.media(sha)
        if not path.exists():
            # Atomic content address; concurrent writers have identical bytes.
            temp = folder / uuid4().hex
            with temp.open('xb') as out:
                os.chmod(temp, 0o600)
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temp, path)
        return sha

    def check_binding(self, row, registry):
        binding = registry.get(row['account'])
        require(binding and all(row.get(field) == binding.get(field)
                                for field in ('brand', 'platform', 'account_id', 'handle')),
                'The account binding differs from the reviewed destination')

    def create(self, brand, destinations, registry=None):
        require(isinstance(destinations, list) and 0 < len(destinations) <= 4, 'Choose 1–4 destinations')
        registry = accounts.registry(self.root) if registry is None else registry
        rows, seen, identities = [], set(), set()
        for source in destinations:
            alias = source['account']
            require(alias in registry and alias not in seen, 'Choose distinct registered account aliases')
            seen.add(alias)
            binding = registry[alias]
            account_id = binding['account_id']
            identity = (binding['platform'], account_id.casefold() if binding['platform'] == 'tiktok' else account_id)
            require(identity not in identities, 'Select each platform account only once')
            identities.add(identity)
            require(binding['brand'] == brand and binding['platform'] in FORMATS, 'Wrong brand or platform')
            require(source['format'] in FORMATS[binding['platform']], 'Format is not wired')
            require(isinstance(source['caption'], str) and len(source['caption'].encode()) <= (5000 if binding['platform'] == 'youtube' else 2200), 'Caption too long')
            title = source.get('title', '')
            require(isinstance(title, str) and 0 < len(title) <= 100 and not any(c in title for c in '<>\n\r'), 'Supply a title')
            sha = source['media_sha256']
            require(self.media(sha).is_file(), 'Import prepared media first')
            require(hashlib.sha256(self.media(sha).read_bytes()).hexdigest() == sha, 'Media changed')
            # Reuse media-job review and topic checks where a production manifest is provided.
            manifest = source.get('manifest')
            require(isinstance(manifest, dict), 'Supply the existing media job review manifest')
            from scripts import publishing_dashboard as queue
            manifest = {**manifest, **binding, 'account': alias}
            topics = json.loads((self.root / 'channels' / f'{brand}-topics.json').read_text())
            matches = [t for t in topics['topics'] if t['id'] == manifest['episode']]
            require(len(matches) == 1 and matches[0].get('video_sha256') == manifest.get('master_sha256'),
                    'Select the current media job master from the topic registry')
            require(manifest.get('video_sha256') == sha and manifest.get('brand') == brand,
                    'Media job review must match this media and brand')
            row = {**binding, 'account': alias, 'format': source['format'], 'caption': source['caption'],
                   'title': title, 'media_sha256': sha, 'manifest': manifest}
            self.adapter.validate_media(row, self.media(sha))
            # A draft preview may exist before consent; never invent a binding verification.
            rows.append(row)
        draft = uuid4().hex
        snapshot = {'brand': brand, 'destinations': rows}
        hashed = fingerprint(snapshot)
        with self.db() as db:
            db.execute('INSERT INTO drafts VALUES (?,?,?)', (draft, canonical(snapshot), hashed))
            for row in rows:
                db.execute('INSERT INTO deliveries VALUES (?,?,?,?)', (draft, row['account'], 'draft', '{}'))
        return self.get(draft)

    def get(self, draft):
        with self.db() as db:
            row = db.execute('SELECT * FROM drafts WHERE id=?', (draft,)).fetchone()
            require(row is not None, 'Draft not found')
            deliveries = [dict(r) for r in db.execute(
                'SELECT alias,status,receipt FROM deliveries WHERE draft=? ORDER BY alias', (draft,))]
        snapshot = json.loads(row['snapshot'])
        require(fingerprint(snapshot) == row['hash'], 'Draft integrity failure')
        for delivery in deliveries:
            delivery['receipt'] = json.loads(delivery['receipt'])
        return {'draft_id': draft, 'snapshot_hash': row['hash'], **snapshot, 'deliveries': deliveries}

    def save(self, draft, alias, status, receipt):
        # Receipts may contain private session state; only adapters return safe public fields.
        with self.db() as db:
            db.execute('UPDATE deliveries SET status=?,receipt=? WHERE draft=? AND alias=?',
                       (status, canonical(receipt), draft, alias))

    def confirm_tiktok(self, draft, alias, receipt):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT status FROM deliveries WHERE draft=? AND alias=?', (draft, alias)).fetchone()
            require(row is not None and row['status'] == 'action_required', 'A pending TikTok handoff is required')
            try:
                db.execute('INSERT INTO tiktok_posts VALUES (?,?,?)', (receipt['provider_id'], draft, alias))
            except sqlite3.IntegrityError:
                raise ValueError('This TikTok post is already attached to a receipt') from None
            db.execute('UPDATE deliveries SET status=?,receipt=? WHERE draft=? AND alias=?',
                       ('published', canonical(receipt), draft, alias))

    def refresh(self, draft, registry=None):
        registry = accounts.registry(self.root) if registry is None else registry
        with youtube.file_lock(self.directory / '.publish.lock'):
            preview = self.get(draft)
            rows = {r['account']: r for r in preview['destinations']}
            for state in preview['deliveries']:
                if state['status'] not in ('submitted', 'processing', 'needs_reconciliation'):
                    continue
                row = rows[state['alias']]
                try:
                    self.check_binding(row, registry)
                    result = self.adapter.read_status(row, state)
                except Exception:
                    continue  # Keep the existing receipt when a provider read fails.
                if result:
                    self.save(draft, state['alias'], result['status'], {**state['receipt'], **result})
            return self.get(draft)

    def publish(self, draft, snapshot_hash, destinations, approved, registry=None):
        require(approved is True, 'Explicit owner approval of this exact preview is required')
        preview = self.get(draft)
        require(snapshot_hash == preview['snapshot_hash'], 'Review the current immutable preview')
        require(isinstance(destinations, list) and destinations and len(set(destinations)) == len(destinations),
                'Select an exact nonempty destination subset')
        rows = {r['account']: r for r in preview['destinations']}
        require(set(destinations) <= rows.keys(), 'Destination not in reviewed draft')
        registry = accounts.registry(self.root) if registry is None else registry
        # Across processes, hold a file lock through the provider call. Crash releases the lock
        # but leaves working status; retry then reconciles instead of issuing a fresh write.
        with youtube.file_lock(self.directory / '.publish.lock'):
            for alias in destinations:
                row = rows[alias]
                state = next(r for r in self.get(draft)['deliveries'] if r['alias'] == alias)
                if state['status'] in ('published', 'action_required'):
                    continue
                from scripts import publishing_dashboard as queue
                try:
                    self.check_binding(row, registry)
                    queue.load_review(self.root, row['manifest'])
                except (ValueError, KeyError, OSError):
                    status = 'blocked_review' if state['status'] in ('draft', 'awaiting_consent', 'blocked_review') else state['status']
                    self.save(draft, alias, status, {**state['receipt'], 'verification': 'check_review_or_account_binding'})
                    continue
                identity = fingerprint({k: row[k] for k in ('brand', 'platform', 'account_id')} |
                    {'episode': row['manifest']['episode']})
                with self.db() as db:
                    db.execute('INSERT OR IGNORE INTO operations VALUES (?,?)', (identity, draft))
                    owner = db.execute('SELECT draft FROM operations WHERE identity=?', (identity,)).fetchone()['draft']
                if owner != draft:
                    self.save(draft, alias, 'duplicate_operation', {'original_draft_id': owner})
                    continue
                try:
                    self.adapter.verify(row)  # always read-only, including refresh/identity checks
                except Exception:
                    if state['status'] in ('draft', 'awaiting_consent', 'blocked_review'):
                        self.save(draft, alias, 'awaiting_consent', {})
                    else:
                        self.save(draft, alias, state['status'],
                                  {**state['receipt'], 'verification': 'reconnect_required'})
                    continue
                checkpoint = lambda value, a=alias: self.save(draft, a, 'working', value)
                try:
                    if state['status'] in ('draft', 'awaiting_consent', 'blocked_review'):
                        checkpoint({})  # durable intent before the first provider mutation
                        result = self.adapter.start(row, self.media(row['media_sha256']), draft, checkpoint)
                    else:
                        result = self.adapter.reconcile(row, self.media(row['media_sha256']), draft,
                                                        state, checkpoint)
                    require(result['status'] in ('published', 'submitted', 'processing',
                            'action_required', 'needs_reconciliation', 'failed'), 'Invalid provider outcome')
                    self.save(draft, alias, result['status'], result)
                except Exception:
                    # Do not leak errors (SDK errors may contain tokens/session URLs).
                    with self.db() as db:
                        db.execute("UPDATE deliveries SET status='needs_reconciliation' WHERE draft=? AND alias=?",
                                   (draft, alias))
        return self.get(draft)
