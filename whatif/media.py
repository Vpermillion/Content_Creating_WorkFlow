"""Deterministic local media worker; all tool invocations use argument arrays."""
import html
import json
import math
import re
import subprocess
import textwrap
from pathlib import Path
from .store import atomic_json, digest


def command(args, cwd=None, timeout=300):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'{args[0]} exited {result.returncode}: {result.stderr[-2500:]}')
    return result


def ffmpeg(args, cwd):
    return command(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                    "-threads", "2", "-filter_threads", "1", *args], cwd)


def probe(path):
    return json.loads(command(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]).stdout)


def duration(path):
    return float(probe(path)["format"]["duration"])


def diagram(scene, index, count, title):
    """Original vector diagrams. No downloaded photography or implied real footage."""
    kind = scene["visual"]
    if kind not in {"earth-moon", "earth-alone", "tides", "rotation", "day-night", "sun", "light-delay", "orbit", "freeze"}:
        raise ValueError("Unsupported original diagram kind")
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="720" height="1280" viewBox="0 0 720 1280">',
           '<rect width="720" height="1280" fill="#0b1325"/>']
    for i in range(45):
        x, y = (i*197+31) % 700+10, (i*103+17) % 950+130
        svg.append(f'<circle cx="{x}" cy="{y}" r="1.5" fill="#7387a0"/>')
    def txt(y, text, size=26, color="#edf4ff"):
        svg.append(f'<text x="60" y="{y}" font-family="DejaVu Sans" font-size="{size}" fill="{color}">{html.escape(text)}</text>')
    txt(90, "WHAT IF / SCIENCE NOTES", 20, "#7dd3fc")
    for j, line in enumerate(textwrap.wrap(title.upper(), width=24)):
        txt(190+j*52, line, 38)
    txt(370, scene["label"], 25, "#fbbf24")
    earth = '<circle cx="360" cy="625" r="130" fill="#227da5"/><path d="M300 517L356 535 340 587 385 616 370 668 315 699 295 632 250 605Z" fill="#5ee0ad"/>'
    if kind in {"earth-moon", "earth-alone", "tides", "rotation", "day-night", "orbit", "freeze"}:
        svg.append('<ellipse cx="360" cy="625" rx="275" ry="190" fill="none" stroke="#2d455d" stroke-width="3" stroke-dasharray="8 8"/>')
        svg.append(earth)
    if kind == "earth-moon":
        svg.append('<circle cx="610" cy="490" r="36" fill="#cbd5e1"/>')
    if kind == "earth-alone":
        svg.append('<circle cx="610" cy="490" r="36" fill="none" stroke="#fbbf24" stroke-dasharray="4 5"/>')
    if kind == "tides":
        svg.append('<ellipse cx="360" cy="625" rx="175" ry="145" fill="none" stroke="#7dd3fc" stroke-width="7"/>')
    if kind in {"rotation", "day-night"}:
        svg.append('<path d="M180 590 A190 190 0 0 1 530 550L520 520M530 550L495 549" fill="none" stroke="#fbbf24" stroke-width="8"/>')
        svg.append('<path d="M360 495 A130 130 0 0 1 360 755Z" fill="#071124" opacity="0.7"/>')
    if kind in {"sun", "light-delay"}:
        svg.append('<circle cx="190" cy="620" r="95" fill="#fbbf24"/><circle cx="550" cy="620" r="58" fill="#227da5"/><path d="M310 620H460" stroke="#7dd3fc" stroke-width="5" stroke-dasharray="12 10"/>')
    if kind == "freeze":
        svg.append('<path d="M360 510V740M255 560L460 690M255 690L460 560" stroke="#ccefff" stroke-width="9"/>')
    txt(885, "ILLUSTRATIVE DIAGRAM / NOT TO SCALE", 18, "#91a3bb")
    txt(1140, "PROVISIONAL PILOT / REVIEW REQUIRED", 17, "#91a3bb")
    svg.append(f'<rect x="60" y="1190" width="{600*(index+1)/count}" height="5" fill="#7dd3fc"/>')
    svg.append('</svg>')
    return "\n".join(svg)


