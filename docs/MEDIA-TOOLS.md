# Reusable media tools

Use these tools before ad-hoc web scripting or repeated downloads. They are project code, callable from a terminal, a replacement agent, or the GitHub workflow. No model API calls are made by the tools.

## Quick commands

Install Python 3.12+, FFmpeg/ffprobe and DejaVu Sans. The optional YouTube downloader is pinned in requirements-media.txt:

```sh
python -m pip install -r requirements-media.txt
python -m whatif.media_tools find "Naruto running"
python -m whatif.media_tools search "Naruto official trailer" --provider youtube --limit 3
python -m whatif.media_tools collect "Naruto running" --provider tenor --limit 3
python -m whatif.media_tools enhance INPUT.mp4 NEW_OUTPUT.mp4 --preset anime-light --height 720
python -m whatif.media_tools build media-stories/STORY.json --narration PRIVATE.wav --output private/review/NEW_VERSION --download
```

Use --bank /persistent/private/media-bank **before** the subcommand to choose shared durable storage. Default: ignored private/media-bank. Linux/WSL is supported; the catalog uses an OS process lock. Private bank data is separate from Git and needs its own backup. An ephemeral cloud task does not make the cache permanent.

Every command returns compact JSON and exits 2 for a blocked/partial result. Read the short result first. Do not repeat searches/downloads on a blocked result without diagnosing the actual source once. No login, browser cookies or machine yt-dlp configuration is loaded.

## What is cached and bounded

- Successful keyword searches persist until --refresh. Failed searches and failed source downloads have a 30-minute cooldown.
- Verified videos are stored once by SHA-256, with labels, source, publisher/uploader, reuse status, dimensions and duration. Repeated collect calls verify/reuse the catalog before any network request.
- Defaults: three search candidates, one downloaded clip per label, a 360-pixel minimum height, at most six labels/two clips per label, 100 MiB per source and 180 seconds per source. Choose --min-height 720 for stricter acquisition or 144 to deliberately allow low-resolution sources.
- Search/download retries are disabled; subprocesses have timeouts and batches have a 180-second soft deadline checked between sources. A current direct HTTP transfer may finish after that deadline, bounded by its socket timeout and byte cap.
- A download exit code does not prove a video exists: ffprobe validates actual video/duration/dimensions before catalog insertion. Error HTML never becomes a successful video entry.
- build uses recorded labels to create an editable plan and the existing single-pass renderer. It retains narration, checks the complete output, and caches successful results keyed by inputs, sources and renderer/tool code. A changed/corrupt cached result is rejected.
- Label matching is lexical, not a trained understanding of an anime plot. Inspect the draft for relevance; automated checks do not give editorial or publication approval.

Import an already-downloaded source with provenance:

```sh
python -m whatif.media_tools import CLIP.mp4 --label "Naruto running" \
  --source-url https://tenor.com/view/ACTUAL_POST \
  --reuse-status "Actual usage basis or unverified review-draft status"
```

The scene-story schema is described in media-stories/README.md. Each scene has one to four visual_queries. Exact labels take priority, and an excerpt must be long enough. Low-resolution sources use the frame-preserving contain layout automatically when a portrait fill would require more than 2x enlargement. The original manually reviewed edit plans remain valid.

## Non-AI enhancement

Presets are off, anime-light and clean-light. Light presets use mild hqdn3d denoising, Lanczos resizing and restrained luma sharpening. Source colors and native frame rate are retained. The standalone enhancer preserves aspect ratio, checks audio/duration/decode, writes to a new file and refuses to replace originals. Enhancement can also be applied inside the render through the plan's enhancement field, avoiding a separate lossy pre-encode. It may improve perceived cleanliness; it does not restore missing detail or turn a tiny crop into genuine HD. Avoid aggressive automatic contrast, saturation, sharpening or frame interpolation.

## GitHub workflow and assistant entry

.github/workflows/media-tools.yml accepts search, collect, find, enhance, build and preview. It now runs on GitHub-hosted ubuntu-24.04 with a five-minute job limit. No self-hosted runner or owner PC is required for this path. The old self-hosted configuration is historical.

**Agent-triggered route:** commit exactly one unique JSON request under media-requests/ on codex/youtube-oauth, using examples/media-request.json as the data schema. The push runs the workflow from that branch without merging. Inspect the commit's workflow run/jobs and ifverse-media-result artifact before retrying. Requests accept fixed operations/data, never shell commands.

**Manual route:** workflow_dispatch offers the same operations. GitHub first requires the workflow on the default branch for that manual entry; no merge was performed.

The preview operation collects one matching source, repeats collection to measure the verified cache, enhances the clip, and emits compact timing/result JSON. It does not generate a new narration or publish anything. Other operations keep their existing bounds. A hosted build still needs its private narration supplied securely; this trial did not set up narration transfer.

Separate GitHub caches preserve the source bank and a checksum-pinned BtbN FFmpeg/ffprobe tool pair. The pinned dated archive is installed by scripts/bootstrap_media_tools.py, verified against its recorded SHA-256, and binaries are verified again before reuse. This avoids repeated apt installations on minimal images. Tool installation has a three-minute step limit. Cache keys include tool/code versions; a source-code change can intentionally invalidate an older footage-cache generation. Cache retention/availability is controlled by GitHub and is not a backup guarantee. The YouTube downloader is optional; this test used Tenor's direct public MP4 sources.

**Measured GitHub result:** run [40491183923](https://github.com/Vpermillion/Content_Creating_WorkFlow/actions/runs/40491183923) succeeded. Job: 36 seconds; full workflow elapsed: 39 seconds. Media work: 3.845 seconds (1.377 collect, 0.002 cached lookup, 2.467 enhance). A 2,308,968-byte, 4.6-second source became a 4,802,868-byte 960x720 review clip. Tooling and footage caches were saved; cross-run restoration has not yet been benchmarked. Zero model calls occurred inside the job. This does not measure this chat's usage percentage, which the agent cannot read. The setup/debugging turn is not a fair estimate of a later steady-state request. Full measurements: artifacts/hosted-media-trial-20261027.json.

An earlier six-second hosted job failed because the image lacked FFmpeg; no source was processed. The pinned installer fixed that prerequisite. A historical invalid workflow was also corrected; actionlint now validates the workflow expression contexts. All 47 local tests pass, including bootstrap checksum/cache confinement and preview cache timing. The separate GitHub Software checks run 40491191629 also completed successfully.

The identical request adapter runs locally:

```sh
python scripts/run_media_workflow.py --request examples/media-request.json
```

Current verification includes live local YouTube/Tenor keyword search, local and GitHub Tenor download/enhancement, verified repeated-lookup reuse, actionlint validation, and 47 passing local tests. This was an on-demand project-tool trial; no public post, OAuth change, recurring job or production deployment occurred.

The installed [Ifverse Media Workflow skill](https://chatgpt.com/skills?skill_id=6ae07b2505b881919bafe480e0d6b819) is a thin instruction layer over this repository. Replacement assistants can use these commands without that personal installation. Source/tool behavior belongs here, so switching assistants does not require rebuilding it. A fixed ChatGPT usage reduction has not been measured.

