import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from whatif import media, pipeline
from whatif.store import Store


def fixture():
    root=Path(__file__).resolve().parents[1]
    value=json.loads((root/'pilots/pilot-001.json').read_text())
    value['id']='integrity-check'
    value['profile'].update(width=360,height=640,min_seconds=1,max_seconds=30)
    value['scenes']=[{'visual':'earth-moon','label':'TEST','text':'A short opening.'},
                     {'visual':'earth-alone','label':'TEST','text':'The final scene must remain visible.'}]
    return value


class RenderIntegrityTests(unittest.TestCase):
    def test_zero_exit_with_corrupt_scene_is_rejected_before_concatenation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            spec=fixture()
            media.assets(spec,folder)
            media.narration(spec,folder)
            original=media.ffmpeg
            def drop_final_frame(args,cwd):
                if args[-1]=='clip-01.mp4':
                    (folder/'clip-01.mp4').write_bytes(b'empty container fixture')
                    return None  # Simulate a tool returning zero with an unusable file.
                return original(args,cwd)
            with patch.object(media,'ffmpeg',side_effect=drop_final_frame):
                with self.assertRaises((RuntimeError,ValueError)):
                    media.render(spec,folder)
            self.assertFalse((folder/'video.mp4').exists())

    def test_validation_rejects_a_missing_video_tail_even_when_audio_matches_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(tmp)
            spec=fixture()
            store.add(spec)
            pipeline.run(store,spec['id'])
            folder=store.root/'jobs'/spec['id']
            actual=media.probe(folder/'video.mp4')
            truncated=copy.deepcopy(actual)
            video=next(s for s in truncated['streams'] if s['codec_type']=='video')
            video['duration']=str(float(video['duration'])-1)
            with patch.object(media,'probe',return_value=truncated):
                with self.assertRaisesRegex(ValueError,'Media validation failed'):
                    media.validate_output(spec,folder)
            report=json.loads((folder/'quality.json').read_text())
            self.assertFalse(report['checks']['video_track_covers_speech'])
            self.assertFalse(report['checks']['video_audio_duration_match'])
            self.assertTrue(report['checks']['duration_matches_speech'])


if __name__=='__main__':
    unittest.main()