def assets(spec, folder):
    records, files = [], []
    for i, scene in enumerate(spec["scenes"]):
        path = folder / f"scene-{i:02}.svg"
        path.write_text(diagram(scene, i, len(spec["scenes"]), spec["title"]))
        files.append(path)
        records.append({"id":f"scene-{i:02}", "path":path.name, "scene":i, "creator":"What If workspace procedural renderer",
                        "source_url":None, "usage_basis":"Original procedural diagram created by this workspace",
                        "license":"User project original graphic; no third-party stock", "attribution_required":False,
                        "illustrative":True, "sha256":digest(path)})
    manifest = folder / "assets.json"
    atomic_json(manifest, {"schema_version":1, "assets":records})
    return [manifest, *files]


def narration(spec, folder):
    files, segments = [], []
    cursor = 0.0
    for i, scene in enumerate(spec["scenes"]):
        text, wav = folder / f"speech-{i:02}.txt", folder / f"speech-{i:02}.wav"
        text.write_text(scene["text"])
        # The filter contains generated names only, never user-supplied text or paths.
        ffmpeg(["-f", "lavfi", "-i", f"flite=textfile={text.name}:voice=slt", "-ar", "48000", "-ac", "1", wav.name], folder)
        length = duration(wav)
        if not 0.2 < length < 25:
            raise ValueError("Unexpected narration segment duration")
        segments.append({"scene":i, "text":scene["text"], "start":cursor, "end":cursor+length, "file":wav.name})
        cursor += length
        files.extend([text, wav])
    (folder / "audio-concat.txt").write_text("\n".join(f"file 'speech-{i:02}.wav'" for i in range(len(segments))))
    ffmpeg(["-f", "concat", "-safe", "1", "-i", "audio-concat.txt", "-c:a", "pcm_s16le", "narration.wav"], folder)
    manifest = folder / "narration.json"
    atomic_json(manifest, {"schema_version":1, "provider":"ffmpeg-libflite", "voice":"slt", "prototype":True,
                          "timing_basis":"Exact boundaries of separately synthesized sentence/scene WAVs; not word alignment",
                          "duration":cursor, "segments":segments, "sha256":digest(folder/"narration.wav")})
    return [*files, manifest, folder/"narration.wav"]


def timestamp(seconds):
    ms = round(seconds*1000)
    return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"


def captions(folder):
    data = json.loads((folder/"narration.json").read_text())
    rows, events = [], []
    def ass_time(seconds):
        cs=round(seconds*100)
        return f"{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}"
    for i, segment in enumerate(data["segments"]):
        text = "\n".join(textwrap.wrap(segment["text"], width=36))
        if len(text.splitlines()) > 4:
            raise ValueError("Caption too long; shorten the scene or split at sentence boundaries")
        rows.append(f'{i+1}\n{timestamp(segment["start"])} --> {timestamp(segment["end"])}\n{text}\n')
        ass_text=text.replace("\n", "\\N")
        events.append(f'Dialogue: 0,{ass_time(segment["start"])},{ass_time(segment["end"])},Default,,0,0,0,,{ass_text}')
    path = folder / "captions.srt"
    path.write_text("\n".join(rows))
    # Explicit play resolution avoids libass rescaling an SRT default 384x288 canvas.
    ass=folder/"captions.ass"
    ass.write_text("[Script Info]\nScriptType: v4.00+\nPlayResX: 720\nPlayResY: 1280\nWrapStyle: 2\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,DejaVu Sans,30,&H00FFFFFF,&H000000FF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,70,90,190,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"+"\n".join(events)+"\n")
    return [path, ass]


