from base64 import b64encode
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from whatif.hosted_publishers import Publishers
from whatif.publishing_api import server
from whatif.publishing_service import Drafts


class StudioBrowserTests(unittest.TestCase):
    def test_browser_confirmation_is_separate_from_the_chat_bearer(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'channels').mkdir()
            binding = {'account_id':'fictional','platform':'tiktok','brand':'anime','handle':'@fictional'}
            (root / 'channels/publishing-accounts.json').write_text(json.dumps({'tt':binding}))
            token, key, password = 'a'*32, 'b'*32, 'c'*32
            origin = 'https://example.test'
            publisher = Publishers(root, root / 'private', origin, key)
            drafts = Drafts(publisher.state, root, publisher)
            http = server(drafts, None, token, key, ('127.0.0.1', 0), owner_password=password)
            thread = Thread(target=http.serve_forever)
            thread.start()
            self.addCleanup(http.server_close)
            self.addCleanup(thread.join, 5)
            self.addCleanup(http.shutdown)
            base = f'http://127.0.0.1:{http.server_port}'
            owner = 'Basic ' + b64encode(('owner:'+password).encode()).decode()

            def call(path, auth, data, content='application/json', form_origin=origin):
                request = Request(base + path, data=data,
                                  headers={'Authorization':auth, 'Origin':form_origin, 'Content-Type':content})
                with urlopen(request, timeout=4) as response:
                    return response.read()

            def form(auth, fields, form_origin=origin):
                return call('/owner/studio', auth, urlencode(fields).encode(),
                            'application/x-www-form-urlencoded', form_origin)

            account = {'account':'tt','observed_handle':'@fictional'}
            with self.assertRaises(HTTPError) as failure:
                form('Bearer '+token, account)
            self.assertEqual(failure.exception.code, 401)
            with self.assertRaises(HTTPError):
                form(owner, account, 'https://wrong.example')
            with self.assertRaises(HTTPError):
                form(owner, {**account, 'observed_handle':'@other'})
            form(owner, account)
            self.assertEqual(publisher.verify({**binding, 'account':'tt'})['identity_status'], 'studio_operator_confirmed')

            row = {**binding, 'account':'tt', 'caption':'reviewed', 'media_sha256':'a'*64}
            from whatif.publishing_service import canonical, fingerprint
            for draft_id in ('first','second'):
                snapshot = {'brand':'anime','destinations':[row]}
                with drafts.db() as db:
                    db.execute('INSERT INTO drafts VALUES (?,?,?)', (draft_id, canonical(snapshot), fingerprint(snapshot)))
                    receipt = {'handed_off_at':datetime.now(timezone.utc).isoformat(), 'media_sha256':'a'*64}
                    db.execute('INSERT INTO deliveries VALUES (?,?,?,?)', (draft_id,'tt','action_required',canonical(receipt)))
            observation = {**account,'draft':'first','url':'https://www.tiktok.com/@fictional/video/123',
                           'observed_caption':'reviewed','matches':'yes','public':'yes'}
            with self.assertRaises(HTTPError):
                form(owner, {**observation,'observed_caption':'different'})
            self.assertEqual(drafts.get('first')['deliveries'][0]['status'], 'action_required')
            form(owner, observation)
            self.assertEqual(drafts.get('first')['deliveries'][0]['receipt']['verification_method'], 'operator_browser')
            with self.assertRaises(HTTPError):
                form(owner, {**observation,'draft':'second'})
            self.assertEqual(drafts.get('second')['deliveries'][0]['status'], 'action_required')
