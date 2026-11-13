"""Hosted web OAuth. State and PKCE live privately, callbacks never log queries."""
import hashlib
import json
import os
import secrets
import time
from base64 import urlsafe_b64encode
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from scripts import publishing_accounts as accounts, publishing_direct as direct
from . import youtube, youtube_publish as yp
from .hosted_publishers import tiktok_request


class OAuth:
    def __init__(self, root, directory, origin, publishers):
        self.root, self.directory, self.origin, self.publishers = root, directory, origin.rstrip('/'), publishers
        for name in ('oauth', 'grants'):
            (directory / name).mkdir(mode=0o700, exist_ok=True)

    def settings(self, platform):
        # JSON entered through host secret settings, never passed through ChatGPT.
        config = json.loads(os.environ['IFVERSE_OAUTH_CONFIG'])[platform]
        direct.require(config.get('client_id') and config.get('client_secret'), 'Configure OAuth client privately')
        return config

    def begin(self, alias):
        row = accounts.registry(self.root)[alias]
        platform = row['platform']
        config = self.settings('meta' if platform in ('instagram', 'facebook') else platform)
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
        callback = self.origin + '/oauth/callback'
        record = {'alias': alias, 'binding': row, 'expires': time.time() + 600, 'verifier': verifier}
        youtube.atomic_json(self.directory / 'oauth' / (hashlib.sha256(state.encode()).hexdigest() + '.json'), record)
        query = {'client_id': config['client_id'], 'redirect_uri': callback, 'state': state, 'response_type': 'code'}
        if platform == 'youtube':
            url = 'https://accounts.google.com/o/oauth2/v2/auth'
            query.update(scope=youtube.READ_SCOPE + ' ' + yp.UPLOAD_SCOPE, access_type='offline',
                prompt='consent select_account', code_challenge_method='S256',
                code_challenge=urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode())
        elif platform in ('instagram', 'facebook'):
            version = config['graph_version']
            direct.require(__import__('re').fullmatch(r'v[0-9]+\.[0-9]+', version), 'Invalid Graph version')
            url = f'https://www.facebook.com/{version}/dialog/oauth'
            query.update(scope='pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish')
        elif platform == 'tiktok':
            url = 'https://www.tiktok.com/v2/auth/authorize/'
            query.pop('client_id')
            query.update(client_key=config['client_id'], scope='user.info.basic,user.info.profile,video.list')
        else:
            raise ValueError('Unsupported platform')
        return {'account': alias, 'authorization_url': url + '?' + urlencode(query), 'expires_in': 600}

    def callback(self, state, code):
        direct.require(isinstance(state, str) and 20 <= len(state) <= 200 and isinstance(code, str)
                       and 0 < len(code) <= 4096, 'Invalid OAuth callback')
        path = self.directory / 'oauth' / (hashlib.sha256(state.encode()).hexdigest() + '.json')
        # Atomic consume across workers; stale/replayed callbacks cannot replace grants.
        claimed = path.with_suffix('.consuming')
        path.rename(claimed)
        try:
            record = json.loads(claimed.read_text())
            direct.require(record['expires'] >= time.time(), 'OAuth session expired')
            alias, row = record['alias'], record['binding']
            direct.require(accounts.registry(self.root)[alias] == row, 'Account changed during consent')
            platform = row['platform']
            config = self.settings('meta' if platform in ('instagram', 'facebook') else platform)
            callback = self.origin + '/oauth/callback'
            if platform == 'youtube':
                from google_auth_oauthlib.flow import Flow
                from google.auth.transport.requests import AuthorizedSession
                flow = Flow.from_client_config({'web': {'client_id': config['client_id'],
                    'client_secret': config['client_secret'], 'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': youtube.TOKEN_URI, 'redirect_uris': [callback]}},
                    scopes=[youtube.READ_SCOPE, yp.UPLOAD_SCOPE], state=state, code_verifier=record['verifier'])
                flow.redirect_uri = callback
                flow.fetch_token(code=code)
                credentials = flow.credentials
                yp.require_upload_scope(credentials)
                direct.require(credentials.refresh_token, 'Offline access is required')
                channel = yp.upload_channel(credentials, AuthorizedSession, row['account_id'], row.get('handle'))
                store = youtube.ConnectionStore(self.directory / 'youtube')
                with store.lock(alias):
                    store.save(alias, {'schema_version': 1, 'connection': alias, 'channel': channel,
                        'verified_at': youtube.now(), 'credentials': json.loads(credentials.to_json())})
            else:
                grant = self.exchange(platform, config, code, callback, row)
                # Verify before persisting any connection binding.
                if platform == 'tiktok':
                    result = tiktok_request('https://open.tiktokapis.com/v2/user/info/?fields=open_id,username', grant['token'])
                    user = result['data']['user']
                    direct.require(user['open_id'] == row['account_id'] and
                        user.get('username', '').lstrip('@').casefold() == row['handle'].lstrip('@').casefold(),
                        'Wrong TikTok account')
                else:
                    handle = direct.client(platform, row['account_id'], grant).verify(row['account_id'])
                    direct.require(platform != 'instagram' or not row.get('handle') or
                        handle.lstrip('@').casefold() == row['handle'].lstrip('@').casefold(), 'Wrong Instagram handle')
                youtube.atomic_json(self.directory / 'grants' / (alias + '.json'), grant)
            return {'account': alias, 'account_id': row['account_id'], 'handle': row.get('handle'), 'verified': True}
        finally:
            claimed.unlink(missing_ok=True)

    @staticmethod
    def exchange(platform, config, code, callback, row):
        if platform == 'tiktok':
            url = 'https://open.tiktokapis.com/v2/oauth/token/'
            form = {'client_key': config['client_id'], 'client_secret': config['client_secret'],
                    'code': code, 'grant_type': 'authorization_code', 'redirect_uri': callback}
        else:
            url = 'https://graph.facebook.com/' + config['graph_version'] + '/oauth/access_token'
            form = {'client_id': config['client_id'], 'client_secret': config['client_secret'],
                    'code': code, 'redirect_uri': callback}
        with build_opener(direct.NoRedirect()).open(Request(url, urlencode(form).encode(),
                {'Content-Type': 'application/x-www-form-urlencoded'}), timeout=30) as response:
            token = json.loads(response.read(1_000_000))
        direct.require(token.get('access_token'), 'Consent exchange failed')
        if platform == 'tiktok':
            direct.require(token.get('open_id') == row['account_id'], 'Wrong TikTok owner')
            return {'token': token['access_token'], 'refresh_token': token.get('refresh_token'),
                    'expires_at': time.time() + token.get('expires_in', 0)}
        pages = direct.request('https://graph.facebook.com/' + config['graph_version'] +
            '/me/accounts?fields=id,access_token,instagram_business_account{id,username}', token['access_token'])
        matches = [p for p in pages.get('data', []) if
                   (p['id'] == row['account_id'] if platform == 'facebook' else
                    p.get('instagram_business_account', {}).get('id') == row['account_id'])]
        direct.require(len(matches) == 1, 'Intended Page or linked professional account is not in the grant')
        grant = {'token': matches[0]['access_token'], 'graph_version': config['graph_version']}
        if platform == 'instagram':
            grant['page_id'] = matches[0]['id']
        return grant