def render(spec, folder):
    profile = spec["profile"]
    w, h, fps = profile["width"], profile["height"], profile["fps"]
    narration_data = json.loads((folder/"narration.json").read_text())
    records = []
    for i, segment in enumerate(narration_data["segments"]):
        length = segment["end"]-segment["start"]
        name = f"clip-{i:02}.mp4"
        # SVG is authored locally. Modest zoom is centered; captions are added afterwards.
        frames = math.ceil(length*fps)
        vf = f"scale={w}:{h},zoompan=z='min(zoom+0.00015,1.04)':d={frames}:s={w}x{h}:fps={fps},setsar=1"
        ffmpeg(["-i", f"scene-{i:02}.svg", "-vf", vf, "-t", f"{length:.6f}", "-an", "-c:v", "libx264",
                "-threads", "2", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", name], folder)
        records.append({"scene":i,"duration":length,"visual":f"scene-{i:02}.svg","audio":segment.get("file","narration.wav"),
                        "audio_start":segment["start"],"clip":name})
    (folder/"video-concat.txt").write_text("\n".join(f"file 'clip-{i:02}.mp4'" for i in range(len(records))))
    ffmpeg(["-f", "concat", "-safe", "1", "-i", "video-concat.txt", "-i", "narration.wav", "-vf",
            "ass=captions.ass",
            "-af", "alimiter=limit=0.89", "-t", str(narration_data["duration"]), "-c:v", "libx264", "-threads", "2",
            "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", "video.mp4"], folder)
    manifest = folder/"edit.json"
    atomic_json(manifest, {"schema_version":1,"job_id":spec["id"],"profile":profile,"scenes":records,
                          "caption_file":"captions.srt","narration":"narration.wav","music":None,"sound_effects":[],
                          "renderer":"ffmpeg/libx264; cuts, center zoom, sentence captions, limited narration",
                          "output":"video.mp4","sha256":digest(folder/"video.mp4")})
    return [manifest, folder/"video.mp4"]


def validate_output(spec, folder):
    info = probe(folder/"video.mp4")
    streams = info["streams"]
    video = next(s for s in streams if s["codec_type"] == "video")
    audio = next(s for s in streams if s["codec_type"] == "audio")
    narr = json.loads((folder/"narration.json").read_text())
    actual = float(info["format"]["duration"])
    analysis = command(["ffmpeg","-nostdin","-v","info","-i",str(folder/"video.mp4"),"-af","volumedetect","-vn","-f","null","-"], timeout=120)
    peak = re.search(r'max_volume: ([-\d.]+) dB', analysis.stderr)
    checks = {"resolution":(video["width"],video["height"]) == (spec["profile"]["width"],spec["profile"]["height"]),
              "aspect_9_16":video["width"]*16 == video["height"]*9,
              "codec_h264_aac":video["codec_name"]=="h264" and audio["codec_name"]=="aac",
              "pixel_format":video["pix_fmt"]=="yuv420p", "audio_present":float(audio.get("duration",0))>0,
              "duration_matches_speech":abs(actual-narr["duration"])<0.2,
              "provisional_length_range":spec["profile"]["min_seconds"] <= actual <= spec["profile"]["max_seconds"],
              "sentence_caption_coverage":abs(narr["segments"][-1]["end"]-actual)<0.2,
              "peak_below_zero": bool(peak) and float(peak[1])<0,
              "all_scene_assets_exist":all((folder/f"scene-{i:02}.svg").is_file() for i in range(len(spec["scenes"])))}
    # Decode the complete output; a successful mux alone is not sufficient.
    command(["ffmpeg","-nostdin","-v","error","-xerror","-i",str(folder/"video.mp4"),"-f","null","-"],timeout=180)
    report = {"schema_version":1,"job_id":spec["id"],"automated_pass":all(checks.values()),"checks":checks,
              "duration_seconds":actual,"peak_dbfs":float(peak[1]) if peak else None,
              "output_sha256":digest(folder/"video.mp4"),"human_review":{
                  "visual":"pending","audible":"pending","pronunciation":"pending","factual":"pending",
                  "platform_safe_areas":"pending; provisional 720x1280 layout"},
              "publish_ready":False,"limitations":["Synthetic prototype voice; sentence boundaries only",
                  "Original illustrative diagrams; not documentary footage","Sources and narration need editorial approval"]}
    atomic_json(folder/"quality.json", report)
    if not report["automated_pass"]:
        raise ValueError("Media validation failed: "+str([k for k,v in checks.items() if not v]))
    return [folder/"quality.json"]
