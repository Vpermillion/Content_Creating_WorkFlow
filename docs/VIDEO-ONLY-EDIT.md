> Historical record. Read [CURRENT.md](CURRENT.md) for active status and [START_HERE.md](../START_HERE.md) for current task guidance. Earlier branch pointers, runtime checks and action requests below describe their recorded sessions.

# Video-only anime review cut

Recorded 2026-10-27, Asia/Ulaanbaatar. Branch: `codex/youtube-oauth`.

The owner found the first internet-still edit too static and explicitly requested moving internet video clips only, visually tied to narration. Completed a **46.975-second, 720x1280 review cut with 18 ordered video shots from 15 downloaded anime clips and zero still-image shots**. Original narration and measured sentence-caption timing are retained. Native source motion replaces the first cut's simulated image zooms. No generated imagery, game footage or source soundtrack is included.

[Watch the revised video](https://chatgpt.com/library?file_id=libfile_9922c2295e588191b8a12be471c82e88&account_id=personal). Same persistent pilot identity, now `Ifverse_Anime_Video_Only.mp4`, version 2. The original storyboard and still-edit source plans remain preserved. This replaces the still cut as the current review output.

## Sources and editorial plan

`edits/alpha-anime-video.v2.json` records the exact public post/media URLs, uploader/publisher status, SHA-256, excerpt start, framing and narration-match reason for every selected shot. Inputs are MP4 animated excerpts obtained from Tenor; several are from the Naruto Shippuden official partner profile, while the Pain, Team 7 and Sakura excerpts are community posts with uploader/rights status recorded separately. An official-profile label is not a republication license. Source videos are copyrighted and reuse permission remains unverified; this is an original fan-commentary review draft.

The footage shows Naruto, the Nine-Tails, Obito, the Six Paths of Pain, Team 7, Kakashi, Sakura and the threatened Leaf. These canon excerpts illustrate an invented alternate storyline. No existing source scene is represented as Naruto literally joining Akatsuki or making the invented deal. Repeated sources use short excerpts to return to the opposing choices. Canon imagery cannot literally show every hypothetical action.

The official Road of Naruto YouTube metadata was readable, but attempted media downloads produced 195-byte HTML error pages despite a success report. ffprobe rejected them and they were not used. Public Steam trailer downloads were also explored, but none is in this edit. No sign-in, restricted stream, DRM removal or account operation was used.

## Reproduce

Privately restore the original matching narration; its SHA-256 is pinned in the plan. Do not regenerate narration merely to edit visuals.

```sh
python -m whatif.media_edit edits/alpha-anime-video.v2.json \
  --assets-root private/moving-edit --fetch \
  --narration /path/to/alpha-anime-001/narration.wav \
  --output private/moving-edit/render-v2-final
```

The plan sets `video_only: true`, which rejects any still-image shot, and `single_pass: true`, which frames, trims and assembles the source excerpts in one FFmpeg process without intermediate MP4 dependencies. Local source audio is omitted; the unchanged narration receives the existing limiter. The downloader permits only the recorded approved hosts and requires exact bytes/checksums. Source availability can change; a changed checksum stops reproduction and needs a deliberate new asset/version review. Original private audio/database backup across hosts is still unverified.

The standalone edit CLI does not read/write job stages, alter publication state or initialize a new job database. In single-pass `edit.json`, shot filenames describe logical clip positions only; no intermediate MP4s are created. The source plan, not those logical intermediate names, is the reproduction input.

## Checks and result

All **33 unit/integration tests pass**, including complete single-pass video/audio tracks, absence of intermediate MP4s, mixed import rendering, explicit video-only enforcement, subtitle-credit validation and prior OAuth/state/media regressions. No Google authorization was exercised.

Final output fully decodes. Video track: 46.966667 seconds and 1,409 frames; narration/audio: 46.975 seconds. Resolution/codecs are 720x1280, H.264/AAC. Output size: 8,828,870 bytes. SHA-256: `ab34a0d875bd719503d0b8b085f26ef6d47922abb2414674a5c8acd3bfa65d1c`.

A frame from the middle of every shot was inspected for framing/captions, including the final scene. All 18 selected source excerpts show pixel changes in a 6 fps grayscale sample; see `artifacts/alpha-anime-video-v2.motion.json`. This supports observed source movement, not semantic accuracy or a guarantee of motion in every anime frame. Full listening/pronunciation/editorial review remains pending. Captions remain measured narration segments, not word-aligned karaoke captions.

The first multi-file assembly was rejected for a short video track after intermediate corruption. The cause was not established. The single-pass renderer avoids those intermediates and passed complete final-track/decode validation. No invalid file was saved over the user's video.

No public upload, OAuth/channel binding, account recovery, merge or purchase occurred. The owner will explain their connection fix later; preserve that context and continue from the current editorial cut.


