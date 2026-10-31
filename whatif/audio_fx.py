"""Download described sound effects and place them on verified narration anchors."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import urllib.parse
import urllib.request
import wave

from . import media
from .media_edit import local_asset
from .store import atomic_json, digest


def number(value, low, high, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Invalid ' + label)
    return float(value)


def search_effects(catalog, query):
    tokens = set(re.findall(r'\w+', query.casefold()))
    found = []
    for asset in catalog['assets']:
        tags = set(re.findall(r'\w+', ' '.join(asset['tags']).casefold()))
        description = set(re.findall(r'\w+', asset['description'].casefold()))
        score = len(tokens & tags) * 3 + len(tokens & description)
        if score:
            found.append({'id': asset['id'], 'score': score, 'description': asset['description'],
                          'source_url': asset['source_url'], 'license': asset['license']})
    return sorted(found, key=lambda row: (-row['score'], row['id']))


def fetch_effect(asset, cache):
    if not all(asset.get(k) for k in ['source_url', 'license', 'license_url', 'usage_basis', 'description']):
        raise ValueError('Sound effect provenance missing')
    url = urllib.parse.urlparse(asset['download_url'])
    if (url.scheme != 'https' or url.hostname != 'raw.githubusercontent.com' or url.username or url.password
            or url.port not in {None, 443} or not re.search(r'/[0-9a-f]{40}/', url.path)):
        raise ValueError('Use a commit-pinned HTTPS sound source from raw.githubusercontent.com')
    target = local_asset(cache, asset['file'])
    if target.exists():
        if digest(target) != asset['sha256']:
            raise ValueError('Cached sound effect checksum changed')
        return target
    with urllib.request.urlopen(asset['download_url'], timeout=25) as response:
        if urllib.parse.urlparse(response.url).hostname != url.hostname:
            raise ValueError('Unexpected sound-effect redirect')
        data = response.read(2_000_001)
    if len(data) > 2_000_000 or hashlib.sha256(data).hexdigest() != asset['sha256']:
        raise ValueError('Sound effect size/checksum mismatch')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def anchor_time(words, cue):
    tokens = []
    for word in words:
        for token in re.findall(r'\w+', word['word'].casefold()):
            tokens.append((token, word['start'], word['end']))
    anchor = cue['anchor']
    wanted = re.findall(r'\w+', anchor['phrase'].casefold())
    if not wanted:
        raise ValueError('Sound cue needs a spoken phrase')
    matches = [i for i in range(len(tokens) - len(wanted) + 1)
               if [t[0] for t in tokens[i:i + len(wanted)]] == wanted]
    occurrence = anchor.get('occurrence')
    if occurrence is None:
        if len(matches) != 1:
            raise ValueError('Sound anchor missing or ambiguous; specify its occurrence')
        selected = matches[0]
    else:
        if isinstance(occurrence, bool) or not isinstance(occurrence, int) or not 1 <= occurrence <= len(matches):
            raise ValueError('Invalid sound anchor occurrence')
        selected = matches[occurrence - 1]
    edge = anchor.get('edge', 'end')
    if edge not in {'start', 'end'}:
        raise ValueError('Invalid sound anchor edge')
    at = tokens[selected][1] if edge == 'start' else tokens[selected + len(wanted) - 1][2]
    return at + number(cue.get('offset_seconds', .04), -.3, .5, 'sound offset')


def read_pcm(path):
    import numpy as np
    with wave.open(str(path), 'rb') as stream:
        if (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) != (1, 2, 24000):
            raise ValueError('Expected mono 24 kHz PCM narration/effects')
        return np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2').astype(np.float32) / 32768


def mix_effects(video, narration, transcript, plan, catalog, cache, output):
    import numpy as np
    video, narration, output, cache = [Path(p).resolve() for p in [video, narration, output, cache]]
    original_hash = digest(narration)
    if plan.get('schema_version') != 1 or plan.get('narration_sha256') != original_hash:
        raise ValueError('Sound plan must match the retained narration checksum')
    if transcript.get('audio_sha256') != original_hash:
        raise ValueError('Sound anchors belong to different audio')
    cues = plan.get('cues')
    if not isinstance(cues, list) or not 1 <= len(cues) <= 20:
        raise ValueError('Use one to twenty intentional sound cues')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a fresh directory for the sound-effect version')
    if video.is_relative_to(output) or narration.is_relative_to(output):
        raise ValueError('Keep original video and narration outside sound output')
    dry = read_pcm(narration)
    duration = len(dry) / 24000
    if abs(media.duration(video) - duration) > .1:
        raise ValueError('Video and retained narration durations differ')
    assets = {a['id']: a for a in catalog['assets']}
    prepared = []
    for cue in cues:
        if cue.get('effect') not in assets or not cue.get('reason'):
            raise ValueError('Sound cue needs a known effect and a script-specific reason')
        at = anchor_time(transcript['words'], cue)
        if not 0 <= at < duration:
            raise ValueError('Sound cue falls outside the video')
        length = number(cue.get('max_seconds', .8), .08, 1.8, 'sound duration')
        level = number(cue.get('peak_dbfs', -18), -32, -12, 'sound level')
        asset = assets[cue['effect']]
        number(asset.get('playback_rate', 1), .5, 1.5, 'sound playback rate')
        prepared.append((cue, asset, at, length, level))
    output.mkdir(parents=True, exist_ok=True)
    wet = np.zeros_like(dry)
    receipts = []
    # Detect speech on a 20 ms energy envelope, then attenuate effects during it.
    block = 480
    padded = np.pad(dry, (0, (-len(dry)) % block))
    rms = np.sqrt(np.mean(padded.reshape(-1, block) ** 2, axis=1))
    envelope = np.pad(rms, (2, 2))
    active = np.maximum.reduce([envelope[i:i + len(rms)] for i in range(5)]) > .018
    duck = np.interp(np.arange(len(dry)), (np.arange(len(rms)) + .5) * block,
                     np.where(active, .5, 1)).astype(np.float32)
    for i, (cue, asset, at, length, level) in enumerate(prepared):
        source = fetch_effect(asset, cache)
        decoded = output / f'effect-{i:02}.wav'
        rate = asset.get('playback_rate', 1)
        media.ffmpeg(['-i', str(source), '-ar', '24000', '-ac', '1', '-af',
                      f'aresample=24000,asetrate={round(24000 * rate)},aresample=24000',
                      '-t', str(length), '-c:a', 'pcm_s16le', decoded.name], output)
        sound = read_pcm(decoded)[:round(length * 24000)]
        if len(sound) < 2 or not np.isfinite(sound).all() or float(np.max(np.abs(sound))) <= 0:
            raise ValueError('Downloaded sound effect is empty or silent')
        sound = sound / np.max(np.abs(sound))
        if asset.get('sub_bass_hz'):
            hz = number(asset['sub_bass_hz'], 35, 100, 'sub-bass frequency')
            seconds = np.arange(len(sound)) / 24000
            sound = .55 * sound + .65 * np.sin(2 * np.pi * hz * seconds) * np.exp(-7 * seconds)
        sound = sound / np.max(np.abs(sound)) * (10 ** (level / 20))
        fade = min(720, len(sound) // 2)
        sound[:min(120, len(sound))] *= np.linspace(0, 1, min(120, len(sound)))
        sound[-fade:] *= np.linspace(1, 0, fade)
        start = round(at * 24000)
        if start + len(sound) > len(wet):
            raise ValueError('Sound effect extends beyond video; choose an earlier beat')
        wet[start:start + len(sound)] += sound
        receipts.append({**cue, 'start_seconds': at, 'end_seconds': at + len(sound) / 24000,
                         'source_sha256': asset['sha256'], 'source_url': asset['source_url'],
                         'license': asset['license'], 'license_url': asset['license_url'],
                         'playback_rate': rate})
    wet *= duck
    mixed = dry + wet
    peak = float(np.max(np.abs(mixed)))
    gain = min(1.0, .97 / peak) if peak else 1.0
    mixed *= gain
    wav = output / 'mix.wav'
    with wave.open(str(wav), 'wb') as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(24000)
        stream.writeframes((mixed * 32767).astype('<i2').tobytes())
    media.ffmpeg(['-i', str(video), '-i', str(wav), '-map', '0:v:0', '-map', '1:a:0',
                  '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-t', str(duration),
                  '-movflags', '+faststart', 'video-sfx.mp4'], output)
    result = output / 'video-sfx.mp4'
    info = media.probe(result)
    v = next(s for s in info['streams'] if s['codec_type'] == 'video')
    a = next(s for s in info['streams'] if s['codec_type'] == 'audio')
    if abs(float(v['duration']) - duration) > .1 or abs(float(a['duration']) - duration) > .1:
        raise ValueError('Sound version lost audio/video coverage')
    media.command(['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-i', str(result), '-f', 'null', '-'])
    if digest(narration) != original_hash:
        raise ValueError('Retained narration changed during sound mix')
    report = {'schema_version': 1, 'status': 'success', 'video': result.name, 'duration_seconds': duration,
              'cues': receipts, 'effects_count': len(receipts), 'effects_ducked_during_speech_db': -6.0206,
              'mix_peak_dbfs': 20 * math.log10(max(float(np.max(np.abs(mixed))), 1e-10)),
              'master_gain': gain, 'narration_sha256': original_hash, 'source_video_sha256': digest(video),
              'video_sha256': digest(result), 'video_stream_copied': True,
              'source_catalog': catalog, 'caption_timing_unchanged': True, 'publishing_enabled': False}
    atomic_json(output / 'sound-effects.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['search', 'mix'])
    parser.add_argument('--catalog', default='assets/sfx/catalog.json')
    parser.add_argument('--query')
    for name in ['video', 'narration', 'transcript', 'plan', 'output']:
        parser.add_argument('--' + name)
    parser.add_argument('--cache', default='private/sfx-cache')
    args = parser.parse_args()
    catalog = json.loads(Path(args.catalog).read_text())
    if args.operation == 'search':
        if not args.query: parser.error('search requires --query')
        print(json.dumps(search_effects(catalog, args.query)))
    else:
        if not all(getattr(args, key) for key in ['video', 'narration', 'transcript', 'plan', 'output']):
            parser.error('mix requires video, narration, transcript, plan and output paths')
        print(json.dumps(mix_effects(args.video, args.narration, json.loads(Path(args.transcript).read_text()),
                                   json.loads(Path(args.plan).read_text()), catalog, args.cache, args.output)))


if __name__ == '__main__':
    main()
