import json
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Thread
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts.publishing_accounts import gateway_alias
from whatif.hosted_publishers import Publishers
from whatif.publishing_api import server

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
        code = ('import json,sys; from whatif.publishing_service import Drafts; '
                'print(json.dumps(Drafts(sys.argv[1],sys.argv[2],None).get(sys.argv[3])))')
        restored = json.loads(subprocess.check_output(
            [sys.executable, '-c', code, str(self.root / 'private'), str(self.root), self.preview['draft_id']]))
        self.assertEqual(restored, self.preview)
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
        result = self.service.publish(second['draft_id'],second['snapshot_hash'],['ig'],True)
        receipt = next(r for r in result['deliveries'] if r['alias']=='ig')
        self.assertEqual(receipt['status'], 'duplicate_operation')
        self.assertEqual(receipt['receipt']['original_draft_id'], self.preview['draft_id'])
        self.assertEqual(self.adapter.starts,['ig'])

    def test_changed_binding_and_media_fail_closed(self):
        path = self.root / 'channels/publishing-accounts.json'
        registry = json.loads(path.read_text())
        registry['ig']['account_id'] = '999'
        path.write_text(json.dumps(registry))
        result = self.publish(['ig','fb'])
        self.assertEqual({r['alias']:r['status'] for r in result['deliveries']},
                         {'ig':'blocked_review','fb':'published','yt':'draft'})
        self.assertEqual(self.adapter.starts, ['fb'])

    def test_gateway_draft_and_publish_validate_exact_linked_identity(self):
        token, key = 'a' * 32, 'b' * 32
        publisher = Publishers(self.root, self.service.directory, 'https://fixture.example', key)
        publisher.validate_media = Mock()
        publisher.verify = Mock(side_effect=publisher.operation_grant)
        publisher.start = Mock(return_value={'status': 'submitted', 'provider_id': 'post-123'})
        self.service.adapter = publisher
        http = server(self.service, Mock(), token, key, ('127.0.0.1', 0))
        thread = Thread(target=http.serve_forever)
        thread.start()
        self.addCleanup(http.server_close)
        self.addCleanup(thread.join, 5)
        self.addCleanup(http.shutdown)

        def call(route, args, credential='Bearer ' + token):
            request = Request(f'http://127.0.0.1:{http.server_port}' + route, data=json.dumps(args).encode(),
                              headers={'Authorization': credential, 'Content-Type': 'application/json'})
            with urlopen(request, timeout=4) as response:
                return json.load(response)

        brand = 'ifverse_anime'
        account_id = '739'
        binding = {'brand': brand, 'platform': 'instagram', 'account_id': account_id, 'handle': '@linked'}
        alias = gateway_alias('instagram', account_id)
        draft_args = {'brand': brand, 'destinations': [{**self.rows[0], 'account': alias}]}
        body = {**draft_args, 'account_bindings': {alias: binding}}
        with self.assertRaises(HTTPError) as unauthenticated:
            call('/broker/drafts/create', body, credential='')
        self.assertEqual(unauthenticated.exception.code, 401)
        with self.assertRaises(HTTPError):
            call('/drafts/create', body)
        with self.assertRaises(HTTPError):
            call('/broker/drafts/create', {**body, 'account_bindings': {alias: {**binding, 'account_id': '999'}}})
        existing_id = '123'
        duplicate_alias = gateway_alias('instagram', existing_id)
        with self.assertRaises(HTTPError):
            call('/broker/drafts/create', {'brand': brand, 'destinations': [self.rows[0],
                  {**self.rows[0], 'account': duplicate_alias}],
                  'account_bindings': {duplicate_alias: {**binding, 'account_id': existing_id}}})

        preview = call('/broker/drafts/create', body)
        self.assertEqual(preview['destinations'][0]['account_id'], account_id)
        self.assertEqual(preview['destinations'][0]['handle'], '@linked')
        approved = {'draft_id': preview['draft_id'], 'snapshot_hash': preview['snapshot_hash'],
                    'destinations': [alias], 'approved': True}
        grant = {'platform': 'instagram', 'account_id': account_id, 'token': 'fixture-private-token',
                 'graph_version': 'v25.0', 'page_id': '988'}
        request = {**approved, 'account_grants': {alias: grant}, 'account_bindings': {alias: binding}}
        with self.assertRaises(HTTPError):
            call('/broker/drafts/publish', {**request, 'approved': False})
        with self.assertRaises(HTTPError):
            call('/broker/drafts/publish', {**request, 'account_bindings': {}})
        with self.assertRaises(HTTPError):
            call('/broker/drafts/publish', {**request, 'account_grants': {alias: {**grant, 'account_id': '999'}}})
        publisher.start.assert_not_called()
        result = call('/broker/drafts/publish', request)
        self.assertEqual(result['deliveries'][0]['status'], 'submitted')
        self.assertNotIn(grant['token'], json.dumps(result))
        publisher.start.assert_called_once()
        publisher.read_status = Mock(side_effect=lambda row, state: {
            'status': 'published', 'provider_id': state['receipt']['provider_id']
        } if publisher.operation_grant(row) else None)
        status = call('/broker/drafts/status', {**request, 'draft_id': preview['draft_id']})
        self.assertEqual(status['deliveries'][0]['status'], 'published')
