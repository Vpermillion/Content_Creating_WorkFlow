"""Callable bridge to the existing bounded media renderer, never a shell runner.

Only checked-in review requests are executable. Existing topic-choice and script
validation still run. Production output lives on the private service volume.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from urllib.parse import quote, urlencode
from urllib.request import Request, build_opener

from scripts.publishing_accounts import BRAND
from scripts.publishing_direct import NoRedirect, require
from . import youtube


class MediaJobs:
    def __init__(self, root, directory, drafts):
        self.root, self.directory, self.drafts = Path(root), Path(directory) / 'media-jobs', drafts
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=1)

    def path(self, job):
        require(isinstance(job, str) and re.fullmatch('[a-z0-9][a-z0-9_-]{0,79}', job), 'Invalid media job ID')
        return self.directory / (job + '.json')

    def submit(self, request_id):
        path = self.path(request_id)
        request_path = self.root / 'review-requests' / (request_id + '.json')
        require(request_path.is_file() and not request_path.is_symlink(), 'Choose a checked-in review request')
        request = json.loads(request_path.read_text())
        require(request['id'] == request_id, 'Request ID mismatch')
        sha = hashlib.sha256(request_path.read_bytes()).hexdigest()
        # A prior job is returned, never silently rerendered after a crash.
        with youtube.file_lock(self.directory / '.submit.lock'):
            if path.exists():
                result = json.loads(path.read_text())
                require(result['request_sha256'] == sha, 'Request changed; use a new job ID')
                return result
            record = {'job_id': request_id, 'request_sha256': sha, 'status': 'queued'}
            youtube.atomic_json(path, record)
            self.executor.submit(self.run, request, record)
        return record

    def run(self, request, record):
        path = self.path(record['job_id'])
        output = self.directory / record['job_id']
        record = {**record, 'status': 'working'}
        youtube.atomic_json(path, record)
        try:
            # Reuse all existing source, voice, caption, edit and owner-choice checks.
            from scripts.render_test_video import run
            report = run(request, output, self.directory / 'cache' / 'models')
            require(report['status'] == 'success', 'Renderer did not succeed')
            selected = report['video']
            media_path = (output / selected).resolve()
            require(media_path.is_relative_to(output.resolve()) and media_path.is_file(), 'Invalid renderer output')
            sha = self.drafts.put_media(media_path.read_bytes())
            record.update(status='prepared', media_sha256=sha,
                          next_action='Review actual media and source evidence; create a draft with per-platform captions. '
                          'Update the selected master in the topic registry through the existing review process.')
        except Exception:
            record.update(status='needs_attention', next_action='Inspect private media job output; no automatic rerender or publication.')
        youtube.atomic_json(path, record)

    def get(self, request_id):
        path = self.path(request_id)
        require(path.is_file(), 'Media job not found')
        return json.loads(path.read_text())

    def import_result(self, brand, episode, export='master'):
        self.path(episode)
        require(export in ('master', 'facebook_reel', 'jpeg'), 'Choose a supported media export')
        require(isinstance(brand, str) and BRAND.fullmatch(brand), 'Choose a registered brand')
        registry = json.loads((self.root / 'channels' / (brand + '-topics.json')).read_text(encoding='utf-8'))
        matches = [row for row in registry['topics'] if row['id'] == episode]
        require(len(matches) == 1, 'Choose one registered episode')
        topic = matches[0]
        path, commit, checksum = (topic.get(field) for field in ('video_path', 'result_commit', 'video_sha256'))
        require(isinstance(commit, str) and re.fullmatch('[0-9a-f]{40}', commit)
                and isinstance(checksum, str) and re.fullmatch('[0-9a-f]{64}', checksum)
                and isinstance(path, str) and re.fullmatch(r'(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_.-]+\.mp4', path),
                'The episode needs a selected, pinned MP4 from the topic registry')
        if not self.drafts.media(checksum).is_file():
            token = os.getenv('IFVERSE_GITHUB_READ_TOKEN')
            require(token, 'Set a read-only GitHub repo token in the hosting settings')
            name = quote(f'artifacts/{episode}/{path}', safe='/')
            url = 'https://api.github.com/repos/Vpermillion/Content_Creating_WorkFlow/contents/' + name
            request = Request(url + '?' + urlencode({'ref': commit}), headers={
                'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github.raw+json',
                'User-Agent': 'Ifverse-publishing',
            })
            with build_opener(NoRedirect()).open(request, timeout=35) as response:
                data = response.read(100 * 1024 * 1024 + 1)
            require(len(data) <= 100 * 1024 * 1024 and hashlib.sha256(data).hexdigest() == checksum,
                    'GitHub media did not match the selected render')
            self.drafts.put_media(data)
        output_sha = checksum if export == 'master' else self.export_media(checksum, export)
        return {'status': 'prepared', 'episode': episode, 'export': export, 'media_sha256': output_sha,
                'manifest': {'brand': brand, 'episode': episode, 'master_sha256': checksum, 'video_sha256': output_sha},
                'preview_url': self.drafts.adapter.media_url(output_sha)}

    def export_media(self, checksum, export):
        source = self.drafts.media(checksum)
        with source.open('rb') as stream:
            require(hashlib.file_digest(stream, 'sha256').hexdigest() == checksum, 'The selected master changed')
        with TemporaryDirectory(dir=self.directory) as directory:
            if export == 'jpeg':
                path = Path(directory) / 'frame.jpg'
                args = ['-ss', '1', '-i', str(source), '-frames:v', '1', '-vf',
                        'scale=720:900:force_original_aspect_ratio=increase,crop=720:900', '-q:v', '2']
            else:
                path = Path(directory) / 'facebook.mp4'
                args = ['-i', str(source), '-t', '59.9', '-map', '0:v:0', '-map', '0:a:0',
                        '-c:v', 'libx264', '-threads:v', '1', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
                        '-movflags', '+faststart']
            try:
                subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-xerror', *args, str(path)],
                               capture_output=True, check=True, timeout=180)
                require(path.is_file() and 0 < path.stat().st_size <= 100 * 1024 * 1024,
                        'The export was missing or exceeded the media limit')
                return self.drafts.put_media(path.read_bytes())
            except (OSError, subprocess.SubprocessError):
                raise ValueError('Could not prepare the selected export') from None
