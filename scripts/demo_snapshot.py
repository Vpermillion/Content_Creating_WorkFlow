"""Export/restore only the three synthetic demonstration jobs, with no SQLite DB.

Never use a source repository to back up real/private application databases.
"""
import argparse
import json
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from whatif.store import Store, atomic_json, digest
from whatif import backup, pipeline

JOBS={"pilot-001","pilot-002","pilot-003"}


def export_demo(store, archive):
    rows=store.snapshot()
    if {r["id"] for r in rows["jobs"]} != JOBS:
        raise ValueError("Demo export only supports the three bundled pilot fixtures")
    if any(r["state"]!="draft" or r["receipt"] for r in rows["publications"]):
        raise ValueError("Never export live publication receipts into demo source control")
    with tempfile.TemporaryDirectory() as temp:
        stage=Path(temp)/"state"; stage.mkdir()
        exported=[]
        for row in rows["jobs"]:
            source=store.root/"jobs"/row["id"]
            target=stage/"jobs"/row["id"]
            target.mkdir(parents=True)
            stages=[s for s in rows["stages"] if s["job"]==row["id"] and s["status"]=="completed"]
            needed={"jobs/"+row["id"]+"/input.json"}
            for s in stages: needed.update(json.loads(s["result"])["files"])
            for rel in needed:
                p=store.root/rel
                if p.is_symlink() or not p.resolve().is_relative_to(store.root): raise ValueError("Unsafe artifact")
                dest=stage/rel; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,dest)
            exported.append({"spec":json.loads(row["spec"]),"status":row["status"],"next_action":row["next_action"],"stages":stages})
        atomic_json(stage/"demo-state.json",{"schema_version":1,"demo_only":True,"jobs":exported})
        atomic_json(stage/"backup-manifest.json",{"schema_version":1,"files":{str(p.relative_to(stage)):digest(p) for p in stage.rglob('*') if p.is_file()}})
        with tarfile.open(archive,"w:gz") as tar: tar.add(stage,arcname="state")


def restore_demo(archive, destination):
    # The checked archive extractor creates a fresh, separate SQLite DB.
    restored=backup.restore(archive,destination)
    store=Store(restored)
    snapshot=json.loads((restored/"demo-state.json").read_text())
    if snapshot.get("demo_only") is not True or snapshot.get("schema_version")!=1:
        raise ValueError("Not a demonstration snapshot")
    for row in snapshot["jobs"]:
        spec=pipeline.validate_spec(row["spec"])
        if spec["id"] not in JOBS: raise ValueError("Unexpected fixture")
        store.add(spec)
        for stage in row["stages"]:
            if stage["name"] not in pipeline.STAGES: raise ValueError("Unknown stage")
            files=[]
            for rel,checksum in json.loads(stage["result"])["files"].items():
                path=(restored/rel).resolve()
                if not path.is_relative_to(restored) or digest(path)!=checksum: raise ValueError("Artifact mismatch")
                files.append(path)
            store.start(spec["id"],stage["name"])
            store.complete(spec["id"],stage["name"],files)
        store.set_status(spec["id"],row["status"],row["next_action"])
    return restored


if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['export','restore']); p.add_argument('archive'); p.add_argument('--data',default='data'); p.add_argument('--destination')
    a=p.parse_args()
    if a.action=='export': export_demo(Store(a.data),a.archive)
    else:
        if not a.destination: p.error('--destination required for restore')
        print(restore_demo(a.archive,a.destination))
