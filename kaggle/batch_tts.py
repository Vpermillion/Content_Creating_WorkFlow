"""Run once in an authorized Kaggle notebook. Not a long-lived speech server.

Install kokoro==0.9.4 soundfile==0.13.1 first; inspect current model/voice rights.
Use a private input dataset containing input.json, never account credentials.
"""
import hashlib
import json
import os
import re
import time
from pathlib import Path


def main():
    import numpy as np
    import soundfile as sf
    import torch
    from kokoro import KPipeline
    input_file=Path(os.environ.get("WHATIF_BATCH_INPUT","/kaggle/input/whatif-batch/input.json"))
    output_dir=Path("/kaggle/working/tts-output")
    batch=json.loads(input_file.read_text())
    if batch["schema_version"]!=1 or not re.fullmatch(r"batch-[a-f0-9]{32}",batch["batch_id"]):
        raise ValueError("Unsupported batch manifest")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("Output directory not empty; do not mix notebook runs")
    output_dir.mkdir(exist_ok=True,parents=True)
    # Load once for the whole finite batch. Device choice is measured and recorded.
    device="cuda" if torch.cuda.is_available() else "cpu"
    started=time.monotonic()
    pipeline=KPipeline(lang_code="a",repo_id="hexgrad/Kokoro-82M",device=device)
    results=[]
    seen=set()
    for job in batch["jobs"]:
        job_id=job["job_id"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}",job_id) or job_id in seen:
            raise ValueError("Invalid or duplicate job ID")
        seen.add(job_id)
        if job["language"]!="en" or job["voice"]!="af_heart":
            raise ValueError("This notebook template supports the provisional English built-in voice only")
        audio_parts=[]
        segments=[]
        sample_count=0
        for i,text in enumerate(job["segments"]):
            if not isinstance(text,str) or not 1<=len(text)<=140: raise ValueError("Invalid scene text")
            chunks=[]
            for _,_,audio in pipeline(text,voice="af_heart",speed=1):
                samples=audio.detach().cpu().numpy() if hasattr(audio,"detach") else np.asarray(audio)
                chunks.append(samples.astype(np.float32))
            if not chunks: raise ValueError("TTS returned no speech")
            scene_audio=np.concatenate(chunks)
            if not np.isfinite(scene_audio).all(): raise ValueError("Invalid audio samples")
            begin=sample_count/24000
            sample_count+=len(scene_audio)
            segments.append({"scene":i,"text":text,"start":begin,"end":sample_count/24000})
            audio_parts.append(scene_audio)
        if not 1<=sample_count/24000<=90: raise ValueError("Audio duration outside batch limits")
        path=output_dir/(job_id+".wav")
        sf.write(path,np.concatenate(audio_parts),24000,subtype="PCM_16")
        results.append({"job_id":job_id,"content_version":job["content_version"],"file":path.name,
                        "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"segments":segments})
    # Write the completion manifest last. Its absence means the batch is incomplete.
    (output_dir/"output.json").write_text(json.dumps({"schema_version":1,"batch_id":batch["batch_id"],
        "jobs":results,"device":device,"elapsed_seconds":time.monotonic()-started,
        "model":"hexgrad/Kokoro-82M","voice":"af_heart","alignment":"scene sample boundaries"},indent=2))
    print(f"Completed {len(results)} jobs on {device}; download tts-output and stop the session.")


if __name__=="__main__": main()
