import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('render_test_video', Path(__file__).resolve().parents[1] / 'scripts/render_test_video.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestVideoPlanTests(unittest.TestCase):
    def test_zero_duration_alignment_tokens_join_timed_phrases_without_losing_text(self):
        words = [{'word': 'Oh!', 'start': 0, 'end': 0},
                 {'word': 'Fantastic.', 'start': .1, 'end': .9},
                 {'word': 'Fine.', 'start': 1, 'end': 1}]
        captions = module.phrase_captions(words, 1.1)
        self.assertEqual(captions, [{'start': 0, 'end': 1, 'text': 'Oh! Fantastic. Fine.'}])

    def test_known_script_alignment_preserves_all_words_and_offsets_audio_windows(self):
        import numpy as np
        class Engine:
            def feature_extractor(self, audio):
                return audio
            def encode(self, features):
                return features
            def find_alignment(self, tokenizer, tokens, encoded, frames):
                return [[{'word': text, 'start': .5 + i * .3, 'end': .8 + i * .3,
                          'probability': .8} for i, text in enumerate(tokens[0])]]
        engine = Engine()
        tokenizer = SimpleNamespace(encode=lambda text: text.split())
        scenes = [{'start': 0, 'end': 20, 'text': 'First word.'},
                  {'start': 20, 'end': 30, 'text': 'Second word.'}]
        words = module.align_script_words(engine, tokenizer, np.zeros(480000), scenes, lambda f: f)
        self.assertEqual([w['word'] for w in words], ['First', 'word.', 'Second', 'word.'])
        self.assertAlmostEqual(words[2]['start'], 20.1)
        with patch.object(engine, 'find_alignment', return_value=[[{
                'word': 'Wrong', 'start': .5, 'end': .8, 'probability': .9}]]):
            with self.assertRaisesRegex(ValueError, 'complete supplied script'):
                module.align_script_words(engine, tokenizer, np.zeros(480000), scenes, lambda f: f)

    def test_request_rejects_unapproved_model_before_creating_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'output'
            with self.assertRaisesRegex(ValueError, 'recognition model'):
                module.run({'id': 'model-test', 'channel': 'ifverse_anime', 'voice': 'af_heart',
                            'caption_model': '../../untrusted'}, output, Path(temp) / 'models')
            self.assertFalse(output.exists())

    def test_scene_recognition_offsets_timestamps_and_excludes_neighbor_padding(self):
        import numpy as np
        class Engine:
            def transcribe(self, waveform, **kwargs):
                self.calls = getattr(self, 'calls', 0) + 1
                # The second window begins .12 seconds before its scene boundary.
                words = ([(' First.', .1, .8)] if self.calls == 1 else
                         [(' Previous.', .01, .05), (' Second.', .22, .82)])
                return [SimpleNamespace(words=[SimpleNamespace(word=t, start=a, end=b, probability=.9)
                                               for t, a, b in words])], None
        engine = Engine()
        words = module.recognize_words(engine, np.zeros(32000), [{'start': 0, 'end': 1}, {'start': 1, 'end': 2}])
        self.assertEqual(engine.calls, 2)
        self.assertEqual([w['word'].strip() for w in words], ['First.', 'Second.'])
        self.assertAlmostEqual(words[1]['start'], 1.1)
        self.assertAlmostEqual(words[1]['end'], 1.7)

    def test_requested_script_rejects_outside_paths_and_caption_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'pilots').mkdir()
            source = {'schema_version': 1, 'language': 'en', 'title': 'Test',
                      'scenes': [{'text': 'A new story.', 'label': 'INTRO'}]}
            path = root / 'pilots/story.json'
            path.write_text(json.dumps(source))
            with patch.object(module, 'ROOT', root):
                self.assertEqual(module.requested_script('pilots/story.json'), source)
                with self.assertRaisesRegex(ValueError, 'under pilots'):
                    module.requested_script('pilots/../../secret.json')
                source['scenes'][0]['text'] = 'Injected {caption}'
                path.write_text(json.dumps(source))
                with self.assertRaisesRegex(ValueError, 'caption control'):
                    module.requested_script('pilots/story.json')

    def test_new_speech_retimes_to_exact_duration_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            module.media.ffmpeg(['-f', 'lavfi', '-i', 'sine=frequency=330:duration=31',
                                 '-ar', '24000', '-ac', '1', 'narration.wav'], root)
            original = module.digest(root / 'narration.wav')
            segments = [{'start': 0, 'end': 15.5}, {'start': 15.5, 'end': 31}]
            receipt = module.fit_narration_duration(root, segments, 30)
            self.assertAlmostEqual(module.media.duration(root / 'narration.wav'), 30, places=3)
            self.assertAlmostEqual(segments[0]['end'], 15, places=3)
            self.assertEqual(segments[-1]['end'], 30)
            self.assertEqual(receipt['original_sha256'], original)
            self.assertEqual(module.digest(root / 'narration-unretimed.wav'), original)

    def test_new_speech_rejects_excessive_or_invalid_duration_before_modifying_audio(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            module.media.ffmpeg(['-f', 'lavfi', '-i', 'sine=frequency=330:duration=1',
                                 'narration.wav'], root)
            original = module.digest(root / 'narration.wav')
            for target in [True, float('nan'), 100, 60]:
                with self.assertRaises(ValueError):
                    module.fit_narration_duration(root, [{'start': 0, 'end': 1}], target)
            self.assertEqual(module.digest(root / 'narration.wav'), original)

    def test_caption_input_is_real_mono_16khz_waveform_and_keeps_original_audio(self):
        from whatif.store import digest
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            module.media.ffmpeg(['-f', 'lavfi', '-i', 'sine=frequency=330:duration=1',
                                 '-ar', '24000', 'voice.wav'], root)
            original = digest(root / 'voice.wav')
            waveform = module.asr_audio(root / 'voice.wav', root)
            self.assertEqual(waveform.shape, (16000,))
            self.assertGreater(float(abs(waveform).max()), .01)
            self.assertEqual(digest(root / 'voice.wav'), original)

    def test_caption_phrases_keep_recognizer_timestamps(self):
        words = [{'word': word, 'start': i * .5, 'end': (i + 1) * .5}
                 for i, word in enumerate(['What', 'if', 'Naruto', 'joined', 'Akatsuki?', 'A', 'test.'])]
        phrases = module.phrase_captions(words, 3.5)
        self.assertEqual(phrases[0], {'start': 0, 'end': 2.5, 'text': 'What if Naruto joined Akatsuki?'})
        self.assertEqual(phrases[1]['start'], 2.5)

    def test_short_final_words_stay_with_the_previous_phrase(self):
        words = [{'word': word, 'start': i * .2, 'end': (i + 1) * .2}
                 for i, word in enumerate(['What', 'if', 'Naruto', 'joined', 'the', 'Akatsuki?'])]
        phrases = module.phrase_captions(words, 1.2)
        self.assertEqual(len(phrases), 1)
        self.assertEqual(phrases[0]['text'], 'What if Naruto joined the Akatsuki?')

    def test_script_spelling_correction_preserves_recognized_time_and_original(self):
        words = [{'word': ' the', 'start': .2, 'end': .4}, {'word': ' Akkitsuki?', 'start': .4, 'end': 1.1}]
        fixed, changes = module.reconcile_words(words, 'the Akatsuki?')
        self.assertEqual(fixed[1]['word'], 'Akatsuki?')
        self.assertEqual(fixed[1]['start'], .4)
        self.assertEqual(fixed[1]['end'], 1.1)
        self.assertEqual(words[1]['word'], ' Akkitsuki?')
        self.assertEqual(len(changes), 1)

    def test_retiming_preserves_original_plan_and_adds_only_matching_shots(self):
        original = {'scenes': [{'start': 0, 'end': 2, 'text': 'Old', 'label': 'TEST',
                               'shots': [{'asset': 'a', 'fit': 'cover', 'match_reason': 'Narrative match'}]}],
                    'assets': [{'id': 'a', 'file': 'source.mp4'}]}
        speech = [{'start': 0, 'end': 5, 'text': 'New narration', 'label': 'TEST'}]
        with patch.object(module.media, 'duration', return_value=2), patch.object(module, 'digest', return_value='checksum'):
            result = module.retime_plan(original, speech, Path('/assets'), Path('/speech.wav'))
        self.assertEqual(len(result['scenes'][0]['shots']), 3)
        self.assertEqual(result['scenes'][0]['text'], 'New narration')
        self.assertEqual(original['scenes'][0]['end'], 2)
        self.assertTrue(all(s['asset'] == 'a' and s['fit'] == 'contain' for s in result['scenes'][0]['shots']))

    def test_inadequate_matching_footage_fails_instead_of_inserting_other_clips(self):
        plan = {'scenes': [{'shots': [{'asset': 'a'}]}], 'assets': [{'id': 'a', 'file': 'a.mp4'}]}
        with patch.object(module.media, 'duration', return_value=.5):
            with self.assertRaisesRegex(ValueError, 'cannot cover'):
                module.retime_plan(plan, [{'start': 0, 'end': 9}], Path('/assets'), Path('/voice.wav'))

    def test_retime_keeps_reviewed_beats_and_requires_new_alignment_for_changed_audio(self):
        plan = {'scenes': [{'start': 0, 'end': 2, 'shots': [
                    {'asset': 'a', 'start': 0, 'end': .5}, {'asset': 'a', 'start': .5, 'end': 2}]}],
                'assets': [{'id': 'a', 'file': 'a.mp4'}]}
        speech = [{'start': 0, 'end': 2, 'text': 'Reviewed script', 'label': 'BEATS'}]
        with patch.object(module.media, 'duration', return_value=3), patch.object(module, 'digest', return_value='hash'):
            result = module.retime_plan(plan, speech, Path('/assets'), Path('/voice.wav'))
            self.assertEqual([s['end'] for s in result['scenes'][0]['shots']], [.5, 2])
            with self.assertRaisesRegex(ValueError, 're-align'):
                module.retime_plan(plan, [{'start': 0, 'end': 3}], Path('/assets'), Path('/voice.wav'))


if __name__ == '__main__':
    unittest.main()
