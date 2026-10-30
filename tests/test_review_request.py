import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('select_review_request', Path(__file__).resolve().parents[1]/'scripts/select_review_request.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReviewRequestTests(unittest.TestCase):
    def test_exactly_one_data_request_selects_its_own_result_branch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'review-requests').mkdir()
            name = 'review-requests/test-video.json'
            (root/name).write_text(json.dumps({'schema_version':1, 'id':'test-video',
                                             'result_branch':'codex/results/test-video'}))
            self.assertEqual(module.select_request([name,'README.md'],root),(name,'test-video'))
            for names in [[],[name,'review-requests/another.json'],['review-requests/../../secret.json']]:
                with self.assertRaises(ValueError):
                    module.select_request(names,root)

    def test_request_cannot_write_to_an_unrelated_branch(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'review-requests').mkdir()
            name='review-requests/test.json'
            (root/name).write_text(json.dumps({'schema_version':1,'id':'test','result_branch':'main'}))
            with self.assertRaisesRegex(ValueError,'result branch'):
                module.select_request([name],root)
