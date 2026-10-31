"""Produce a new anime review test from existing footage plans in one finite run."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import difflib
import hashlib
import json
import math
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
from whatif import audio_fx, media, media_edit
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
    timing = fit_narration_duration(output, segments, spec.get('target_duration_seconds'))
    atomic_json(output / 'narration.json', {'provider': 'kokoro-onnx', 'version': '0.6.1', 'voice': voice,
                'device': 'cpu', 'new_test_version': True, 'segments': segments, 'model_files': receipts,
                'duration_adjustment': timing,
                'sha256': digest(output / 'narration.wav')})
    return segments


def fit_narration_duration(output, segments, target):
    """Fit a newly generated version to its requested length without changing pitch."""
    if target is None:
        return None
    if isinstance(target, bool) or not isinstance(target, (int, float)) or not math.isfinite(target) or not 30 <= target <= 75:
        raise ValueError('Target duration must be between 30 and 75 seconds')
    original = media.duration(output / 'narration.wav')
    tempo = original / target
    if not .7 <= tempo <= 1.35:
        raise ValueError('Rewrite the script; requested length needs excessive speech retiming')
    raw = output / 'narration-unretimed.wav'
    (output / 'narration.wav').rename(raw)
    media.ffmpeg(['-i', str(raw), '-af', f'atempo={tempo:.10f},apad,atrim=duration={target}',
                  '-ar', '24000', '-ac', '1', '-c:a', 'pcm_s16le', 'narration.wav'], output)
    actual = media.duration(output / 'narration.wav')
    for scene in segments:
        scene['start'] *= actual / original
        scene['end'] *= actual / original
    segments[-1]['end'] = actual
    return {'original_seconds': original, 'target_seconds': target, 'actual_seconds': actual,
            'tempo': tempo, 'original_sha256': digest(raw), 'pitch_preserved': True}


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
    timed, pending = [], []
    for phrase in phrases:
        pending.extend(phrase)
        if pending[-1]['end'] > pending[0]['start']:
            timed.append(pending)
            pending = []
    if pending:
        if not timed:
            raise ValueError('No positive caption interval was aligned')
        timed[-1].extend(pending)
    captions = []
    for phrase in timed:
        start, end = max(0, phrase[0]['start']), min(duration, phrase[-1]['end'])
        if end <= start:
            raise ValueError('Speech recognizer returned an empty caption interval')
        text = ' '.join(w['word'] for w in phrase)
        if captions and end - start < .65 and len(captions[-1]['text']) + len(text) < 90:
            captions[-1]['text'] += ' ' + text
            captions[-1]['end'] = end
        else:
            captions.append({'start': start, 'end': end, 'text': text})
    if not captions:
        raise ValueError('No speech recognized')
    return captions


def reconcile_words(words, script):
    """Correct known-script substitutions without changing any recognition timestamp."""
    reference = script.split()
    normalize = lambda text: re.sub(r'[^\w]', '', text.casefold())
    expected = [normalize(word) for word in reference]
    observed = [normalize(word['word']) for word in words]
    corrected, changes = copy.deepcopy(words), []
    for tag, a, b, c, d in difflib.SequenceMatcher(a=expected, b=observed, autojunk=False).get_opcodes():
        if tag != 'replace' or b - a != d - c or b - a > 3:
            continue
        for i, j in zip(range(a, b), range(c, d)):
            original = words[j]['word']
            suffix = re.search(r'[^\w\s]+$', original)
            replacement = re.sub(r'[^\w\s\x27-]', '', reference[i])
            corrected[j]['word'] = replacement + (suffix.group() if suffix else '')
            changes.append({'from': original.strip(), 'to': corrected[j]['word'],
                            'start': words[j]['start'], 'end': words[j]['end']})
    return corrected, changes


def asr_audio(audio, output):
    """Use Whisper's supported waveform input, avoiding version-specific PyAV decoding."""
    import numpy as np
    media.ffmpeg(['-i', str(Path(audio).resolve()), '-ar', '16000', '-ac', '1',
                  '-c:a', 'pcm_s16le', 'asr-input.wav'], output)
    with wave.open(str(output / 'asr-input.wav'), 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 16000):
            raise ValueError('Unexpected caption audio format')
        return np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2').astype(np.float32) / 32768


