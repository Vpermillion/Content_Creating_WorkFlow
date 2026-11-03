"""Sound-only repair of pinned saved results; no speech or footage generation."""
import argparse
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from whatif.audio_fx import mix_effects, read_pcm
from whatif import media
from whatif.store import atomic_json, digest

# Editorial choices for the four retained spoken anchors in each saved script.
CHOICES = {
'naruto-clone-strike': [('vine_boom','The unpaid-staff roast lands'),('faaah','Exhausted-teenager productivity plan fails'),('vine_boom','Lunch-schedule bureaucracy is the reveal'),('faaah','Forehead payoff invites disbelief')],
'rock-lee-rinnegan': [('vine_boom','Guy reacts to the impossible eye reveal'),('faaah','Missing drivers mocks lack of control'),('rizz_effect','Motivational-brand line mocks confident swagger'),('faaah','Different department undercuts the boast')],
'shikamaru-hokage-day': [('vine_boom','Indoor-composting paperwork roast'),('faaah','Calendar chaos exposes failed logistics'),('vine_boom','Explosive-trailer comparison lands'),('rizz_effect','Political-platform line gives sarcastic confidence')],
'luffy-no-devil-fruit': [('vine_boom','Plot-childproofing roast lands'),('faaah','Be-serious rebuke rejects the easy solution'),('vine_boom','Single-brain-cell roast'),('faaah','Second rescue objective exposes failure')],
'zoro-perfect-directions': [('vine_boom','Shopping-cart navigation comparison lands'),('faaah','Unsupported early arrival is a failed plan'),('faaah','Refusing eye contact is an awkward reaction'),('vine_boom','Damage-stat payoff lands')],
'light-explains-every-name': [('vine_boom','Peer-review reversal lands'),('faaah','Bibliography demand frustrates Light'),('vine_boom','Whole-forecast exaggeration lands'),('faaah','Academic-hearing humiliation')],
'vegeta-peaceful-week': [('vine_boom','Tuesday-activities incongruity lands'),('faaah','Enemy-combatant overreaction'),('vine_boom','Historic-scenes mock praise'),('faaah','Horrible-phrasing reaction')],
'levi-cleaning-drill': [('vine_boom','Bucket reveal lands'),('faaah','Safety-equipment failure'),('vine_boom','Squad responsibility punchline'),('faaah','Aggressive-eye-contact absurdity')],
'gojo-no-powers-day': [('vine_boom','Vanished backup stakes reveal'),('faaah','Marketing-campaign insult'),('rizz_effect','Personality-reset line preserves Gojo swagger'),('vine_boom','Practical-application payoff')],
'tanjiro-demon-thoughts': [('vine_boom','No-mute-button premise roast'),('faaah','Terrible-acoustics disbelief'),('vine_boom','Enormous-heart contrast lands'),('faaah','Local-government escalation reaction')],
}

def git(*args, **kw):
    return subprocess.check_output(['git', *args], cwd=ROOT, **kw)

def picture_hash(path):
    return subprocess.check_output(['ffmpeg','-nostdin','-v','error','-i',str(path),'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-'],text=True).strip()

