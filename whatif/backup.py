"""Checked portable application-state archives; credentials are excluded."""
import json
import shutil
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath
from .store import Store, atomic_json, digest


def backup(store, destination):
    destination=Path(destination).resolve()
    if destination.is_relative_to(store.root):
        raise ValueError("Backup must be outside application state")
    if destination.exists(): raise ValueError("Refusing to overwrite a backup")
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        stage=Path(temp)/"state"
        stage.mkdir()
        # Reserve writes while checking leases and taking a consistent filesystem + DB copy.
        with store.connect() as lock:
            lock.execute("BEGIN IMMEDIATE")
            if lock.execute("SELECT 1 FROM jobs WHERE owner IS NOT NULL AND lease_until>?", (time.time(),)).fetchone():
                raise RuntimeError("Pause workers before backup; an active lease exists")
            for source in store.root.rglob("*"):
                if source.is_symlink(): raise ValueError("Symlinks are not permitted in application state")
                if source.is_file() and source.name not in {"jobs.sqlite3","jobs.sqlite3-wal","jobs.sqlite3-shm"}:
                    target=stage/source.relative_to(store.root)
                    target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(source,target)
            store.backup_database(stage/"jobs.sqlite3")
        atomic_json(stage/"backup-manifest.json",{"schema_version":1,"created_utc_epoch":time.time(),
                   "files":{str(p.relative_to(stage)):digest(p) for p in stage.rglob("*") if p.is_file()}})
        with tarfile.open(destination,"w:gz") as archive:
            archive.add(stage,arcname="state")
    destination.chmod(0o600)
    return destination


def restore(archive_path, destination):
    destination=Path(destination).resolve()
    if destination.exists(): raise ValueError("Restore destination must not exist")
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        with tarfile.open(archive_path,"r:gz") as archive:
            members=archive.getmembers()
            if sum(m.size for m in members)>2_000_000_000 or len(members)>20000:
                raise ValueError("Archive exceeds restore limits")
            for member in members:
                path=PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0]!="state" or not (member.isfile() or member.isdir()):
                    raise ValueError("Unsafe archive member")
            archive.extractall(temp,filter="data")
        stage=Path(temp)/"state"
        manifest=json.loads((stage/"backup-manifest.json").read_text())
        if manifest.get("schema_version") != 1: raise ValueError("Unsupported backup schema")
        actual={str(p.relative_to(stage)):digest(p) for p in stage.rglob("*") if p.is_file() and p.name!="backup-manifest.json"}
        if actual!=manifest["files"]: raise ValueError("Backup checksum mismatch")
        (stage/"backup-manifest.json").unlink()
        restored=Store(stage)
        with restored.connect() as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok": raise ValueError("Database integrity failed")
            db.execute("UPDATE jobs SET owner=NULL,lease_until=NULL")
        shutil.move(stage,destination)
    return destination
