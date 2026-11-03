"""Acquire the published collection with bounded reads and full decode receipts."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from whatif.audio_fx import checked_effect_url
from whatif.store import atomic_json

LIMIT = 16 * 1024 * 1024

def acquire(entry):
    entry = dict(entry)
    target = ROOT / 'assets/sfx/bank' / (entry['id'] + '.mp3')
    target.parent.mkdir(exist_ok=True)
    checked_effect_url(entry['download_url'])
    if target.exists():
        data = target.read_bytes()
    else:
        request = urllib.request.Request(entry['download_url'], headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=60) as response:
            if checked_effect_url(response.url).hostname != 'dvi.dubbingai.io':
                raise ValueError('Unexpected redirect')
            data = response.read(LIMIT + 1)
    if not data or len(data) > LIMIT:
        raise ValueError('Recording exceeds bounded bank size')
    sha = hashlib.sha256(data).hexdigest()
    if entry.get('sha256') and entry['sha256'] != sha:
        raise ValueError('Previously frozen source changed: ' + entry['id'])
    target.write_bytes(data)
    subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(target),'-f','null','-'], check=True, capture_output=True)
    probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(target)]))
    audio = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    entry.update(sha256=sha, file=target.name, bytes=len(data), duration_seconds=float(probe['format']['duration']),
                 download_status='downloaded_probed_hashed', decode_check='passed_complete_ffmpeg_xerror',
                 sample_rate=int(audio['sample_rate']), channels=audio['channels'], playback_rate=1,
                 license='Community-hosted excerpt; reuse rights unverified', license_url=entry['source_url'],
                 usage_basis='Owner-requested sound-only repair and review; publication not authorized',
                 checksum_origin='Published HTTPS acquisition; frozen for subsequent verification')
    entry['media_kind'] = 'short_effect' if entry['id'] in {'dubbingai_vine_boom','dubbingai_rizz_effect','dubbingai_faaah'} else 'music_or_vocal_excerpt_requires_audition'
    entry['selection_note'] = 'Audition actual duration/content; descriptions are discovery summaries, not a short-effect guarantee.'
    print(entry['id'], len(data), flush=True)
    return entry

def main():
    discovery = json.loads((ROOT / 'assets/sfx/dubbingai-discovery.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        assets = list(pool.map(acquire, discovery['discovered_recordings']))
    atomic_json(ROOT / 'assets/sfx/dubbingai-bank.json', {'schema_version':1, 'cache_directory':'assets/sfx/bank',
                'max_recording_bytes':LIMIT, 'source_url':discovery['source_url'], 'assets':assets})
    discovery.update(status='all_17_downloaded_decoded_hashed', discovered_recordings=assets)
    atomic_json(ROOT / 'assets/sfx/dubbingai-discovery.json', discovery)

if __name__ == '__main__':
    main()
