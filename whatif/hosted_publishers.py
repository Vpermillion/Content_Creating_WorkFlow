"""Adapters for the durable owner-only publishing API; secrets stay on its volume."""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import hmac
import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

from scripts import publishing_accounts as accounts, publishing_direct as direct
from . import hosted_tiktok, media, youtube, youtube_publish as yp


def tiktok_request(url, token, body=None):
    # TikTok success includes error.code=ok; the Meta client treats any error object as failure.
    from urllib.request import Request, build_opener
    headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
    with build_opener(direct.NoRedirect()).open(Request(url, body, headers), timeout=30) as response:
        result = json.loads(response.read(1_000_000))
    direct.require(result.get('error', {}).get('code') == 'ok', 'TikTok request did not succeed')
    return result


def verify_youtube_handle(session, row):
    if row.get('handle'):
        result = session.get(youtube.CHANNELS_URL, params={'part': 'snippet', 'forHandle': row['handle']},
                             timeout=25, allow_redirects=False)
        direct.require(result.status_code == 200, 'YouTube handle lookup failed')
        direct.require([channel.get('id') for channel in result.json().get('items', [])] == [row['account_id']],
                       'The YouTube handle differs from the authorized channel')


class Publishers:
    def __init__(self, root, state, public_origin, signing_key):
        self.root, self.state = root, state
        self.origin, self.key = public_origin.rstrip('/'), signing_key
        self._operation_grants = ContextVar('ifverse_operation_grants', default=None)

    @contextmanager
    def broker_grants(self, grants, bindings=None):
        direct.require(isinstance(grants, dict) and len(grants) <= 4, 'Invalid broker grants')
        bindings = accounts.registry(self.root) if bindings is None else bindings
        for alias, grant in grants.items():
            binding = bindings.get(alias)
            direct.require(binding and isinstance(grant, dict)
                           and grant.get('platform') == binding['platform']
                           and grant.get('account_id') == binding['account_id'], 'Broker grant destination mismatch')
            token = grant.get('token')
            direct.require(isinstance(token, str) and 0 < len(token) <= 8000
                           and all('!' <= char <= '~' for char in token), 'Invalid provider token')
            fields = {'platform', 'account_id', 'token'}
            if binding['platform'] in ('facebook', 'instagram'):
                version = grant.get('graph_version')
                direct.require(isinstance(version, str) and re.fullmatch(r'v[0-9]+\.[0-9]+', version),
                               'Invalid broker Graph API version')
                fields.add('graph_version')
                if binding['platform'] == 'instagram':
                    direct.numeric_id(grant.get('page_id'))
                    fields.add('page_id')
            direct.require(grant.keys() == fields, 'Unexpected broker grant fields')
        context = self._operation_grants.set(grants)
        try:
            yield
        finally:
            self._operation_grants.reset(context)

    def operation_grant(self, row):
        grants = self._operation_grants.get()
        if grants is None:
            return None
        grant = grants.get(row['account'])
        direct.require(grant and grant['platform'] == row['platform'] and grant['account_id'] == row['account_id'],
                       'Connect the reviewed account in Ifverse Publishing')
        return grant

    def config(self, row):
        grant = self.operation_grant(row)
        if grant is not None:
            return grant
        path = self.state / 'grants' / (row['account'] + '.json')
        return json.loads(path.read_text()) if path.exists() else accounts.grant(self.root, row['account'])

    def session(self, row):
        grant = self.operation_grant(row)
        if grant is not None:
            _, Credentials, _, Session = youtube.sdk()
            credentials = Credentials(token=grant['token'])
            yp.upload_channel(credentials, Session, row['account_id'], row.get('handle'))
            return Session(credentials)
        return yp.verified_session(youtube.ConnectionStore(self.state / 'youtube'), row['account_id'],
                                   row['account'], row.get('handle'))

    def verify(self, row):
        if row['platform'] == 'youtube':
            with self.session(row) as session:
                verify_youtube_handle(session, row)
                return {'account_id': row['account_id'], 'handle': row.get('handle'), 'verified': True}
        if row['platform'] == 'tiktok':
            confirmed = self.state / 'grants' / (row['account'] + '.studio.json')
            if confirmed.is_file():
                proof = json.loads(confirmed.read_text())
                direct.require(proof['account_id'] == row['account_id']
                               and proof['handle'] == hosted_tiktok.normalize_handle(row['handle']),
                               'TikTok Studio confirmation differs from the registered account')
                return {**proof, 'verified': True}
            config = self.config(row)
            result = tiktok_request('https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name,username',
                                    config['token'])
            user = result['data']['user']
            direct.require(user['open_id'] == row['account_id'] and
                user.get('username', '').lstrip('@').casefold() == row['handle'].lstrip('@').casefold(),
                'TikTok account mismatch')
            handle = user['username']
        else:
            config = self.config(row)
            handle = direct.client(row['platform'], row['account_id'], config).verify(row['account_id'])
            if row['platform'] == 'instagram' and row.get('handle'):
                direct.require(handle.lstrip('@').casefold() == row['handle'].lstrip('@').casefold(),
                               'Instagram handle mismatch')
        return {'account_id': row['account_id'], 'handle': handle, 'verified': True}

    def media_url(self, sha, ttl=900):
        expiry = str(int(time.time()) + ttl)
        signature = hmac.new(self.key.encode(), f'{sha}:{expiry}'.encode(), hashlib.sha256).hexdigest()
        return f'{self.origin}/media/{sha}?' + urlencode({'expires': expiry, 'signature': signature})

    def validate_media(self, row, path):
        direct.require(hashlib.sha256(path.read_bytes()).hexdigest() == row['media_sha256'], 'Reviewed media changed')
        info = media.probe(path)
        video = next((s for s in info['streams'] if s['codec_type'] == 'video'), {})
        if row['format'] in ('jpeg', 'feed'):
            direct.require(video.get('codec_name') == 'mjpeg' and int(info['format'].get('nb_streams', 0)) == 1,
                           'A photo feed post requires one JPEG image')
            ratio = video.get('width', 0) / max(video.get('height', 0), 1)
            direct.require(0.8 <= ratio <= 1.91, 'JPEG aspect ratio must be 4:5 through 1.91:1')
        else:
            duration = float(info['format'].get('duration', 0))
            high = 60 if row['platform'] == 'facebook' else 180
            direct.require(3 <= duration <= high and video.get('width', 0) >= 540
                and (video['width'] * 16 == video['height'] * 9
                     or row['platform'] == 'youtube' and video['width'] == video['height'])
                and any(s['codec_type'] == 'audio' for s in info['streams']), 'Invalid vertical video export')
        media.command(['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-'])

    def start(self, row, path, draft, checkpoint):
        self.validate_media(row, path)
        if row['platform'] == 'tiktok':
            return self.handoff(row)
        if row['platform'] == 'youtube':
            return self.youtube(row, path, draft)
        provider = direct.client(row['platform'], row['account_id'], self.config(row))
        if row['format'] == 'jpeg':
            container = direct.numeric_id(provider.graph(row['account_id'] + '/media',
                image_url=self.media_url(row['media_sha256']), caption=row['caption'])['id'])
            checkpoint({'checkpoint': 'container_id', 'checkpoint_id': container})
            return self.result(provider.finish_instagram(container,
                lambda phase, resource: checkpoint({'checkpoint': phase, 'checkpoint_id': resource})))
        if row['format'] == 'feed':
            checkpoint({'checkpoint': 'posting_feed'})
            result = provider.graph(row['account_id'] + '/photos',
                url=self.media_url(row['media_sha256']), caption=row['caption'], published='true')
            resource = result['post_id']
            checkpoint({'provider_id': resource})
            return self.meta_status(provider, resource, row)
        return self.result(provider.publish(row, path.read_bytes(),
            lambda phase, resource: checkpoint({'checkpoint': phase, 'checkpoint_id': resource})))

    @staticmethod
    def result(value):
        status, resource, url = value
        if url and url.startswith('/') and not url.startswith('//'):
            url = 'https://www.facebook.com' + url
        return {'status': status, 'provider_id': resource, 'url': url if status == 'published' else None}

    def youtube(self, row, path, draft):
        # Existing resumable uploader persists the original session before sending chunks.
        review = row['manifest']['review']
        body = {'snippet': {'title': row['title'], 'description': row['caption'], 'categoryId': '24'},
                'status': {'privacyStatus': 'public',
                    'selfDeclaredMadeForKids': review['audience'] == 'made_for_kids',
                    'containsSyntheticMedia': review['synthetic_disclosure']}}
        operation = draft + '-' + row['account']
        with self.session(row) as session:
            receipt = yp.upload(session, operation, path, row['media_sha256'],
                hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest(), body,
                row['account_id'], self.state / 'uploads' / row['account'])
            receipt = yp.verify_uploaded(session, receipt)
        return {'status': 'published' if receipt['publicly_posted'] else 'submitted',
                'provider_id': receipt['video_id'], 'url': receipt['url'] if receipt['publicly_posted'] else None}

    def handoff(self, row):
        return {'status': 'action_required', 'target': row['handle'], 'account_id': row['account_id'],
                'studio_url': 'https://www.tiktok.com/tiktokstudio/upload',
                'media_url': self.media_url(row['media_sha256']), 'media_sha256': row['media_sha256'],
                'caption': row['caption'], 'handed_off_at': datetime.now(timezone.utc).isoformat(),
                'instructions': 'Confirm this target in Studio, upload the exact download, paste this caption, '
                'review visibility and publish. Open the resulting public post and use the browser verification link.'}

    def meta_status(self, provider, resource, row):
        if row['format'] == 'feed':
            result = provider.graph(resource, fields='id,from,permalink_url,is_published')
            direct.require(result.get('from', {}).get('id') == row['account_id'], 'Wrong Page author')
            published = result.get('is_published') is True and result.get('permalink_url')
            return {'status': 'published' if published else 'submitted', 'provider_id': resource,
                    'url': result.get('permalink_url') if published else None}
        if row['format'] == 'jpeg':
            result = provider.graph(resource, fields='id,permalink,media_type,owner')
            direct.require(result.get('owner', {}).get('id') == row['account_id'], 'Wrong image owner')
            published = result.get('media_type') == 'IMAGE' and result.get('permalink')
            return {'status': 'published' if published else 'submitted', 'provider_id': resource,
                    'url': result.get('permalink') if published else None}
        status, url = provider.status(resource)
        return self.result((status, resource, url))

    def reconcile(self, row, path, draft, state, checkpoint):
        self.validate_media(row, path)
        if row['platform'] == 'youtube':
            return self.youtube(row, path, draft)
        if row['platform'] == 'tiktok':
            receipt = state['receipt']
            return {**receipt, 'status': 'action_required', 'media_url': self.media_url(row['media_sha256'])} if (
                receipt.get('handed_off_at')) else self.handoff(row)
        provider = direct.client(row['platform'], row['account_id'], self.config(row))
        receipt = state['receipt']
        if receipt.get('provider_id'):
            resource = receipt['provider_id']
            if state['status'] == 'processing':
                return self.result(provider.finish_instagram(resource,
                    lambda phase, value: checkpoint({'checkpoint': phase, 'checkpoint_id': value})))
            return self.meta_status(provider, resource, row)
        phase, resource = receipt.get('checkpoint'), receipt.get('checkpoint_id')
        if phase == 'container_id':
            # Bytes may be incomplete: never publish or allocate another container blindly.
            status = provider.graph(resource, fields='status_code').get('status_code')
            if status == 'FINISHED':
                return self.result(provider.finish_instagram(resource,
                    lambda phase, value: checkpoint({'checkpoint': phase, 'checkpoint_id': value})))
        if phase == 'publishing_container_id':
            if provider.graph(resource, fields='status_code').get('status_code') == 'PUBLISHED':
                return {'status': 'published', 'provider_id': None, 'url': None}
        if phase in ('video_id', 'finishing_video_id'):
            return self.meta_status(provider, resource, row)
        # In particular media_publish may have succeeded but lost its response.
        return {**receipt, 'status': 'needs_reconciliation'}

    def read_status(self, row, state):
        """Check existing provider resources without resuming a write."""
        receipt = state['receipt']
        provider_id = receipt.get('provider_id')
        phase, resource = receipt.get('checkpoint'), receipt.get('checkpoint_id')
        if row['platform'] == 'tiktok':
            return None
        if row['platform'] == 'youtube':
            if not provider_id:
                return None
            with self.session(row) as session:
                current = yp.verify_uploaded(session, {'video_id': provider_id, 'verified_channel_id': row['account_id'],
                    'url': 'https://www.youtube.com/shorts/' + provider_id})
            status = 'published' if current['publicly_posted'] else 'submitted'
            if current['provider_upload_status'] in ('deleted', 'failed', 'rejected'):
                status = 'failed'
            return {'status': status, 'provider_id': provider_id,
                    'url': current['url'] if status == 'published' else None,
                    'provider_upload_status': current['provider_upload_status']}
        provider = direct.client(row['platform'], row['account_id'], self.config(row))
        provider.verify(row['account_id'])
        if row['platform'] == 'instagram' and phase == 'publishing_container_id':
            if provider.graph(resource, fields='status_code').get('status_code') == 'PUBLISHED':
                return {'status': 'published', 'provider_id': None, 'url': None}
            return None
        if row['platform'] == 'instagram' and state['status'] == 'processing':
            code = provider.graph(provider_id, fields='status_code').get('status_code')
            return {**receipt, 'status': 'processing', 'provider_status': code}
        known_id = provider_id or (resource if row['platform'] == 'facebook' and phase == 'finishing_video_id' else None)
        return self.meta_status(provider, known_id, row) if known_id else None

    def verify_tiktok_video(self, row, video_id, handoff):
        direct.require(row['platform'] == 'tiktok' and isinstance(video_id, str)
                       and video_id.isdigit() and len(video_id) <= 30, 'Invalid TikTok video ID')
        url = f'https://www.tiktok.com/{hosted_tiktok.normalize_handle(row["handle"])}/video/{video_id}'
        result = hosted_tiktok.verify_publication(row, url, handed_off_at=handoff['handed_off_at'],
                                                  access_token=self.config(row)['token'], open_id=row['account_id'])
        direct.require(result['status'] == 'published', 'TikTok could not verify the reviewed publication')
        return result
