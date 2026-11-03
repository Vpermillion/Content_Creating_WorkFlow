"""Durable, non-secret topic reservations; publication requires a real receipt."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import difflib
import fcntl
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from .store import atomic_json, identifier


def normalized(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Topic text must be nonempty')
    return ' '.join(re.findall(r'[a-z0-9]+', unicodedata.normalize('NFKD', value).casefold()))


def script_hash(scenes):
    return hashlib.sha256('\n'.join(s['text'] for s in scenes).encode()).hexdigest()


def topic_record(episode, batch_id):
    identifier(episode['id']); identifier(episode['topic_key']); identifier(batch_id)
    return {'id': episode['id'], 'topic_key': episode['topic_key'], 'title': episode['title'],
            'premise': episode['premise'], 'franchise': episode['franchise'],
            'characters': episode['characters'], 'aliases': episode.get('aliases', []),
            'distinctive_development': episode['distinctive_development'],
            'script_sha256': script_hash(episode['scenes']), 'batch_id': batch_id,
            'state': 'reserved', 'video_id': None, 'youtube_url': None,
            'reserved_at': datetime.now(timezone.utc).isoformat()}


def conflicts(registry, candidate):
    """Exact identity/script/alias plus conservative fuzzy warnings, not semantics."""
    found = []
    proposed = [normalized(candidate[k]) for k in ('title', 'premise')] + [normalized(x) for x in candidate.get('aliases', [])]
    for prior in registry['topics']:
        if prior['id'] == candidate['id']:
            if prior['topic_key'] == candidate['topic_key'] and prior.get('script_sha256') == candidate.get('script_sha256'):
                continue  # Same reserved operation may resume without a second entry.
            raise ValueError('Existing episode ID has different content; preserve it and use a new ID')
        reasons = []
        if prior['topic_key'] == candidate['topic_key']:
            reasons.append('same_topic_key')
        if prior.get('script_sha256') and prior['script_sha256'] == candidate.get('script_sha256'):
            reasons.append('same_ordered_script')
        old = [normalized(prior[k]) for k in ('title', 'premise')] + [normalized(x) for x in prior.get('aliases', [])]
        if set(proposed) & set(old):
            reasons.append('same_title_premise_or_alias')
        if prior['franchise'].casefold() == candidate['franchise'].casefold() and any(
                difflib.SequenceMatcher(None, a, b).ratio() >= .88 for a in proposed for b in old):
            reasons.append('very_similar_wording_review_required')
        if reasons:
            found.append({'id': prior['id'], 'state': prior['state'], 'title': prior['title'], 'reasons': reasons})
    return found


@contextmanager
def locked(path):
    path = Path(path)
    if not path.parent.exists():
        raise ValueError('Registry directory must already exist')
    lock = path.with_suffix(path.suffix + '.lock')
    with lock.open('a') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield


def reserve(path, batch):
    with locked(path):
        registry = json.loads(Path(path).read_text())
        if registry.get('schema_version') != 1 or registry.get('channel') != batch.get('channel'):
            raise ValueError('Registry schema/channel mismatch')
        candidates = [topic_record(e, batch['id']) for e in batch['episodes']]
        if len({e['id'] for e in candidates}) != len(candidates):
            raise ValueError('Duplicate episode ID in batch')
        # Check every entry before the single atomic write; no partial reservation.
        for c in candidates:
            overlaps = conflicts(registry, c)
            if overlaps:
                raise ValueError('Topic overlap: ' + json.dumps(overlaps))
            if not any(t['id'] == c['id'] for t in registry['topics']):
                registry['topics'].append(c)
        atomic_json(path, registry)
    return registry


def record_result(path, episode_id, result, receipt_path):
    with locked(path):
        registry = json.loads(Path(path).read_text())
        matches = [e for e in registry['topics'] if e['id'] == episode_id]
        if len(matches) != 1:
            raise ValueError('Exactly one reserved episode must exist')
        entry = matches[0]
        if entry['state'] == 'published':
            raise ValueError('Published records are immutable here')
        if result['id'] != entry['id'] or result['script_sha256'] != entry['script_sha256']:
            raise ValueError('Result belongs to different episode/script')
        entry.update(state='rendered' if result['status'] == 'success' else 'render_failed',
                     result_receipt=receipt_path, result_branch=result.get('result_branch'),
                     video_sha256=result.get('video_sha256'),
                     publication_clearance=result.get('publication_clearance', 'not_established'))
        atomic_json(path, registry)


def revise_batch(path, batch, reason):
    """Explicitly revise unpublished cuts of the same topics, preserving history."""
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError('Record the requested revision reason')
    with locked(path):
        registry = json.loads(Path(path).read_text())
        if registry['channel'] != batch['channel']:
            raise ValueError('Registry channel mismatch')
        replacements = []
        for episode in batch['episodes']:
            candidate = topic_record(episode, batch['id'])
            matches = [t for t in registry['topics'] if t['id'] == candidate['id']]
            if len(matches) != 1 or matches[0]['topic_key'] != candidate['topic_key']:
                raise ValueError('Revision must refer to one existing identical topic key')
            old = matches[0]
            if old.get('video_id') or old['state'] == 'published':
                raise ValueError('Do not replace a published topic with another upload')
            others = {'topics': [t for t in registry['topics'] if t['id'] != old['id']]}
            if conflicts(others, candidate):
                raise ValueError('Revision overlaps a different topic')
            history = old.get('versions', []) + [{k: old[k] for k in
                       ('batch_id','script_sha256','state','result_branch','video_sha256') if k in old} | {'revision_reason':reason}]
            replacements.append({**candidate, 'versions': history})
        for candidate in replacements:
            registry['topics'] = [candidate if t['id'] == candidate['id'] else t for t in registry['topics']]
        atomic_json(path, registry)
    return registry


def mark_published(path, episode_id, receipt):
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', receipt.get('video_id', '')) or not receipt.get('verified_channel_id'):
        raise ValueError('Actual provider video ID and verified channel are required')
    with locked(path):
        registry = json.loads(Path(path).read_text())
        entry = next(e for e in registry['topics'] if e['id'] == episode_id)
        if entry.get('video_sha256') != receipt.get('video_sha256'):
            raise ValueError('Uploaded video differs from rendered registry entry')
        if entry.get('video_id') not in (None, receipt['video_id']):
            raise ValueError('Episode already has a different publication receipt')
        entry.update(state='published', video_id=receipt['video_id'],
                     youtube_url='https://www.youtube.com/shorts/' + receipt['video_id'],
                     verified_channel_id=receipt['verified_channel_id'], published_at=receipt['published_at'])
        atomic_json(path, registry)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--registry', default='channels/ifverse_anime-topics.json')
    sub = p.add_subparsers(dest='operation', required=True)
    sub.add_parser('list')
    reserve_parser = sub.add_parser('reserve'); reserve_parser.add_argument('--batch', required=True)
    args = p.parse_args()
    if args.operation == 'reserve':
        value = reserve(args.registry, json.loads(Path(args.batch).read_text()))
    else:
        value = json.loads(Path(args.registry).read_text())
    print(json.dumps(value, indent=2))


if __name__ == '__main__':
    main()
