import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import render_anime_batch as batch
from whatif.topics import topic_record


class AnimeBatchTests(unittest.TestCase):
    def test_real_batch_is_reserved_distinct_and_long_enough(self):
        value=batch.load_batch('batch-requests/ifverse-anime-ten-61s-20261103-01.json')
        self.assertEqual(len(value['episodes']),10)
        self.assertGreaterEqual(value['target_duration_seconds'],60)
        self.assertEqual(len({e['topic_key'] for e in value['episodes']}),10)

    def test_failed_source_preserves_successful_acquisitions(self):
        episode={'id':'episode','franchise':'Anime','sources':[
            {'id':'good','key':'good','query':'Good character','required_terms':['good'],'visual_intent':'good'},
            {'id':'bad','key':'bad','query':'Bad character','required_terms':['bad'],'visual_intent':'bad'}]}
        def acquire(spec,out):
            if spec['id']=='bad':raise ValueError('not found')
            return {'id':'good','sha256':'hash'}
        with tempfile.TemporaryDirectory() as temp, patch.object(batch.sources,'acquire_footage',side_effect=acquire):
            with self.assertRaisesRegex(ValueError,'bad'):
                batch.collect_episode(episode,Path(temp))
            receipt=json.loads((Path(temp)/'sources.json').read_text())
            self.assertEqual(receipt['results'][0]['asset']['id'],'good')
            self.assertEqual(len(receipt['results'][1]['attempts']),2)

    def test_invalid_cue_and_already_published_reservation_fail_before_render(self):
        original=batch.load_batch('batch-requests/ifverse-anime-ten-61s-20261103-01.json')
        for mutation, message in [('cue','Sound cue'),('published','not already published')]:
            value=copy.deepcopy(original);value['episodes']=value['episodes'][:1]
            if mutation=='cue':value['episodes'][0]['cues'][0]['phrase']='This phrase does not exist'
            registry={'topics':[topic_record(value['episodes'][0],value['id'])]}
            if mutation=='published':registry['topics'][0]['state']='published'
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);(root/'batch-requests').mkdir();(root/'channels').mkdir()
                (root/'batch-requests/test.json').write_text(json.dumps(value))
                (root/'channels/ifverse_anime-topics.json').write_text(json.dumps(registry))
                with patch.object(batch,'ROOT',root),self.assertRaisesRegex(ValueError,message):
                    batch.load_batch('batch-requests/test.json')
