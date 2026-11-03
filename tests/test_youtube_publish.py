import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from whatif import youtube as yt, youtube_publish as pub

CHANNEL='UC'+'a'*22
OTHER='UC'+'b'*22


def response(status, body=None, **headers):
    r=Mock(status_code=status,headers=headers);r.json.return_value=body;return r


def final(channel=CHANNEL,privacy='public',processed=True):
    return response(200,{'id':'abc123_-XYZ','snippet':{'channelId':channel},
                         'status':{'privacyStatus':privacy,'uploadStatus':'processed' if processed else 'uploaded'}})


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.video=self.root/'video.mp4';self.video.write_bytes(b'x'*100)
        self.body={'snippet':{'title':'Fixture'},'status':{'privacyStatus':'public'}}

    def tearDown(self):self.temp.cleanup()

    def upload(self,session,**kwargs):
        return pub.upload(session,'episode',self.video,'video-hash','metadata-hash',self.body,CHANNEL,self.root/'private-state',**kwargs)

    def test_readonly_scope_cannot_upload(self):
        creds=Mock(granted_scopes=[yt.READ_SCOPE]);creds.has_scopes.return_value=False
        with self.assertRaisesRegex(pub.UploadError,'Read-only consent'):pub.require_upload_scope(creds)

    def test_success_and_retry_return_same_receipt_without_second_insert(self):
        s=Mock();s.post.return_value=response(200,Location=pub.UPLOAD_URL+'?upload_id=fixture')
        s.put.return_value=final()
        receipt=self.upload(s);again=self.upload(s)
        self.assertEqual(receipt,again);self.assertTrue(receipt['publicly_posted'])
        self.assertEqual(s.post.call_count,1);self.assertEqual(s.put.call_count,1)
        self.assertEqual((self.root/'private-state/episode.json').stat().st_mode & 0o777,0o600)
        self.assertNotIn('session_url',json.dumps(receipt))

    def test_lost_final_response_is_reconciled_with_same_session(self):
        s=Mock();s.post.return_value=response(200,Location=pub.UPLOAD_URL+'?upload_id=fixture')
        s.put.side_effect=TimeoutError('fixture transport loss')
        with self.assertRaisesRegex(pub.UploadError,'same session'):self.upload(s)
        s.put.side_effect=None;s.put.return_value=final()
        receipt=self.upload(s)
        self.assertEqual(s.post.call_count,1);self.assertTrue(receipt['publicly_posted'])
        self.assertEqual(s.put.call_args.kwargs['headers']['Content-Range'],'bytes */100')

    def test_lost_initiation_does_not_create_another_session(self):
        s=Mock();s.post.side_effect=TimeoutError('fixture transport loss')
        for _ in range(2):
            with self.assertRaises(pub.UploadError):self.upload(s)
        self.assertEqual(s.post.call_count,1);s.put.assert_not_called()

    def test_wrong_channel_final_result_stays_uncertain_and_cannot_reinsert(self):
        s=Mock();s.post.return_value=response(200,Location=pub.UPLOAD_URL+'?upload_id=fixture')
        s.put.return_value=final(channel=OTHER)
        for _ in range(2):
            with self.assertRaises(pub.UploadError):self.upload(s)
        self.assertEqual(s.post.call_count,1)

    def test_changed_video_or_metadata_cannot_reuse_existing_operation(self):
        s=Mock();s.post.return_value=response(200,Location=pub.UPLOAD_URL+'?upload_id=fixture');s.put.return_value=final()
        self.upload(s)
        with self.assertRaisesRegex(pub.UploadError,'different media'):
            pub.upload(s,'episode',self.video,'changed','metadata-hash',self.body,CHANNEL,self.root/'private-state')
        self.assertEqual(s.post.call_count,1)

    def test_private_or_processing_video_is_not_reported_as_public(self):
        for privacy,processed in [('private',True),('public',False)]:
            with self.subTest(privacy=privacy,processed=processed),tempfile.TemporaryDirectory() as t:
                s=Mock();s.post.return_value=response(200,Location=pub.UPLOAD_URL+'?upload_id=fixture')
                s.put.return_value=final(privacy=privacy,processed=processed)
                r=pub.upload(s,'episode',self.video,'hash','meta',self.body,CHANNEL,Path(t)/'private')
                self.assertFalse(r['publicly_posted'])

    def test_untrusted_session_location_receives_no_video(self):
        s=Mock();s.post.return_value=response(200,Location='https://evil.example/upload')
        with self.assertRaises(pub.UploadError):self.upload(s)
        s.put.assert_not_called()

    def test_chunk_acknowledgement_and_resume_offset_are_bounded(self):
        s=Mock();s.post.return_value=response(200,Location=pub.UPLOAD_URL+'?upload_id=fixture')
        s.put.side_effect=[response(308,Range='bytes=0-31'),response(308,Range='bytes=0-63'),
                           response(308,Range='bytes=0-95'),final()]
        with patch.object(pub,'CHUNK_BYTES',32):r=self.upload(s)
        self.assertTrue(r['publicly_posted']);self.assertEqual(s.put.call_count,4)
        self.assertEqual(s.put.call_args_list[-1].kwargs['headers']['Content-Range'],'bytes 96-99/100')

    def test_pending_review_blocks_before_media_or_provider_calls(self):
        with patch.object(pub.media,'probe') as probe:
            with self.assertRaisesRegex(pub.UploadError,'review are pending'):
                pub.preflight({'id':'episode'},self.root,{'topics':[{'id':'episode'}]})
            probe.assert_not_called()

    def test_saved_wrong_channel_is_rejected_before_any_provider_request(self):
        store=yt.ConnectionStore(self.root/'connection')
        store.save('ifverse-anime',{'schema_version':1,'connection':'ifverse-anime',
            'channel':{'id':OTHER},'credentials':{'token_uri':yt.TOKEN_URI}})
        with patch.object(yt,'sdk',return_value=(Mock(),Mock(),Mock(),Mock())) as sdk:
            with self.assertRaisesRegex(pub.UploadError,'different channel'):
                pub.verified_session(store,CHANNEL)
            sdk.return_value[-1].assert_not_called()

    def test_real_short_preflight_checks_media_hash_and_maps_post_settings(self):
        folder=self.root/'artifacts/episode';folder.mkdir(parents=True)
        pub.media.ffmpeg(['-f','lavfi','-i','color=s=90x160:r=1:d=61',
                         '-f','lavfi','-i','anullsrc=r=24000:cl=mono','-t','61',
                         '-c:v','libx264','-c:a','aac','fixture.mp4'],folder)
        fingerprint=pub.digest(folder/'fixture.mp4')
        item={'id':'episode','video':'artifacts/episode/fixture.mp4','video_sha256':fingerprint,
              'publication_clearance':'cleared','review':{'source_use':'approved','audiovisual':'approved',
              'reviewed_by':'offline test fixture','evidence':'Generated color and silence, not a production approval',
              'audience':'not_made_for_kids','synthetic_disclosure':False},
              'metadata':{'title':'Generated fixture','description':'Offline test #Shorts','tags':['fixture']}}
        registry={'topics':[{'id':'episode','video_sha256':fingerprint}]}
        video,sha,metadata_hash,body=pub.preflight(item,self.root,registry)
        self.assertEqual(sha,fingerprint);self.assertEqual(len(metadata_hash),64)
        self.assertFalse(body['status']['selfDeclaredMadeForKids'])
        self.assertFalse(body['status']['containsSyntheticMedia'])
        self.assertEqual(body['snippet']['tags'],['fixture'])
        item['video_sha256']='changed'
        with self.assertRaisesRegex(pub.UploadError,'same SHA-256'):pub.preflight(item,self.root,registry)
