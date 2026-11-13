import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from whatif.publishing_jobs import MediaJobs


class MediaJobTests(unittest.TestCase):
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
