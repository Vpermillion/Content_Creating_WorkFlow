"""Produce a new anime review test from existing footage plans in one finite run."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import difflib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import urllib.request
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from whatif import media, media_edit
from whatif.store import atomic_json, digest, identifier

MODEL_URLS = {
    'kokoro-v1.0.onnx': 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx',
    'voices-v1.0.bin': 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin',
}


def model_files(folder):
    folder.mkdir(parents=True, exist_ok=True)
    checksums = {}
    for name, url in MODEL_URLS.items():
        target = folder / name
        receipt = target.with_suffix(target.suffix + '.sha256')
        if target.exists():
            if not receipt.exists() or digest(target) != receipt.read_text().strip():
                raise ValueError('Cached model checksum changed')
        else:
            partial = target.with_suffix(target.suffix + '.partial')
            count = 0
            with urllib.request.urlopen(url, timeout=40) as response, partial.open('wb') as out:
                while chunk := response.read(1024 * 1024):
                    count += len(chunk)
                    if count > 550 * 1024 * 1024:
                        raise ValueError('Model file exceeds download limit')
                    out.write(chunk)
            partial.replace(target)
            receipt.write_text(digest(target) + '\n')
        checksums[name] = {'url': url, 'sha256': digest(target)}
    return checksums


def narrate(spec, output, models, voice):
    import numpy as np
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    receipts = model_files(models / 'kokoro')
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(models / 'kokoro/kokoro-v1.0.onnx'), sess_options=options,
                                 providers=['CPUExecutionProvider'])
    engine = Kokoro.from_session(session, str(models / 'kokoro/voices-v1.0.bin'))
    parts, segments, cursor = [], [], 0
    for scene in spec['scenes']:
        samples, rate = engine.create(scene['text'], voice=voice, speed=1.08, lang='en-us')
        samples = np.asarray(samples, dtype=np.float32).reshape(-1)
        if rate != 24000 or not np.isfinite(samples).all() or not .5 < len(samples) / rate < 25:
            raise ValueError('Invalid generated speech')
        peak = float(np.max(np.abs(samples)))
        if peak > .95:
            samples *= .95 / peak
        begin = cursor / rate
        cursor += len(samples)
        segments.append({'start': begin, 'end': cursor / rate, 'text': scene['text'], 'label': scene['label']})
        parts.append(samples)
    samples = np.concatenate(parts)
    with wave.open(str(output / 'narration.wav'), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes((samples * 32767).astype('<i2').tobytes())
    atomic_json(output / 'narration.json', {'provider': 'kokoro-onnx', 'version': '0.6.1', 'voice': voice,
                'device': 'cpu', 'new_test_version': True, 'segments': segments, 'model_files': receipts,
                'sha256': digest(output / 'narration.wav')})
    return segments


def phrase_captions(words, duration):
    phrases, group = [], []
    for word in words:
        token = word['word'].strip()
        if not token:
            continue
        token = re.sub(r'[{}<>\\\r\n]', '', token)
        group.append({'word': token, 'start': float(word['start']), 'end': float(word['end'])})
        if len(group) >= 5 or token.endswith(('.', '?', '!')):
            phrases.append(group)
            group = []
    if group:
        phrases.append(group)
    captions = []
    for phrase in phrases:
        start, end = max(0, phrase[0]['start']), min(duration, phrase[-1]['end'])
        if end <= start:
            raise ValueError('Speech recognizer returned an empty caption interval')
        captions.append({'start': start, 'end': end, 'text': ' '.join(w['word'] for w in phrase)})
    if not captions:
        raise ValueError('No speech recognized')
    return captions


def asr_audio(audio, output):
    """Use Whisper's supported waveform input, avoiding version-specific PyAV decoding."""
    import numpy as np
    media.ffmpeg(['-i', str(Path(audio).resolve()), '-ar', '16000', '-ac', '1',
                  '-c:a', 'pcm_s16le', 'asr-input.wav'], output)
    with wave.open(str(output / 'asr-input.wav'), 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 16000):
            raise ValueError('Unexpected caption audio format')
        return np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2').astype(np.float32) / 32768


def transcribe(audio, output, models, spec):
    from faster_whisper import WhisperModel
    engine = WhisperModel('tiny.en', device='cpu', compute_type='int8', cpu_threads=2, num_workers=1,
                          download_root=str(models / 'whisper'))
    found, info = engine.transcribe(asr_audio(audio, output), language='en', beam_size=3, word_timestamps=True,
                                   initial_prompt='Naruto, Akatsuki, Nine Tails, Hidden Leaf.',
                                   condition_on_previous_text=False, vad_filter=False)
    words = []
    for segment in found:
        words.extend({'word': w.word, 'start': w.start, 'end': w.end, 'probability': w.probability}
                     for w in segment.words or [])
    captions = phrase_captions(words, media.duration(audio))
    expected = re.findall(r'\w+', ' '.join(s['text'] for s in spec['scenes']).casefold())
    recognized = re.findall(r'\w+', ' '.join(w['word'] for w in words).casefold())
    agreement = difflib.SequenceMatcher(a=expected, b=recognized, autojunk=False).ratio()
    if agreement < .75:
        raise ValueError('Caption transcript differs substantially from the prepared script')
    atomic_json(output / 'transcription.json', {'engine': 'faster-whisper', 'model': 'tiny.en',
                'device': 'cpu', 'compute_type': 'int8', 'words': words, 'captions': captions,
                'script_token_agreement': agreement, 'review_names_required': True})
    return captions, agreement


