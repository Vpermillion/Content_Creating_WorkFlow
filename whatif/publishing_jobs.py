"""Callable bridge to the existing bounded media renderer, never a shell runner.

Only checked-in review requests are executable. Existing topic-choice and script
validation still run. Production output lives on the private service volume.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re

from scripts.publishing_direct import require
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
