# Current sound defaults — 2026-11-03

Use `assets/sfx/dubbingai-bank.json` and the saved `assets/sfx/bank/` recordings. All 17 were downloaded, hashed and fully decoded; the download cap is 16 MiB each. The three frozen historical hashes match. No CDN-access blocker remains in this environment. Long music/vocal excerpts need audition; do not assume short-effect content or public-domain rights.

[Corrected ten-video batch](BATCH_61S.md) · [Repair provenance and commands](SOUND_REPAIR_HANDOFF.md). Production defaults select actual recordings and reject legacy cue IDs rather than substitute. Preserve historical plans explicitly; do not use custom bass or Brackeys for these repairs. No music is embedded.

The following records are historical and do not describe the current defaults or bank completion.

# Script-timed comedy sound effects

Use the current implementation on `codex/ifverse-workflow`. The owner requested downloadable modern meme-style sound effects at specific scripted reactions and punchlines, with reusable descriptions so future agents can choose suitable sounds. The user’s example describes **question → roast → impact → comeback** timing. Write playful clean dialogue consistent with `prompts/script-style.md`.

**Latest actual-collection test:** [Goku joins the Avengers with Michael](https://github.com/Vpermillion/Content_Creating_WorkFlow/blob/codex/results/ifverse-michael-goku-avengers-01/artifacts/ifverse-michael-goku-avengers-01/sound-effects/video-sfx.mp4), request `ifverse-michael-goku-avengers-01`, run `41468364961`. It uses the actual Vine Boom, faaah and Rizz recordings at 11 script anchors, fresh voice/alignment and new footage. All 80 local tests and final technical/shot-sample checks passed; listening/editorial approval remains separate. The paragraphs below retain the earlier test history.

The first test overlays the existing 60-second Naruto roast. It preserves its original generated speech, 24-shot picture edit and 50 caption phrases. This audio-edit test does not claim that the older narration was rewritten for the later, denser v2 comedy preference. See CURRENT for actual completion/review status before rerunning.

Completed request `ifverse-anime-sfx-review-01`, hosted run `41199650499`: [watch the nine-cue test](https://github.com/Vpermillion/Content_Creating_WorkFlow/blob/codex/results/ifverse-anime-sfx-review-01/artifacts/ifverse-anime-sfx-review-01/sound-effects/video-sfx.mp4). All 74 final-source local tests passed; the demonstrated hosted run passed its then-current 73 regression tests and final media checks. Local final decode, cue-energy, preserved-input/video-stream and numeric level checks also passed. The final source voice and captions are retained; full listening/editorial approval remains separate.

## Requested DubbingAI collection

The owner asked to use the actual recordings from [this collection](https://dubbingai.io/articles/en/collection/tiktok-meme-sound-effects). The article was read successfully after using an ordinary browser-compatible request header. It lists 17 clips including Vine Boom, Rizz Effect and faaah, and supplies MP3 URLs on **`dvi.dubbingai.io`**. Metadata and project-authored description summaries are saved in `assets/sfx/dubbingai-discovery.json`.

Three selected MP3s have now been acquired, fully decoded and hashed as normal production inputs on the GitHub media runner. The frozen playable catalog is `assets/sfx/dubbingai-verified-catalog.json`; the remaining 14 discovery entries are not claimed downloaded. The legitimate production-source collector preserves partial results, verifies identifying metadata/media bounds, records first-download provenance and produces a review contact sheet. Subsequent mixes require the frozen source hash. The cloud shell's separate `dvi.dubbingai.io` allowlist draft still needs user activation for direct shell access; that does not describe the production runner's own network. Do not use source review as a general-purpose web proxy or claim a preexisting independent checksum/commercial license.

The first useful replacement choices are the real Vine Boom at roast/revelation punchlines and faaah at disbelief/failure beats. Use Rizz Effect only where confidence/romantic swagger fits. The collection also includes music and character dialogue; do not select those arbitrarily, assume all clips are public-domain, or talk over narration with a long vocal/music excerpt. Existing source/usage records must describe what is actually verified.

## New-story source preparation

On `codex/ifverse-workflow`, commit exactly one bounded `source-requests/*.json` to trigger `source-review.yml`. A request contains a unique ID/result branch, up to 16 character-specific footage queries with identifying terms, and up to four known DubbingAI discovery IDs (zero sounds is allowed for a footage-only retry). The collector searches the existing Tenor provider, checks candidate identity metadata/duration/resolution, downloads/probes media, and preserves a contact sheet plus source receipts on `codex/results/<id>`.

Inspect `sources.json` status/errors and the pictures before freezing a final edit plan. Finished acquisitions survive other query failures. Retry missing queries with a new version ID and reuse completed sources/sound hashes; do not re-collect a whole library or treat file presence alone as a successful full request. Register actual audio hashes after the bounded HTTPS first acquisition, then require those hashes for subsequent cache/mix checks. Initial sourcing/review may be a preparation run; once sources are frozen the final voice/alignment/render/SFX production remains one finite review job.

## Library and selection

`assets/sfx/catalog.json` contains six downloadable Brackeys effects with project-authored descriptions/tags, immutable upstream commit URLs, SHA-256, duration, license and source links. The pinned upstream README explicitly permits everything including commercial use; its LICENSE is the Unlicense/public-domain dedication, preserved in `assets/sfx/BRACKEYS-LICENSE.txt`. The test uses four effect types. These are modern meme-style **editing choices**, not claims to contain the original viral Vine boom, Roblox or movie sound recordings. The bass impact is a downloaded explosion pitched down and reinforced with a decaying 55 Hz sub pulse; the catalog records this derivative treatment.

Search the descriptions and tags:

```sh
python -m whatif.audio_fx search --query 'boom punchline bad decision'
python -m whatif.audio_fx search --query 'confusion error'
```

Selection is lexical lookup plus the assistant's explicit script reasoning; it is not an automated comedy-understanding model. Choose a sound based on the beat's meaning, not just a word like “boom” appearing in the dialogue. Keep the description honest about the actual recording. Future effects can be added with verified source/license/checksum metadata; the downloader accepts commit-pinned `raw.githubusercontent.com` sources and the exact published `/cs/YYYYMMDD/id-id.mp3` pattern on `dvi.dubbingai.io`, with a verified SHA-256 required for both. Redirects must remain on the supported source host, and the runtime allowlist still applies.

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