def retime_plan(original, segments, root, narration):
    plan = copy.deepcopy(original)
    if len(plan['scenes']) != len(segments):
        raise ValueError('Prepared script and footage plan have different scene counts')
    assets = {a['id']: a for a in plan['assets']}
    for scene, speech in zip(plan['scenes'], segments):
        original_shots = scene['shots']
        duration = speech['end'] - speech['start']
        selected = None
        for count in range(len(original_shots), 5):
            shots = [copy.deepcopy(original_shots[i % len(original_shots)]) for i in range(count)]
            if all(media.duration(root / assets[s['asset']]['file']) - s.get('trim_start', 0)
                   >= duration / count + .04 for s in shots):
                selected = shots
                break
        if selected is None:
            raise ValueError('Retained matching excerpts cannot cover the new speech; review the shot plan')
        for shot in selected:
            shot['fit'] = 'contain'  # Preserve the source frame; avoid an enlarged narrow portrait crop.
        scene.update(speech)
        scene['shots'] = selected
    plan.update(narration_sha256=digest(narration), video_only=True, single_pass=True,
                enhancement='anime-light', source_credit='ONLINE ANIME EXCERPTS / REVIEW DRAFT',
                publishing_authorized=False)
    return plan


def run(request, output, models):
    operation = identifier(request['id'])
    if request.get('channel') != 'ifverse_anime' or request.get('voice') not in {'af_heart', 'am_michael'}:
        raise ValueError('Unsupported test channel or voice')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a fresh output directory for a new test version')
    output.mkdir(parents=True, exist_ok=True)
    source = json.loads((ROOT / 'pilots/alpha-anime-001.json').read_text())
    original = json.loads((ROOT / 'edits/alpha-anime-video.v2.json').read_text())
    started, timings = time.monotonic(), {}
    atomic_json(output / 'request.json', request)
    (output / 'script.md').write_text('# ' + source['title'] + '\n\n' +
                                    '\n\n'.join(s['text'] for s in source['scenes']) + '\n')
    assets = models.parent / 'footage'
    mark = time.monotonic()
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda asset: media_edit.fetch_assets({'assets': [asset]}, assets), original['assets']))
    timings['footage_seconds'] = round(time.monotonic() - mark, 3)
    mark = time.monotonic()
    retained = request.get('reuse_narration_from')
    if retained:
        prior = (ROOT / retained).resolve()
        if not prior.is_relative_to(ROOT / 'artifacts'):
            raise ValueError('Retained test narration must come from the repository artifacts')
        receipt = json.loads((prior / 'narration.json').read_text())
        if receipt['voice'] != request['voice'] or receipt['sha256'] != digest(prior / 'narration.wav'):
            raise ValueError('Retained narration voice or checksum mismatch')
        segments = receipt['segments']
        if [s['text'] for s in segments] != [s['text'] for s in source['scenes']]:
            raise ValueError('Retained narration belongs to another script')
        for name in ['narration.wav', 'narration.json']:
            shutil.copy2(prior / name, output / name)
    else:
        segments = narrate(source, output, models, request['voice'])
    timings['narration_seconds'] = round(time.monotonic() - mark, 3)
    mark = time.monotonic()
    captions, agreement = transcribe(output / 'narration.wav', output, models, source)
    timings['captioning_seconds'] = round(time.monotonic() - mark, 3)
    plan = retime_plan(original, segments, assets, output / 'narration.wav')
    plan.update(id=operation, caption_segments=captions)
    atomic_json(output / 'plan.json', plan)
    mark = time.monotonic()
    video = media_edit.render_edit(plan, assets, output / 'narration.wav', output / 'render')
    timings['render_and_decode_seconds'] = round(time.monotonic() - mark, 3)
    timings['pipeline_seconds'] = round(time.monotonic() - started, 3)
    report = {'status': 'success', 'id': operation, 'video': str(video.relative_to(output)),
              'duration_seconds': media.duration(video), 'timings': timings,
              'voice': {'provider': 'kokoro-onnx', 'voice': request['voice'], 'device': 'cpu',
                        'reused_verified_audio': bool(retained)},
              'captions': {'engine': 'faster-whisper', 'model': 'tiny.en', 'compute_type': 'int8',
                           'phrases': len(captions), 'script_token_agreement': agreement},
              'footage': 'Existing traced online Naruto clip plan; reframed to retain source image',
              'publishing_enabled': False, 'github_run_id': os.environ.get('GITHUB_RUN_ID'),
              'limitations': ['Fan-made hypothetical review draft; source reuse permissions unverified',
                              'Pronunciation, character names and full audiovisual review remain required']}
    atomic_json(output / 'result.json', report)
    print(json.dumps(report))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--models', default='private/test-video/models')
    args = parser.parse_args()
    destination = Path(args.output)
    try:
        run(json.loads(Path(args.request).read_text()), destination, Path(args.models))
    except Exception as error:
        atomic_json(destination / 'result.json', {'status': 'failed', 'error_type': type(error).__name__,
                    'error': str(error)[:500], 'github_run_id': os.environ.get('GITHUB_RUN_ID'),
                    'publishing_enabled': False})
        raise
