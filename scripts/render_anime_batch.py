"""One bounded batch request; reuse the tested CPU renderer for each episode."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import json
from pathlib import Path
import re
import shutil
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import prepare_review_sources as sources
from scripts import render_test_video as renderer
from whatif import media
from whatif.store import atomic_json, digest, identifier
from whatif.topics import script_hash, topic_record, conflicts


def load_batch(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT / 'batch-requests') or path.suffix != '.json' or path.stat().st_size > 250_000:
        raise ValueError('Use a bounded batch JSON under batch-requests/')
    batch = json.loads(path.read_text())
    identifier(batch['id'])
    if batch.get('schema_version') != 1 or batch.get('channel') != 'ifverse_anime' or batch.get('voice') != 'am_michael':
        raise ValueError('Unsupported batch schema, channel or voice')
    if not 60 <= batch['target_duration_seconds'] <= 75 or isinstance(batch['target_duration_seconds'], bool):
        raise ValueError('Batch Shorts must target 60–75 seconds')
    episodes = batch['episodes']
    if not isinstance(episodes, list) or not 1 <= len(episodes) <= 10 or len({e['id'] for e in episodes}) != len(episodes):
        raise ValueError('Use one to ten unique episode IDs')
    registry = json.loads((ROOT / 'channels/ifverse_anime-topics.json').read_text())
    for episode in episodes:
        record = topic_record(episode, batch['id'])
        reserved = [t for t in registry['topics'] if t['id'] == episode['id']]
        if len(reserved) != 1 or reserved[0]['script_sha256'] != record['script_sha256'] or reserved[0]['state'] == 'published':
            raise ValueError('Episode must be reserved with its exact script and not already published')
        if conflicts(registry, record):
            raise ValueError('Overlapping topic in batch registry')
        if not 4 <= len(episode['scenes']) <= 30 or not 1 <= len(episode['sources']) <= 12:
            raise ValueError('Invalid scene/source count')
        if not isinstance(episode['title'], str) or not 1 <= len(episode['title']) <= 100:
            raise ValueError('Invalid YouTube title')
        keys = {s['key'] for s in episode['sources']}
        if len(keys) != len(episode['sources']):
            raise ValueError('Duplicate source key')
        for source in episode['sources']:
            identifier(source['id']); identifier(source['key'])
        for scene in episode['scenes']:
            if scene['source'] not in keys or not scene.get('match_reason'):
                raise ValueError('Every scene needs an identified source and purpose')
            for key in ('text', 'label'):
                if not isinstance(scene[key], str) or not scene[key] or len(scene[key]) > (1500 if key == 'text' else 70) or any(c in scene[key] for c in '{}<>\\\n\r'):
                    raise ValueError('Invalid scene text/controls')
        text = ' '.join(s['text'] for s in episode['scenes'])
        for cue in episode['cues']:
            tokens = re.findall(r'\w+', text.casefold())
            wanted = re.findall(r'\w+', cue['phrase'].casefold())
            if not wanted or sum(tokens[i:i+len(wanted)] == wanted for i in range(len(tokens))) != 1:
                raise ValueError('Sound cue must match exactly one actual phrase: ' + cue['phrase'])
    return batch


def collect_episode(episode, output):
    """Keep successful downloads across a bounded fallback; never relabel failures."""
    def acquire(spec):
        attempts = []
        queries = [spec['query'], spec['required_terms'][0].replace('-', ' ') + ' ' + episode['franchise']]
        for query in dict.fromkeys(queries):
            try:
                asset = sources.acquire_footage({**spec, 'query': query, 'min_seconds': 1.8}, output)
                asset['source_key'] = spec['key']; asset['visual_intent'] = spec['visual_intent']
                return {'asset': asset, 'attempts': attempts}
            except Exception as exc:
                attempts.append({'query': query, 'error_type': type(exc).__name__, 'error': str(exc)[:200]})
        return {'failed_source': spec['key'], 'attempts': attempts}
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(acquire, episode['sources']))
    atomic_json(output / 'sources.json', {'episode_id': episode['id'], 'results': results,
                                        'rights_status': 'unverified_publicly_posted_excerpts'})
    failed = [r['failed_source'] for r in results if 'failed_source' in r]
    if failed:
        raise ValueError('Missing identified sources: ' + ', '.join(failed))
    return [r['asset'] for r in results]


def render_episode(batch, episode, output, models):
    output = output.resolve(); models = models.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a fresh output; inspect saved result before retrying')
    output.mkdir(parents=True, exist_ok=True)
    result = {'id': episode['id'], 'batch_id': batch['id'], 'status': 'running',
              'script_sha256': script_hash(episode['scenes']),
              'result_branch': 'codex/results/' + episode['id'],
              'publication_clearance': 'not_established', 'uploaded': False}
    atomic_json(output / 'batch-result.json', result)
    try:
        assets = collect_episode(episode, output / 'source-review')
        cache = models.parent / 'footage'; cache.mkdir(parents=True, exist_ok=True)
        for asset in assets:
            destination = cache / asset['file']
            if destination.exists() and digest(destination) != asset['sha256']:
                raise ValueError('Existing source cache checksum mismatch')
            shutil.copy2(output / 'source-review/footage' / asset['file'], destination)
        by_key = {a['source_key']: a for a in assets}
        scenes = []
        for i, scene in enumerate(episode['scenes']):
            asset = by_key[scene['source']]
            scenes.append({**{k: scene[k] for k in ('text', 'label')}, 'start': i * 5, 'end': (i+1) * 5,
                           'shots': [{'asset': asset['id'], 'fit': 'contain', 'trim_start': 0,
                                      'match_reason': scene['match_reason']}]})
        spec = {'schema_version': 1, 'id': episode['id'], 'channel_id': batch['channel'],
                'language': 'en', 'title': episode['title'], 'scenes': scenes,
                'script_style': 'ifverse-playful-roast-v2',
                'target_duration_seconds': batch['target_duration_seconds'],
                'assumptions': ['Fan-made alternate scenario, not canon or an official episode.']}
        plan = {'schema_version': 1, 'id': episode['id'], 'title': episode['title'],
                'width': 720, 'height': 1280, 'fps': 30, 'assets': assets, 'scenes': scenes,
                'video_only': True, 'single_pass': True, 'enhancement': 'anime-light',
                'source_credit': 'IFVERSE ANIME / FAN-MADE WHAT-IF', 'publishing_authorized': False}
        # Explicitly choose documented public-domain effects for this publication-oriented batch.
        effects = {'schema_version': 1, 'id': episode['id'],
                   'script_sha256': result['script_sha256'], 'catalog': 'assets/sfx/catalog.json',
                   'cues': [{'anchor': {'phrase': c['phrase'], 'edge': 'end'}, 'offset_seconds': .03,
                             'effect': c['effect'], 'peak_dbfs': -17, 'max_seconds': .75,
                             'reason': 'Punctuate the specific scripted joke without covering the next phrase.'}
                            for c in episode['cues']]}
        script_path = 'pilots/' + episode['id'] + '.json'
        plan_path = 'edits/' + episode['id'] + '.json'
        sfx_path = 'edits/' + episode['id'] + '-sfx.json'
        for path, value in [(script_path, spec), (plan_path, plan), (sfx_path, effects)]:
            if (ROOT / path).exists():
                raise ValueError('Refusing to overwrite existing production inputs')
            atomic_json(ROOT / path, value)
        request = {'schema_version': 1, 'id': episode['id'], 'channel': batch['channel'], 'voice': batch['voice'],
                   'script': script_path, 'edit_plan': plan_path, 'sound_effects_plan': sfx_path,
                   'caption_mode': 'script_alignment', 'caption_model': 'base.en',
                   'result_branch': result['result_branch'], 'publishing_enabled': False}
        atomic_json(output / 'request.json', request)
        rendered = renderer.run(request, output / 'production', models)
        video = output / 'production' / rendered['video']
        duration = media.duration(video)
        if duration < 60 or duration > 180:
            raise ValueError('Final Short is outside requested duration bounds')
        probe = media.probe(video); track = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        if track['width'] * 16 != track['height'] * 9:
            raise ValueError('Final video is not vertical 9:16')
        # One frame for every actual shot: durable evidence for semantic review.
        edit = json.loads((output / 'production/render/edit.json').read_text())
        frames = output / 'review-frames'; frames.mkdir()
        for i, shot in enumerate(edit['shots']):
            mid = (shot['start'] + shot['end']) / 2
            media.ffmpeg(['-ss', str(mid), '-i', str(video), '-frames:v', '1',
                          '-vf', 'scale=180:320', str(frames / f'{i:03}.jpg')], frames)
        media.ffmpeg(['-pattern_type', 'glob', '-i', str(frames / '*.jpg'), '-vf',
                      'tile=6x' + str((len(edit['shots'])+5)//6) + ':padding=3:margin=3',
                      '-frames:v', '1', str(output / 'contact-sheet.jpg')], output)
        result.update(status='success', video=str(video.relative_to(output)),
                      video_sha256=digest(video), duration_seconds=duration,
                      frame_size=[track['width'], track['height']],
                      source_count=len(assets), source_use_status='unverified',
                      sound_catalog='assets/sfx/catalog.json', sound_rights='documented_public_domain',
                      technical_receipt='production/result.json',
                      audiovisual_editorial_review='pending',
                      metadata={'title': episode['title'], 'description':
                                'An original fan-made alternate scenario and comedic commentary by Ifverse Anime. '
                                'Hypothetical events and dialogue are invented, not canon. AI-assisted narration (Kokoro am_michael). '
                                '#Shorts #Anime #WhatIf', 'categoryId': '24', 'defaultLanguage': 'en'})
    except Exception as exc:
        result.update(status='failed', error_type=type(exc).__name__, error=str(exc)[:500])
        traceback.print_exc()
    finally:
        atomic_json(output / 'batch-result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', required=True); parser.add_argument('--episode')
    parser.add_argument('--output'); parser.add_argument('--models', default='private/test-video/models')
    parser.add_argument('--validate', action='store_true')
    args = parser.parse_args(); batch = load_batch(args.batch)
    if args.validate:
        print(json.dumps({'batch_id': batch['id'], 'ids': [e['id'] for e in batch['episodes']]})); return 0
    matches = [e for e in batch['episodes'] if e['id'] == args.episode]
    if len(matches) != 1 or not args.output:
        raise ValueError('Select one episode from the batch and a fresh output directory')
    result = render_episode(batch, matches[0], Path(args.output), Path(args.models))
    print(json.dumps(result)); return 0 if result['status'] == 'success' else 1


if __name__ == '__main__':
    sys.exit(main())
