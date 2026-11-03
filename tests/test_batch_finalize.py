import copy
import unittest
from scripts.finalize_anime_batch import merge_outcomes


class BatchFinalizeTests(unittest.TestCase):
    def setUp(self):
        self.entry={'id':'episode','script_sha256':'current','state':'reserved','video_id':None}
        self.result={'id':'episode','script_sha256':'current','status':'success','video_sha256':'video',
                     'duration_seconds':61,'branch':'codex/results/episode-r2','commit':'commit'}

    def test_success_marks_rendered_without_fabricating_publication(self):
        value=merge_outcomes({'topics':[copy.deepcopy(self.entry)]},[self.result])['topics'][0]
        self.assertEqual(value['state'],'rendered');self.assertIsNone(value['video_id'])
        self.assertEqual(value['publication_clearance'],'not_established')

    def test_old_script_result_cannot_replace_newer_revision(self):
        self.result['script_sha256']='old'
        value=merge_outcomes({'topics':[copy.deepcopy(self.entry)]},[self.result])['topics'][0]
        self.assertEqual(value,self.entry)

    def test_failed_repair_does_not_discard_saved_success_and_post_is_immutable(self):
        self.entry.update(state='rendered',video_sha256='prior')
        failed={**self.result,'status':'failed','error':'fixture failure'}
        value=merge_outcomes({'topics':[copy.deepcopy(self.entry)]},[failed])['topics'][0]
        self.assertEqual(value,self.entry)
        self.entry.update(state='published',video_id='provider-id')
        value=merge_outcomes({'topics':[copy.deepcopy(self.entry)]},[self.result])['topics'][0]
        self.assertEqual(value,self.entry)
