"""Publish one reviewed YouTube Short or Instagram Reel from a pinned Git result."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import time

from . import publishing_accounts as accounts, publishing_dashboard as queue, publishing_direct as direct

ROOT = accounts.ROOT
REQUEST = re.compile(r'social-publish-requests/[a-z0-9][a-z0-9_-]{0,100}\.json')
COMMIT = re.compile(r'[0-9a-f]{40}')
MAX_MEDIA = 100 * 1024 * 1024


def git(root, *args, data=None):
    return subprocess.check_output(['git', *args], cwd=root, input=data)


def request_from_push(root, before):
    direct.require(COMMIT.fullmatch(before) and before != '0' * 40, 'The push must have a previous commit')
    git(root, 'fetch', '--quiet', '--depth=1', 'origin', before)
    changes = git(root, 'diff', '--name-status', '--no-renames', before, 'HEAD').decode().splitlines()
    direct.require(len(changes) == 1 and changes[0].startswith('A\t') and REQUEST.fullmatch(changes[0][2:]),
                   'Submit exactly one new social publishing JSON in a request-only push')
    return changes[0][2:]


def load_request(root, name):
    direct.require(REQUEST.fullmatch(name), 'Choose a JSON under social-publish-requests/')
    path = (root / name).resolve()
    direct.require(path == root / name and path.stat().st_size <= 250_000, 'Use a bounded request file')
    item = json.loads(path.read_text(encoding='utf-8'))
    direct.require(item['platform'] in ('youtube', 'instagram') and item.get('account')
                   and item.get('schema_version') == 1, 'A named YouTube or Instagram destination is required')
    due = datetime.fromisoformat(queue.validate(root, item))
    _, topic = queue.load_review(root, item)
    ref, commit, video = item['result_branch'], item['result_commit'], item['video']
    direct.require(ref == topic.get('result_branch') and commit == topic.get('result_commit')
                   and COMMIT.fullmatch(commit)
                   and re.fullmatch(re.escape(f'codex/results/{item["episode"]}') + r'(?:-[a-z0-9-]+)?', ref),
                   'Pin the current selected result branch and commit from the topic registry')
    media = PurePosixPath(video)
    direct.require(video == media.as_posix() and '..' not in media.parts and not media.is_absolute()
                   and media.parts[:2] == ('artifacts', item['episode']) and media.suffix == '.mp4'
                   and re.fullmatch(r'[A-Za-z0-9_./-]+', video), 'Use a pinned episode artifact MP4')
    return item, due, accounts.resolve(root, item)


def fetch_media(root, workspace, item):
    ref = 'refs/heads/' + item['result_branch']
    git(root, 'fetch', '--quiet', '--depth=1', 'origin', ref)
    commit = git(root, 'rev-parse', 'FETCH_HEAD').decode().strip()
    direct.require(commit == item['result_commit'], 'The result branch moved since review')
    object_name = f'{commit}:{item["video"]}'
    direct.require(git(root, 'cat-file', '-t', object_name).strip() == b'blob'
                   and 0 < int(git(root, 'cat-file', '-s', object_name)) <= MAX_MEDIA,
                   'Use a nonempty Git media blob up to 100 MiB')
    path = workspace / item['video']
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as output:
        subprocess.run(['git', 'cat-file', 'blob', object_name], cwd=root, stdout=output, check=True)


class Receipt:
    """A provider-account/episode receipt committed before and after each remote write."""

    def __init__(self, root, item):
        self.root = root
        identity = {key: item[key] for key in ('brand', 'episode', 'platform', 'account_id')}
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        self.ref = f'refs/heads/codex/social-receipts/{key}'
        self.fields = {**identity, 'account': item['account'], 'video_sha256': item['video_sha256'],
                       'receipt_branch': self.ref.removeprefix('refs/heads/'),
                       'request_sha256': hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()}
        refs = git(root, 'ls-remote', 'origin', self.ref).decode().splitlines()
        self.head = None
        self.state = None
        if refs:
            git(root, 'fetch', '--quiet', '--depth=1', 'origin', self.ref)
            self.head = git(root, 'rev-parse', 'FETCH_HEAD').decode().strip()
            self.state = json.loads(git(root, 'show', f'{self.head}:receipt.json'))
            direct.require(all(self.state.get(k) == v for k, v in self.fields.items()),
                           'This episode and account already have a different publishing operation')

    def save(self, status, **values):
        record = {**(self.state or self.fields), **values, 'status': status,
                  'updated_at': datetime.now(timezone.utc).isoformat()}
        blob = git(self.root, 'hash-object', '-w', '--stdin', data=json.dumps(record).encode()).strip()
        tree = git(self.root, 'mktree', data=b'100644 blob ' + blob + b'\treceipt.json\n').decode().strip()
        parent = ('-p', self.head) if self.head else ()
        commit = git(self.root, '-c', 'user.name=github-actions[bot]',
                     '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
                     'commit-tree', tree, *parent, '-m', f'Record social publication status: {status}').decode().strip()
        git(self.root, 'push', '--quiet', 'origin', f'{commit}:{self.ref}')
        self.head, self.state = commit, record

    def checkpoint(self, phase, resource):
        self.save('working', checkpoint=phase, checkpoint_id=resource)

    def result(self, status, resource, url):
        self.save(status, provider_id=resource, url=url if url and queue.https(url) else None)
        return self.state


def publish_youtube(root, item, binding, receipt, workspace, prepared):
    state = receipt.state or {}
    with accounts.youtube_session(root, item['account'], binding) as session:
        video_id = state.get('provider_id') if state.get('status') == 'submitted' else state.get('checkpoint_id')
        if video_id:
            direct.require(re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id), 'Invalid YouTube receipt video ID')
            result = queue.youtube_result(session, {'video_id': video_id, 'verified_channel_id': item['account_id'],
                'url': 'https://www.youtube.com/shorts/' + video_id})
        else:
            receipt.save('working')
            result = queue.named_youtube(workspace, item, session, prepared, receipt.checkpoint)
    return receipt.result(*result)


def publish_instagram(root, item, binding, receipt, data):
    config = accounts.grant(root, item['account'])
    direct.require(config.get('page_id'), 'Hosted Instagram requires a Facebook Login grant with a linked Page')
    provider = direct.client('instagram', binding['account_id'], config)
    provider.verify(binding['account_id'])
    state = receipt.state or {}
    if state.get('status') == 'submitted':
        resource = state['provider_id']
        status, url = provider.status(resource)
        return receipt.result(status, resource, url)

    if state.get('status') == 'processing':
        receipt.save('working')
        result = provider.finish_instagram(state['provider_id'], receipt.checkpoint)
    else:
        receipt.save('working')
        result = provider.publish(item, data, receipt.checkpoint)
    receipt.result(*result)
    for _ in range(20):
        if result[0] != 'processing':
            break
        time.sleep(5)
        result = provider.finish_instagram(result[1], receipt.checkpoint)
        if result[0] != 'processing':
            receipt.result(*result)
    if result[0] == 'submitted':
        status, url = provider.status(result[1])
        receipt.result(status, result[1], url)
    return receipt.state


def run(root, name, execute):
    item, due, binding = load_request(root, name)
    if execute:
        direct.require(due <= datetime.now(timezone.utc), 'Hosted requests must be due when submitted')
        receipt = Receipt(root, item)
        status = (receipt.state or {}).get('status')
        if status in ('published', 'failed'):
            return receipt.state
        if status == 'working' and item['platform'] == 'youtube' and receipt.state.get('checkpoint') == 'video_id':
            return publish_youtube(root, item, binding, receipt, None, None)
        direct.require(status != 'working', f'Inspect {receipt.fields["receipt_branch"]} before retrying an uncertain upload')
        if status == 'submitted':
            if item['platform'] == 'youtube':
                return publish_youtube(root, item, binding, receipt, None, None)
            return publish_instagram(root, item, binding, receipt, None)
        if status == 'processing':
            return publish_instagram(root, item, binding, receipt, None)

    with tempfile.TemporaryDirectory(prefix='ifverse-social-') as temp:
        workspace = Path(temp)
        (workspace / 'channels').symlink_to(root / 'channels', target_is_directory=True)
        fetch_media(root, workspace, item)
        if item['platform'] == 'youtube':
            prepared = queue.named_youtube_preflight(workspace, item)
            if execute:
                return publish_youtube(root, item, binding, receipt, workspace, prepared)
        else:
            data = queue.read_video(workspace, item)
            if execute:
                return publish_instagram(root, item, binding, receipt, data)
    return {'status': 'validated', 'platform': item['platform'], 'account': item['account'], 'episode': item['episode']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--request')
    source.add_argument('--push-before')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    try:
        name = args.request or request_from_push(ROOT, args.push_before)
        result = run(ROOT, name, args.publish)
        print(json.dumps(result))
        return 0 if result['status'] in ('validated', 'published', 'submitted', 'processing') else 1
    except direct.PublishingError as error:
        print(str(error), file=sys.stderr)
    except (OSError, KeyError, TypeError, ValueError, RuntimeError, ImportError, subprocess.SubprocessError):
        print('Social publishing stopped. Check the request, private account setup and existing receipt.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
