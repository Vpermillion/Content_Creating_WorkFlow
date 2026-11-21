"""Hand reviewed TikTok videos to Studio and verify the resulting public post."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener

from scripts.publishing_direct import NoRedirect, PublishingError, require


STUDIO_URL = 'https://www.tiktok.com/tiktokstudio/upload?from=creator_center'
TIKTOK = 'https://www.tiktok.com'
DISPLAY_API = 'https://open.tiktokapis.com/v2/'
HANDLE = re.compile(r'[A-Za-z0-9_.]{1,24}(?<!\.)')
VIDEO_PATH = re.compile(r'/@(?P<handle>[A-Za-z0-9_.]{1,24})/video/(?P<id>[0-9]{1,20})/?')


class DisplayError(PublishingError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__({
            'grant_expired': 'Reconnect the read-only TikTok account grant.',
            'scope_missing': 'The TikTok grant needs the requested read-only scope.',
            'provider_unavailable': 'TikTok did not return read-only verification data. Check again later.',
        }[reason])


@dataclass(frozen=True)
class BrowserObservation:
    """Evidence assembled by a trusted operator who observed the public post in Chrome.

    The service must assign operator from its authenticated browser session. A chat
    tool or an ordinary status request must never be able to construct this record.
    """

    operator: str
    url: str
    handle: str
    caption: str
    observed_at: str | datetime
    media_matches: bool
    publicly_visible: bool


def normalize_handle(handle):
    require(isinstance(handle, str), 'Use the TikTok @handle shown in Studio')
    username = handle.strip().removeprefix('@')
    require(HANDLE.fullmatch(username), 'Use the TikTok @handle shown in Studio')
    return '@' + username.lower()


def profile(handle):
    expected = normalize_handle(handle)
    return {'handle': expected, 'profile_url': TIKTOK + '/' + expected,
            'identity_status': 'studio_confirmation_required', 'studio_url': STUDIO_URL}


def confirm_studio_account(expected_handle, studio_handle, operator):
    """Record manual account confirmation by an authenticated Studio operator."""
    account = profile(expected_handle)
    require(normalize_handle(studio_handle) == account['handle'],
            'The signed-in Studio handle differs from the selected destination')
    require(isinstance(operator, str) and operator.strip(), 'An authenticated operator must confirm the account')
    return {**account, 'identity_status': 'studio_operator_confirmed', 'confirmed_by': operator,
            'confirmed_at': datetime.now(timezone.utc).isoformat()}


def _item_handle(item):
    return normalize_handle(item.get('handle') or item.get('account_id'))


def handoff(item, media_url):
    """Return a manual action receipt after the caller records approval for the draft."""
    expected = _item_handle(item)
    parts = urlsplit(media_url)
    require(parts.scheme == 'https' and parts.hostname and parts.username is None and parts.password is None
            and not parts.fragment, 'Use a private HTTPS download for the reviewed TikTok video')
    require(isinstance(item.get('caption'), str), 'A reviewed TikTok caption is required')
    return {
        'status': 'action_required', 'handle': expected, 'profile_url': TIKTOK + '/' + expected,
        'studio_url': STUDIO_URL, 'media_url': media_url, 'caption': item['caption'],
        'steps': [
            'Download the reviewed MP4 and open TikTok Studio in Chrome.',
            f'Confirm the signed-in account shows {expected}.',
            'Click Select file, choose the reviewed MP4, and paste the reviewed caption.',
            'Review the visibility and click Post.',
            'Open the published video and submit its full TikTok post URL for verification.',
        ],
    }


def _canonical_video(url, expected_handle):
    require(isinstance(url, str) and len(url) <= 4096, 'Use the full TikTok video URL from your browser')
    parts = urlsplit(url)
    match = VIDEO_PATH.fullmatch(parts.path)
    require(parts.scheme == 'https' and parts.netloc.lower() in ('www.tiktok.com', 'tiktok.com') and match,
            'Use the full TikTok video URL from your browser')
    require(normalize_handle(match['handle']) == expected_handle,
            'The TikTok video URL points to a different handle')
    video_id = match['id']
    return video_id, f'{TIKTOK}/{expected_handle}/video/{video_id}'


def _timestamp(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    require(isinstance(value, datetime) and value.utcoffset() is not None,
            'TikTok verification requires a timezone-aware timestamp')
    return value.timestamp()


def _caption(value):
    return value.replace('\r\n', '\n').strip() if isinstance(value, str) else None


def _display_error(code, status=None):
    if code == 'scope_not_authorized' or status == 403:
        return DisplayError('scope_missing')
    if code == 'access_token_invalid' or status == 401:
        return DisplayError('grant_expired')
    return DisplayError('provider_unavailable')


def _read_json(source):
    return json.loads(source.read(1_000_000))


def _display_request(path, access_token, *, fields, body=None):
    payload = None if body is None else json.dumps(body).encode('utf-8')
    request = Request(DISPLAY_API + path + '?' + urlencode({'fields': fields}), payload, {
        'Accept': 'application/json', 'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    })
    try:
        with build_opener(NoRedirect()).open(request, timeout=20) as response:
            result = _read_json(response)
    except HTTPError as error:
        with error:
            try:
                result = _read_json(error)
            except (OSError, ValueError):
                result = {}
        error_code = result.get('error') if isinstance(result, dict) else None
        code = error_code.get('code') if isinstance(error_code, dict) else None
        raise _display_error(code, error.code) from None
    except (URLError, OSError, ValueError):
        raise DisplayError('provider_unavailable') from None
    error = result.get('error') if isinstance(result, dict) else None
    if not isinstance(error, dict) or error.get('code') != 'ok':
        raise _display_error(error.get('code') if isinstance(error, dict) else None)
    data = result.get('data')
    if not isinstance(data, dict):
        raise DisplayError('provider_unavailable')
    return data


def verify_account(handle, *, access_token, open_id=None):
    """Read the identity covered by an eligible app's authorized Display API grant."""
    account = profile(handle)
    require(isinstance(access_token, str) and access_token and not any(char.isspace() for char in access_token),
            'Configure the read-only TikTok grant in private settings')
    data = _display_request('user/info/', access_token, fields='open_id,display_name,username')
    user = data.get('user')
    require(isinstance(user, dict) and isinstance(user.get('open_id'), str) and user['open_id'],
            'TikTok did not return the authenticated account ID')
    require((open_id is None or user['open_id'] == open_id)
            and normalize_handle(user.get('username')) == account['handle'],
            'The TikTok grant belongs to a different account')
    return {**account, 'identity_status': 'provider_verified', 'account_id': user['open_id'],
            'display_name': user.get('display_name') or account['handle']}


