"""Import the local workflow + encrypted worker credential without exposing a token.

Requires an already running compose n8n container. No social accounts are connected.
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

docker=["docker","--host=unix:///var/run/docker.sock","compose"]
clean_env={k:v for k,v in os.environ.items() if k not in {"DOCKER_HOST","DOCKER_CONTEXT","DOCKER_TLS","DOCKER_TLS_VERIFY","DOCKER_CERT_PATH"}}
def call(args): subprocess.run([*docker,*args],env=clean_env,check=True)

def main():
    # Confirm the container runs before copying a plaintext transfer file into it.
    call(["exec","-T","n8n","test","-d","/home/node/.n8n"])
    settings=dict(line.split("=",1) for line in Path('.env').read_text().splitlines() if line and not line.startswith('#'))
    token=settings["WORKER_TOKEN"]
    if len(token)<32: raise ValueError("Generate .env first")
    credential=[{"id":"whatifWorkerLocal","name":"WhatIf worker","type":"httpHeaderAuth",
                 "data":{"name":"Authorization","value":"Bearer "+token}}]
    temp_path=None
    try:
        with tempfile.NamedTemporaryFile(mode="w",prefix="whatif-credentials-",suffix=".json",delete=False) as f:
            json.dump(credential,f); temp_path=f.name
        call(["cp",temp_path,"n8n:/tmp/whatif-credentials.json"])
        call(["exec","-T","n8n","n8n","import:credentials","--input=/tmp/whatif-credentials.json"])
        call(["exec","-T","n8n","n8n","import:workflow","--input=/exports/prepared-pilot.v1.json"])
    finally:
        if temp_path: Path(temp_path).unlink(missing_ok=True)
        # Remove the plaintext transfer file; n8n retains the credential encrypted in its DB.
        subprocess.run([*docker,"exec","-T","n8n","rm","-f","/tmp/whatif-credentials.json"],env=clean_env,check=False)
    print("Imported inactive draft workflow and local worker credential; publishing remains disabled.")

if __name__=="__main__": main()