def recognize_words(engine, waveform, scenes=None):
    """Recognize bounded speech windows and retain measured global word timestamps."""
    duration = len(waveform) / 16000
    windows = scenes if scenes is not None else [{'start': 0, 'end': duration}]
    words = []
    for scene in windows:
        begin, end = scene['start'], scene['end']
        offset = max(0, int((begin - .12) * 16000))
        stop = min(len(waveform), int((end + .12) * 16000))
        found, _ = engine.transcribe(waveform[offset:stop], language='en', beam_size=5, word_timestamps=True,
                                    initial_prompt=scene.get('text', 'Naruto, Akatsuki, Nine Tails, Hidden Leaf, Sakura, Obito, motherflicker.'),
                                    condition_on_previous_text=False, vad_filter=False)
        for segment in found:
            for word in segment.words or []:
                start, finish = offset / 16000 + word.start, offset / 16000 + word.end
                if not begin <= (start + finish) / 2 < end:
                    continue  # Ignore padding belonging to a neighboring narration beat.
                start, finish = max(begin, start), min(end, finish)
                if finish > start:
                    words.append({'word': word.word, 'start': start, 'end': finish,
                                  'probability': word.probability})
    return words


def align_script_words(engine, tokenizer, waveform, scenes, pad_features):
    """Align supplied TTS text to audio with Whisper's cross-attention/DTW API."""
    groups = []
    for scene in scenes:
        if not groups or scene['end'] - groups[-1]['start'] > 24:
            groups.append({'start': scene['start'], 'end': scene['end'], 'text': scene['text']})
        else:
            groups[-1]['end'] = scene['end']
            groups[-1]['text'] += ' ' + scene['text']
    words = []
    for group in groups:
        offset = max(0, round((group['start'] - .4) * 16000))
        stop = min(len(waveform), round((group['end'] + .4) * 16000))
        features = engine.feature_extractor(waveform[offset:stop])
        tokens = tokenizer.encode(group['text'])
        if not tokens or len(tokens) > 400:
            raise ValueError('Known-script alignment window exceeds token limit')
        encoded = engine.encode(pad_features(features))
        aligned = engine.find_alignment(tokenizer, [tokens], encoded, round((stop - offset) / 160))[0]
        if not aligned:
            raise ValueError('Known-script alignment returned no timing')
        for word in aligned:
            text = word['word'].strip()
            if not text:
                continue
            start = max(group['start'], min(group['end'], offset / 16000 + float(word['start'])))
            end = max(start, min(group['end'], offset / 16000 + float(word['end'])))
            if words and not re.search(r'\w', text):
                words[-1]['word'] += text
                words[-1]['end'] = max(words[-1]['end'], end)
            else:
                words.append({'word': text, 'start': start, 'end': end,
                              'probability': float(word['probability'])})
    normalize = lambda text: re.findall(r'\w+', text.casefold())
    expected = normalize(' '.join(s['text'] for s in scenes))
    if normalize(' '.join(w['word'] for w in words)) != expected:
        raise ValueError('Alignment did not preserve the complete supplied script')
    return words


def forced_align(audio, output, models, scenes, model):
    from faster_whisper import WhisperModel
    from faster_whisper.audio import pad_or_trim
    from faster_whisper.tokenizer import Tokenizer
    engine = WhisperModel(model, device='cpu', compute_type='int8', cpu_threads=2, num_workers=1,
                          download_root=str(models / 'whisper'))
    tokenizer = Tokenizer(engine.hf_tokenizer, engine.model.is_multilingual, task='transcribe', language='en')
    words = align_script_words(engine, tokenizer, asr_audio(audio, output), scenes, pad_or_trim)
    captions = phrase_captions(words, media.duration(audio))
    receipt = {'engine': 'faster-whisper', 'model': model, 'device': 'cpu', 'compute_type': 'int8',
               'recognition_mode': 'script_alignment', 'known_script': True,
               'timing_basis': 'Whisper cross-attention DTW alignment to the final waveform; estimated word times',
               'audio_sha256': digest(audio), 'words': words, 'captions': captions,
               'script_token_agreement': None, 'independent_recognition_accuracy': None,
               'zero_duration_words': sum(w['end'] <= w['start'] for w in words),
               'review_names_required': True}
    atomic_json(output / 'transcription.json', receipt)
    return captions, None


