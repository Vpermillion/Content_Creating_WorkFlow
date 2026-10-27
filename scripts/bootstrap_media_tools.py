"""Install a checksum-pinned FFmpeg/ffprobe pair for minimal Linux runners."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request

CONFIG = {"url":"https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-10-26-14-25/ffmpeg-N-128100-gceb466cbcd-linux64-gpl.tar.xz","sha256":"cd6219478e044024cea76bbd3e053bd85b57485381d5c61e72415c8e8b8db9cd","max_bytes":209715200}


def install(root, config=CONFIG):
    root = Path(root).resolve()
    marker = root / 'verified.json'
    if marker.exists():
        prior = json.loads(marker.read_text())
        if prior.get('archive_sha256') == config['sha256'] and all(
            (root/'bin'/name).is_file() and hashlib.sha256((root/'bin'/name).read_bytes()).hexdigest() == checksum
            for name, checksum in prior['binaries'].items()
        ) and set(prior['binaries']) == {'ffmpeg','ffprobe'}:
            return {'status':'ok','cached':True,'downloaded_bytes':0,'bin':str(root/'bin')}
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        archive = Path(temporary)/'tools.tar.xz'
        checksum = hashlib.sha256()
        count = 0
        with urllib.request.urlopen(config['url'],timeout=30) as response, archive.open('wb') as output:
            while chunk := response.read(1024*1024):
                count += len(chunk)
                if count > config['max_bytes']:
                    raise ValueError('tool_archive_too_large')
                checksum.update(chunk);output.write(chunk)
        if checksum.hexdigest() != config['sha256']:
            raise ValueError('tool_archive_checksum_mismatch')
        binaries = {}
        with tarfile.open(archive,'r:xz') as source:
            for member in source:
                name = Path(member.name).name
                if name not in {'ffmpeg','ffprobe'} or not member.name.endswith('/bin/'+name) or not member.isfile():
                    continue
                if member.size > 500*1024*1024:
                    raise ValueError('tool_binary_too_large')
                data = source.extractfile(member).read()
                target = root/'bin'/name
                target.parent.mkdir(parents=True,exist_ok=True)
                pending = target.with_suffix('.tmp')
                pending.write_bytes(data);pending.chmod(0o755);pending.replace(target)
                binaries[name] = hashlib.sha256(data).hexdigest()
        if set(binaries) != {'ffmpeg','ffprobe'}:
            raise ValueError('missing_tool_binary')
        marker.write_text(json.dumps({'archive_sha256':config['sha256'],'binaries':binaries})+'\n')
    return {'status':'ok','cached':False,'downloaded_bytes':count,'bin':str(root/'bin')}


if __name__ == '__main__':
    result = install(os.environ.get('IFVERSE_TOOLS_ROOT','private/hosted-tools'))
    if os.environ.get('GITHUB_PATH'):
        with open(os.environ['GITHUB_PATH'],'a') as output:
            output.write(result['bin']+'\n')
    print(json.dumps(result))

