import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from whatif.publishing_oauth import OAuth


class OAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root/'channels').mkdir()
        self.registry = {'ig': {'brand':'ifverse_anime','platform':'instagram','account_id':'123','handle':'@fictional'},
            'ifverse-anime': {'brand':'ifverse_anime','platform':'youtube',
                'account_id':'UCpB_wi5MlernpSJxUf7zWcw','handle':'@ifverse_anime'}}
        (self.root/'channels/publishing-accounts.json').write_text(json.dumps(self.registry))
        self.state = self.root/'private'; self.state.mkdir(mode=0o700)
        self.oauth = OAuth(self.root,self.state,'https://example.invalid',None)
        self.settings = patch.dict(os.environ, {'IFVERSE_OAUTH_CONFIG': json.dumps({
            'meta':{'client_id':'fixture','client_secret':'fixture','graph_version':'v25.0'},
            'youtube':{'client_id':'fixture.apps.googleusercontent.com','client_secret':'fixture'}})})
        self.settings.start()

    def tearDown(self):
        self.settings.stop(); self.temp.cleanup()

    def state_from(self, alias):
        result=self.oauth.begin(alias)
        return parse_qs(urlsplit(result['authorization_url']).query)

    def test_google_hosted_offline_pkce(self):
        query=self.state_from('ifverse-anime')
        self.assertEqual(query['redirect_uri'],['https://example.invalid/oauth/callback'])
        self.assertEqual(query['access_type'],['offline'])
        self.assertEqual(query['code_challenge_method'],['S256'])
        self.assertNotIn('client_secret',query)
        self.assertIn('youtube.upload',query['scope'][0])

    def test_meta_wrong_identity_never_persists_and_state_cannot_replay(self):
        state=self.state_from('ig')['state'][0]
        with patch.object(self.oauth,'exchange',return_value={'token':'fixture'}), \
                patch('scripts.publishing_direct.client') as client:
            client.return_value.verify.side_effect=ValueError('Wrong Page')
            with self.assertRaises(ValueError): self.oauth.callback(state,'fixture-code')
        self.assertFalse((self.state/'grants/ig.json').exists())
        with self.assertRaises(FileNotFoundError): self.oauth.callback(state,'fixture-code')

    def test_expired_state_and_successful_separate_binding(self):
        state=self.state_from('ig')['state'][0]
        with patch.object(self.oauth,'exchange',return_value={'token':'fixture'}), \
                patch('scripts.publishing_direct.client') as client:
            client.return_value.verify.return_value='fictional'
            result=self.oauth.callback(state,'fixture-code')
            self.assertTrue(result['verified'])
        self.assertTrue((self.state/'grants/ig.json').exists())
        self.assertFalse((self.state/'grants/ifverse-anime.json').exists())
        state=self.state_from('ig')['state'][0]
        with patch('whatif.publishing_oauth.time.time', return_value=time.time()+1000):
            with self.assertRaises(ValueError): self.oauth.callback(state,'fixture-code')
