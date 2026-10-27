import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from whatif import media, media_edit
from whatif.media_tools import Bank, ToolError, build, checked_url, enhance_file, make_plan, probe_video
from whatif.store import digest


class MediaToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.fixture.name)
        media.ffmpeg(['-f','lavfi','-i','testsrc2=size=320x240:rate=24:duration=3',
                      '-f','lavfi','-i','sine=frequency=440:duration=3','-c:v','libx264',
                      '-pix_fmt','yuv420p','-c:a','aac','fixture.mp4'], cls.folder)
        media.ffmpeg(['-f','lavfi','-i','sine=frequency=330:duration=2','speech.wav'], cls.folder)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bank = Bank(self.root/'bank')
        self.video = self.folder/'fixture.mp4'
        self.audio = self.folder/'speech.wav'

    def tearDown(self):
        self.temp.cleanup()

    def add(self, label='Naruto protects friends'):
        return self.bank.add(self.video, label, 'https://tenor.com/view/fixture', 'Generated software test fixture')

    def story(self):
        return {'id':'tool-test','title':'Test','width':360,'height':640,'narration_sha256':digest(self.audio),
                'scenes':[{'start':0,'end':2,'text':'An original test.','label':'TEST','visual_queries':['Naruto protects friends']}]}

    def test_verified_cache_reuses_bytes_and_detects_corruption(self):
        checksum = digest(self.video)
        first = self.add()
        second = self.add('Naruto determined')
        self.assertTrue(second['cached'])
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(digest(self.video), checksum)
        self.assertEqual(len(self.bank.catalog()['assets']), 1)
        self.assertEqual(len(second['labels']), 2)
        self.bank.asset_path(second).write_bytes(b'broken')
        with self.assertRaisesRegex(ToolError, 'cache_corrupted'):
            self.add()

    def test_search_success_and_failure_caches_prevent_repeated_network_calls(self):
        with patch('whatif.media_tools.search_web', return_value=[]) as search:
            self.assertFalse(self.bank.search('Naruto')['cached'])
            self.assertTrue(self.bank.search('Naruto')['cached'])
            self.assertEqual(search.call_count, 1)
        with patch('whatif.media_tools.search_web', side_effect=ToolError('provider_failed')) as search:
            self.assertEqual(self.bank.search('Pain')['status'], 'blocked')
            self.assertTrue(self.bank.search('Pain')['cached'])
            self.assertEqual(search.call_count, 1)

    def test_collect_downloads_once_and_reuses_the_verified_catalog(self):
        candidate={'source_url':'https://tenor.com/view/test','download_url':'https://media.tenor.com/test.mp4',
                   'duration':3,'height':240,'publisher':'Generated fixture'}
        with patch.object(self.bank, 'search', return_value={'status':'ok','cached':False,'candidates':[candidate]}), \
             patch('whatif.media_tools.public_bytes', return_value=self.video.read_bytes()) as download:
            first=self.bank.collect(['Naruto'],min_height=144)
            second=self.bank.collect(['Naruto'],min_height=144)
        self.assertEqual(first['status'],'ok')
        self.assertEqual(second['results'][0]['status'],'cached')
        self.assertEqual(download.call_count,1)

    def test_bogus_successful_download_is_rejected_and_failure_is_cached(self):
        candidate={'source_url':'https://tenor.com/view/test','download_url':'https://media.tenor.com/test.mp4',
                   'duration':3,'height':240,'publisher':'Generated fixture'}
        with patch.object(self.bank,'search',return_value={'status':'ok','cached':False,'candidates':[candidate]}), \
             patch('whatif.media_tools.public_bytes',return_value=b'<html>Site unavailable</html>') as download:
            first=self.bank.collect(['Naruto'],min_height=144)
            second=self.bank.collect(['Naruto'],min_height=144)
        self.assertEqual(first['status'],'partial')
        self.assertIn('cached_source_failure',second['results'][0]['failures'])
        self.assertEqual(download.call_count,1)
        self.assertEqual(self.bank.catalog()['assets'],{})

    def test_enhancement_preserves_original_audio_duration_and_aspect(self):
        original=digest(self.video)
        output=self.root/'enhanced.mp4'
        report=enhance_file(self.video,output,height=360)
        self.assertEqual(digest(self.video),original)
        self.assertFalse(report['detail_restoration_claimed'])
        self.assertEqual((report['after']['width'],report['after']['height']),(480,360))
        self.assertTrue(report['after']['has_audio'])
        self.assertAlmostEqual(report['after']['duration'],3,delta=.1)
        with self.assertRaises(ToolError):enhance_file(self.video,output)
        with self.assertRaises(ToolError):enhance_file(self.video,self.video)

    def test_build_renders_once_and_validates_cached_output(self):
        self.add()
        output=self.root/'render'
        first=build(self.story(),self.audio,self.bank,output)
        with patch.object(media_edit,'render_edit',side_effect=AssertionError('must reuse output')):
            second=build(self.story(),self.audio,self.bank,output)
        self.assertEqual(second['status'],'cached')
        self.assertEqual(first['sha256'],second['sha256'])
        report=json.loads((output/'quality.json').read_text())
        self.assertEqual(report['enhancement'],'anime-light')
        self.assertTrue(report['video_only'])
        (output/'video.mp4').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ToolError,'cached_output_corrupted'):
            build(self.story(),self.audio,self.bank,output)

    def test_short_clips_missing_labels_and_untrusted_urls_are_rejected(self):
        self.add()
        story=self.story();story['scenes'][0]['end']=5
        with self.assertRaisesRegex(ToolError,'no_cached_clip_long_enough'):make_plan(story,self.bank)
        for url in ['http://tenor.com/a','https://127.0.0.1/a','file:///tmp/video','https://user:pass@tenor.com/a']:
            with self.assertRaises(ToolError):checked_url(url,{'tenor.com'})
        with self.assertRaises(ToolError):self.bank.collect(['a']*7)
        with self.assertRaises(ToolError):self.bank.search('Naruto',limit=100)

    def test_unknown_enhancement_cannot_inject_filters(self):
        self.add();story=self.story()
        with self.assertRaises(ToolError):make_plan(story,self.bank,'arbitrary,filter')
        plan=make_plan(story,self.bank);plan['enhancement']='arbitrary,filter'
        with self.assertRaisesRegex(ValueError,'enhancement'):
            media_edit.validated_inputs(plan,self.bank.root,self.audio)


if __name__ == '__main__':unittest.main()
