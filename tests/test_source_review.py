import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('prepare_review_sources',Path(__file__).resolve().parents[1]/'scripts/prepare_review_sources.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class SourceReviewTests(unittest.TestCase):
    def candidate(self, name='Goku', length=3):
        return {'title':name,'source_url':'https://tenor.com/view/'+name,'download_url':'https://media.tenor.com/test.mp4',
                'duration':length,'width':640,'height':360,'publisher':'Generated fixture'}

    def test_selection_requires_the_named_character_and_sufficient_clip_length(self):
        candidates=[self.candidate('Unrelated',8),self.candidate('Goku',.5),self.candidate('Goku',3)]
        self.assertEqual(module.choose_candidate(candidates,['goku']),candidates[-1])
        with self.assertRaisesRegex(ValueError,'identified'):
            module.choose_candidate([self.candidate('Other',4)],['goku'])

    def test_footage_acquisition_probes_and_records_downloaded_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            module.media.ffmpeg(['-f','lavfi','-i','color=c=blue:s=320x240:r=24:d=2','-c:v','libx264','fixture.mp4'],root)
            data=(root/'fixture.mp4').read_bytes()
            with patch.object(module.media_tools,'search_web',return_value=[self.candidate('Goku')]),patch.object(module.media_tools,'public_bytes',return_value=data):
                result=module.acquire_footage({'id':'goku','query':'Goku','required_terms':['goku']},root/'output')
            self.assertEqual(result['sha256'],module.digest(root/'output/footage/goku.mp4'))
            self.assertAlmostEqual(result['duration'],2,places=1)

    def test_first_sound_acquisition_decodes_and_freezes_a_hash_without_claiming_preexisting_pin(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            module.media.ffmpeg(['-f','lavfi','-i','sine=frequency=200:duration=0.3','effect.mp3'],root)
            record={'id':'boom','download_url':'https://dvi.dubbingai.io/cs/20260713/1-2.mp3',
                    'source_url':'https://dubbingai.io/articles/example','description':'Generated source fixture'}
            response=io.BytesIO((root/'effect.mp3').read_bytes());response.url=record['download_url']
            with patch.object(module.urllib.request,'urlopen',return_value=response):
                result=module.acquire_sound(record,root/'output')
            self.assertEqual(result['sha256'],module.digest(root/'output/sounds/boom.mp3'))
            self.assertEqual(result['download_status'],'downloaded_probed_hashed')
            self.assertIn('First acquisition',result['checksum_origin'])

    def test_sound_acquisition_rejects_non_audio_without_registering_it(self):
        with tempfile.TemporaryDirectory() as temp:
            response=io.BytesIO(b'<html>not audio</html>');response.url='https://dvi.dubbingai.io/cs/20260713/1-2.mp3'
            with patch.object(module.urllib.request,'urlopen',return_value=response):
                with self.assertRaises((RuntimeError,ValueError)):
                    module.acquire_sound({'id':'bad','download_url':response.url,'source_url':'https://dubbingai.io/'},Path(temp))


if __name__=='__main__':unittest.main()
