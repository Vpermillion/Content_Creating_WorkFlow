# Start here: Ifverse project handoff

**Current audio request:** [voice choices](docs/VOICE_OPTIONS.md) and actual DubbingAI meme clips. The article is readable; its separate audio host needs the saved network-domain addition applied before download and a new sound cut. See [CURRENT](docs/CURRENT.md).

**Script tone:** follow [the owner-approved style addon](prompts/script-style.md): frequent creative roasts, playful trash talk, Gen Z/millennial slang and streetwise banter throughout the narration, with varied comparisons and callbacks. Swearing remains occasional and light. This applies to both English channels. Sound design now supports described downloadable effects on specific joke/reaction anchors; see [SOUND_EFFECTS](docs/SOUND_EFFECTS.md).

This repository is the durable workspace for **ifverse_anime** and **ifverse_hollywood**, initially English YouTube what-if videos. The user owns the project; a new authorized assistant must resume it without requiring the old conversation or rebuilding working tools.

## Find the current implementation first

**Current development branch: [`codex/ifverse-workflow`](https://github.com/Vpermillion/Content_Creating_WorkFlow/tree/codex/ifverse-workflow).** The default branch `codex/portable-workspace` retains older application code and now carries this routing guide. Its old source does not describe everything implemented on the current branch. Do not repeat the earlier mistake of declaring a feature absent after inspecting only that old checkout.

Use the existing task checkout. Inspect changes before selecting another branch, preserve local work, and never force-reset, implicitly merge historical branches, or create a worktree unless the user asks. A GitHub-only assistant should read files on the named current branch. See [docs/CURRENT.md](docs/CURRENT.md) for the latest result rather than relying on a branch name or the date of an old report.

Read in this order:

1. This guide and [docs/CURRENT.md](docs/CURRENT.md): purpose, branch, latest output and exact next action.
2. [README.md](README.md): architecture and capabilities.
3. [docs/NEW_AGENT_PROMPT.md](docs/NEW_AGENT_PROMPT.md): reusable resumption instructions.
4. [docs/PROJECT_HISTORY.md](docs/PROJECT_HISTORY.md): how decisions and implementation changed.
5. For code changes, read the relevant current-branch [media tools guide](https://github.com/Vpermillion/Content_Creating_WorkFlow/blob/codex/ifverse-workflow/docs/MEDIA-TOOLS.md), [product brief](https://github.com/Vpermillion/Content_Creating_WorkFlow/blob/codex/ifverse-workflow/docs/IFVERSE_BRIEF.md), and [test-video record](https://github.com/Vpermillion/Content_Creating_WorkFlow/blob/codex/ifverse-workflow/docs/TEST_VIDEO.md). Load the original master prompt or detailed histories only when needed; their older channel plans are superseded.

## What the user wants

The assistant prepares **one script/production plan**, submits **one finite GitHub job**, and reviews **one compact result**. Software handles cache lookup, footage search/download, cleanup, narration, caption timing, ordered editing, validation and output preservation. Repeated per-clip tool calls, log inspection and model-led editing waste the user's allowance. Planning, dispatch, diagnosis and review still consume it; never promise a percentage reduction or claim to read the allowance meter.

Footage should **visually explain the specific words**: named characters, actions, threats, locations and alternatives. Prefer moving online clips. A broad keyword match, a moving MP4 or passing FFmpeg checks does not establish narrative relevance. The assistant should prepare concrete shot reasons and timing anchors, then let the renderer execute them. Where a hypothetical has no literal existing scene, use a relevant illustrative shot and acknowledge that distinction instead of claiming the invented event occurred in canon.

Current scope is two English channels: `ifverse_anime` and `ifverse_hollywood`. Earlier science pilots, seven-account plans, cartoon/Marvel rollout and other platforms are historical. Channel names and saved profiles do not establish created channels, verified handles or live authorization. Keep each channel's topics, styles, outputs and state separate.

## What already works

**Latest completed review:** the **60-second Naruto cut with nine timed sound effects**, 24 moving shots and 50 retained caption phrases, hosted run `41199650499`. Result branch `codex/results/ifverse-anime-sfx-review-01`. Original speech/captions and the SFX-stage picture stream were verified unchanged; all nine cue additions, full decoding and numeric levels passed. The clean cut remains preserved. Read CURRENT and SOUND_EFFECTS for actual receipts and listening-review limits.

- `whatif/media_tools.py`: Tenor/optional YouTube discovery, bounded verified downloads, labeled clip bank, cache reuse, short JSON results and mild FFmpeg enhancement.
- `whatif/media_edit.py`: selected moving clips, ordered single-pass H.264/AAC rendering, source trimming, full-frame containment, subtitles, complete stream/decode validation, and explicit per-shot narration-beat boundaries. Legacy equal scene splits remain supported.
- `scripts/render_test_video.py`: finite anime review runner with validated repository script/plan intake and new/reused Kokoro-ONNX `af_heart` English CPU narration and faster-whisper CPU/int8 phrase captions (`tiny.en` recognition or `base.en` known-script forced alignment). Recognition spelling corrections retain raw words and original timestamps. Known audio/captions are checksum-verified and reused.
- The prior delivered test is **44.672 seconds, 18 moving shots, 27 caption phrases**. Its completed output is on `codex/ifverse-test-result-20261029-04`, hosted run `40846229359`. This is actual tested work, not a design proposal.
- `whatif/audio_fx.py`: searchable described/tagged public-domain effect catalog, source checksum cache, spoken-phrase anchors, fades, pitch/sub-bass treatment, speech ducking and a video-copy mix. The hosted review request can supply `sound_effects_plan`; see [SOUND_EFFECTS](docs/SOUND_EFFECTS.md).
- `.github/workflows/review-video.yml` is the current finite review entry. A commit changing **exactly one** `review-requests/*.json` on `codex/ifverse-workflow` triggers it. It preserves output on `codex/results/<request-id>` and as the `ifverse-review-video` GitHub artifact. Documentation-only commits do not start rendering.

## Commands and request format

From the repository root on the current branch:

```sh
python -m unittest discover -s tests -v
python -m whatif.media_tools find "Naruto protects friends"
python -m whatif.media_tools collect "Naruto protects friends" --provider tenor --limit 3
python scripts/render_test_video.py --request review-requests/ifverse-anime-visual-match-20261030-01.json --output private/review-video/output --models private/test-video/models
```

The last command requires a fresh output directory and available source/model access; do not rerun it merely to see the existing video. Read its completed result first. FFmpeg/ffprobe, DejaVu Sans and Python 3.12+ are prerequisites; `requirements-test-video.txt` pins the speech/caption packages. The GitHub workflow installs its own prerequisites and caches verified sources/models. n8n/Docker are optional older coordination/development paths; the user's PC need not remain on for a GitHub-hosted review job.

A review request contains `schema_version`, a unique `id`, `channel`, `voice`, `edit_plan`, `result_branch: codex/results/<id>`, optional `script` under `pilots/`, and optional `reuse_narration_from` / `reuse_transcription_from` pointing to matching non-secret test artifacts. The runner accepts an optional `script` path under `pilots/` and checks its ordered scene text against the supplied edit plan. It is **not** a finished arbitrary-plain-script product. A new story needs validated script/profile input, an actual matching shot plan, fresh version IDs and correct speech/caption timing. Never quietly substitute another story's audio.

For newly generated speech with a known script, use `caption_mode: "script_alignment"` and `caption_model: "base.en"` to retain exact script words while estimating their times against the final waveform. Recognition modes `whole_audio` / `narration_scenes` and model `tiny.en` remain available for existing requests; the roast recognition drafts changed words and were not accepted. Alignment is not an independent speech-recognition score. Preserve receipts and inspect caption timing. If only visuals change, reuse the verified completed transcription instead of recomputing it.

When a source request is pushed, record its ID/commit/expected result branch. Read the final `result.json` once, inspect logs for failures, and reconcile a previous attempt before issuing another. Exit status, metadata and output must agree. A valid cached completed video should be reused. GitHub caches are conveniences, not durable private backups.

## Remaining work and limits

The Naruto tests are integrated and bounded repository script intake is implemented; free-form story intake, stronger automatic semantic footage matching, automatic quality decisions and Hollywood branding/generalization remain. Clip-label search is lexical. Current enhancement is mild denoise/resize/sharpen, not restoration of absent detail. CPU speech/caption generation has run; Kaggle remains an unexecuted optional batch template. Word timestamps are recognition estimates, not guaranteed forced alignment.

YouTube OAuth tooling exists on the current branch, but no live channel binding or public upload was verified in this task. Do not resume old login/recovery attempts or publish just because a video renders. Inspect current connections by names/status and test authorized operations; personal plugins, skills and credentials do not automatically transfer between accounts. Git read/push proxy access does not prove GitHub API/CLI access. Never extract proxy-held credentials or ask for a token only because a CLI login is missing.

Keep actual tokens, OAuth files, account addresses/passwords, databases and private real-user media out of Git. The source PDF includes account information and must not be committed. Committed generated narration/video here is explicitly non-secret fictional review material; production/private media needs separately configured storage. Preserve original assets and approved narration. Human listening, meaning, source-use and platform review are separate from automated file checks. No public posting, purchases, new accounts, continuous production host or recurring scheduler is authorized by this guide.

Before ending substantial work, update `docs/CURRENT.md`, `PROJECT_STATE.md`, `HANDOFF.md` and `BACKLOG.md`, record passed/failed/unrun checks accurately, and save authorized source changes remotely. Preserve all prior user work and result versions. Each replacement agent should continue from this checkpoint, not recreate the project from the original chat.
