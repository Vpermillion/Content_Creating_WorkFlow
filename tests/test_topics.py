import copy
import json
from pathlib import Path
import tempfile
import unittest

from whatif import topics


class TopicTests(unittest.TestCase):
    def setUp(self):
        self.episode = {'id': 'first', 'topic_key': 'naruto-clone-strike', 'title': 'What if clones went on strike?',
                        'premise': 'Naruto negotiates with his shadow clones', 'franchise': 'Naruto',
                        'characters': ['Naruto'], 'aliases': ['Naruto clone labor dispute'],
                        'distinctive_development': 'Negotiation, smaller teams, shared costs',
                        'scenes': [{'text': 'One original test story.'}]}

    def registry(self):
        return {'schema_version': 1, 'channel': 'ifverse_anime', 'topics': []}

    def test_changed_title_cannot_hide_identical_script_or_topic(self):
        first = topics.topic_record(self.episode, 'batch')
        other = copy.deepcopy(first); other.update(id='second', title='Completely new title', premise='Different words here')
        found = topics.conflicts({'topics': [first]}, other)
        self.assertIn('same_topic_key', found[0]['reasons'])
        self.assertIn('same_ordered_script', found[0]['reasons'])

    def test_alias_punctuation_and_case_are_normalized(self):
        first = topics.topic_record(self.episode, 'batch')
        other = copy.deepcopy(first); other.update(id='second', topic_key='different', script_sha256='different',
                                                  title='NARUTO: CLONE LABOR DISPUTE!!!', premise='Unrelated framing')
        self.assertIn('same_title_premise_or_alias', topics.conflicts({'topics': [first]}, other)[0]['reasons'])

    def test_reservation_is_idempotent_but_changed_script_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'topics.json'; topics.atomic_json(path, self.registry())
            batch={'id':'batch','channel':'ifverse_anime','episodes':[self.episode]}
            topics.reserve(path,batch); topics.reserve(path,batch)
            self.assertEqual(len(json.loads(path.read_text())['topics']),1)
            batch['episodes'][0]['scenes'][0]['text']='Changed script'
            with self.assertRaisesRegex(ValueError,'different content'):
                topics.reserve(path,batch)

    def test_batch_overlap_fails_without_partial_reservations(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'topics.json';topics.atomic_json(path,self.registry());before=path.read_bytes()
            other=copy.deepcopy(self.episode);other['id']='second'
            with self.assertRaisesRegex(ValueError,'overlap'):
                topics.reserve(path,{'id':'batch','channel':'ifverse_anime','episodes':[self.episode,other]})
            self.assertEqual(before,path.read_bytes())

    def test_failed_or_rendered_topic_still_blocks_duplicate(self):
        first=topics.topic_record(self.episode,'batch')
        candidate=copy.deepcopy(first);candidate['id']='second'
        for state in ['reserved','render_failed','rendered','published']:
            first['state']=state
            self.assertTrue(topics.conflicts({'topics':[first]},candidate))

    def test_result_must_match_reserved_script_and_not_mark_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'topics.json';topics.atomic_json(path,self.registry())
            topics.reserve(path,{'id':'batch','channel':'ifverse_anime','episodes':[self.episode]})
            result={'id':'first','script_sha256':'wrong','status':'success'}
            with self.assertRaisesRegex(ValueError,'different episode'):
                topics.record_result(path,'first',result,'receipt.json')
            result.update(script_sha256=topics.script_hash(self.episode['scenes']),video_sha256='hash')
            topics.record_result(path,'first',result,'receipt.json')
            value=json.loads(path.read_text())['topics'][0]
            self.assertEqual(value['state'],'rendered');self.assertIsNone(value['video_id'])
            with self.assertRaisesRegex(ValueError,'provider video ID'):
                topics.mark_published(path,'first',{})

    def test_requested_revision_preserves_history_and_published_topic_cannot_be_revised(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'topics.json';topics.atomic_json(path,self.registry())
            batch={'id':'batch','channel':'ifverse_anime','episodes':[self.episode]}
            topics.reserve(path,batch)
            batch['episodes'][0]['scenes'][0]['text']='A shorter authorized script.'
            value=topics.revise_batch(path,batch,'Owner requested a 61-second cut')
            self.assertEqual(len(value['topics'][0]['versions']),1)
            self.assertEqual(value['topics'][0]['script_sha256'],topics.script_hash(batch['episodes'][0]['scenes']))
            value['topics'][0]['state']='published';topics.atomic_json(path,value)
            with self.assertRaisesRegex(ValueError,'published topic'):
                topics.revise_batch(path,batch,'Another cut')
