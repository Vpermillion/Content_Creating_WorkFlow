import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from whatif import audio_fx, media
from whatif.store import digest


class AudioEffectsTests(unittest.TestCase):
    def test_anchors_follow_actual_words_and_repetition_requires_a_choice(self):
        words = [{'word': 'Oh,', 'start': 0, 'end': .2},
                 {'word': 'genius!', 'start': .2, 'end': .7},
                 {'word': 'genius.', 'start': 1, 'end': 1.4}]
        cue = {'anchor': {'phrase': 'oh genius'}, 'offset_seconds': .03}
        self.assertAlmostEqual(audio_fx.anchor_time(words, cue), .73)
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            audio_fx.anchor_time(words, {'anchor': {'phrase': 'genius'}})
        self.assertAlmostEqual(audio_fx.anchor_time(words, {'anchor': {'phrase': 'genius', 'occurrence': 2},
                                                          'offset_seconds': 0}), 1.4)
        with self.assertRaisesRegex(ValueError, 'missing'):
            audio_fx.anchor_time(words, {'anchor': {'phrase': 'not spoken'}})

    def test_description_search_selects_relevant_effect_and_can_return_no_match(self):
        catalog = {'assets': [
            {'id': 'impact', 'tags': ['boom', 'punchline'], 'description': 'Bass impact',
             'source_url': 'https://example.invalid/a', 'license': 'fixture'},
            {'id': 'ping', 'tags': ['reward'], 'description': 'Bright sarcastic reward ping',
             'source_url': 'https://example.invalid/b', 'license': 'fixture'}]}
        self.assertEqual(audio_fx.search_effects(catalog, 'boom punchline')[0]['id'], 'impact')
        self.assertEqual(audio_fx.search_effects(catalog, 'sarcastic')[0]['id'], 'ping')
        self.assertEqual(audio_fx.search_effects(catalog, 'unmatched'), [])

    def fixture(self, root):
        media.ffmpeg(['-f', 'lavfi', '-i', 'color=c=navy:s=320x240:r=24:d=3',
                      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', 'video.mp4'], root)
        media.ffmpeg(['-f', 'lavfi', '-i', 'sine=frequency=250:duration=3',
                      '-ar', '24000', '-ac', '1', 'voice.wav'], root)
        media.ffmpeg(['-f', 'lavfi', '-i', 'sine=frequency=1200:duration=0.2',
                      '-ar', '44100', '-ac', '1', 'source.wav'], root)
        asset = {'id': 'test', 'file': 'effect.wav',
                 'download_url': 'https://raw.githubusercontent.com/example/audio/' + 'a' * 40 + '/effect.wav',
                 'source_url': 'https://example.invalid/generated-test-fixture',
                 'license': 'Original generated test fixture', 'license_url': 'https://example.invalid/license',
                 'usage_basis': 'Generated test sound', 'description': 'A generated test chirp',
                 'tags': ['test'], 'sha256': digest(root / 'source.wav'), 'playback_rate': 1}
        transcript = {'audio_sha256': digest(root / 'voice.wav'),
                      'words': [{'word': 'Punchline.', 'start': .6, 'end': .9}]}
        plan = {'schema_version': 1, 'narration_sha256': digest(root / 'voice.wav'),
                'cues': [{'anchor': {'phrase': 'Punchline'}, 'effect': 'test', 'reason': 'Test punchline',
                          'offset_seconds': .1, 'max_seconds': .2, 'peak_dbfs': -14}]}
        return asset, transcript, plan

    def test_source_download_is_verified_cached_and_rejects_changed_bytes_and_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            asset, _, _ = self.fixture(root)
            response = io.BytesIO((root / 'source.wav').read_bytes())
            response.url = asset['download_url']
            with patch.object(audio_fx.urllib.request, 'urlopen', return_value=response) as download:
                first = audio_fx.fetch_effect(asset, root / 'cache')
                self.assertEqual(download.call_count, 1)
            with patch.object(audio_fx.urllib.request, 'urlopen', side_effect=AssertionError('must use cache')):
                self.assertEqual(audio_fx.fetch_effect(asset, root / 'cache'), first)
            first.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'checksum changed'):
                audio_fx.fetch_effect(asset, root / 'cache')
            bad = {**asset, 'download_url': 'https://raw.githubusercontent.com/example/audio/main/effect.wav'}
            with self.assertRaisesRegex(ValueError, 'commit-pinned'):
                audio_fx.fetch_effect(bad, root / 'cache')
            with self.assertRaisesRegex(ValueError, 'inside'):
                audio_fx.fetch_effect({**asset, 'file': '../../outside.wav'}, root / 'cache')

    def test_real_mix_preserves_video_and_voice_and_only_adds_sound_at_the_anchor(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            asset, transcript, plan = self.fixture(root)
            original_hash = digest(root / 'voice.wav')
            with patch.object(audio_fx, 'fetch_effect', return_value=root / 'source.wav'):
                report = audio_fx.mix_effects(root / 'video.mp4', root / 'voice.wav', transcript, plan,
                                              {'assets': [asset]}, root / 'cache', root / 'output')
            self.assertEqual(digest(root / 'voice.wav'), original_hash)
            self.assertEqual(report['effects_count'], 1)
            self.assertAlmostEqual(report['cues'][0]['start_seconds'], 1)
            self.assertLess(report['mix_peak_dbfs'], 0)
            dry, mixed = audio_fx.read_pcm(root / 'voice.wav'), audio_fx.read_pcm(root / 'output/mix.wav')
            self.assertEqual(len(dry), len(mixed))
            delta = mixed - dry
            self.assertLess(float(np.max(np.abs(delta[:23000]))), 2 / 32768)
            self.assertGreater(float(np.max(np.abs(delta[24000:28800]))), .08)
            self.assertLess(float(np.max(np.abs(delta[24000:28800]))), .11)
            self.assertLess(float(np.max(np.abs(delta[30000:]))), 2 / 32768)
            def video_hash(path):
                return media.command(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:v:0',
                                      '-c', 'copy', '-f', 'hash', '-hash', 'sha256', '-']).stdout
            self.assertEqual(video_hash(root / 'video.mp4'), video_hash(root / 'output/video-sfx.mp4'))

    def test_mismatched_audio_missing_anchors_and_unsafe_levels_fail_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            asset, transcript, plan = self.fixture(root)
            for kind in ['audio', 'anchor', 'level', 'end']:
                changed = copy.deepcopy(plan)
                if kind == 'audio': changed['narration_sha256'] = 'wrong'
                if kind == 'anchor': changed['cues'][0]['anchor']['phrase'] = 'missing'
                if kind == 'level': changed['cues'][0]['peak_dbfs'] = 3
                if kind == 'end': changed['cues'][0]['offset_seconds'] = 50
                with self.assertRaises(ValueError):
                    audio_fx.mix_effects(root / 'video.mp4', root / 'voice.wav', transcript, changed,
                                         {'assets': [asset]}, root / 'cache', root / 'output')
                self.assertFalse((root / 'output').exists())


if __name__ == '__main__':
    unittest.main()
