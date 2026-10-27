import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from whatif.media_tools import Bank, ToolError

spec=importlib.util.spec_from_file_location('media_workflow',Path(__file__).resolve().parents[1]/'scripts'/'run_media_workflow.py')
workflow=importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


class WorkflowRequestTests(unittest.TestCase):
    def test_requests_cannot_select_shell_commands_or_escape_catalog_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            bank=Bank(Path(temp)/'bank')
            for request in [
                {'schema_version':1,'operation':'shell','command':'anything'},
                {'schema_version':1,'operation':'enhance','asset_id':'../../private'},
                {'schema_version':1,'operation':'search','provider':'file','label':'test'},
            ]:
                with self.assertRaises(ToolError):workflow.execute(request,bank,Path(temp)/'output')

    def test_story_and_request_paths_are_confined_to_expected_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            repo=Path(temp);(repo/'media-stories').mkdir();(repo/'media-stories'/'story.json').write_text('{}')
            (repo/'outside.json').write_text('{"private":"do not read"}')
            with patch.object(workflow,'REPO',repo):
                self.assertEqual(workflow.repository_json('media-stories/story.json','media-stories'),{})
                with self.assertRaises(ToolError):workflow.repository_json('media-stories/../outside.json','media-stories')

    def test_preview_reports_repeated_cache_lookup_and_enhancement(self):
        with tempfile.TemporaryDirectory() as temp:
            bank=Bank(Path(temp)/'bank')
            first={'status':'ok','results':[{'status':'ok','assets':['a']}]}
            cached={'status':'ok','results':[{'status':'cached','assets':['a']}]}
            with patch.object(bank,'collect',side_effect=[first,cached]) as collect, \
                 patch.object(bank,'catalog',return_value={'assets':{'a':{'bytes':123}}}), \
                 patch.object(bank,'asset_path',return_value=Path(temp)/'original.mp4'), \
                 patch.object(workflow,'enhance_file',return_value={'status':'ok'}) as enhance:
                result=workflow.execute({'schema_version':1,'operation':'preview','label':'Naruto running'},bank,Path(temp)/'out')
            self.assertEqual(result['repeat_collection']['results'][0]['status'],'cached')
            self.assertEqual(result['source_bytes'],123)
            self.assertEqual(collect.call_count,2)
            self.assertEqual(enhance.call_count,1)
            self.assertEqual(result['model_calls_inside_job'],0)
            self.assertIn('total',result['seconds'])

    def test_blocked_preview_does_not_enhance_unrelated_content(self):
        with tempfile.TemporaryDirectory() as temp:
            bank=Bank(Path(temp)/'bank')
            with patch.object(bank,'collect',return_value={'status':'partial','results':[{'assets':[]}]}), \
                 patch.object(workflow,'enhance_file') as enhance:
                result=workflow.execute({'schema_version':1,'operation':'preview','label':'missing'},bank,Path(temp)/'out')
            self.assertEqual(result['status'],'blocked')
            enhance.assert_not_called()


if __name__=='__main__':unittest.main()
