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


if __name__=='__main__':unittest.main()