def transcribe(audio, output, models, spec, scenes=None, model='tiny.en'):
    from faster_whisper import WhisperModel
    engine = WhisperModel(model, device='cpu', compute_type='int8', cpu_threads=2, num_workers=1,
                          download_root=str(models / 'whisper'))
    words = recognize_words(engine, asr_audio(audio, output), scenes)
    expected = re.findall(r'\w+', ' '.join(s['text'] for s in spec['scenes']).casefold())
    recognized = re.findall(r'\w+', ' '.join(w['word'] for w in words).casefold())
    agreement = difflib.SequenceMatcher(a=expected, b=recognized, autojunk=False).ratio()
    mode = 'narration_scenes' if scenes is not None else 'whole_audio'
    atomic_json(output / 'transcription-raw.json', {'words': words, 'model': model, 'script_token_agreement': agreement,
                'mode': mode, 'audio_sha256': digest(audio)})
    if agreement < .75:
        raise ValueError('Caption transcript differs substantially from the prepared script')
    raw_words = words
    words, corrections = reconcile_words(words, ' '.join(s['text'] for s in spec['scenes']))
    captions = phrase_captions(words, media.duration(audio))
    atomic_json(output / 'transcription.json', {'engine': 'faster-whisper', 'model': model,
                'device': 'cpu', 'compute_type': 'int8', 'words': words, 'captions': captions,
                'audio_sha256': digest(audio),
                'raw_words': raw_words, 'script_corrections': corrections,
                'recognition_mode': mode,
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
        explicit = any('start' in shot or 'end' in shot for shot in original_shots)
        if explicit:
            if any(abs(scene[k] - speech[k]) > .001 for k in ['start', 'end']):
                raise ValueError('Narration timing changed; re-align the reviewed visual beats')
            for shot, (begin, end) in zip(original_shots, media_edit.shot_intervals(scene)):
                available = media.duration(root / assets[shot['asset']]['file']) - shot.get('trim_start', 0)
                if available < end - begin - .03:
                    raise ValueError('Matching excerpt cannot cover its reviewed beat')
            selected = copy.deepcopy(original_shots)
        for count in ([] if explicit else range(len(original_shots), 5)):
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


def requested_plan(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT / 'edits') or path.suffix != '.json':
        raise ValueError('Edit plans must be repository JSON files under edits/')
    if path.stat().st_size > 1_000_000:
        raise ValueError('Edit plan exceeds size limit')
    return json.loads(path.read_text())


def requested_script(relative):
    if not isinstance(relative, str):
        raise ValueError('Script path must be a string')
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT / 'pilots') or path.suffix != '.json' or path.stat().st_size > 100_000:
        raise ValueError('Script must be a bounded repository JSON file under pilots/')
    spec = json.loads(path.read_text())
    scenes = spec.get('scenes')
    if spec.get('schema_version') != 1 or spec.get('language') != 'en' or not isinstance(scenes, list) or not 1 <= len(scenes) <= 30:
        raise ValueError('Unsupported English script schema')
    for scene in scenes:
        for key, limit in [('text', 1500), ('label', 70)]:
            value = scene.get(key)
            if not isinstance(value, str) or not 1 <= len(value) <= limit or any(c in value for c in '{}<>\\\n\r'):
                raise ValueError('Invalid script text or caption control character')
    title = spec.get('title')
    if not isinstance(title, str) or not 1 <= len(title) <= 200 or '\n' in title or '\r' in title:
        raise ValueError('Invalid script title')
    return spec


def requested_sound_effects(relative):
    if not isinstance(relative, str):
        raise ValueError('Sound effects plan path must be a string')
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT / 'edits') or path.suffix != '.json' or path.stat().st_size > 100_000:
        raise ValueError('Sound effects plans must be bounded JSON under edits/')
    plan = json.loads(path.read_text())
    catalog = (ROOT / plan['catalog']).resolve()
    if not catalog.is_relative_to(ROOT / 'assets/sfx') or catalog.suffix != '.json' or catalog.stat().st_size > 200_000:
        raise ValueError('Sound effects catalog must be bounded JSON under assets/sfx/')
    return plan, json.loads(catalog.read_text())


def bind_sound_plan(plan, source, narration):
    """Allow a one-job new-script plan to bind to its as-yet ungenerated audio."""
    bound = copy.deepcopy(plan)
    checksum = digest(narration)
    if bound.get('narration_sha256'):
        if bound['narration_sha256'] != checksum:
            raise ValueError('Sound plan belongs to another narration')
    else:
        script_hash = hashlib.sha256('\n'.join(s['text'] for s in source['scenes']).encode('utf-8')).hexdigest()
        if bound.get('script_sha256') != script_hash:
            raise ValueError('New-audio sound plan must match the ordered script checksum')
        bound['narration_sha256'] = checksum
        bound['narration_binding'] = 'Final waveform generated/reused for the matching ordered script checksum'
    return bound


