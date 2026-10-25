"""Application state. No dependency on the coordinator's internal database."""
import contextlib
import hashlib
import json
import re
import sqlite3
import time
import uuid
from pathlib import Path


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", value):
        raise ValueError("Expected a lower-case job/channel identifier")
    return value


def digest(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
              PRAGMA journal_mode=WAL;
              CREATE TABLE IF NOT EXISTS jobs(
                id TEXT PRIMARY KEY, channel TEXT NOT NULL, version TEXT NOT NULL,
                spec TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
                next_action TEXT NOT NULL DEFAULT 'run', owner TEXT, lease_until REAL,
                created REAL NOT NULL, updated REAL NOT NULL);
              CREATE TABLE IF NOT EXISTS stages(
                job TEXT NOT NULL REFERENCES jobs(id), name TEXT NOT NULL,
                status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                result TEXT, error TEXT, retry_at REAL DEFAULT 0,
                PRIMARY KEY(job,name));
              CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY, job TEXT, at REAL NOT NULL,
                kind TEXT NOT NULL, detail TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS publications(
                job TEXT NOT NULL REFERENCES jobs(id), platform TEXT NOT NULL,
                version TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'draft',
                idempotency_key TEXT UNIQUE NOT NULL, payload TEXT NOT NULL,
                receipt TEXT, updated REAL NOT NULL,
                PRIMARY KEY(job,platform,version));
              PRAGMA user_version=1;
            """)

    @contextlib.contextmanager
    def connect(self):
        db = sqlite3.connect(self.root / "jobs.sqlite3", timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def add(self, spec):
        job, channel = identifier(spec["id"]), identifier(spec["channel_id"])
        version = hashlib.sha256(canonical(spec).encode()).hexdigest()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT version FROM jobs WHERE id=?", (job,)).fetchone()
            if prior and prior[0] != version:
                raise ValueError("Job inputs changed; create a new job ID/version")
            topic=re.sub(r"\W+", "", spec["title"].casefold())
            for previous in db.execute("SELECT id,spec FROM jobs WHERE channel=? AND id!=?",(channel,job)):
                if re.sub(r"\W+", "", json.loads(previous["spec"])["title"].casefold())==topic:
                    raise ValueError("Topic title already exists in channel history; make a distinct story")
            db.execute("INSERT OR IGNORE INTO jobs(id,channel,version,spec,created,updated) VALUES(?,?,?,?,?,?)",
                       (job, channel, version, canonical(spec), time.time(), time.time()))
        return job

    def get(self, job):
        identifier(job)
        with self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()
            if row is None:
                raise ValueError("Unknown job")
            return dict(row)

    def snapshot(self):
        with self.connect() as db:
            return {table: [dict(r) for r in db.execute("SELECT * FROM " + table)]
                    for table in ("jobs", "stages", "publications", "events")}

    def claim(self, job, seconds=120):
        owner = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT owner,lease_until FROM jobs WHERE id=?", (job,)).fetchone()
            if row is None:
                raise ValueError("Unknown job")
            if row[0] and row[1] > time.time():
                raise RuntimeError("Job has an active worker lease")
            db.execute("UPDATE jobs SET owner=?,lease_until=? WHERE id=?", (owner, time.time()+seconds, job))
        return owner

    def heartbeat(self, job, owner):
        with self.connect() as db:
            n = db.execute("UPDATE jobs SET lease_until=? WHERE id=? AND owner=? AND lease_until>?",
                           (time.time()+120, job, owner, time.time())).rowcount
            if n != 1:
                raise RuntimeError("Worker lease lost")

    def release(self, job, owner):
        with self.connect() as db:
            db.execute("UPDATE jobs SET owner=NULL,lease_until=NULL WHERE id=? AND owner=?", (job, owner))

    def stage(self, job, name):
        with self.connect() as db:
            row = db.execute("SELECT * FROM stages WHERE job=? AND name=?", (job, name)).fetchone()
            return dict(row) if row else None

    def start(self, job, name, owner=None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self.check_owner(db,job,owner)
            row = db.execute("SELECT attempts,retry_at FROM stages WHERE job=? AND name=?", (job, name)).fetchone()
            if row and (row[0] >= 3 or row[1] > time.time()):
                raise RuntimeError("Retry exhausted or backoff active; inspect recorded error")
            db.execute("INSERT INTO stages(job,name,status,attempts) VALUES(?,?,'running',1) "
                       "ON CONFLICT(job,name) DO UPDATE SET status='running',attempts=attempts+1,error=NULL",
                       (job, name))
            db.execute("UPDATE jobs SET status='running',next_action=?,updated=? WHERE id=?", (name, time.time(), job))

    @staticmethod
    def check_owner(db, job, owner):
        if owner is not None and not db.execute("SELECT 1 FROM jobs WHERE id=? AND owner=? AND lease_until>?",
                                              (job,owner,time.time())).fetchone():
            raise RuntimeError("Worker lease lost; stale worker cannot save checkpoints")

    def complete(self, job, name, files, details=None, owner=None):
        result = {"files": {str(Path(f).resolve().relative_to(self.root)): digest(f) for f in files},
                  "details": details or {}}
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self.check_owner(db,job,owner)
            db.execute("UPDATE stages SET status='completed',result=?,error=NULL WHERE job=? AND name=?",
                       (canonical(result), job, name))
            db.execute("INSERT INTO events(job,at,kind,detail) VALUES(?,?,?,?)",
                       (job, time.time(), name+".completed", canonical(result)))

    def fail(self, job, name, error, blocked=False, owner=None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self.check_owner(db,job,owner)
            row = db.execute("SELECT attempts FROM stages WHERE job=? AND name=?", (job, name)).fetchone()
            db.execute("UPDATE stages SET status=?,error=?,retry_at=? WHERE job=? AND name=?",
                       ("blocked" if blocked else "failed", str(error), time.time()+min(300, 2**(row[0] if row else 1)), job, name))
            db.execute("UPDATE jobs SET status=?,next_action=?,updated=? WHERE id=?",
                       ("blocked" if blocked else "failed", str(error), time.time(), job))
            db.execute("INSERT INTO events(job,at,kind,detail) VALUES(?,?,?,?)",
                       (job, time.time(), name+".failed", str(error)))

    def set_status(self, job, status, action):
        with self.connect() as db:
            db.execute("UPDATE jobs SET status=?,next_action=?,updated=? WHERE id=?", (status, action, time.time(), job))

    def draft(self, job, platform, payload):
        row = self.get(job)
        key = hashlib.sha256(f'{job}:{platform}:{row["version"]}'.encode()).hexdigest()
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO publications(job,platform,version,idempotency_key,payload,updated) "
                       "VALUES(?,?,?,?,?,?)", (job, platform, row["version"], key, canonical(payload), time.time()))
            return dict(db.execute("SELECT * FROM publications WHERE idempotency_key=?", (key,)).fetchone())

    def begin_delivery(self, key, *, authorized=False):
        """Transport boundary: an uncertain upload can only be reconciled, never retried blindly."""
        if not authorized:
            raise PermissionError("Explicit platform publishing authorization is required")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM publications WHERE idempotency_key=?", (key,)).fetchone()
            if not row or row["state"] != "draft":
                raise RuntimeError("Already attempted; reconcile provider status before retry")
            if self.get(row["job"])["status"] != "ready":
                raise RuntimeError("Job requires quality and factual approval")
            db.execute("UPDATE publications SET state='uncertain',updated=? WHERE idempotency_key=?", (time.time(), key))

    def receipt(self, key, receipt):
        if not receipt.get("provider_id") or not receipt.get("state") in {"scheduled", "published", "rejected"}:
            raise ValueError("Actual provider ID and state required")
        with self.connect() as db:
            changed = db.execute("UPDATE publications SET state=?,receipt=?,updated=? WHERE idempotency_key=? AND state='uncertain'",
                                (receipt["state"], canonical(receipt), time.time(), key)).rowcount
            if changed != 1:
                raise RuntimeError("No uncertain delivery to reconcile")

    def backup_database(self, destination):
        with self.connect() as source:
            target = sqlite3.connect(destination)
            try:
                source.backup(target)
            finally:
                target.close()
