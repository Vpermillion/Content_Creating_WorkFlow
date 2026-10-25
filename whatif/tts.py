"""Finite, manually transferred Kaggle batches with strict run-to-job matching."""
import hashlib
import json
import shutil
import uuid
from pathlib import Path
from .store import atomic_json, digest
from .media import duration


def export_batch(store, jobs, destination):
    batch_id="batch-"+uuid.uuid4().hex
    entries=[]
    for job in jobs:
        row=store.get(job)
        spec=json.loads(row["spec"])
        entries.append({"job_id":job,"content_version":row["version"],"language":spec["language"],
                        "voice":"af_heart","segments":[s["text"] for s in spec["scenes"]]})
    payload={"schema_version":1,"batch_id":batch_id,"jobs":entries,"submission":"manual; Kaggle account not connected"}
    path=store.root/"batches"/batch_id/"input.json"
    atomic_json(path,payload)
    atomic_json(destination,payload)
    return payload


def import_batch(store, folder):
    folder=Path(folder).resolve()
    output=json.loads((folder/"output.json").read_text())
    batch_id=output["batch_id"]
    from .store import identifier
    identifier(batch_id)
    expected=json.loads((store.root/"batches"/batch_id/"input.json").read_text())
    wanted={j["job_id"]:j for j in expected["jobs"]}
    received=output["jobs"]
    if output.get("schema_version")!=1 or len(received)!=len(wanted) or set(j["job_id"] for j in received)!=set(wanted):
        raise ValueError("Batch outputs are missing, duplicated, or from another run")
    checked=[]
    for item in received:
        job=item["job_id"]
        request=wanted[job]
        if item["content_version"]!=request["content_version"] or store.get(job)["version"]!=request["content_version"]:
            raise ValueError("Speech content version mismatch")
        if item["file"]!=job+".wav": raise ValueError("Unexpected batch audio path")
        audio=folder/item["file"]
        if audio.is_symlink() or digest(audio)!=item["sha256"]: raise ValueError("Speech checksum mismatch")
        length=duration(audio)
        segments=item["segments"]
        if len(segments)!=len(request["segments"]): raise ValueError("Speech segments incomplete")
        end=0.0
        for i,s in enumerate(segments):
            if s["text"]!=request["segments"][i] or abs(s["start"]-end)>0.002 or s["end"]<=s["start"]:
                raise ValueError("Speech text or timing mismatch")
            s["scene"]=i
            end=s["end"]
        if not 1<length<90 or abs(end-length)>0.03: raise ValueError("Speech duration mismatch")
        # Rendering must not silently change a previously produced video.
        if store.stage(job,"narration") or store.stage(job,"render"):
            raise ValueError("Narration already exists; use a new job version for a replacement voice")
        checked.append((job,audio,item,length))
    # Validate the whole batch before saving any successful stage.
    owners=[]
    try:
        for job,_,_,_ in checked: owners.append((job,store.claim(job)))
        for (job,audio,item,length),(_,owner) in zip(checked,owners):
            target=store.root/"jobs"/job
            target.mkdir(parents=True,exist_ok=True)
            shutil.copy2(audio,target/"narration.wav")
            atomic_json(target/"narration.json",{"schema_version":1,"provider":"kaggle-kokoro","voice":"af_heart",
                        "batch_id":batch_id,"duration":length,"segments":item["segments"],"sha256":item["sha256"],
                        "timing_basis":"Concatenated generated scene samples; sentence-level boundaries"})
            store.start(job,"narration",owner=owner)
            store.complete(job,"narration",[target/"narration.wav",target/"narration.json"],{"batch_id":batch_id},owner=owner)
    finally:
        for job,owner in owners: store.release(job,owner)
    atomic_json(store.root/"batches"/batch_id/"imported.json",output)
    return list(wanted)
