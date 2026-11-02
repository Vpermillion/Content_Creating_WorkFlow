import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from whatif import media
from whatif.media_edit import local_asset, render_edit, validated_inputs
from whatif.store import digest


class ImportedMediaTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.assets=self.root/'assets';self.assets.mkdir()
        media.ffmpeg(['-f','lavfi','-i','color=c=navy:s=320x240','-frames:v','1','still.png'],self.assets)
        media.ffmpeg(['-f','lavfi','-i','testsrc2=size=320x240:rate=30:duration=2',
                      '-c:v','libx264','-pix_fmt','yuv420p','movie.mp4'],self.assets)
        media.ffmpeg(['-f','lavfi','-i','sine=frequency=440:duration=2','-ar','48000','sound.wav'],self.root)
        self.audio=self.root/'sound.wav'
        self.plan={'schema_version':1,'width':360,'height':640,'fps':30,'narration_sha256':digest(self.audio),
                   'assets':[{'id':'still','file':'still.png','type':'image','sha256':digest(self.assets/'still.png'),'source_url':'fixture:original','reuse_status':'Generated software test fixture'},
                             {'id':'movie','file':'movie.mp4','type':'video','sha256':digest(self.assets/'movie.mp4'),'source_url':'fixture:original','reuse_status':'Generated software test fixture'}],
                   'scenes':[{'start':0,'end':1,'text':'A software test.','label':'ONE','shots':[{'asset':'still','fit':'contain','match_reason':'Fixture image path'}]},
                             {'start':1,'end':2,'text':'A second test.','label':'TWO','shots':[{'asset':'movie','fit':'cover','trim_start':.25,'match_reason':'Fixture video path'}]}]}

    def tearDown(self):self.temp.cleanup()

    def test_mixed_image_video_cut_covers_audio_and_retains_original_narration(self):
        original=digest(self.audio)
        output=render_edit(self.plan,self.assets,self.audio,self.root/'render')
        info=media.probe(output)
        self.assertEqual(digest(self.audio),original)
        self.assertAlmostEqual(float(info['format']['duration']),2,delta=.1)
        self.assertTrue((output.parent/'captions.srt').is_file())

    def test_corrupt_asset_wrong_audio_and_path_traversal_are_rejected(self):
        with self.assertRaises(ValueError):local_asset(self.assets,'../sound.wav')
        plan=copy.deepcopy(self.plan);plan['narration_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Narration changed'):validated_inputs(plan,self.assets,self.audio)
        (self.assets/'still.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'provenance or checksum'):validated_inputs(self.plan,self.assets,self.audio)

    def test_video_only_requirement_and_credit_controls_are_enforced(self):
        plan=copy.deepcopy(self.plan);plan['video_only']=True
        with self.assertRaisesRegex(ValueError,'Video-only'):validated_inputs(plan,self.assets,self.audio)
        plan=copy.deepcopy(self.plan);plan['source_credit']='Bad{control}'
        with self.assertRaisesRegex(ValueError,'source credit'):validated_inputs(plan,self.assets,self.audio)

    def test_single_pass_video_cut_has_complete_tracks_and_no_intermediate_mp4s(self):
        plan=copy.deepcopy(self.plan);plan.update(video_only=True,single_pass=True,source_credit='GENERATED VIDEO FIXTURE')
        plan['scenes'][0]['shots'][0]['asset']='movie'
        plan['scenes'][0]['shots'][0]['crop_bottom']=.2
        result=render_edit(plan,self.assets,self.audio,self.root/'direct')
        info=media.probe(result)
        for stream in info['streams']:
            self.assertAlmostEqual(float(stream['duration']),2,delta=.1)
        self.assertEqual(list(result.parent.glob('shot-*.mp4')),[])

    def test_a_shot_truncated_before_concat_is_repaired_once(self):
        original=media.probe
        calls=0
        def probe(path):
            nonlocal calls
            if Path(path).name=='shot-000.mp4':
                calls+=1
                if calls==2:Path(path).write_bytes(b'truncated local render fixture')
            return original(path)
        with patch.object(media,'probe',side_effect=probe):
            result=render_edit(self.plan,self.assets,self.audio,self.root/'repair')
        import json
        report=json.loads((result.parent/'quality.json').read_text())
        self.assertEqual(report['repaired_local_shots'],['shot-000.mp4'])
        self.assertTrue(report['automated_pass'])

    def test_timing_gaps_subtitle_controls_and_missing_semantic_match_are_rejected(self):
        for change in ['gap','subtitle','match']:
            plan=copy.deepcopy(self.plan)
            if change=='gap':plan['scenes'][1]['start']=1.1
            if change=='subtitle':plan['scenes'][0]['text']='{control}'
            if change=='match':plan['scenes'][0]['shots'][0]['match_reason']=''
            with self.assertRaises(ValueError):validated_inputs(plan,self.assets,self.audio)

    def test_recognized_caption_intervals_are_rendered_independently_of_scene_headings(self):
        plan = copy.deepcopy(self.plan)
        plan['caption_segments'] = [{'start': .2, 'end': .8, 'text': 'Actual spoken timing.'},
                                    {'start': 1.2, 'end': 1.8, 'text': 'Another phrase.'}]
        output = render_edit(plan, self.assets, self.audio, self.root/'recognized')
        srt = (output.parent/'captions.srt').read_text()
        self.assertIn('00:00:00,200 --> 00:00:00,800', srt)
        self.assertIn('Actual spoken timing.', srt)
        self.assertNotIn('A software test.', srt)
        ass = (output.parent/'captions.ass').read_text()
        self.assertIn('Heading,,0,0,0,,ONE', ass)

    def test_recognized_captions_cannot_overlap_or_escape_audio_or_inject_ass(self):
        for captions in [
            [{'start': 0, 'end': 3, 'text': 'Too long.'}],
            [{'start': 0, 'end': 1, 'text': 'First.'}, {'start': .5, 'end': 1.5, 'text': 'Overlap.'}],
            [{'start': 0, 'end': 1, 'text': '{control}'}],
            [{'start': float('nan'), 'end': 1, 'text': 'Invalid.'}],
        ]:
            plan = copy.deepcopy(self.plan)
            plan['caption_segments'] = captions
            with self.assertRaises(ValueError):
                validated_inputs(plan, self.assets, self.audio)

    def test_reviewed_shot_boundaries_survive_rendering_without_equal_resplit(self):
        plan = copy.deepcopy(self.plan)
        plan.update(single_pass=True, video_only=True)
        plan['scenes'][0]['shots'] = [
            {'asset': 'movie', 'start': 0, 'end': .25, 'match_reason': 'Short spoken beat'},
            {'asset': 'movie', 'start': .25, 'end': 1, 'match_reason': 'Longer spoken beat'}]
        result = render_edit(plan, self.assets, self.audio, self.root/'beats')
        import json
        shots = json.loads((result.parent/'edit.json').read_text())['shots']
        self.assertEqual([(s['start'], s['end'], s['frames']) for s in shots[:2]],
                         [(0, .25, 8), (.25, 1, 22)])
        self.assertAlmostEqual(float(media.probe(result)['format']['duration']), 2, delta=.1)

    def test_gapped_overlapping_partial_or_nonfinite_shot_timings_fail_before_render(self):
        from whatif.media_edit import shot_intervals
        for shots in [
            [{'start': 0, 'end': .4}, {'start': .6, 'end': 1}],
            [{'start': 0, 'end': .7}, {'start': .5, 'end': 1}],
            [{'start': .1, 'end': 1}],
            [{'start': 0, 'end': .9}],
            [{'start': 0, 'end': float('nan')}],
            [{'start': 0, 'end': .5}, {}],
        ]:
            with self.assertRaises(ValueError):
                shot_intervals({'start': 0, 'end': 1, 'shots': shots})


if __name__=='__main__':unittest.main()
