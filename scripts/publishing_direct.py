"""Direct Meta and Snap clients for the Ifverse publishing worker."""
from base64 import b64encode
import json
import os
import re
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID, uuid4


class PublishingError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PublishingError(message)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(url, token, body=None, content_type='application/json', headers=None, scheme='Bearer'):
    arguments = {'Authorization': f'{scheme} {token}', 'Accept': 'application/json'}
    if body is not None:
        arguments['Content-Type'] = content_type
    arguments.update(headers or {})
    try:
        with build_opener(NoRedirect()).open(Request(url, body, arguments), timeout=90) as response:
            result = json.loads(response.read(2_000_000))
    except Exception:
        raise PublishingError('Provider request failed. Check permissions and saved IDs before retrying.') from None
    require(isinstance(result, dict) and not result.get('error'), 'Provider rejected the request')
    return result


def numeric_id(value):
    require(isinstance(value, str) and re.fullmatch(r'[0-9]{1,32}', value), 'Invalid Meta resource ID')
    return value


class Meta:
    def __init__(self, platform, account=None, config=None):
        prefix = 'IFVERSE_FB_PAGE' if platform == 'facebook' else 'IFVERSE_IG'
        if config is None:
            account = os.environ.get(prefix + '_ID')
            config = {'token': os.environ.get(prefix + '_TOKEN'),
                      'graph_version': os.environ.get('IFVERSE_META_GRAPH_VERSION', '')}
        self.account = numeric_id(account)
        self.token = config.get('token')
        version = config.get('graph_version', '')
        require(isinstance(self.token, str) and self.token and re.fullmatch(r'v[0-9]+\.[0-9]+', version),
                'Configure the Meta token and Graph API version privately')
        self.facebook = platform == 'facebook'
        self.page = numeric_id(config['page_id']) if 'page_id' in config else None
        host = 'graph.facebook.com' if self.facebook or self.page else 'graph.instagram.com'
        self.base = f'https://{host}/{version}/'

    def graph(self, path, *, fields=None, **form):
        query = '?' + urlencode({'fields': fields}) if fields else ''
        body = urlencode(form).encode() if form else None
        return request(self.base + path + query, self.token, body, 'application/x-www-form-urlencoded')

    def verify(self, expected):
        require(expected == self.account, 'Configured Meta account differs from the reviewed destination')
        if self.page:
            data = self.graph('me', fields='id,instagram_business_account{id,username}')
            profile = data.get('instagram_business_account', {})
            require(str(data.get('id')) == self.page and str(profile.get('id')) == expected,
                    'Meta Page token does not identify the intended linked Instagram account')
            return profile.get('username') or expected
        data = self.graph('me', fields='id,name' if self.facebook else 'user_id,username')
        require(str(data.get('id') if self.facebook else data.get('user_id')) == expected,
                'Meta token does not identify the intended account')
        return data.get('name' if self.facebook else 'username') or expected

    def upload_bytes(self, url, resource, data, prefix):
        parsed = urlsplit(url)
        require(parsed.scheme == 'https' and parsed.netloc == 'rupload.facebook.com'
                and re.fullmatch(f'/{prefix}/(?:v[0-9]+\\.[0-9]+/)?{resource}', parsed.path)
                and not parsed.query and not parsed.fragment, 'Unexpected Meta upload URL')
        response = request(url, self.token, data, 'application/octet-stream',
                           {'offset': '0', 'file_size': str(len(data))}, scheme='OAuth')
        require(response.get('success') is True, 'Meta did not acknowledge the video upload')

    def publish(self, item, data, checkpoint):
        if self.facebook:
            resource = self.graph('me/video_reels', upload_phase='start')
            video_id = numeric_id(resource['video_id'])
            checkpoint('video_id', video_id)
            self.upload_bytes(resource['upload_url'], video_id, data, 'video-upload')
            checkpoint('finishing_video_id', video_id)
            result = self.graph('me/video_reels', upload_phase='finish', video_id=video_id,
                                video_state='PUBLISHED', title=item['title'], description=item['caption'])
            require(result.get('success') is True, 'Facebook did not acknowledge publishing')
            return 'submitted', video_id, None

        resource = self.graph(f'{self.account}/media', media_type='REELS', upload_type='resumable',
                              share_to_feed='true', caption=item['caption'])
        container = numeric_id(resource['id'])
        checkpoint('container_id', container)
        self.upload_bytes(resource['uri'], container, data, 'ig-api-upload')
        return self.finish_instagram(container, checkpoint)

    def finish_instagram(self, container, checkpoint):
        status = self.graph(numeric_id(container), fields='status_code').get('status_code')
        if status == 'IN_PROGRESS':
            return 'processing', container, None
        require(status == 'FINISHED', 'Instagram container is unavailable or requires reconciliation')
        checkpoint('publishing_container_id', container)
        result = self.graph(f'{self.account}/media_publish', creation_id=container)
        return 'submitted', numeric_id(result['id']), None

    def status(self, resource):
        resource = numeric_id(resource)
        if self.facebook:
            info = self.graph(resource, fields='status,permalink_url')
            phase = info.get('status', {}).get('publishing_phase', {})
            if phase.get('publish_status') == 'published' and phase.get('status') == 'complete':
                return 'published', info.get('permalink_url')
            if phase.get('status') == 'error' or info.get('status', {}).get('video_status') == 'error':
                return 'failed', None
        else:
            info = self.graph(resource, fields='id,permalink,media_product_type')
            if info.get('id') == resource and info.get('media_product_type') == 'REELS' and info.get('permalink'):
                return 'published', info['permalink']
        return 'submitted', None


