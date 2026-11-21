import json
import hashlib
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from whatif.publishing_jobs import MediaJobs


class MediaJobTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg tools are required')
    def test_pinned_master_can_produce_a_reviewable_reel_and_image(self):
        from whatif import media
        from whatif.publishing_service import Drafts

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/'fixture.mp4'
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
                            'color=red:s=180x320:r=12', '-f', 'lavfi', '-i', 'anullsrc',
                            '-t', '4', '-c:v', 'libx264', '-threads:v', '1', '-c:a', 'aac', str(source)], check=True)
            drafts = Drafts(root/'private', root, Mock())
            master = drafts.put_media(source.read_bytes())
            jobs = MediaJobs(root, root/'private', drafts)
            self.addCleanup(jobs.executor.shutdown)
            image = jobs.export_media(master, 'jpeg')
            reel = jobs.export_media(master, 'facebook_reel')
            self.assertEqual(len({master, image, reel}), 3)
            frame = media.probe(drafts.media(image))['streams'][0]
            self.assertEqual((frame['codec_name'], frame['width'], frame['height']), ('mjpeg', 720, 900))
            self.assertLessEqual(float(media.probe(drafts.media(reel))['format']['duration']), 60)

    def test_import_uses_pinned_private_result_and_checks_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'channels').mkdir()
            content = b'review fixture'
            sha = hashlib.sha256(content).hexdigest()
            (root/'channels/anime-topics.json').write_text(json.dumps({'topics': [{
                'id':'episode', 'video_path':'render/final.mp4', 'result_commit':'a'*40, 'video_sha256':sha}]}))
            drafts = Mock()
            drafts.media.return_value = root/'missing'
            jobs = MediaJobs(root, root/'private', drafts)
            self.addCleanup(jobs.executor.shutdown)
            with patch.dict('os.environ', {'IFVERSE_GITHUB_READ_TOKEN':'fictional'}), \
                    patch('whatif.publishing_jobs.build_opener') as opener:
                get = opener.return_value.open
                get.return_value = io.BytesIO(b'wrong bytes')
                with self.assertRaises(ValueError):
                    jobs.import_result('anime', 'episode')
                drafts.put_media.assert_not_called()
                get.return_value = io.BytesIO(content)
                result = jobs.import_result('anime', 'episode')
                request = get.call_args.args[0]
            self.assertTrue(request.full_url.endswith('/artifacts/episode/render/final.mp4?ref='+'a'*40))
            self.assertEqual(result['manifest']['video_sha256'], sha)
            drafts.put_media.assert_called_once_with(content)

    def test_durable_request_retrieval_and_no_rerender_after_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'review-requests').mkdir()
            (root/'review-requests/fixture.json').write_text(json.dumps({'id':'fixture'}))
            drafts=Mock(); drafts.put_media.return_value='a'*64
            jobs=MediaJobs(root,root/'private',drafts)
            jobs.executor.shutdown()
            jobs.executor=Mock()
            first=jobs.submit('fixture')
            jobs.executor.submit.assert_called_once()
            fresh=MediaJobs(root,root/'private',drafts)
            self.assertEqual(fresh.submit('fixture'),first)
            fresh.executor.shutdown()
            self.assertEqual(fresh.get('fixture')['status'],'queued')
            (root/'review-requests/fixture.json').write_text(json.dumps({'id':'fixture','changed':True}))
            with self.assertRaises(ValueError): fresh.submit('fixture')
            with self.assertRaises(ValueError): fresh.submit('../escape')

    def test_completed_renderer_final_media_is_staged(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); drafts=Mock(); drafts.put_media.return_value='a'*64
            jobs=MediaJobs(root,root/'private',drafts)
            def render(request,output,models):
                output.mkdir(); (output/'final.mp4').write_bytes(b'fictional final')
                return {'status':'success','video':'final.mp4','sound_effects':None}
            with patch('scripts.render_test_video.run', side_effect=render):
                jobs.run({'id':'fixture'},{'job_id':'fixture','request_sha256':'b'*64})
            self.assertEqual(jobs.get('fixture')['status'],'prepared')
            drafts.put_media.assert_called_once_with(b'fictional final')
            jobs.executor.shutdown()
