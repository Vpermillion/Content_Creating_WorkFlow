# Script-timed comedy sound effects

Use the current implementation on `codex/ifverse-workflow`. The owner requested downloadable modern meme-style sound effects at specific scripted reactions and punchlines, with reusable descriptions so future agents can choose suitable sounds. The user’s example describes **question → roast → impact → comeback** timing. Write playful clean dialogue consistent with `prompts/script-style.md`.

The first test overlays the existing 60-second Naruto roast. It preserves its original generated speech, 24-shot picture edit and 50 caption phrases. This audio-edit test does not claim that the older narration was rewritten for the later, denser v2 comedy preference. See CURRENT for actual completion/review status before rerunning.

Completed request `ifverse-anime-sfx-review-01`, hosted run `41199650499`: [watch the nine-cue test](https://github.com/Vpermillion/Content_Creating_WorkFlow/blob/codex/results/ifverse-anime-sfx-review-01/artifacts/ifverse-anime-sfx-review-01/sound-effects/video-sfx.mp4). All 74 final-source local tests passed; the demonstrated hosted run passed its then-current 73 regression tests and final media checks. Local final decode, cue-energy, preserved-input/video-stream and numeric level checks also passed. The final source voice and captions are retained; full listening/editorial approval remains separate.

## Library and selection

`assets/sfx/catalog.json` contains six downloadable Brackeys effects with project-authored descriptions/tags, immutable upstream commit URLs, SHA-256, duration, license and source links. The pinned upstream README explicitly permits everything including commercial use; its LICENSE is the Unlicense/public-domain dedication, preserved in `assets/sfx/BRACKEYS-LICENSE.txt`. The test uses four effect types. These are modern meme-style **editing choices**, not claims to contain the original viral Vine boom, Roblox or movie sound recordings. The bass impact is a downloaded explosion pitched down and reinforced with a decaying 55 Hz sub pulse; the catalog records this derivative treatment.

Search the descriptions and tags:

```sh
python -m whatif.audio_fx search --query 'boom punchline bad decision'
python -m whatif.audio_fx search --query 'confusion error'
```

Selection is lexical lookup plus the assistant's explicit script reasoning; it is not an automated comedy-understanding model. Choose a sound based on the beat's meaning, not just a word like “boom” appearing in the dialogue. Keep the description honest about the actual recording. Future effects can be added with verified source/license/checksum metadata; this downloader currently accepts commit-pinned `raw.githubusercontent.com` sources only.

## Cue timing and mix

A cue references an exact spoken phrase, its `start` or `end`, a small offset, an effect ID, a script-specific reason, a maximum length and a peak level. `anchor.occurrence` is required when the phrase occurs more than once. Cue times come from the retained word/alignment receipt, not guessed reading speed. For retained speech, pin `narration_sha256`; the plan and transcript must match the actual narration hash. For a new script whose voice does not exist yet, omit that field and supply `script_sha256` as SHA-256 of the ordered scene texts joined by a single newline (UTF-8). The hosted runner verifies that ordered script, then binds a copied plan to the final generated waveform before mixing. This keeps a new-script production within one job and preserves the original submitted plan. The standalone mixer requires the final bound waveform hash. Missing/ambiguous phrases, changed audio, excessive gains, path escapes and cues beyond the video are rejected.

Use an impact just after a roast or revelation, an error buzz at a failed plan, a bright ping for sarcastic praise, or a cartoon boing at an absurd payoff. A useful starting density is around six to ten deliberate cues per minute, adjusting to the story rather than filling a quota. Keep sincere stakes and ordinary dialogue clear. For newly generated dialogue, plan a short beat before the comeback when needed; adding effects to retained audio must not silently insert pauses or alter its approved timing.

The mixer downloads/checksums/reuses sources, converts to mono 24 kHz PCM, applies recorded pitch treatment, limits effect duration and peak, fades edges, and smoothly attenuates effects by about 6 dB during detected speech. It adds effects to the retained voice, applies a measured master headroom guard if necessary, and writes a separate mixed waveform and MP4. The MP4 picture stream is copied without re-encoding; the original voice file remains untouched. The mix receipt records cue anchors, exact times, source hashes/licenses, levels, source/mixed output hashes and master gain. Caption timing is unchanged.

## One-command review

Python with NumPy and FFmpeg/ffprobe is sufficient for the sound-only step; `requirements-test-video.txt` also supplies NumPy through the existing speech dependencies.

```sh
python -m whatif.audio_fx mix \
  --video /workspace/Ifverse_Anime_60s_Roast.mp4 \
  --narration artifacts/ifverse-anime-roast-20261030-04/narration.wav \
  --transcript artifacts/ifverse-anime-roast-20261030-04/transcription.json \
  --plan edits/ifverse-anime-roast-sfx-v1.json \
  --output private/sfx-review-new
```

Use a fresh output directory. The portable inputs and source result branch are recorded in CURRENT; the example cloud path is not a claim that every future machine has the old MP4. A production job can instead render its base video and pass it directly to this step.

## Hosted integration

A normal review request can add `sound_effects_plan: edits/ifverse-anime-roast-sfx-v1.json`. `scripts/render_test_video.py` then loads a bounded plan/catalog, renders the base cut, performs the mix and reports the final `sound-effects/video-sfx.mp4` rather than returning the dry cut. The GitHub workflow caches downloaded effects with the existing models/footage. A new script needs a matching plan hash and fresh phrase anchors; unchanged speech/captions should be reused.

First hosted request: `review-requests/ifverse-anime-sfx-review-01.json`; expected result branch `codex/results/ifverse-anime-sfx-review-01`. Read its result before retrying. Documentation-only changes do not dispatch another job.

Automated checks establish file integrity, timing/coverage, unchanged inputs and numeric levels. They do not establish a full listening or editorial judgment; audition the comedy, intelligibility and perceived loudness in the finished video. Keep the original clean cut for comparison and preserve all prior results. This step does not publish to YouTube.
