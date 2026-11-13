import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from whatif.publishing_service import Drafts


class Adapter:
    def __init__(self):
        self.starts, self.resumes, self.expired, self.uncertain = [], [], set(), set()

    def validate_media(self, row, path):
        pass

    def verify(self, row):
        if row['account'] in self.expired:
            raise RuntimeError('token must never appear')

    def start(self, row, path, draft, checkpoint):
        alias = row['account']
        self.starts.append(alias)
        checkpoint({'checkpoint': 'container_id', 'checkpoint_id': '123'})
        if alias in self.uncertain:
            raise RuntimeError('uncertain upload')
        return {'status': 'published', 'provider_id': alias, 'url': 'https://example.test/' + alias}

    def reconcile(self, row, path, draft, state, checkpoint):
        self.resumes.append((row['account'], state['receipt']))
        return {'status': 'published', 'provider_id': row['account'], 'url': 'https://example.test/result'}


class DraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'channels').mkdir()
        registry = {a: {'brand': 'ifverse_anime', 'platform': p, 'account_id': n, 'handle': '@fictional'}
                    for a,p,n in [('ig','instagram','123'),('fb','facebook','456'),('yt','youtube','UCfictional')]}
        (self.root / 'channels/publishing-accounts.json').write_text(json.dumps(registry))
        self.adapter = Adapter()
        self.service = Drafts(self.root / 'private', self.root, self.adapter)
        sha = self.service.put_media(b'fictional mocked media')
        (self.root / 'channels/ifverse_anime-topics.json').write_text(json.dumps({'topics':
            [{'id':'fixture','video_sha256':sha}]}))
        self.rows = [{'account': a, 'format': f, 'title': 'Review fixture', 'caption': a + ' caption',
                     'media_sha256': sha, 'manifest': {'brand':'ifverse_anime', 'episode':'fixture', 'master_sha256':sha, 'video_sha256':sha}}
                    for a,f in [('ig','reel'),('fb','reel'),('yt','short')]]
        self.review = patch('scripts.publishing_dashboard.load_review')
        self.review.start()
        self.preview = self.service.create('ifverse_anime', self.rows)

    def tearDown(self):
        self.review.stop()
        self.temp.cleanup()

    def publish(self, aliases):
        return self.service.publish(self.preview['draft_id'], self.preview['snapshot_hash'], aliases, True)

    def test_retrieve_fresh_session_and_exact_subset(self):
        fresh = Drafts(self.root / 'private', self.root, self.adapter)
        self.assertEqual(fresh.get(self.preview['draft_id']), self.preview)
        self.publish(['ig'])
        self.assertEqual(self.adapter.starts, ['ig'])
        self.publish(['ig'])
        self.assertEqual(self.adapter.starts, ['ig'])
        self.assertEqual(self.adapter.resumes, [])

    def test_partial_failure_retry_never_reposts_success(self):
        self.adapter.uncertain.add('fb')
        result = self.publish(['ig','fb','yt'])
        self.assertEqual({r['alias']:r['status'] for r in result['deliveries']},
                         {'ig':'published','fb':'needs_reconciliation','yt':'published'})
        self.publish(['fb'])
        self.assertEqual(self.adapter.starts, ['ig','fb','yt'])
        self.assertEqual(self.adapter.resumes, [('fb', {'checkpoint':'container_id','checkpoint_id':'123'})])

    def test_expired_grant_no_write_then_reconnect(self):
        self.adapter.expired.add('ig')
        result = self.publish(['ig'])
        self.assertEqual(next(r for r in result['deliveries'] if r['alias']=='ig')['status'], 'awaiting_consent')
        self.assertFalse(self.adapter.starts)
        self.adapter.expired.clear()
        self.publish(['ig'])
        self.assertEqual(self.adapter.starts, ['ig'])

    def test_approval_hash_and_destination_are_required(self):
        for hashed, selected, approved in [('wrong',['ig'],True), (self.preview['snapshot_hash'],['unknown'],True),
                (self.preview['snapshot_hash'],['ig'],False)]:
            with self.assertRaises(ValueError):
                self.service.publish(self.preview['draft_id'],hashed,selected,approved)
        self.assertFalse(self.adapter.starts)

    def test_duplicate_draft_cannot_bypass_destination_operation(self):
        second = self.service.create('ifverse_anime', self.rows)
        self.publish(['ig'])
        with self.assertRaises(ValueError):
            self.service.publish(second['draft_id'],second['snapshot_hash'],['ig'],True)
        self.assertEqual(self.adapter.starts,['ig'])

    def test_changed_binding_and_media_fail_closed(self):
        path = self.root / 'channels/publishing-accounts.json'
        registry = json.loads(path.read_text())
        registry['ig']['account_id'] = '999'
        path.write_text(json.dumps(registry))
        with self.assertRaises(ValueError):
            self.publish(['ig'])
        self.assertFalse(self.adapter.starts)
