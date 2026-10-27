"""GitHub/local request entry point. Data inputs never become shell commands."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from whatif.media_tools import Bank, ToolError, build, enhance_file
from whatif.store import atomic_json


def repository_json(relative, prefix):
    path = (REPO / relative).resolve()
    if not path.is_relative_to(REPO / prefix) or path.suffix != '.json' or path.stat().st_size > 100_000:
        raise ToolError('invalid_repository_request_path')
    return json.loads(path.read_text())


def request_from_commit():
    names = subprocess.check_output(['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD'], cwd=REPO, text=True).splitlines()
    selected = [n for n in names if n.startswith('media-requests/') and n.endswith('.json')]
    if len(selected) != 1:
        raise ToolError('commit_exactly_one_media_request')
    return repository_json(selected[0], 'media-requests')


def execute(request, bank, output, narration=None):
    if request.get('schema_version') != 1 or request.get('operation') not in {'search','collect','find','enhance','build'}:
        raise ToolError('invalid_media_request')
    operation = request['operation']
    provider = request.get('provider', 'tenor')
    if provider not in {'youtube','tenor'}:
        raise ToolError('invalid_provider')
    label = request.get('label', '')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if operation == 'search': result = bank.search(label, provider, 3)
    elif operation == 'collect': result = bank.collect([label], provider, min_height=int(request.get('min_height',360)))
    elif operation == 'find':
        result = {'status':'ok','assets':[{k:a[k] for k in ['id','labels','width','height','duration']} for a in bank.find(label)]}
    elif operation == 'enhance':
        ident = request.get('asset_id','')
        if not re.fullmatch(r'[a-f0-9]{24}', ident): raise ToolError('invalid_asset_id')
        asset = bank.catalog()['assets'][ident]
        result = enhance_file(bank.asset_path(asset),output/'enhanced.mp4',request.get('enhancement','anime-light'))
    else:
        if not narration: raise ToolError('configure_private_narration_path')
        story = repository_json(request.get('story_path',''), 'media-stories')
        result = build(story,narration,bank,output/'render',request.get('enhancement','anime-light'),
                       download=bool(request.get('download',False)),provider=provider)
    atomic_json(output/'result.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request');parser.add_argument('--from-commit',action='store_true')
    args=parser.parse_args()
    output=Path(os.environ.get('IFVERSE_MEDIA_OUTPUT','private/media-workflow-output'))
    try:
        if args.from_commit:request=request_from_commit()
        elif args.request:
            path=Path(args.request)
            if path.stat().st_size>100_000:raise ToolError('request_too_large')
            request=json.loads(path.read_text())
        else:
            request={'schema_version':1,'operation':os.environ.get('MEDIA_OPERATION','find'),
                     'label':os.environ.get('MEDIA_LABEL','Naruto running'),'provider':os.environ.get('MEDIA_PROVIDER','tenor'),
                     'asset_id':os.environ.get('MEDIA_ASSET_ID',''),'story_path':os.environ.get('MEDIA_STORY_PATH',''),
                     'enhancement':os.environ.get('MEDIA_ENHANCEMENT','anime-light')}
        result=execute(request,Bank(os.environ.get('IFVERSE_MEDIA_BANK','private/media-bank')),output,
                       os.environ.get('IFVERSE_NARRATION_PATH'))
    except (ToolError,OSError,ValueError,KeyError,RuntimeError) as e:
        result={'status':'blocked','error':str(e) if isinstance(e,ToolError) else 'media_request_failed'}
        atomic_json(output/'result.json',result)
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result['status'] in {'ok','cached'} else 2


if __name__=='__main__':raise SystemExit(main())
