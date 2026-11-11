from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from scripts import publish_social as social
from whatif import youtube_publish


class HostedPublishingTests(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        base = Path(folder.name)
        self.root = base / 'workflow'
        self.root.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('init', '--bare', '-q', str(base / 'remote.git'))
        self.git('remote', 'add', 'origin', str(base / 'remote.git'))
        media = self.root / 'artifacts/episode/reel.mp4'
        media.parent.mkdir(parents=True)
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i',
                        'color=c=black:s=576x1024:r=10', '-f', 'lavfi', '-i', 'anullsrc',
                        '-t', '3.5', '-c:v', 'libx264', '-c:a', 'aac', str(media)], check=True)
        fingerprint = hashlib.sha256(media.read_bytes()).hexdigest()
        self.git('add', 'artifacts')
        self.git('commit', '-qm', 'Fixture media')
        commit = self.git('rev-parse', 'HEAD').decode().strip()
        self.git('push', '-q', 'origin', 'HEAD:refs/heads/codex/results/episode')
        self.item = {'schema_version': 1, 'brand': 'ifverse_anime', 'episode': 'episode', 'platform': 'instagram',
                     'account': 'anime-instagram', 'account_id': '42', 'owner_requested_publication': True,
                     'scheduled_for': datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat(),
                     'result_branch': 'codex/results/episode', 'result_commit': commit,
                     'video': 'artifacts/episode/reel.mp4', 'title': 'Fixture', 'caption': 'Fixture caption',
                     'video_sha256': fingerprint, 'master_sha256': fingerprint, 'review': {
                         'approved_video_sha256': fingerprint, 'source_use': 'approved', 'audiovisual': 'approved',
                         'reviewed_by': 'fixture', 'evidence': 'fixture', 'synthetic_disclosure': False,
                         'audience': 'not_made_for_kids'}}
        (self.root / 'channels').mkdir()
        (self.root / 'social-publish-requests').mkdir()
        self.name = 'social-publish-requests/reel.json'
        self.write(self.name, self.item)
        self.write('channels/publishing-accounts.json', {'anime-instagram': {
            'brand': 'ifverse_anime', 'platform': 'instagram', 'account_id': '42'}})
        self.write('channels/ifverse_anime-topics.json', {'topics': [{
            'id': 'episode', 'state': 'rendered', 'video_sha256': fingerprint,
            'result_branch': self.item['result_branch'], 'result_commit': commit, 'script_sha256': 'script',
            'owner_topic_choice': {'status': 'approved', 'selected_by': 'owner', 'selected_at': 'now',
                                   'decision_reference': 'fixture', 'script_sha256': 'script'},
        }]})

    def git(self, *args):
        return social.git(self.root, *args)

    def write(self, name, data):
        (self.root / name).write_text(json.dumps(data))

    def test_dry_run_validates_real_git_media_without_loading_grants(self):
        with patch.object(social.accounts, 'grant') as grant:
            self.assertEqual(social.run(self.root, self.name, False)['status'], 'validated')
        grant.assert_not_called()

    def test_hosted_publish_uses_account_grant_and_records_one_provider_write(self):
        provider = Mock()
        provider.publish.return_value = ('submitted', '123', None)
        provider.status.return_value = ('published', 'https://www.instagram.com/reel/fixture/')
        grant = {'token': 'test-secret', 'page_id': '100', 'graph_version': 'v25.0'}
        with patch.object(social.accounts, 'grant', return_value=grant), \
                patch.object(social.direct, 'client', return_value=provider) as factory:
            receipt = social.run(self.root, self.name, True)
            self.assertEqual(receipt, social.run(self.root, self.name, True))
        self.assertEqual(receipt['status'], 'published')
        self.assertNotIn('test-secret', json.dumps(receipt))
        factory.assert_called_once_with('instagram', '42', grant)
        provider.verify.assert_called_once_with('42')
        provider.publish.assert_called_once()

    def test_interrupted_provider_write_is_held_on_rerun(self):
        receipt = social.Receipt(self.root, self.item)
        receipt.save('working', checkpoint='publishing_container_id', checkpoint_id='123')
        with patch.object(social.accounts, 'grant') as grant:
            with self.assertRaisesRegex(social.direct.PublishingError, 'uncertain upload'):
                social.run(self.root, self.name, True)
        grant.assert_not_called()

    def test_push_only_accepts_one_new_request(self):
        self.git('add', 'channels')
        self.git('commit', '-qm', 'Fixture account registry')
        before = self.git('rev-parse', 'HEAD').decode().strip()
        self.git('push', '-q', 'origin', 'HEAD:refs/heads/workflow')
        self.git('add', self.name)
        self.git('commit', '-qm', 'Fixture request')
        self.assertEqual(social.request_from_push(self.root, before), self.name)
        self.write('extra.json', {})
        self.git('add', 'extra.json')
        self.git('commit', '-qm', 'Fixture unrelated change')
        with self.assertRaisesRegex(social.direct.PublishingError, 'exactly one'):
            social.request_from_push(self.root, before)


class YoutubeAccountTests(unittest.TestCase):
    def test_upload_refuses_a_grant_that_exposes_multiple_channels(self):
        channels = [{'id': 'UC' + 'a' * 22}, {'id': 'UC' + 'b' * 22}]
        with patch.object(youtube_publish.yt, 'owned_channels', return_value=channels):
            with self.assertRaisesRegex(youtube_publish.UploadError, 'exactly one'):
                youtube_publish.upload_channel(None, None, channels[0]['id'], None)
