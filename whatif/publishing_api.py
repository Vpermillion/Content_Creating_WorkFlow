"""Owner-only hosted API. Put behind HTTPS; never enable request/query logging."""
import hashlib
import hmac
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


def server(drafts, oauth, token, signing_key, address=('127.0.0.1', 8080)):
    require(len(token) >= 32 and len(signing_key) >= 32, 'Configure strong independent private API and signing keys')

    from .publishing_jobs import MediaJobs
    jobs = MediaJobs(drafts.root, drafts.directory, drafts)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, value, content_type='application/json', filename=None):
            body = value if isinstance(value, bytes) else json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            if filename:
                self.send_header('Content-Disposition', f'inline; filename="{filename}"')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            try:
                parsed = urlsplit(self.path)
                query = parse_qs(parsed.query)
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
                elif self.path == '/accounts':
                    result = {'accounts': accounts.registry(drafts.root), 'formats': FORMATS}
                elif self.path == '/connect':
                    result = oauth.begin(args['account'])
                elif self.path == '/verify':
                    row = accounts.registry(drafts.root)[args['account']]
                    result = drafts.adapter.verify({**row, 'account': args['account']})
                elif self.path == '/drafts/create':
                    result = drafts.create(args['brand'], args['destinations'])
                elif self.path == '/drafts/get':
                    result = drafts.get(args['draft_id'])
                    for row in result['destinations']:
                        row['preview_url'] = drafts.adapter.media_url(row['media_sha256'])
                elif self.path == '/drafts/publish':
                    result = drafts.publish(args['draft_id'], args['snapshot_hash'], args['destinations'], args['approved'])
                elif self.path == '/tiktok/verify':
                    preview = drafts.get(args['draft_id'])
                    require(preview['snapshot_hash'] == args['snapshot_hash'], 'Wrong snapshot')
                    row = next(r for r in preview['destinations'] if r['account'] == args['account'])
                    state = next(r for r in preview['deliveries'] if r['alias'] == args['account'])
                    require(state['status'] == 'action_required', 'A reviewed Studio handoff is required')
                    result = drafts.adapter.verify_tiktok_video(row, args['video_id'])
                    drafts.save(args['draft_id'], args['account'], result['status'], result)
                else:
                    return self.reply(404, {'error': 'Not found'})
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
    origin = os.environ['IFVERSE_PUBLIC_ORIGIN']
    require(origin.startswith('https://') and not urlsplit(origin).query, 'Configure HTTPS public origin')
    publishers = Publishers(root, directory, origin, key)
    drafts = Drafts(directory, root, publishers)
    oauth = OAuth(root, directory, origin, publishers)
    server(drafts, oauth, token, key, ('0.0.0.0', int(os.environ.get('PORT', '8080')))).serve_forever()


if __name__ == '__main__':
    main()
