"""Encrypt resumable journals before preserving them on a dedicated Git branch."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from whatif.youtube import atomic_json
from whatif.youtube_publish import private_directory

BRANCH='codex/youtube-upload-state'
BLOB='publishing-state/uploads.enc'


def cipher():
    from cryptography.fernet import Fernet
    return Fernet(os.environ['YOUTUBE_UPLOAD_STATE_KEY'].encode())


def git(*args,input=None,env=None):
    return subprocess.check_output(['git',*args],cwd=ROOT,input=input,env=env)


def restore():
    f=cipher()  # Validate key before any remote upload can occur.
    state=private_directory(ROOT/'private/youtube-upload-state')
    if list(state.glob('*.json')):
        raise ValueError('Restore only into fresh private journal storage')
    refs=git('ls-remote','origin','refs/heads/'+BRANCH).decode().strip()
    if not refs:return
    git('fetch','--quiet','--depth=1','origin','refs/heads/'+BRANCH)
    files=json.loads(f.decrypt(git('show','FETCH_HEAD:'+BLOB)))
    for name,value in files.items():
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}\.json',name):raise ValueError('Invalid journal filename')
        atomic_json(state/name,value)


def save():
    f=cipher();folder=private_directory(ROOT/'private/youtube-upload-state')
    files={p.name:json.loads(p.read_text()) for p in folder.glob('*.json')}
    if not files:return
    encrypted=f.encrypt(json.dumps(files,sort_keys=True).encode())
    refs=git('ls-remote','origin','refs/heads/'+BRANCH).decode().strip()
    if refs:
        git('fetch','--quiet','--depth=1','origin','refs/heads/'+BRANCH)
        parent=git('rev-parse','FETCH_HEAD').decode().strip()
    else:parent=git('rev-parse','HEAD').decode().strip()
    fd,index=tempfile.mkstemp(prefix='upload-state-index-');os.close(fd);os.unlink(index)
    env=os.environ.copy();env['GIT_INDEX_FILE']=index
    env.update(GIT_AUTHOR_NAME='github-actions[bot]',GIT_AUTHOR_EMAIL='41898282+github-actions[bot]@users.noreply.github.com',
               GIT_COMMITTER_NAME='github-actions[bot]',GIT_COMMITTER_EMAIL='41898282+github-actions[bot]@users.noreply.github.com')
    try:
        git('read-tree',parent,env=env)
        blob=git('hash-object','-w','--stdin',input=encrypted).decode().strip()
        git('update-index','--add','--cacheinfo','100644,'+blob+','+BLOB,env=env)
        paths=list((ROOT/'publication-receipts').glob('*.json'))+[ROOT/'channels/ifverse_anime-topics.json']
        for path in paths:
            name=path.relative_to(ROOT).as_posix();blob=git('hash-object','-w','--stdin',input=path.read_bytes()).decode().strip()
            git('update-index','--add','--cacheinfo','100644,'+blob+','+name,env=env)
        tree=git('write-tree',env=env).decode().strip()
        commit=git('commit-tree',tree,'-p',parent,env=env,input=b'Preserve encrypted upload checkpoints and nonsecret receipts\n').decode().strip()
        subprocess.run(['git','push','origin',commit+':refs/heads/'+BRANCH],cwd=ROOT,check=True)
    finally:
        if Path(index).exists():Path(index).unlink()
    publish_receipts_to_source()


def publish_receipts_to_source():
    """Merge provider receipts into current Git history without touching new topics."""
    source_branch='codex/ifverse-workflow'
    receipts=[json.loads(p.read_text()) for p in (ROOT/'publication-receipts').glob('*.json')]
    if not receipts:return
    git('fetch','--quiet','--depth=1','origin','refs/heads/'+source_branch)
    parent=git('rev-parse','FETCH_HEAD').decode().strip()
    registry=json.loads(git('show',parent+':channels/ifverse_anime-topics.json'))
    for receipt in receipts:
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}',receipt.get('video_id','')):raise ValueError('Invalid provider receipt')
        matches=[e for e in registry['topics'] if e['id']==receipt['id']]
        if len(matches)!=1 or matches[0].get('video_sha256')!=receipt['video_sha256']:
            raise ValueError('Current topic registry differs from uploaded artifact; preserve receipt and reconcile')
        entry=matches[0]
        if entry.get('video_id') not in (None,receipt['video_id']):raise ValueError('Conflicting publication receipt')
        entry.update(state='published' if receipt['publicly_posted'] else 'uploaded_status_pending',
                     video_id=receipt['video_id'],youtube_url=receipt['url'],
                     actual_privacy=receipt['actual_privacy'],provider_upload_status=receipt['provider_upload_status'],
                     verified_channel_id=receipt['verified_channel_id'],published_at=receipt['published_at'])
    fd,index=tempfile.mkstemp(prefix='publication-receipt-index-');os.close(fd);os.unlink(index)
    env=os.environ.copy();env['GIT_INDEX_FILE']=index
    env.update(GIT_AUTHOR_NAME='github-actions[bot]',GIT_AUTHOR_EMAIL='41898282+github-actions[bot]@users.noreply.github.com',
               GIT_COMMITTER_NAME='github-actions[bot]',GIT_COMMITTER_EMAIL='41898282+github-actions[bot]@users.noreply.github.com')
    try:
        git('read-tree',parent,env=env)
        files={'channels/ifverse_anime-topics.json':(json.dumps(registry,indent=2)+'\n').encode()}
        for receipt in receipts:files['publication-receipts/'+receipt['id']+'.json']=(json.dumps(receipt,indent=2)+'\n').encode()
        for name,data in files.items():
            blob=git('hash-object','-w','--stdin',input=data).decode().strip()
            git('update-index','--add','--cacheinfo','100644,'+blob+','+name,env=env)
        tree=git('write-tree',env=env).decode().strip()
        commit=git('commit-tree',tree,'-p',parent,env=env,input=b'Record verified YouTube publication receipts and topic status\n').decode().strip()
        subprocess.run(['git','push','origin',commit+':refs/heads/'+source_branch],cwd=ROOT,check=True)
    finally:
        if Path(index).exists():Path(index).unlink()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['restore','save']);args=p.parse_args()
    try:
        restore() if args.operation=='restore' else save()
        print('Encrypted upload state '+args.operation+' completed')
    except Exception:
        print('Upload state could not be safely '+args.operation+'d; preserve existing state and inspect private configuration')
        sys.exit(1)