def verify_publication(item, candidate_url, *, handed_off_at, access_token=None, open_id=None,
                       browser_observation=None):
    """Verify one Studio post without making a publishing request to TikTok."""
    expected = _item_handle(item)
    video_id, canonical = _canonical_video(candidate_url, expected)
    started = _timestamp(handed_off_at)
    caption = _caption(item.get('caption'))
    require(caption is not None, 'A reviewed TikTok caption is required')
    pending = {'status': 'awaiting_verification', 'candidate_url': canonical}
    result = {'status': 'published', 'provider_id': video_id, 'url': canonical}

    if browser_observation is not None:
        require(isinstance(browser_observation, BrowserObservation), 'An authenticated browser observation is required')
        observation = browser_observation
        observed_id, _ = _canonical_video(observation.url, expected)
        if (isinstance(observation.operator, str) and observation.operator.strip()
                and observed_id == video_id and normalize_handle(observation.handle) == expected
                and _timestamp(observation.observed_at) >= started
                and observation.media_matches is True and observation.publicly_visible is True
                and _caption(observation.caption) == caption):
            return {**result, 'verification_method': 'operator_browser', 'verified_by': observation.operator,
                    'verified_at': observation.observed_at if isinstance(observation.observed_at, str)
                    else observation.observed_at.isoformat()}
        return {**pending, 'reason': 'browser_observation_does_not_match_reviewed_post'}

    if not access_token:
        return {**pending, 'reason': 'read_only_grant_or_operator_verification_required'}

    try:
        verify_account(expected, access_token=access_token, open_id=open_id)
        data = _display_request('video/query/', access_token, fields='id,share_url,video_description,create_time',
                                body={'filters': {'video_ids': [video_id]}})
    except DisplayError as error:
        return {**pending, 'reason': error.reason}

    videos = data.get('videos')
    if not isinstance(videos, list) or len(videos) != 1 or not isinstance(videos[0], dict):
        return {**pending, 'reason': 'public_video_not_returned_by_tiktok'}
    video = videos[0]
    created = video.get('create_time')
    if (video.get('id') != video_id or type(created) is not int or created < int(started)
            or _caption(video.get('video_description')) != caption):
        return {**pending, 'reason': 'public_video_does_not_match_reviewed_post'}
    try:
        returned_id, url = _canonical_video(video.get('share_url'), expected)
    except PublishingError:
        return {**pending, 'reason': 'tiktok_share_url_does_not_match_reviewed_post'}
    if returned_id != video_id:
        return {**pending, 'reason': 'tiktok_share_url_does_not_match_reviewed_post'}
    return {**result, 'url': url, 'verification_method': 'tiktok_display_api',
            'verified_at': datetime.now(timezone.utc).isoformat()}
