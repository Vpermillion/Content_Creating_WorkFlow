import argparse
import json
import os
from pathlib import Path
from .store import Store
from . import pipeline, backup, tts


def main():
    parser=argparse.ArgumentParser(description="Portable What If video workspace; no publishing transport enabled")
    parser.add_argument("--data",default=os.environ.get("WORKSPACE_DIR","data"))
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("init")
    seed=sub.add_parser("pilots"); seed.add_argument("--from-dir",default="pilots")
    for name in ("run","drafts"):
        p=sub.add_parser(name); p.add_argument("job")
    sub.add_parser("status")
    p=sub.add_parser("rebuild"); p.add_argument("job"); p.add_argument("--from-stage",choices=pipeline.STAGES,required=True); p.add_argument("--reason",required=True)
    p=sub.add_parser("backup"); p.add_argument("destination")
    p=sub.add_parser("restore"); p.add_argument("archive"); p.add_argument("destination")
    p=sub.add_parser("tts-export"); p.add_argument("destination"); p.add_argument("jobs",nargs="+")
    p=sub.add_parser("tts-import"); p.add_argument("folder")
    p=sub.add_parser("approve"); p.add_argument("job"); p.add_argument("--reviewer",required=True)
    for flag in ("factual","audiovisual","platform"): p.add_argument("--"+flag,action="store_true")
    p=sub.add_parser("serve"); p.add_argument("--host",default="127.0.0.1"); p.add_argument("--port",type=int,default=8090)
    args=parser.parse_args()
    if args.command=="restore":
        print(backup.restore(args.archive,args.destination)); return
    store=Store(args.data)
    if args.command=="init": print("Initialized "+str(store.root))
    elif args.command=="pilots": pipeline.seed(store,args.from_dir); print("Pilot inputs saved without overwriting existing versions")
    elif args.command=="run": print(pipeline.run(store,args.job))
    elif args.command=="rebuild": print(pipeline.rebuild(store,args.job,args.from_stage,args.reason))
    elif args.command=="drafts": print(json.dumps(pipeline.drafts(store,args.job),indent=2))
    elif args.command=="status":
        snapshot=store.snapshot()
        print(json.dumps({"jobs":[{k:r[k] for k in ["id","channel","status","next_action","updated"]} for r in snapshot["jobs"]],
                          "stages":snapshot["stages"],"publications":snapshot["publications"]},indent=2))
    elif args.command=="backup": print(backup.backup(store,args.destination))
    elif args.command=="tts-export": print(json.dumps(tts.export_batch(store,args.jobs,args.destination),indent=2))
    elif args.command=="tts-import": print(tts.import_batch(store,args.folder))
    elif args.command=="approve": pipeline.approve(store,args.job,args.reviewer,factual=args.factual,audiovisual=args.audiovisual,platform=args.platform)
    elif args.command=="serve":
        from .server import serve
        serve(store,args.host,args.port)


if __name__=="__main__":
    main()
