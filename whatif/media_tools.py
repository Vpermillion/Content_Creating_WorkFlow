"""Bounded footage search, verified cache and draft production. No model calls."""
import argparse
import contextlib
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from . import media
from .store import atomic_json, canonical, digest

PRESETS = {
    'off': ('', ''),
    'anime-light': ('hqdn3d=0.6:0.4:1.0:0.7,', ',unsharp=5:5:0.35:3:3:0'),
    'clean-light': ('hqdn3d=1.0:0.7:1.5:1.0,', ',unsharp=5:5:0.3:3:3:0'),
}
PAGE_HOSTS = {'youtube.com', 'www.youtube.com', 'youtu.be', 'vimeo.com', 'www.vimeo.com', 'tenor.com'}
MEDIA_HOSTS = {'media.tenor.com', 'media1.tenor.com', 'cmsapi-frontend.naruto-official.com'}


class ToolError(RuntimeError):
    """Short, non-secret error codes suitable for agent output."""


def key(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def checked_url(url, hosts):
    p = urllib.parse.urlparse(url)
    if p.scheme != 'https' or p.hostname not in hosts or p.username or p.password or p.port not in {None, 443}:
        raise ToolError('unsupported_public_source')
    return url


def text(value, maximum=160):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise ToolError('invalid_label')
    return value.strip()


def run(args, timeout=90):
    try:
        r = subprocess.run(args, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ToolError('command_timeout') from None
    except FileNotFoundError:
        raise ToolError('missing_dependency') from None
    if r.returncode:
        raise ToolError('provider_or_media_command_failed')
    return r.stdout


def ytdlp(args, timeout=45):
    # Ignore machine/browser configs. No cookies, passwords or account login.
    return run([sys.executable, '-m', 'yt_dlp', '--ignore-config', '--compat-options', 'no-certifi',
                '--socket-timeout', '12', '--retries', '0', '--extractor-retries', '0',
                '--no-progress', '--no-warnings', *args], timeout)


class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked_url(newurl, MEDIA_HOSTS | {'tenor.com'})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def public_bytes(url, hosts, max_bytes=4 * 1024 * 1024):
    checked_url(url, hosts)
    with urllib.request.build_opener(PublicRedirect()).open(url, timeout=20) as response:
        checked_url(response.url, hosts)
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ToolError('download_too_large')
    return data


def probe_video(path, max_duration=180, max_bytes=100 * 1024 * 1024):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > max_bytes:
        raise ToolError('missing_or_oversize_video')
    try:
        info = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], 15))
        video = next(s for s in info['streams'] if s['codec_type'] == 'video')
        length = float(video.get('duration') or info['format']['duration'])
        width, height = int(video['width']), int(video['height'])
        if not 0.2 <= length <= max_duration or min(width, height) < 32:
            raise ValueError()
    except (KeyError, ValueError, StopIteration, ToolError):
        raise ToolError('invalid_video') from None
    return {'width': width, 'height': height, 'duration': length, 'bytes': path.stat().st_size,
            'has_audio': any(s['codec_type'] == 'audio' for s in info['streams'])}