def run(request, output, models):
    output = output.resolve()
    operation = identifier(request['id'])
    if request.get('channel') != 'ifverse_anime' or request.get('voice') not in {'af_heart', 'am_michael'}:
        raise ValueError('Unsupported test channel or voice')
    if request.get('caption_mode', 'whole_audio') not in {'whole_audio', 'narration_scenes', 'script_alignment'}:
        raise ValueError('Unsupported caption recognition mode')
    if request.get('caption_model', 'tiny.en') not in {'tiny.en', 'base.en'}:
        raise ValueError('Unsupported caption recognition model')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a fresh output directory for a new test version')
    output.mkdir(parents=True, exist_ok=True)
    source = requested_script(request.get('script', 'pilots/alpha-anime-001.json'))
    original = requested_plan(request.get('edit_plan', 'edits/alpha-anime-video.v2.json'))
    if [s['text'] for s in source['scenes']] != [s['text'] for s in original['scenes']]:
        raise ValueError('Script and footage plan must describe the same ordered narration')
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
    caption_source = request.get('reuse_transcription_from')
    if caption_source:
        prior = (ROOT / caption_source).resolve()
        if not prior.is_relative_to(ROOT / 'artifacts'):
            raise ValueError('Retained captions must come from repository artifacts')
        if digest(prior / 'narration.wav') != digest(output / 'narration.wav'):
            raise ValueError('Retained captions belong to different narration')
        transcript = json.loads((prior / 'transcription.json').read_text())
        captions, agreement = transcript['captions'], transcript['script_token_agreement']
        shutil.copy2(prior / 'transcription.json', output / 'transcription.json')
    elif request.get('caption_mode') == 'script_alignment':
        captions, agreement = forced_align(output / 'narration.wav', output, models, segments,
                                          request.get('caption_model', 'tiny.en'))
    else:
        captions, agreement = transcribe(output / 'narration.wav', output, models, source,
                                        segments if request.get('caption_mode') == 'narration_scenes' else None,
                                        request.get('caption_model', 'tiny.en'))
    timings['captioning_seconds'] = round(time.monotonic() - mark, 3)
    plan = retime_plan(original, segments, assets, output / 'narration.wav')
    plan.update(id=operation, caption_segments=captions)
    atomic_json(output / 'plan.json', plan)
    mark = time.monotonic()
    video = media_edit.render_edit(plan, assets, output / 'narration.wav', output / 'render')
    timings['render_and_decode_seconds'] = round(time.monotonic() - mark, 3)
    effects = None
    if request.get('sound_effects_plan'):
        mark = time.monotonic()
        effect_plan, catalog = requested_sound_effects(request['sound_effects_plan'])
        effect_plan = bind_sound_plan(effect_plan, source, output / 'narration.wav')
        atomic_json(output / 'sound-effects-plan.json', effect_plan)
        effects = audio_fx.mix_effects(video, output / 'narration.wav',
                                      json.loads((output / 'transcription.json').read_text()),
                                      effect_plan, catalog, models.parent / 'sound-effects', output / 'sound-effects')
        video = output / 'sound-effects' / effects['video']
        timings['sound_effects_seconds'] = round(time.monotonic() - mark, 3)
    timings['pipeline_seconds'] = round(time.monotonic() - started, 3)
    report = {'status': 'success', 'id': operation, 'video': str(video.relative_to(output)),
              'duration_seconds': media.duration(video), 'timings': timings,
              'voice': {'provider': 'kokoro-onnx', 'voice': request['voice'], 'device': 'cpu',
                        'reused_verified_audio': bool(retained)},
              'captions': {'engine': 'faster-whisper', 'model': request.get('caption_model', 'tiny.en'), 'compute_type': 'int8',
                           'recognition_mode': request.get('caption_mode', 'whole_audio'),
                           'phrases': len(captions), 'script_token_agreement': agreement,
                           'reused_verified_timing': bool(caption_source)},
              'footage': 'Traced online Naruto clips with reviewed narration-beat matching',
              'edit_plan': request.get('edit_plan', 'edits/alpha-anime-video.v2.json'),
              'script': request.get('script', 'pilots/alpha-anime-001.json'),
              'script_style': source.get('script_style'),
              'sound_effects': ({'count': effects['effects_count'], 'receipt': 'sound-effects/sound-effects.json',
                                 'plan': request['sound_effects_plan']} if effects else None),
              'explicit_beat_timing': all('start' in shot and 'end' in shot
                                          for scene in plan['scenes'] for shot in scene['shots']),
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
