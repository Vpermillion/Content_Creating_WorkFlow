import copy
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from whatif.topics import require_owner_choice
from whatif.audio_fx import fetch_effect

class OwnerReviewTests(unittest.TestCase):
    def test_owner_choice_requires_real_reference_and_matching_script(self):
        entry={'id':'topic','owner_topic_choice':{'status':'approved','selected_by':'owner',
               'decision_reference':'Owner message choosing the reviewed script','selected_at':'2026-11-03','script_sha256':'a'*64}}
        self.assertIs(require_owner_choice({'topics':[entry]},'topic','a'*64),entry)
        for field,value in [('selected_by','assistant'),('decision_reference',None),('selected_at',None),('script_sha256','b'*64),('status','proposed')]:
            changed=copy.deepcopy(entry);changed['owner_topic_choice'][field]=value
            with self.assertRaises(ValueError):require_owner_choice({'topics':[changed]},'topic','a'*64)
        with self.assertRaises(ValueError):require_owner_choice({'topics':[]},'missing')

    def test_old_batch_finalization_cannot_replace_sound_repair(self):
        from scripts.finalize_anime_batch import merge_outcomes, index_text
        entry={'id':'topic','state':'rendered','script_sha256':'a'*64,'sound_repair':'actual',
               'result_branch':'codex/results/topic-dubbingai-01','video_sha256':'corrected',
               'video_path':'production/sound-effects-dubbingai/video-sfx.mp4',
               'posting_packet_path':'post-settings-dubbingai.json'}
        result={'id':'topic','status':'success','script_sha256':'a'*64,'branch':'codex/results/topic-r2',
                'video_sha256':'old','duration_seconds':61,'commit':'b'*40}
        registry={'topics':[entry]}
        merge_outcomes(registry,[result])
        self.assertEqual(entry['video_sha256'],'corrected')
        index=index_text(registry,{'episodes':[{'id':'topic','title':'Topic'}]})
        self.assertIn('sound-effects-dubbingai/video-sfx.mp4',index)
        self.assertIn('post-settings-dubbingai.json',index)

    def test_recordings_over_old_cap_download_but_bank_limit_is_enforced(self):
        data=b'a'*(2_000_001)
        asset={'id':'fixture','source_url':'https://dubbingai.io/','license':'unverified','license_url':'https://dubbingai.io/',
               'usage_basis':'test','description':'test','download_url':'https://dvi.dubbingai.io/cs/20260713/1-2.mp3',
               'file':'test.mp3','sha256':hashlib.sha256(data).hexdigest()}
        with tempfile.TemporaryDirectory() as temp:
            response=io.BytesIO(data);response.url=asset['download_url']
            with patch('whatif.audio_fx.urllib.request.urlopen',return_value=response):
                self.assertEqual(fetch_effect(asset,Path(temp)).stat().st_size,len(data))
            response=io.BytesIO(b'a'*(16*1024*1024+1));response.url=asset['download_url']
            with patch('whatif.audio_fx.urllib.request.urlopen',return_value=response):
                with self.assertRaisesRegex(ValueError,'size/checksum'):fetch_effect({**asset,'file':'too-large.mp3'},Path(temp))