def search_web(label, provider, limit):
    if provider == 'youtube':
        info = json.loads(ytdlp(['--flat-playlist', '--skip-download', '--dump-single-json', f'ytsearch{limit}:{label}']))
        found = []
        for entry in info.get('entries', [])[:limit]:
            ident = entry.get('id', '')
            if not re.fullmatch(r'[A-Za-z0-9_-]{11}', ident):
                continue
            found.append({'id': ident, 'title': str(entry.get('title', ''))[:180],
                          'source_url': 'https://www.youtube.com/watch?v=' + ident,
                          'publisher': str(entry.get('channel') or entry.get('uploader') or 'Unknown')[:120],
                          'duration': entry.get('duration'), 'provider': provider})
        return found
    if provider != 'tenor':
        raise ToolError('unsupported_search_provider')
    slug = urllib.parse.quote(re.sub(r'\s+', '-', label), safe='')
    page = public_bytes('https://tenor.com/search/' + slug + '-gifs', {'tenor.com'}).decode()
    match = re.search(r'<script[^>]*id="store-cache"[^>]*>(.*?)</script>', page, re.S)
    if not match:
        raise ToolError('provider_page_changed')
    state = json.loads(match.group(1))
    groups = state.get('universal', {}).get('search', {})
    entries = next(iter(groups.values()), {}).get('results', [])
    found = []
    for entry in entries:
        mp4 = entry.get('media_formats', {}).get('mp4', {})
        if not mp4.get('url') or not mp4.get('duration'):
            continue
        checked_url(mp4['url'], MEDIA_HOSTS)
        source = checked_url(entry['itemurl'], PAGE_HOSTS)
        found.append({'id': str(entry['id']), 'title': html.unescape(entry.get('content_description', ''))[:180],
                      'source_url': source, 'download_url': mp4['url'], 'duration': mp4['duration'],
                      'width': mp4['dims'][0], 'height': mp4['dims'][1],
                      'publisher': entry.get('user', {}).get('username') or 'Unknown Tenor uploader', 'provider': provider})
        if len(found) == limit:
            break
    return found


