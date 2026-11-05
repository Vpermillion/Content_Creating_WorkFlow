from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts import publishing_dashboard as publish


class PublishingDashboardTests(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        db = publish.open_state(self.root / 'queue.db')
        self.addCleanup(db.close)
        self.db = db
        (self.root / 'channels').mkdir()
        (self.root / 'artifacts').mkdir()
        video = b'reviewed video bytes'
        (self.root / 'artifacts/video.mp4').write_bytes(video)
        sha = hashlib.sha256(video).hexdigest()
        self.topic = {'id': 'episode', 'state': 'rendered', 'script_sha256': 'script',
                      'video_sha256': sha, 'owner_topic_choice': {
                          'status': 'approved', 'selected_by': 'owner', 'selected_at': 'now',
                          'decision_reference': 'review note', 'script_sha256': 'script'}}
        self.save_topic()
        self.item = {'brand': 'ifverse_anime', 'episode': 'episode', 'platform': 'facebook',
                     'account_id': 'a' * 24, 'expected_username': 'ifverse',
                     'scheduled_for': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                     'video': 'artifacts/video.mp4', 'master_sha256': sha, 'video_sha256': sha,
                     'caption': 'Reviewed caption', 'title': 'Episode', 'review': {
                         'approved_video_sha256': sha, 'source_use': 'approved', 'audiovisual': 'approved',
                         'reviewed_by': 'owner', 'evidence': 'review note', 'synthetic_disclosure': False,
                         'audience': 'not_made_for_kids'}}
        self.provider = Mock()
        self.provider.accounts.return_value = [{'_id': 'a' * 24, 'platform': 'facebook', 'username': 'ifverse'}]
        self.provider.upload.return_value = 'https://media.example/clip.mp4'
        self.provider.api.return_value = {'post': {'_id': 'b' * 24, 'status': 'scheduled',
                                                   'platforms': [{'platform': 'facebook', 'status': 'pending',
                                                                  'accountId': 'a' * 24}]}}
        self.set_duration(59.9)

    def save_topic(self):
        (self.root / 'channels/ifverse_anime-topics.json').write_text(json.dumps({'topics': [self.topic]}))

    def set_duration(self, seconds):
        probe = {'format': {'duration': seconds},
                 'streams': [{'codec_type': 'video', 'width': 720, 'height': 1280}, {'codec_type': 'audio'}]}
        patcher = patch.object(publish.subprocess, 'run', return_value=SimpleNamespace(stdout=json.dumps(probe)))
        patcher.start()
        self.addCleanup(patcher.stop)

    def schedule(self):
        return publish.schedule(self.db, self.root, self.item, self.provider)

    def test_schedules_reel_and_shows_it_in_dashboard(self):
        self.assertEqual(self.schedule(), 'b' * 24)
        endpoint, payload, operation = self.provider.api.call_args.args
        self.assertEqual(endpoint, 'posts')
        self.assertTrue(operation)
        self.assertEqual(payload['platforms'][0]['platformSpecificData']['contentType'], 'reel')
        self.assertEqual(payload['mediaItems'][0]['url'], 'https://media.example/clip.mp4')
        out = self.root / 'queue.html'
        publish.dashboard(self.db, out, self.provider.accounts())
        html = out.read_text(encoding='utf-8')
        self.assertIn('scheduled', html)
        self.assertNotIn('media.example', html)
        self.assertIn('Snapchat', html)

    def test_uncertain_result_blocks_duplicate_submission(self):
        self.provider.api.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError):
            self.schedule()
        with self.assertRaisesRegex(publish.PublishingError, 'job already exists'):
            self.schedule()
        self.provider.upload.assert_called_once()
        self.provider.api.assert_called_once()

    def test_sixty_one_second_reel_never_uploads(self):
        self.set_duration(61)
        with self.assertRaisesRegex(publish.PublishingError, '60 second'):
            self.schedule()
        self.provider.upload.assert_not_called()

    def test_pending_owner_decision_never_uploads(self):
        self.topic['owner_topic_choice']['status'] = 'pending_owner_choice'
        self.save_topic()
        with self.assertRaisesRegex(publish.PublishingError, 'owner decision'):
            self.schedule()
        self.provider.upload.assert_not_called()

    def test_wrong_account_never_uploads(self):
        self.item['expected_username'] = 'different'
        with self.assertRaisesRegex(publish.PublishingError, 'Connected account'):
            self.schedule()
        self.provider.upload.assert_not_called()