def repair(topic, episode, bank):
    prior = copy.deepcopy(topic)
    branch = 'codex/results/' + topic['id'] + '-dubbingai-01'
    work = ROOT / 'private/sound-repair' / topic['id']
    summary = work / 'completed.json'
    if summary.exists():
        return json.loads(summary.read_text())
    work.mkdir(parents=True, exist_ok=True)
    head = git('ls-remote','origin','refs/heads/'+topic['result_branch'],text=True).split()[0]
    if head != topic['result_commit']:
        raise ValueError('Selected remote moved; inspect before repair')
    git('fetch','origin',topic['result_branch'])
    prefix = 'artifacts/' + topic['id']
    # Archive only the saved artifact subtree; never switch/reset the user's checkout.
    raw = git('archive',topic['result_commit'],prefix)
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        archive.extractall(work, filter='data')
    source = work / prefix
    production = source / 'production'
    old = source / 'batch-result.json'
    old_result = json.loads(old.read_text())
    if digest(source / old_result['video']) != topic['video_sha256']:
        raise ValueError('Selected video hash differs from registry')
    narration = production / 'narration.wav'
    transcript = json.loads((production / 'transcription.json').read_text())
    narration_receipt = json.loads((production / 'narration.json').read_text())
    assert narration_receipt['voice'] == 'am_michael' and narration_receipt['sha256'] == digest(narration)
    assert picture_hash(production/'render/video.mp4') == picture_hash(source/old_result['video'])
    plan = {'schema_version':1, 'narration_sha256':digest(narration), 'catalog':'assets/sfx/dubbingai-bank.json', 'cues':[]}
    for cue, (effect, reason) in zip(episode['cues'], CHOICES[topic['topic_key']], strict=True):
        plan['cues'].append({'anchor':{'phrase':cue['phrase'],'edge':'end'},'offset_seconds':.03,
                            'effect':'dubbingai_'+effect,'peak_dbfs':-17,'max_seconds':.75,'reason':reason})
    output = production / 'sound-effects-dubbingai'
    atomic_json(source / 'dubbingai-plan.json', plan)
    before = {name:digest(production/name) for name in ('narration.wav','narration.json','transcription.json')}
    result = mix_effects(production/'render/video.mp4', narration, transcript, plan, bank, ROOT/'assets/sfx/bank', output)
    if result['master_gain'] != 1:
        raise ValueError('Mix would attenuate retained voice; lower cue levels')
    video = output / result['video']
    probe = media.probe(video)
    v = next(s for s in probe['streams'] if s['codec_type']=='video')
    assert (v['codec_name'], v['width'], v['height']) == ('h264',720,1280)
    assert abs(float(v['duration'])-61) < .001 and abs(media.duration(video)-61)<.001
    assert picture_hash(video) == picture_hash(production/'render/video.mp4')
    for name, sha in before.items():
        assert digest(production/name)==sha
    # Outside effect windows, PCM differs only by integer quantization (<= 2 LSB).
    import numpy as np
    dry, mixed = read_pcm(narration), read_pcm(output/'mix.wav')
    mask = np.ones(len(dry),dtype=bool)
    for cue in result['cues']:
        a,b=round(cue['start_seconds']*24000),round(cue['end_seconds']*24000)
        mask[a:b]=False
        assert np.max(np.abs(mixed[a:b]-dry[a:b])) > .001
        assert cue['source_sha256']==next(a['sha256'] for a in bank['assets'] if a['id']==cue['effect'])
    delta=float(np.max(np.abs(mixed[mask]-dry[mask])))
    assert delta <= 2/32768
    validation={'status':'passed','duration_seconds':61,'frame_size':[720,1280], 'complete_decode':'passed_ffmpeg_xerror',
                'h264_stream_sha256':picture_hash(video),'retained_inputs_sha256':before,
                'voice_master_gain':1,'outside_cues_max_pcm_delta':delta,'all_cues_have_measured_energy':True,
                'source_hashes_verified':True,'caption_timing_unchanged':True,'old_soundtrack_used':False,
                'narration_receipt_retained':True, 'source_result_commit':prior['result_commit']}
    atomic_json(source/'sound-repair-validation.json',validation)
    settings=json.loads((source/'post-settings.json').read_text())
    def attribution(value):
        if isinstance(value,str):
            return value.replace('Sound effects: Brackeys, public domain.', 'Sound effects: actual Vine Boom/faaah/Rizz recordings from the DubbingAI collection; community excerpt reuse rights unverified.')
        if isinstance(value,dict): return {k:attribution(v) for k,v in value.items()}
        if isinstance(value,list): return [attribution(v) for v in value]
        return value
    settings=attribution(settings)
    settings.update(video_sha256=digest(video),actual_upload_status='not_uploaded',publication_clearance='not_established')
    atomic_json(source/'post-settings-dubbingai.json',settings)
    corrected={**attribution(old_result),'video':'production/sound-effects-dubbingai/video-sfx.mp4','video_sha256':digest(video),
               'result_branch':branch,'sound_catalog':'assets/sfx/dubbingai-bank.json', 'sound_rights':'community_excerpt_rights_unverified',
               'sound_repair_source':prior,'uploaded':False,'publication_clearance':'not_established'}
    atomic_json(source/'batch-result-dubbingai.json',corrected)
    # A separate Git index adds only new versioned repair files to the selected result parent.
    index=work/'result.index'
    env={**os.environ,'GIT_INDEX_FILE':str(index)}
    git('read-tree',prior['result_commit'],env=env)
    files=[source/x for x in ('dubbingai-plan.json','sound-repair-validation.json','post-settings-dubbingai.json','batch-result-dubbingai.json')]
    files+=list(output.iterdir())
    for path in files:
        blob=git('hash-object','-w',str(path),text=True).strip()
        git('update-index','--add','--cacheinfo','100644',blob,str(path.relative_to(work)),env=env)
    tree=git('write-tree',env=env,text=True).strip()
    commit=git('commit-tree',tree,'-p',prior['result_commit'],'-m','Repair soundtrack from retained Michael voice and actual DubbingAI recordings',text=True).strip()
    git('update-ref','refs/heads/'+branch,commit,'0'*40)
    completed={'id':topic['id'],'result_branch':branch,'result_commit':commit,'video_sha256':digest(video),
               'prior':prior,'validation':validation,'video':prefix+'/'+corrected['video'],
               'posting_packet':prefix+'/post-settings-dubbingai.json'}
    atomic_json(summary,completed)
    print(topic['id']+' validated '+commit,flush=True)
    return completed

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--push',action='store_true');args=parser.parse_args()
    registry=json.loads((ROOT/'channels/ifverse_anime-topics.json').read_text())
    batch=json.loads((ROOT/'batch-requests/ifverse-anime-ten-61s-20261103-01.json').read_text())
    bank=json.loads((ROOT/'assets/sfx/dubbingai-bank.json').read_text())
    completed=[]
    for episode in batch['episodes']:
        topic=next(t for t in registry['topics'] if t['id']==episode['id'])
        completed.append(repair(topic,episode,bank))
    atomic_json(ROOT/'docs/sound-repair-results.json',completed)
    if args.push:
        for result in completed:
            git('push','origin',result['result_commit']+':refs/heads/'+result['result_branch'])

if __name__=='__main__':main()
