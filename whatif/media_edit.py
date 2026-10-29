"""Ordered image/video edits against retained narration; no publishing or job DB."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import textwrap
import urllib.parse
import urllib.request
from . import media
from .store import atomic_json, digest

DOWNLOAD_HOSTS = {"cmsapi-frontend.naruto-official.com", "media.tenor.com"}


def local_asset(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("Asset path must stay inside the chosen media directory")
    return path


def fetch_assets(plan, root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for asset in plan["assets"]:
        path = local_asset(root, asset["file"])
        if path.exists():
            if digest(path) != asset["sha256"]:
                raise ValueError("Existing asset differs from its source manifest; refusing overwrite")
            continue
        url = asset["download_url"]
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in DOWNLOAD_HOSTS or parsed.username or parsed.password:
            raise ValueError("Download host is not approved; import other permitted media locally")
        with urllib.request.urlopen(url, timeout=30) as response:
            if urllib.parse.urlparse(response.url).hostname not in DOWNLOAD_HOSTS:
                raise ValueError("Unexpected asset redirect")
            data = response.read(20 * 1024 * 1024 + 1)
        if len(data) > 20 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != asset["sha256"]:
            raise ValueError("Downloaded asset size/checksum does not match")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def validated_inputs(plan, root, narration):
    from .media_tools import PRESETS
    if plan.get('enhancement', 'off') not in PRESETS:
        raise ValueError('Unknown enhancement preset')
    if plan.get("schema_version") != 1 or not 1 <= len(plan.get("scenes", [])) <= 30:
        raise ValueError("Invalid edit plan")
    if digest(narration) != plan["narration_sha256"]:
        raise ValueError("Narration changed; do not reuse an unrelated timing plan")
    w, h, fps = plan.get("width", 720), plan.get("height", 1280), plan.get("fps", 30)
    if w not in {360, 720, 1080} or w * 16 != h * 9 or fps not in {24, 30}:
        raise ValueError("Unsupported vertical profile")
    assets = {}
    credit = plan.get('source_credit', 'SOURCE STILLS: NARUTO OFFICIAL')
    if not isinstance(credit, str) or len(credit) > 70 or any(c in credit for c in '{}<>\\\n\r'):
        raise ValueError('Invalid source credit')
    for asset in plan["assets"]:
        if asset["id"] in assets or asset["type"] not in {"image", "video"}:
            raise ValueError("Invalid or duplicate media asset")
        path = local_asset(root, asset["file"])
        if digest(path) != asset["sha256"] or not asset.get("source_url") or not asset.get("reuse_status"):
            raise ValueError("Asset provenance or checksum missing/changed")
        assets[asset["id"]] = {**asset, "path": path}
    previous = 0.0
    for scene in plan["scenes"]:
        if abs(scene["start"]-previous) > .001 or scene["end"] <= scene["start"]:
            raise ValueError("Scene timings must cover narration contiguously")
        if any(c in scene["text"] + scene["label"] for c in "{}<>\\\n\r"):
            raise ValueError("Subtitle controls are not allowed")
        if not 1 <= len(scene["shots"]) <= 4:
            raise ValueError("Use one to four ordered shots per narration scene")
        for shot in scene["shots"]:
            if shot["asset"] not in assets or not 0 <= shot.get("focus_x", .5) <= 1:
                raise ValueError("Unknown asset or invalid framing")
            if plan.get('video_only') and assets[shot['asset']]['type'] != 'video':
                raise ValueError('Video-only edit cannot include still images')
            if shot.get("fit", "cover") not in {"cover", "contain"}:
                raise ValueError("Unknown framing mode")
            if not shot.get("match_reason"):
                raise ValueError("Every shot must explain its narration match")
        previous = scene["end"]
    if abs(media.duration(narration)-previous) > .1:
        raise ValueError("Scene plan does not cover the actual narration")
    captions = plan.get('caption_segments')
    if captions is not None:
        if not isinstance(captions, list) or not 1 <= len(captions) <= 500:
            raise ValueError('Invalid caption segments')
        last = 0.0
        for caption in captions:
            start, end = caption['start'], caption['end']
            if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in [start, end]):
                raise ValueError('Invalid caption timing')
            if start < last - .001 or end <= start or end > previous + .1:
                raise ValueError('Caption timings must be ordered and inside the narration')
            text = caption['text']
            if not isinstance(text, str) or not 1 <= len(text) <= 180 or any(c in text for c in '{}<>\\\n\r'):
                raise ValueError('Invalid caption text')
            last = end
    return assets, w, h, fps


def write_captions(plan, output, w, h):
    scale = w / 720
    def at(t):
        c=round(t*100)
        return f"{c//360000}:{c//6000%60:02}:{c//100%60:02}.{c%100:02}"
    events, srt = [], []
    for i, scene in enumerate(plan.get('caption_segments', plan['scenes'])):
        caption="\\N".join(textwrap.wrap(scene['text'], width=32))
        if len(caption.split("\\N")) > 4:
            raise ValueError("Caption is too long for the safe area")
        start,end=at(scene["start"]),at(scene["end"])
        events.append(f"Dialogue: 0,{start},{end},Caption,,0,0,0,,{caption}")
        srt.append(f"{i+1}\n{media.timestamp(scene['start'])} --> {media.timestamp(scene['end'])}\n"+caption.replace('\\N','\n')+'\n')
    for scene in plan['scenes']:
        events.append(f"Dialogue: 1,{at(scene['start'])},{at(scene['end'])},Heading,,0,0,0,,{scene['label']}")
    header=(f"[Script Info]\nScriptType: v4.00+\nPlayResX: {w}\nPlayResY: {h}\nWrapStyle: 2\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
    styles=[('Caption',36,'&H00FFFFFF',2,175,1),('Heading',32,'&H0057B4FF',8,135,1),('Brand',22,'&H00FFFFFF',7,62,1),('Credit',15,'&H00CCCCCC',2,65,0)]
    for name,size,color,alignment,margin,bold in styles:
        header+=f"Style: {name},DejaVu Sans,{size*scale:.1f},{color},&H000000FF,&H00111111,&H80000000,{bold},0,0,0,100,100,0,0,1,2,1,{alignment},{int(48*scale)},{int(48*scale)},{int(margin*scale)},1\n"
    total=at(plan['scenes'][-1]['end'])
    events.extend([f"Dialogue: 1,0:00:00.00,{total},Brand,,0,0,0,,IFVERSE ANIME / FAN WHAT-IF",
                   f"Dialogue: 1,0:00:00.00,{total},Credit,,0,0,0,,{plan.get('source_credit', 'SOURCE STILLS: NARUTO OFFICIAL')}"])
    (output/'captions.ass').write_text(header+"\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"+'\n'.join(events)+'\n')
    (output/'captions.srt').write_text('\n'.join(srt))


def render_edit(plan, root, narration, output):
    from .media_tools import PRESETS
    narration = Path(narration).resolve()
    assets,w,h,fps = validated_inputs(plan,root,narration)
    output = Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    if narration.is_relative_to(output):
        raise ValueError("Keep the retained narration outside the render directory")
    write_captions(plan,output,w,h)
    shots=[]
    commands=[]
    direct_inputs=[]
    direct_graphs=[]
    for scene in plan['scenes']:
        count=len(scene['shots'])
        for i,shot in enumerate(scene['shots']):
            start=scene['start']+(scene['end']-scene['start'])*i/count
            end=scene['start']+(scene['end']-scene['start'])*(i+1)/count
            frames=round(end*fps)-round(start*fps)
            if frames<1:raise ValueError("Shot has no frames")
            asset=assets[shot['asset']]
            number=len(shots);name=f'shot-{number:03}.mp4'
            focus=shot.get('focus_x',.5)
            if shot.get('fit','cover')=='contain':
                graph=(f"[0:v]split=2[b][f];[b]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=20:2,eq=brightness=-0.2[b2];"
                       f"[f]scale={w}:{int(h*.73)}:force_original_aspect_ratio=decrease[f2];[b2][f2]overlay=(W-w)/2:(H-h)/2")
            else:
                graph=f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}:x='(iw-ow)*{focus}':y='(ih-oh)*0.45'"
            enhancement = plan.get('enhancement', 'off')
            if enhancement != 'off':
                pre, post = PRESETS[enhancement]
                graph = graph.replace('[0:v]', '[0:v]' + pre)
                graph = graph.replace(':force_original_aspect_ratio=', ':flags=lanczos:force_original_aspect_ratio=') + post
            if asset['type']=='image':
                graph+=f",zoompan=z='min(1.0+on*0.0005,1.08)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={frames}:s={w}x{h}:fps={fps},setsar=1[out]"
                inputs=['-i',str(asset['path'])]
            else:
                trim=shot.get('trim_start',0)
                if trim<0 or media.duration(asset['path'])-trim < frames/fps-.03:
                    raise ValueError('Video excerpt is shorter than the ordered shot')
                inputs=['-ss',str(trim),'-i',str(asset['path'])]
                graph+=f",fps={fps},setpts=PTS-STARTPTS,setsar=1[out]"
            command=[*inputs,'-filter_complex',graph,'-map','[out]','-frames:v',str(frames),'-an',
                     '-c:v','libx264','-threads','2','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',name]
            if plan.get('single_pass'):
                direct_inputs.extend(['-threads','1',*inputs])
                direct=graph.replace('[0:v]',f'[{number}:v]')
                for label in ['b','f','b2','f2']:
                    direct=direct.replace(f'[{label}]',f'[{label}_{number}]')
                direct=direct.replace('[out]',f',trim=end_frame={frames},setpts=PTS-STARTPTS[v{number}]')
                direct_graphs.append(direct)
            else:
                media.ffmpeg(command,output)
                commands.append(command)
                video=next(s for s in media.probe(output/name)['streams'] if s['codec_type']=='video')
                if int(video.get('nb_frames',0))!=frames:raise ValueError('Incomplete ordered shot')
            shots.append({**shot,'file':name,'start':start,'end':end,'frames':frames})
    # Recheck every local file immediately before concatenation. A successful
    # command and earlier probe do not establish that the file is still valid.
    # Repair a deterministic local shot once, then fail closed if still invalid.
    repaired=[]
    for i,shot in enumerate([] if plan.get('single_pass') else shots):
        def complete():
            try:
                v=next(s for s in media.probe(output/shot['file'])['streams'] if s['codec_type']=='video')
                return int(v.get('nb_frames',0))==shot['frames'] and abs(float(v.get('duration',0))-shot['frames']/fps)<1/fps
            except (RuntimeError,ValueError,StopIteration,KeyError):return False
        if not complete():
            media.ffmpeg(commands[i],output)
            repaired.append(shot['file'])
            if not complete():raise ValueError('Shot repair failed; refusing a partial edit')
    (output/'shots.txt').write_text('\n'.join("file '"+s['file']+"'" for s in shots))
    total=plan['scenes'][-1]['end']
    encoding=['-af','alimiter=limit=0.89','-t',str(total),'-c:v','libx264','-threads','2','-preset','veryfast',
              '-crf','21','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart','video.mp4']
    if plan.get('single_pass'):
        direct_graphs.append(''.join(f'[v{i}]' for i in range(len(shots)))+f'concat=n={len(shots)}:v=1:a=0,ass=captions.ass[edited]')
        media.ffmpeg(['-filter_complex_threads','1',*direct_inputs,'-i',str(narration),
                      '-filter_complex',';'.join(direct_graphs),'-map','[edited]','-map',f'{len(shots)}:a',*encoding],output)
    else:
        media.ffmpeg(['-f','concat','-safe','1','-i','shots.txt','-i',str(narration),'-vf','ass=captions.ass',*encoding],output)
    info=media.probe(output/'video.mp4')
    video=next(s for s in info['streams'] if s['codec_type']=='video')
    audio=next(s for s in info['streams'] if s['codec_type']=='audio')
    checks={'resolution':(video['width'],video['height'])==(w,h),'codec':video['codec_name']=='h264' and audio['codec_name']=='aac',
            'video_covers_speech':abs(float(video['duration'])-total)<.1,'audio_covers_speech':abs(float(audio['duration'])-total)<.1,
            'narration_unchanged':digest(narration)==plan['narration_sha256']}
    media.command(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(output/'video.mp4'),'-f','null','-'])
    report={'automated_pass':all(checks.values()),'checks':checks,'duration_seconds':float(info['format']['duration']),
            'shots':len(shots),'image_shots':sum(assets[s['asset']]['type']=='image' for s in shots),
            'video_shots':sum(assets[s['asset']]['type']=='video' for s in shots),'sha256':digest(output/'video.mp4'),
            'video_only':all(assets[s['asset']]['type']=='video' for s in shots),
            'single_pass':bool(plan.get('single_pass')),
            'enhancement':plan.get('enhancement', 'off'),
            'repaired_local_shots':repaired,
            'publishing_enabled':False,'rights_review':'Source permissions not verified; commentary review cut',
            'caption_timing':'Original measured narration scene boundaries; not word-aligned'}
    atomic_json(output/'quality.json',report)
    atomic_json(output/'edit.json',{'schema_version':1,'shots':shots,'assets':plan['assets'],'narration_sha256':plan['narration_sha256']})
    if not report['automated_pass']:raise ValueError('Imported-media edit failed validation')
    return output/'video.mp4'


def main():
    parser=argparse.ArgumentParser(description='Render an ordered media cut against existing narration')
    parser.add_argument('plan')
    parser.add_argument('--assets-root',required=True)
    parser.add_argument('--narration')
    parser.add_argument('--output')
    parser.add_argument('--fetch',action='store_true',help='Download checksum-pinned media from the approved hosts')
    args=parser.parse_args()
    plan=json.loads(Path(args.plan).read_text())
    if args.fetch:fetch_assets(plan,args.assets_root)
    if args.output:
        if not args.narration:parser.error('--narration is required for rendering')
        print(render_edit(plan,args.assets_root,args.narration,args.output))


if __name__=='__main__':main()
