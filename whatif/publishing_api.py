"""Owner-only hosted API. Put behind HTTPS; never enable request/query logging."""
import hashlib
import hmac
from base64 import b64encode
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import time
from urllib.parse import parse_qs, urlsplit

from scripts import publishing_accounts as accounts
from scripts.publishing_direct import require
from .hosted_publishers import Publishers
from .publishing_oauth import OAuth
from .publishing_service import Drafts, FORMATS
from . import publishing_owner


def server(drafts, oauth, token, signing_key, address=('127.0.0.1', 8080), owner_password=None):
    require(len(token) >= 32 and len(signing_key) >= 32 and token != signing_key,
            'Configure strong independent private API and signing keys')
    require(not owner_password or len(owner_password) >= 32 and owner_password not in (token, signing_key),
            'Set an independent browser owner password of at least 32 characters')

    from .publishing_jobs import MediaJobs
    jobs = MediaJobs(drafts.root, drafts.directory, drafts)

    def connect(account, method='studio'):
        row = accounts.registry(drafts.root)[account]
        if row['platform'] == 'tiktok' and method == 'studio':
            return {'status': 'studio_confirmation_required', 'handle': row['handle'],
                    'operator_url': publishing_owner.studio_link(drafts.adapter.origin, account)}
        return oauth.begin(account)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, value, content_type='application/json', filename=None, headers=None):
            body = value if isinstance(value, bytes) else json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            if filename:
                self.send_header('Content-Disposition', f'inline; filename="{filename}"')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; form-action 'self'; frame-ancestors 'none'")
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def owner(self):
            if not owner_password:
                self.reply(503, {'error': 'The browser owner password is not configured'})
                return False
            expected = b'Basic ' + b64encode(('owner:' + owner_password).encode())
            if hmac.compare_digest(self.headers.get('Authorization', '').encode(), expected):
                return True
            self.reply(401, {'error': 'Owner sign-in required'},
                       headers={'WWW-Authenticate': 'Basic realm="Ifverse owner", charset="UTF-8"'})
            return False

        def browser_form(self):
            if not self.owner():
                return
            require(self.headers.get('Origin') == drafts.adapter.origin, 'Submit the browser form from this site')
            require(self.headers.get('Content-Type', '').startswith('application/x-www-form-urlencoded'),
                    'Use the browser owner form')
            size = int(self.headers.get('Content-Length', '0'))
            require(0 < size <= 16_000, 'Invalid browser form length')
            form = {key: values[0] for key, values in parse_qs(self.rfile.read(size).decode(),
                    keep_blank_values=True, max_num_fields=12).items()}
            if self.path == '/owner/accounts':
                account = form['account']
                row = accounts.registry(drafts.root)[account]
                if form.get('action') == 'verify':
                    result = drafts.adapter.verify({**row, 'account': account})
                    return self.reply(200, result)
                require(form.get('action') == 'connect', 'Choose Connect or Verify')
                result = connect(account)
                location = result.get('authorization_url') or result['operator_url']
                return self.reply(303, b'', 'text/plain', headers={'Location': location})
            result = publishing_owner.handle_form(drafts, form)
            self.reply(200, result.encode(), 'text/plain; charset=utf-8')

        def do_GET(self):
            try:
                parsed = urlsplit(self.path)
                query = parse_qs(parsed.query, max_num_fields=16)
                if parsed.path == '/health':
                    return self.reply(200, {'status': 'ready'})
                if parsed.path == '/owner/accounts':
                    if self.owner():
                        page = publishing_owner.accounts_page(drafts)
                        return self.reply(200, page.encode(), 'text/html; charset=utf-8')
                    return
                if parsed.path == '/owner/studio':
                    if self.owner():
                        page = publishing_owner.page(drafts, query['account'][0], query.get('draft', [''])[0])
                        return self.reply(200, page.encode(), 'text/html; charset=utf-8')
                    return
                if parsed.path == '/oauth/callback':
                    oauth.callback(query.get('state', [''])[0], query.get('code', [''])[0])
                    return self.reply(200, b'Account verified. Return to ChatGPT.', 'text/plain')
                if parsed.path.startswith('/media/'):
                    sha = parsed.path.removeprefix('/media/')
                    path = drafts.media(sha)
                    expiry = query['expires'][0]
                    require(time.time() <= int(expiry) <= time.time() + 3600, 'Expired download')
                    expected = hmac.new(signing_key.encode(), f'{sha}:{expiry}'.encode(), hashlib.sha256).hexdigest()
                    require(hmac.compare_digest(expected, query['signature'][0]), 'Invalid download')
                    data = path.read_bytes()
                    jpeg = data.startswith(b'\xff\xd8\xff')
                    suffix, content_type = ('.jpg', 'image/jpeg') if jpeg else ('.mp4', 'video/mp4')
                    return self.reply(200, data, content_type, 'ifverse-' + sha + suffix)
                return self.reply(404, {'error': 'Not found'})
            except Exception:
                return self.reply(400, {'error': 'Request failed; reconnect or inspect private operation state'})

        def do_POST(self):
            if self.path in ('/owner/studio', '/owner/accounts'):
                try:
                    return self.browser_form()
                except Exception:
                    if self.path == '/owner/accounts':
                        return self.reply(400, {'error': 'Account operation failed. Check the registered destination and provider settings, then return to /owner/accounts.'})
                    return self.reply(400, {'error': 'Could not verify. Check the handle, public video, reviewed caption and media.'})
            if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token):
                return self.reply(401, {'error': 'Unauthorized'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                limit = 100 * 1024 * 1024 if self.path == '/media' else 250_000
                require(0 < size <= limit, 'Request too large or empty')
                raw = self.rfile.read(size)
                if self.path == '/media':
                    return self.reply(200, {'media_sha256': drafts.put_media(raw)})
                args = json.loads(raw)
                if self.path == '/jobs/prepare':
                    result = jobs.submit(args['request_id'])
                elif self.path == '/jobs/get':
                    result = jobs.get(args['request_id'])
                elif self.path == '/jobs/import':
                    result = jobs.import_result(args['brand'], args['episode'], args.get('export', 'master'))
                elif self.path == '/accounts':
                    result = {'accounts': accounts.registry(drafts.root), 'formats': FORMATS,
                              'instagram_carousel': 'Supported by Meta; unavailable through this integration'}
                elif self.path == '/connect':
                    result = connect(args['account'], args.get('method', 'studio'))
                elif self.path == '/verify':
                    row = accounts.registry(drafts.root)[args['account']]
                    result = drafts.adapter.verify({**row, 'account': args['account']})
                elif self.path == '/drafts/create':
                    result = drafts.create(args['brand'], args['destinations'])
                elif self.path == '/drafts/get':
                    result = drafts.get(args['draft_id'])
                elif self.path == '/drafts/status':
                    result = drafts.refresh(args['draft_id'])
                elif self.path == '/drafts/publish':
                    result = drafts.publish(args['draft_id'], args['snapshot_hash'], args['destinations'], args['approved'])
                elif self.path == '/tiktok/verify':
                    preview = drafts.get(args['draft_id'])
                    require(preview['snapshot_hash'] == args['snapshot_hash'], 'Wrong snapshot')
                    row = next(r for r in preview['destinations'] if r['account'] == args['account'])
                    state = next(r for r in preview['deliveries'] if r['alias'] == args['account'])
                    require(state['status'] == 'action_required', 'A reviewed Studio handoff is required')
                    result = drafts.adapter.verify_tiktok_video(row, args['video_id'], state['receipt'])
                    drafts.confirm_tiktok(args['draft_id'], args['account'], result)
                else:
                    return self.reply(404, {'error': 'Not found'})
                for row in result.get('destinations', []):
                    row['preview_url'] = drafts.adapter.media_url(row['media_sha256'])
                for delivery in result.get('deliveries', []):
                    if delivery['status'] == 'action_required':
                        receipt = delivery['receipt']
                        receipt['operator_url'] = publishing_owner.studio_link(
                            drafts.adapter.origin, delivery['alias'], result['draft_id'])
                        receipt['media_url'] = drafts.adapter.media_url(receipt['media_sha256'])
                self.reply(200, result)
            except Exception:
                self.reply(400, {'error': 'Request could not complete. Review consent, media review and durable delivery status.'})

    return ThreadingHTTPServer(address, Handler)


def main():
    os.umask(0o077)
    root = Path(os.environ.get('IFVERSE_ROOT', '.')).resolve()
    directory = Path(os.environ['IFVERSE_STATE']).resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    token, key = os.environ['IFVERSE_API_TOKEN'], os.environ['IFVERSE_MEDIA_KEY']
    origin = os.getenv('IFVERSE_PUBLIC_ORIGIN') or os.getenv('RENDER_EXTERNAL_URL', '')
    parsed = urlsplit(origin)
    require(parsed.scheme == 'https' and parsed.hostname and not (
        parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment),
        'Configure HTTPS public origin')
    publishers = Publishers(root, directory, origin, key)
    drafts = Drafts(directory, root, publishers)
    oauth = OAuth(root, directory, origin, publishers)
    server(drafts, oauth, token, key, ('0.0.0.0', int(os.environ.get('PORT', '8080'))),
           owner_password=os.getenv('IFVERSE_OWNER_PASSWORD')).serve_forever()


if __name__ == '__main__':
    main()
