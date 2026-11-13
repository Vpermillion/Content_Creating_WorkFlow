import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from whatif.hosted_publishers import Publishers, tiktok_request


class HostedTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.publishers=Publishers(self.root,self.root,'https://example.invalid','fixture-key')
        self.row={'account':'ig','account_id':'123','platform':'instagram','format':'reel','handle':'@fictional'}

    def tearDown(self): self.temp.cleanup()

    def test_uncertain_media_publish_never_republishes_container(self):
        provider=Mock()
        with patch.object(self.publishers,'validate_media'), patch.object(self.publishers,'config',return_value={}), \
                patch('scripts.publishing_direct.client',return_value=provider):
            result=self.publishers.reconcile(self.row,None,'draft',{'status':'needs_reconciliation',
                'receipt':{'checkpoint':'publishing_container_id','checkpoint_id':'123'}},Mock())
        self.assertEqual(result['status'],'needs_reconciliation')
        provider.publish.assert_not_called(); provider.finish_instagram.assert_not_called()

    def test_uncertain_facebook_finish_only_reads_status(self):
        provider=Mock(); provider.status.return_value=('published','https://www.facebook.com/reel/456')
        row={**self.row,'platform':'facebook'}
        with patch.object(self.publishers,'validate_media'), patch.object(self.publishers,'config',return_value={}), \
                patch('scripts.publishing_direct.client',return_value=provider):
            result=self.publishers.reconcile(row,None,'draft',{'status':'needs_reconciliation',
                'receipt':{'checkpoint':'finishing_video_id','checkpoint_id':'456'}},Mock())
        self.assertEqual(result['status'],'published')
        provider.status.assert_called_once_with('456'); provider.publish.assert_not_called()

    def test_tiktok_query_requires_owner_and_matching_id(self):
        row={**self.row,'platform':'tiktok'}
        with patch.object(self.publishers,'verify'), patch.object(self.publishers,'config',return_value={'token':'fixture'}), \
                patch('whatif.hosted_publishers.tiktok_request') as request:
            request.return_value={'data':{'videos':[]}}
            with self.assertRaises(ValueError): self.publishers.verify_tiktok_video(row,'456')
            request.return_value={'data':{'videos':[{'id':'456','share_url':'https://www.tiktok.com/@wrong/video/456'}]}}
            with self.assertRaises(ValueError): self.publishers.verify_tiktok_video(row,'456')
            request.return_value={'data':{'videos':[{'id':'456','share_url':'https://www.tiktok.com/@fictional/video/456'}]}}
            self.assertEqual(self.publishers.verify_tiktok_video(row,'456')['status'],'published')
            self.assertIn('/video/query/',request.call_args.args[0])

    def test_tiktok_studio_never_reports_published(self):
        row={**self.row,'platform':'tiktok','media_sha256':'a'*64,'caption':'exact reviewed caption'}
        result=self.publishers.handoff(row)
        self.assertEqual(result['status'],'action_required')
        self.assertEqual(result['caption'],row['caption'])
        self.assertIn('/tiktokstudio/upload',result['studio_url'])

    def test_tiktok_success_error_object_is_not_mistaken_for_failure(self):
        response=Mock(); response.read.return_value=json.dumps({'error':{'code':'ok'},'data':{}}).encode()
        response.__enter__=Mock(return_value=response); response.__exit__=Mock(return_value=False)
        with patch('urllib.request.build_opener') as opener:
            opener.return_value.open.return_value=response
            self.assertEqual(tiktok_request('https://open.tiktokapis.com/test','fixture')['error']['code'],'ok')
