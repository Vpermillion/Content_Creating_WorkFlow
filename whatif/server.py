"""Small private worker API. It never accepts shell commands, arbitrary paths or URLs."""
import hmac
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .pipeline import run
from .store import identifier


def make_server(store, host, port, token):
    if len(token)<32:
        raise ValueError("WORKER_TOKEN must be a locally generated secret of at least 32 characters")
    executor=ThreadPoolExecutor(max_workers=1)
    pending=set()
    guard=threading.Lock()
    def work(job):
        try: run(store,job)
        except Exception: pass  # Failure is durably recorded by the pipeline; inspect job status.
        finally:
            with guard: pending.discard(job)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # Never log request headers or payloads, which may contain credentials.
            pass
        def respond(self, status, payload):
            body=json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type","application/json")
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def route(self):
            if self.command=="GET" and self.path=="/health":
                return self.respond(200,{"ok":True,"service":"whatif-worker","publishing_enabled":False})
            if not hmac.compare_digest(self.headers.get("Authorization",""),"Bearer "+token):
                return self.respond(401,{"error":"worker authentication required"})
            try:
                parts=self.path.strip("/").split("/")
                if len(parts)<2 or parts[0]!="jobs": raise ValueError("Unknown route")
                job=identifier(parts[1])
                record=store.get(job)
                if self.command=="GET" and len(parts)==2:
                    return self.respond(200,{k:record[k] for k in ["id","status","next_action","updated"]})
                if self.command=="POST" and len(parts)==3 and parts[2]=="run":
                    if int(self.headers.get("Content-Length","0"))>1024:
                        return self.respond(413,{"error":"request too large"})
                    # Read/discard bounded body; the only input is the validated job ID in the route.
                    self.rfile.read(int(self.headers.get("Content-Length","0")))
                    with guard:
                        if job not in pending:
                            if len(pending)>=10: return self.respond(429,{"error":"queue full; retry later"})
                            pending.add(job)
                            executor.submit(work,job)
                    return self.respond(202,{"job_id":job,"accepted":True,"status_path":"/jobs/"+job})
                return self.respond(404,{"error":"unknown route"})
            except (ValueError,KeyError): return self.respond(400,{"error":"unknown or malformed job"})
        do_GET=route
        do_POST=route
    server=ThreadingHTTPServer((host,port),Handler)
    server.executor=executor
    return server


def serve(store, host, port):
    server=make_server(store,host,port,os.environ.get("WORKER_TOKEN",""))
    try: server.serve_forever()
    finally:
        server.server_close()
        server.executor.shutdown(wait=True)