def multipart(fields, data=None):
    boundary = uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    if data is not None:
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="video.enc"\r\n'
                    'Content-Type: application/octet-stream\r\n\r\n'.encode())
        body.extend(data)
        body.extend(b'\r\n')
    body.extend(f'--{boundary}--\r\n'.encode())
    return bytes(body), f'multipart/form-data; boundary={boundary}'


class Snap:
    def __init__(self, account=None, config=None):
        if config is None:
            account = os.environ.get('IFVERSE_SNAP_PROFILE_ID', '')
            config = {'token': os.environ.get('IFVERSE_SNAP_ACCESS_TOKEN')}
        self.account = str(UUID(account))
        self.token = config.get('token')
        require(self.token, 'Configure the allowlisted Snapchat access token privately')
        self.path = f'/v1/public_profiles/{self.account}'

    def api(self, path, body=None, content_type='application/json'):
        result = request('https://businessapi.snapchat.com' + path, self.token, body, content_type)
        require(result.get('request_status') == 'SUCCESS', 'Snapchat did not acknowledge the request')
        return result

    def verify(self, expected):
        require(expected == self.account, 'Configured Snap profile differs from the reviewed destination')
        result = self.api(self.path)
        profiles = [row['public_profile'] for row in result['public_profiles']
                    if row.get('sub_request_status') == 'SUCCESS']
        require(any(row['id'] == expected for row in profiles), 'Snap token cannot access the reviewed profile')
        return expected

    def publish(self, item, data, checkpoint):
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives.padding import PKCS7

        key, iv = os.urandom(32), os.urandom(16)
        pad = PKCS7(128).padder()
        encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
        encrypted = encryptor.update(pad.update(data) + pad.finalize()) + encryptor.finalize()
        media = self.api(self.path + '/media', json.dumps({
            'type': 'VIDEO', 'name': item['title'], 'key': b64encode(key).decode(), 'iv': b64encode(iv).decode()
        }).encode())
        media_id = str(UUID(media['media_id']))
        checkpoint('media_id', media_id)
        expected_path = rf'/(?:[a-z]{{2}}/)?v1/public_profiles/{self.account}/media/{media_id}/multipart-upload'
        require(all(re.fullmatch(expected_path, media[name]) for name in ('add_path', 'finalize_path')),
                'Unexpected Snapchat multipart path')
        chunk = 32_000_000
        for index, start in enumerate(range(0, len(encrypted), chunk), 1):
            body, content_type = multipart({'action': 'ADD', 'part_number': index}, encrypted[start:start + chunk])
            self.api(media['add_path'], body, content_type)
        self.api(media['finalize_path'], *multipart({'action': 'FINALIZE'}))
        checkpoint('posting_media_id', media_id)
        result = self.api(self.path + '/spotlights', json.dumps({
            'media_id': media_id, 'description': item['caption'], 'locale': 'en_US',
        }).encode())
        return 'submitted', spotlight_id(result['spotlight_id']), None

    def status(self, resource):
        data = self.api(self.path + '/spotlights/' + spotlight_id(resource))
        matches = [row['spotlight'] for row in data['spotlights'] if row.get('sub_request_status') == 'SUCCESS']
        matches = [row for row in matches if row.get('id') == resource and row.get('profile_id') == self.account]
        require(len(matches) == 1, 'Could not verify the Snapchat Spotlight')
        status = {'LIVE': 'published', 'REJECTED': 'failed'}.get(matches[0].get('status'), 'submitted')
        return status, None


def spotlight_id(value):
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{8,160}', value), 'Invalid Spotlight ID')
    return value


def client(platform, account=None, config=None):
    return Snap(account, config) if platform == 'snapchat' else Meta(platform, account, config)