class Bank:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.catalog_path = self.root / 'catalog.json'

    @contextlib.contextmanager
    def locked(self):
        # A process-scoped OS lock also releases after a killed process.
        import fcntl
        with (self.root / 'catalog.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ToolError('bank_busy') from None
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def catalog(self):
        return json.loads(self.catalog_path.read_text()) if self.catalog_path.exists() else {'schema_version': 1, 'assets': {}}

    def search(self, label, provider='youtube', limit=3, refresh=False):
        label = text(label)
        if provider not in {'youtube', 'tenor'} or not 1 <= limit <= 5:
            raise ToolError('invalid_search_bounds')
        path = self.root / 'searches' / (key([provider, label.casefold(), limit]) + '.json')
        if path.exists() and not refresh:
            cached = json.loads(path.read_text())
            if cached['status'] == 'ok' or time.time() < cached.get('retry_after', 0):
                return {**cached, 'cached': True}
        try:
            result = {'status': 'ok', 'label': label, 'provider': provider,
                      'candidates': search_web(label, provider, limit), 'searched_at': time.time()}
        except (ToolError, OSError, ValueError, KeyError) as e:
            result = {'status': 'blocked', 'label': label, 'provider': provider, 'candidates': [],
                      'error': str(e) if isinstance(e, ToolError) else 'search_unavailable', 'retry_after': time.time() + 1800}
        atomic_json(path, result)
        return {**result, 'cached': False}

    def add(self, path, label, source_url, reuse_status, publisher='Unknown'):
        label, reuse_status = text(label), text(reuse_status, 500)
        checked_url(source_url, PAGE_HOSTS | MEDIA_HOSTS)
        path = Path(path).resolve()
        quality = probe_video(path)
        checksum = digest(path)
        ident = checksum[:24]
        with self.locked():
            catalog = self.catalog()
            prior = catalog['assets'].get(ident)
            if prior:
                self.asset_path(prior)
                prior['labels'] = sorted(set(prior['labels'] + [label]))
                if source_url not in [s['source_url'] for s in prior['sources']]:
                    prior['sources'].append({'source_url': source_url, 'reuse_status': reuse_status, 'publisher': publisher})
                atomic_json(self.catalog_path, catalog)
                return {**prior, 'cached': True}
            destination = self.root / 'objects' / (checksum + '.mp4')
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                temporary = destination.with_suffix('.tmp')
                shutil.copyfile(path, temporary)
                if digest(temporary) != checksum:
                    raise ToolError('copy_checksum_failed')
                temporary.replace(destination)
            elif digest(destination) != checksum:
                raise ToolError('cache_corrupted')
            record = {'id': ident, 'file': str(destination.relative_to(self.root)), 'sha256': checksum,
                      'labels': [label], 'sources': [{'source_url': source_url, 'reuse_status': reuse_status, 'publisher': publisher}],
                      **quality}
            catalog['assets'][ident] = record
            atomic_json(self.catalog_path, catalog)
            return {**record, 'cached': False}

    def asset_path(self, record):
        path = (self.root / record['file']).resolve()
        if not path.is_relative_to(self.root) or not path.is_file() or digest(path) != record['sha256']:
            raise ToolError('cache_corrupted')
        return path

    def find(self, label, limit=5, minimum_duration=0):
        if not 1 <= limit <= 20:
            raise ToolError('invalid_result_limit')
        tokens = set(re.findall(r'\w+', text(label).casefold()))
        ranked = []
        for asset in self.catalog()['assets'].values():
            labels = ' '.join(asset['labels']).casefold()
            overlap = len(tokens & set(re.findall(r'\w+', labels)))
            if overlap and asset['duration'] >= minimum_duration:
                exact = int(label.casefold() in [s.casefold() for s in asset['labels']])
                ranked.append((exact, overlap, min(asset['width'], asset['height']), asset))
        ranked.sort(key=lambda row: row[:3], reverse=True)
        return [row[3] for row in ranked[:limit]]

    def collect(self, labels, provider='tenor', limit=3, per_label=1, min_height=360, refresh=False):
        if not 1 <= len(labels) <= 6 or not 1 <= per_label <= 2 or not 144 <= min_height <= 1080:
            raise ToolError('invalid_collect_bounds')
        results = []
        deadline = time.monotonic() + 180
        for label in labels:
            label = text(label)
            if time.monotonic() >= deadline:
                results.append({'label': label, 'status': 'deferred', 'reason': 'batch_time_limit'})
                continue
            existing = [a for a in self.find(label, 10) if label in a['labels'] and a['height'] >= min_height]
            if len(existing) >= per_label:
                for asset in existing[:per_label]:
                    self.asset_path(asset)
                results.append({'label': label, 'status': 'cached', 'assets': [a['id'] for a in existing[:per_label]]})
                continue
            search = self.search(label, provider, limit, refresh)
            obtained, failures = [a['id'] for a in existing], []
            for candidate in search['candidates']:
                if len(obtained) >= per_label or time.monotonic() >= deadline:
                    break
                if candidate.get('duration') and not .2 <= candidate['duration'] <= 180:
                    failures.append('duration_out_of_range'); continue
                if candidate.get('height') and candidate['height'] < min_height:
                    failures.append('below_quality_floor'); continue
                attempt = self.root / 'attempts' / (key(candidate['source_url']) + '.json')
                if attempt.exists() and not refresh and time.time() < json.loads(attempt.read_text()).get('retry_after', 0):
                    failures.append('cached_source_failure'); continue
                try:
                    with tempfile.TemporaryDirectory(prefix='fetch-', dir=self.root) as temp:
                        target = Path(temp) / 'video.mp4'
                        if candidate.get('download_url'):
                            data = public_bytes(candidate['download_url'], MEDIA_HOSTS, 100 * 1024 * 1024)
                            target.write_bytes(data)
                        else:
                            checked_url(candidate['source_url'], PAGE_HOSTS)
                            ytdlp(['--no-playlist', '--max-filesize', '100M', '--match-filter', 'duration <= 180 & !is_live',
                                   '-f', f'bestvideo[height>={min_height}][height<=1080]/best[height>={min_height}][height<=1080]',
                                   '--remux-video', 'mp4', '-o', str(Path(temp) / 'video.%(ext)s'), candidate['source_url']],
                                  min(90, max(1, deadline - time.monotonic())))
                        quality = probe_video(target)
                        if quality['height'] < min_height:
                            raise ToolError('below_quality_floor')
                        record = self.add(target, label, candidate['source_url'],
                                          'Downloaded public excerpt; republication permission unverified; draft review only', candidate['publisher'])
                        obtained.append(record['id'])
                except (OSError, ToolError) as e:
                    code = str(e) if isinstance(e, ToolError) else 'download_unavailable'
                    failures.append(code)
                    atomic_json(attempt, {'status': 'blocked', 'error': code, 'retry_after': time.time() + 1800})
            results.append({'label': label, 'status': 'ok' if obtained else 'blocked', 'assets': obtained[:per_label],
                            'failures': failures, 'search_cached': search['cached'], 'search_status': search['status']})
        return {'status': 'ok' if all(r['status'] in {'ok', 'cached'} for r in results) else 'partial', 'results': results}


def make_plan(story, bank, enhance='anime-light'):
    if enhance not in PRESETS or not 1 <= len(story.get('scenes', [])) <= 30:
        raise ToolError('invalid_story_or_preset')
    plan = {k: story[k] for k in ['id', 'title', 'narration_sha256']}
    plan.update(schema_version=1, width=story.get('width', 720), height=story.get('height', 1280), fps=30,
                video_only=True, single_pass=True, enhancement=enhance, publishing_authorized=False,
                source_credit='SOURCE EXCERPTS / REVIEW DRAFT', editorial_review='Label matches require visual review', assets=[], scenes=[])
    used, usage = {}, {}
    for scene in story['scenes']:
        queries = scene.get('visual_queries', [])
        if not 1 <= len(queries) <= 4:
            raise ToolError('each_scene_needs_1_to_4_visual_queries')
        length = (scene['end'] - scene['start']) / len(queries)
        shots = []
        for query in queries:
            options = bank.find(query, 20, length + .04)
            if not options:
                raise ToolError('no_cached_clip_long_enough_for_label: ' + text(query))
            exact = [a for a in options if query.casefold() in [s.casefold() for s in a['labels']]]
            options = exact or options[:1]
            asset = min(options, key=lambda a: usage.get(a['id'], 0))
            bank.asset_path(asset)
            usage[asset['id']] = usage.get(asset['id'], 0) + 1
            source = asset['sources'][0]
            used[asset['id']] = {'id': asset['id'], 'file': asset['file'], 'type': 'video', 'sha256': asset['sha256'],
                                 **source, 'labels': asset['labels']}
            factor = max(plan['width'] / asset['width'], plan['height'] / asset['height'])
            shots.append({'asset': asset['id'], 'fit': 'contain' if factor > 2 else 'cover', 'trim_start': 0,
                          'match_reason': 'Catalog label match: ' + text(query) + '; editorial verification pending'})
        plan['scenes'].append({k: scene[k] for k in ['start', 'end', 'text', 'label']} | {'shots': shots})
    plan['assets'] = list(used.values())
    return plan


def enhance_file(source, destination, preset='anime-light', height=None):
    if preset not in PRESETS or height not in {None, 360, 720, 1080}:
        raise ToolError('invalid_enhancement_profile')
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or destination.exists():
        raise ToolError('preserve_original_choose_new_output')
    before = probe_video(source)
    pre, post = PRESETS[preset]
    # Resample without changing aspect ratio; preserve color and native frame rate.
    filters = pre + (f'scale=-2:{height}:flags=lanczos' if height else 'scale=trunc(iw/2)*2:trunc(ih/2)*2:flags=lanczos') + post
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.stem + '.partial.mp4')
    try:
        run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-threads', '2', '-filter_threads', '1', '-i', str(source),
             '-map', '0:v:0', '-map', '0:a?', '-vf', filters, '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast',
             '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', str(temporary)], 180)
        after = probe_video(temporary)
        if abs(after['duration'] - before['duration']) > .1 or after['has_audio'] != before['has_audio']:
            raise ToolError('enhancement_track_mismatch')
        run(['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-i', str(temporary), '-f', 'null', '-'], 90)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {'status': 'ok', 'output': str(destination), 'preset': preset, 'before': before, 'after': after,
            'sha256': digest(destination), 'detail_restoration_claimed': False}


