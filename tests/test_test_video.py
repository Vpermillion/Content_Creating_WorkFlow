import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('render_test_video', Path(__file__).resolve().parents[1] / 'scripts/render_test_video.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestVideoPlanTests(unittest.TestCase):
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
        words = [{'word': word, 'start': i * .3, 'end': (i + 1) * .3}
                 for i, word in enumerate(['What', 'if', 'Naruto', 'joined', 'Akatsuki?', 'A', 'test.'])]
        phrases = module.phrase_captions(words, 2.1)
        self.assertEqual(phrases[0], {'start': 0, 'end': 1.5, 'text': 'What if Naruto joined Akatsuki?'})
        self.assertEqual(phrases[1]['start'], 1.5)

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


if __name__ == '__main__':
    unittest.main()
