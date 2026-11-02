"""Collect public review footage/sounds on the media runner; preserve acquisition receipts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from whatif import audio_fx, media, media_tools
from whatif.store import atomic_json, digest, identifier


def choose_candidate(candidates, required, min_seconds=1.8):
    matches = []
    for candidate in candidates:
        haystack = (candidate.get('title', '') + ' ' + candidate.get('source_url', '')).casefold()
        if required and not any(term.casefold() in haystack for term in required):
            continue
        if candidate.get('duration', 0) < min_seconds or candidate.get('width', 0) < 300 or candidate.get('height', 0) < 160:
            continue
        matches.append(candidate)
    if not matches:
        raise ValueError('No sufficiently long, identified moving footage candidate')
    return max(matches, key=lambda c: (min(c['duration'], 6), min(c['width'], 640)))


def acquire_footage(spec, output):
    name = identifier(spec['id'])
    query = media_tools.text(spec['query'])
    terms = spec.get('required_terms', [])
    if not isinstance(terms, list) or not terms or not all(isinstance(t, str) and 1 <= len(t) <= 50 for t in terms):
        raise ValueError('Footage selection needs bounded identifying terms')
    candidates = media_tools.search_web(query, 'tenor', 5)
    selected = choose_candidate(candidates, terms, spec.get('min_seconds', 1.8))
    data = media_tools.public_bytes(selected['download_url'], media_tools.MEDIA_HOSTS, 15_000_000)
    path = output / 'footage' / (name + '.mp4')
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    info = media_tools.probe_video(path)
    return {'id': name, 'file': name + '.mp4', 'type': 'video', 'query': query,
            'source_url': selected['source_url'], 'download_url': selected['download_url'],
            'sha256': digest(path), 'duration': info['duration'], 'dimensions': [info['width'], info['height']],
            'description': selected['title'], 'publisher': selected['publisher'],
            'reuse_status': 'Publicly posted fictional footage; republication rights unverified; private fan-commentary review',
            'selection_basis': 'Identifying term plus duration/resolution; visual/semantic review still required',
            'candidates': candidates}


def acquire_sound(record, output):
    url = audio_fx.checked_effect_url(record['download_url'])
    if url.hostname != 'dvi.dubbingai.io':
        raise ValueError('This acquisition request is limited to the supplied DubbingAI collection')
    request = urllib.request.Request(record['download_url'], headers={
        'User-Agent': 'Mozilla/5.0 (compatible; IfverseSoundReader/1.0)'})
    with urllib.request.urlopen(request, timeout=30) as response:
        if audio_fx.checked_effect_url(response.url).hostname != url.hostname:
            raise ValueError('Unexpected sound acquisition redirect')
        data = response.read(2_000_001)
    if not data or len(data) > 2_000_000:
        raise ValueError('Sound acquisition size exceeds its limit')
    name = identifier(record['id']) + '.mp3'
    path = output / 'sounds' / name
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    probe = media.probe(path)
    stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
    duration = float(probe['format']['duration'])
    if stream is None or not math.isfinite(duration) or not .05 <= duration <= 180:
        raise ValueError('Published source is not bounded decodable audio')
    media.command(['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-'])
    asset = copy.deepcopy(record)
    asset.update(file=name, sha256=digest(path), duration_seconds=duration, playback_rate=1,
                 download_status='downloaded_probed_hashed',
                 license='Community-hosted excerpt; reuse rights unverified',
                 license_url=record['source_url'],
                 usage_basis='Owner-requested collection recording for a fictional private review; no publication authorization',
                 checksum_origin='First acquisition from the published HTTPS source; frozen for subsequent cache/mix verification')
    return asset


def run(request, output):
    identifier(request['id'])
    footage, sound_ids = request.get('footage', []), request.get('sound_ids', [])
    if request.get('schema_version') != 1 or not 1 <= len(footage) <= 16 or not 1 <= len(sound_ids) <= 4:
        raise ValueError('Invalid bounded source request')
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a fresh source output')
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / 'request.json', request)
    discovery = json.loads((ROOT / 'assets/sfx/dubbingai-discovery.json').read_text())
    index = {r['id']: r for r in discovery['discovered_recordings']}
    if not all(s in index for s in sound_ids):
        raise ValueError('Unknown recording in the supplied source collection')
    result = {'schema_version': 1, 'id': request['id'], 'status': 'running', 'footage': [], 'sound_catalog': {'schema_version': 1, 'assets': []}, 'publishing_enabled': False}
    atomic_json(output / 'sources.json', result)
    try:
        # Preserve every finished acquisition even if another provider request fails.
        tasks = [('footage', s) for s in footage] + [('sound', index[s]) for s in sound_ids]
        def execute(task):
            kind, spec = task
            try:
                value = acquire_footage(spec, output) if kind == 'footage' else acquire_sound(spec, output)
                return kind, value, None
            except Exception as exc:
                return kind, None, {'id': spec['id'], 'error_type': type(exc).__name__, 'error': str(exc)[:250]}
        with ThreadPoolExecutor(max_workers=3) as pool:
            for kind, value, error in pool.map(execute, tasks):
                if error:
                    result.setdefault('errors', []).append(error)
                elif kind == 'footage':
                    result['footage'].append(value)
                else:
                    result['sound_catalog']['assets'].append(value)
                atomic_json(output / 'sources.json', result)
        result['status'] = 'failed' if result.get('errors') else 'success'
        # A single contact sheet gives the reviewer source identities before editing.
        for i, asset in enumerate(result['footage']):
            media.ffmpeg(['-ss', str(min(asset['duration'] * .4, 2)), '-i', str(output/'footage'/asset['file']),
                          '-frames:v', '1', '-vf', f"scale=256:144:force_original_aspect_ratio=decrease,pad=256:176:(ow-iw)/2:24,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text={asset['id']}:x=5:y=4:fontsize=12:fontcolor=white",
                          f'preview-{i:02}.jpg'], output)
        count = len(result['footage'])
        if count:
            media.ffmpeg(['-pattern_type', 'glob', '-i', 'preview-*.jpg', '-vf', f'tile=3x{math.ceil(count/3)}:padding=4:margin=4',
                          '-frames:v', '1', 'source-contact.jpg'], output)
    except Exception as exc:
        result['status'] = 'failed'
        result.setdefault('errors', []).append({'stage': 'collection_or_preview', 'error': str(exc)[:250]})
        raise
    finally:
        atomic_json(output / 'sources.json', result)
    print(json.dumps({'status': result['status'], 'footage': len(result['footage']), 'sounds': len(result['sound_catalog']['assets']), 'errors': result.get('errors', [])}))
    if result['status'] != 'success':
        raise ValueError('One or more requested source acquisitions failed; inspect preserved receipts')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args()
    path = Path(args.request).resolve()
    if not path.is_relative_to(ROOT / 'source-requests') or path.suffix != '.json' or path.stat().st_size > 100_000:
        raise ValueError('Source request must be bounded JSON under source-requests/')
    run(json.loads(path.read_text()), args.output)
