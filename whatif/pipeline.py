import json
import threading
from pathlib import Path
from .store import Store, atomic_json, digest, identifier
from . import media

STAGES = ("research", "script", "assets", "narration", "captions", "render", "quality_review")


def rebuild(store, job, from_stage, reason):
    if not reason.strip(): raise ValueError("Record why outputs need to be rebuilt")
    owner=store.claim(job)
    try:
        names=STAGES[STAGES.index(from_stage):]
        with store.connect() as db:
            if db.execute("SELECT 1 FROM publications WHERE job=? AND state!='draft'",(job,)).fetchone():
                raise ValueError("Delivery already attempted; create a new content version")
            db.execute("DELETE FROM publications WHERE job=?",(job,))
            for name in names: db.execute("DELETE FROM stages WHERE job=? AND name=?",(job,name))
            import time
            db.execute("INSERT INTO events(job,at,kind,detail) VALUES(?,?,?,?)",(job,time.time(),"rebuild",reason))
        folder=store.root/"jobs"/job
        for name in ["approval.json","publication-drafts.json"]:
            (folder/name).unlink(missing_ok=True)
        store.set_status(job,"queued","Rebuild from "+from_stage+": "+reason)
    finally: store.release(job,owner)
    return run(store,job)


def validate_spec(spec):
    identifier(spec["id"])
    identifier(spec["channel_id"])
    if spec.get("schema_version") != 1:
        raise ValueError("Unsupported job schema")
    if not isinstance(spec["title"],str) or len(spec["title"])>90:
        raise ValueError("Invalid title")
    profile=spec["profile"]
    if profile["width"] not in {360,720,1080} or profile["height"]*9 != profile["width"]*16 or profile["fps"] not in {24,30}:
        raise ValueError("Unsupported render profile")
    if not 1 <= profile["min_seconds"] <= profile["max_seconds"] <= 90:
        raise ValueError("Duration outside worker limits")
    if not 2 <= len(spec["scenes"]) <= 12:
        raise ValueError("Expected 2–12 scenes")
    for scene in spec["scenes"]:
        if not isinstance(scene["text"],str) or not 1 <= len(scene["text"])<=140:
            raise ValueError("Scene text must be 1–140 characters")
        if any(c in scene["text"] for c in "{}<>\\"):
            raise ValueError("Subtitle control characters are not allowed")
    if spec.get("language")!="en":
        raise ValueError("The local flite prototype supports English only; use an external speech adapter")
    if not spec.get("sources") or not spec.get("assumptions"):
        raise ValueError("Research references and scenario assumptions required")
    return spec


def seed(store, pilots):
    for path in sorted(Path(pilots).glob("*.json")):
        store.add(validate_spec(json.loads(path.read_text())))


def run(store, job):
    record=store.get(job)
    spec=validate_spec(json.loads(record["spec"]))
    owner=store.claim(job)
    stop=threading.Event()
    lease_errors=[]
    def pulse():
        while not stop.wait(20):
            try: store.heartbeat(job,owner)
            except Exception as exc:
                lease_errors.append(exc)
                return
    thread=threading.Thread(target=pulse,daemon=True)
    thread.start()
    folder=store.root/"jobs"/job
    folder.mkdir(parents=True,exist_ok=True)
    current="research"
    try:
        atomic_json(folder/"input.json",spec)
        for current in STAGES:
            if lease_errors: raise lease_errors[0]
            store.heartbeat(job,owner)
            stage=store.stage(job,current)
            if stage and stage["status"]=="completed":
                result=json.loads(stage["result"])
                for relative, checksum in result["files"].items():
                    path=store.root/relative
                    if not path.is_file() or digest(path)!=checksum:
                        raise ValueError(f"Checkpoint artifact changed: {relative}; restore backup or create a new job")
                continue
            store.start(job,current,owner=owner)
            details={}
            if current=="research":
                path=folder/"research.json"
                atomic_json(path,{"sources":spec["sources"],"assumptions":spec["assumptions"],
                                  "status":"provisional_reference_list; verify factual claims before release"})
                files=[path]
                details={"editorial_approval":False}
            elif current=="script":
                path=folder/"script.md"
                path.write_text("# "+spec["title"]+"\n\nPROVISIONAL DEMONSTRATION — REVIEW REQUIRED\n\n"+
                                "\n\n".join(s["text"] for s in spec["scenes"]))
                files=[path]
            elif current=="assets": files=media.assets(spec,folder)
            elif current=="narration":
                # A validated external batch can pre-fill this stage. Otherwise local speech is explicit.
                files=media.narration(spec,folder)
            elif current=="captions": files=media.captions(folder)
            elif current=="render": files=media.render(spec,folder)
            else: files=media.validate_output(spec,folder)
            store.heartbeat(job,owner)
            store.complete(job,current,files,details,owner=owner)
        if record["status"] != "ready":
            store.set_status(job,"quality_review","Review facts, pronunciation, visuals, captions and platform requirements")
        return folder/"video.mp4"
    except Exception as exc:
        try: store.fail(job,current,exc,blocked=isinstance(exc,PermissionError),owner=owner)
        except RuntimeError: pass  # A successor now owns the job; do not overwrite its state.
        raise
    finally:
        stop.set()
        thread.join(timeout=2)
        store.release(job,owner)


def drafts(store, job):
    spec=json.loads(store.get(job)["spec"])
    folder=store.root/"jobs"/job
    if not (folder/"quality.json").is_file():
        raise ValueError("Render and validate before drafting publications")
    output=[]
    for platform in spec["platforms"]:
        if platform not in {"youtube","tiktok","instagram","facebook"}:
            raise ValueError("Unsupported candidate platform")
        payload={"title":spec["title"],"description":"Illustrative What If scenario. Provisional draft; editorial review required.",
                 "hashtags":["WhatIf","Science"],"video":f"jobs/{job}/video.mp4", "video_sha256":digest(folder/"video.mp4"),
                 "cover":None,"disclosure_review_required":True,"scheduled_at":None,"timezone":"Asia/Ulaanbaatar",
                 "authorization":"not_granted","provider":"not_connected","metrics":{"views":None,"watch_time":None,"engagement":None}}
        output.append(store.draft(job,platform,payload))
    atomic_json(folder/"publication-drafts.json",output)
    return output


def approve(store, job, reviewer, *, factual=False, audiovisual=False, platform=False):
    if not all([factual,audiovisual,platform]):
        raise ValueError("All review categories must be explicitly confirmed")
    # Recheck checksums and decode output before recording a human approval.
    run(store,job)
    folder=store.root/"jobs"/job
    quality=json.loads((folder/"quality.json").read_text())
    if not quality["automated_pass"]: raise ValueError("Automated checks failed")
    atomic_json(folder/"approval.json",{"reviewer":reviewer,"factual":True,"audiovisual":True,"platform":True,
                                       "video_sha256":digest(folder/"video.mp4"),"publishing_authorized":False})
    store.set_status(job,"ready","Publishing still requires explicit authorization and a connected transport")