def build(story, narration, bank, output, enhancement='anime-light', download=False, provider='tenor'):
    if digest(narration) != story['narration_sha256']:
        raise ToolError('narration_hash_mismatch')
    if download:
        labels = sorted({q for s in story['scenes'] for q in s['visual_queries']})
        if len(labels) > 6:
            raise ToolError('collect_at_most_6_labels_per_batch')
        bank.collect(labels, provider=provider)
    plan = make_plan(story, bank, enhancement)
    from . import media_edit
    output = Path(output).resolve()
    fingerprint = key([plan, digest(narration), digest(Path(media_edit.__file__)), digest(Path(__file__))])
    receipt = output / 'tool-run.json'
    if receipt.exists():
        prior = json.loads(receipt.read_text())
        if prior['fingerprint'] != fingerprint:
            raise ToolError('output_belongs_to_different_inputs')
        if digest(output / 'video.mp4') != prior['sha256']:
            raise ToolError('cached_output_corrupted')
        return {**prior, 'status': 'cached'}
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / 'plan.json', plan)
    result = media_edit.render_edit(plan, bank.root, narration, output)
    record = {'status': 'ok', 'fingerprint': fingerprint, 'video': str(result), 'sha256': digest(result),
              'plan': str(output / 'plan.json'), 'quality': str(output / 'quality.json'), 'publishing_enabled': False}
    atomic_json(receipt, record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bank', default='private/media-bank')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('search'); p.add_argument('label'); p.add_argument('--provider', choices=['youtube', 'tenor'], default='youtube'); p.add_argument('--limit', type=int, default=3); p.add_argument('--refresh', action='store_true')
    p = sub.add_parser('collect'); p.add_argument('labels', nargs='+'); p.add_argument('--provider', choices=['youtube', 'tenor'], default='tenor'); p.add_argument('--limit', type=int, default=3); p.add_argument('--per-label', type=int, default=1); p.add_argument('--min-height', type=int, default=360); p.add_argument('--refresh', action='store_true')
    p = sub.add_parser('import'); p.add_argument('file'); p.add_argument('--label', required=True); p.add_argument('--source-url', required=True); p.add_argument('--reuse-status', required=True)
    p = sub.add_parser('find'); p.add_argument('label'); p.add_argument('--limit', type=int, default=5)
    p = sub.add_parser('enhance'); p.add_argument('file'); p.add_argument('output'); p.add_argument('--preset', choices=PRESETS, default='anime-light'); p.add_argument('--height', type=int, choices=[360, 720, 1080])
    p = sub.add_parser('build'); p.add_argument('story'); p.add_argument('--narration', required=True); p.add_argument('--output', required=True); p.add_argument('--download', action='store_true'); p.add_argument('--provider', choices=['youtube', 'tenor'], default='tenor'); p.add_argument('--enhance', choices=PRESETS, default='anime-light')
    args = parser.parse_args()
    try:
        bank = Bank(args.bank)
        if args.command == 'search': result = bank.search(args.label, args.provider, args.limit, args.refresh)
        elif args.command == 'collect': result = bank.collect(args.labels, args.provider, args.limit, args.per_label, args.min_height, args.refresh)
        elif args.command == 'import':
            a = bank.add(args.file, args.label, args.source_url, args.reuse_status); result = {'status': 'cached' if a['cached'] else 'ok', 'asset': a['id']}
        elif args.command == 'find': result = {'status': 'ok', 'assets': [{k: a[k] for k in ['id', 'width', 'height', 'duration', 'labels']} for a in bank.find(args.label, args.limit)]}
        elif args.command == 'enhance': result = enhance_file(args.file, args.output, args.preset, args.height)
        else: result = build(json.loads(Path(args.story).read_text()), args.narration, bank, args.output, args.enhance, args.download, args.provider)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['status'] in {'ok', 'cached'} else 2
    except (ToolError, OSError, ValueError, KeyError, RuntimeError) as e:
        print(json.dumps({'status': 'blocked', 'error': str(e) if isinstance(e, ToolError) else 'invalid_input_or_media_failure'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
