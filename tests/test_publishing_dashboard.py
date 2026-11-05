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
        self.provider.publish.return_value = ('submitted', '12345', None)
        provider = patch.object(publish.direct, 'client', return_value=self.provider)
        provider.start()
        self.addCleanup(provider.stop)
        self.now = datetime.now(timezone.utc) + timedelta(hours=2)
        self.set_duration(59.9)

    def save_topic(self):
        (self.root / 'channels/ifverse_anime-topics.json').write_text(json.dumps({'topics': [self.topic]}))

    def set_duration(self, seconds):
        probe = {'format': {'duration': seconds},
                 'streams': [{'codec_type': 'video', 'width': 720, 'height': 1280}, {'codec_type': 'audio'}]}
        patcher = patch.object(publish.subprocess, 'run', return_value=SimpleNamespace(stdout=json.dumps(probe)))
        patcher.start()
        self.addCleanup(patcher.stop)

    def queue(self):
        return publish.enqueue(self.db, self.root, self.item)

    def worker(self):
        return publish.run_due(self.db, self.root, self.now)

    def test_future_job_waits_then_submits_once(self):
        self.assertEqual(self.queue(), 1)
        self.assertEqual(publish.run_due(self.db, self.root, datetime.now(timezone.utc)), [])
        self.assertEqual(self.worker()[0]['status'], 'submitted')
        self.assertEqual(self.worker(), [])
        self.provider.publish.assert_called_once()
        self.provider.verify.assert_called_once_with(self.item['account_id'])
        with self.assertRaisesRegex(publish.PublishingError, 'already has a job'):
            self.queue()

    def test_uncertain_post_is_never_automatically_retried(self):
        self.queue()
        self.provider.publish.side_effect = TimeoutError()
        self.assertEqual(self.worker()[0]['status'], 'needs_reconciliation')
        self.assertEqual(self.worker(), [])
        self.provider.publish.assert_called_once()

    def test_sixty_one_second_facebook_reel_never_uploads(self):
        self.queue()
        self.set_duration(61)
        self.assertEqual(self.worker()[0]['status'], 'awaiting_setup_or_review')
        self.provider.publish.assert_not_called()

    def test_review_is_rechecked_at_dispatch(self):
        self.queue()
        self.topic['owner_topic_choice']['status'] = 'pending_owner_choice'
        self.save_topic()
        self.assertEqual(self.worker()[0]['status'], 'awaiting_setup_or_review')
        self.provider.publish.assert_not_called()

    def test_tiktok_appears_as_manual_in_dashboard(self):
        self.item['platform'] = 'tiktok'
        self.queue()
        self.assertEqual(self.worker()[0]['status'], 'manual_action_required')
        out = self.root / 'dashboard.html'
        publish.dashboard(self.db, out, None)
        self.assertIn('Open TikTok Studio', out.read_text(encoding='utf-8'))
        self.provider.publish.assert_not_called()

    def test_instagram_resumes_processing_container(self):
        self.item['platform'] = 'instagram'
        self.queue()
        self.provider.publish.return_value = ('processing', '12345', None)
        self.provider.finish_instagram.return_value = ('submitted', '67890', None)
        self.assertEqual(self.worker()[0]['status'], 'processing')
        self.assertEqual(self.worker()[0]['status'], 'submitted')
        self.assertEqual(self.provider.finish_instagram.call_args.args[0], '12345')
        self.provider.publish.assert_called_once()

    def test_provider_status_supplies_post_link(self):
        self.queue()
        self.worker()
        self.provider.status.return_value = ('published', '/reel/12345')
        publish.refresh(self.db)
        row = self.db.execute('SELECT status, url FROM posts').fetchone()
        self.assertEqual(tuple(row), ('published', 'https://www.facebook.com/reel/12345'))


class DirectClientsTests(unittest.TestCase):
    def test_facebook_upload_stays_on_meta_and_uses_same_video_id(self):
        with patch.dict(publish.os.environ, {'IFVERSE_FB_PAGE_ID': '42', 'IFVERSE_FB_PAGE_TOKEN': 'fixture',
                                           'IFVERSE_META_GRAPH_VERSION': 'v25.0'}):
            client = publish.direct.Meta('facebook')
        checkpoint = Mock()
        with patch.object(publish.direct, 'request', side_effect=[
                {'id': '42', 'name': 'Ifverse'},
                {'video_id': '12345', 'upload_url': 'https://rupload.facebook.com/video-upload/v25.0/12345'},
                {'success': True}, {'success': True}]) as request:
            self.assertEqual(client.verify('42'), 'Ifverse')
            self.assertEqual(client.publish({'title': 'Title', 'caption': 'Caption'}, b'video', checkpoint),
                             ('submitted', '12345', None))
        self.assertEqual(request.call_args_list[2].args[2], b'video')
        self.assertIn(b'video_id=12345', request.call_args_list[3].args[2])
        checkpoint.assert_called_with('finishing_video_id', '12345')

    def test_rejects_foreign_upload_host_before_sending_credentials(self):
        with patch.dict(publish.os.environ, {'IFVERSE_FB_PAGE_ID': '42', 'IFVERSE_FB_PAGE_TOKEN': 'fixture',
                                           'IFVERSE_META_GRAPH_VERSION': 'v25.0'}):
            client = publish.direct.Meta('facebook')
        with patch.object(publish.direct, 'request') as request:
            with self.assertRaisesRegex(publish.PublishingError, 'Unexpected Meta upload URL'):
                client.upload_bytes('https://untrusted.example/video-upload/12345', '12345', b'video', 'video-upload')
            request.assert_not_called()
