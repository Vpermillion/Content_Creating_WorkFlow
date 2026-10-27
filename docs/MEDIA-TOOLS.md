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

.github/workflows/media-tools.yml accepts search, collect, find, enhance and build. It is on-demand, uses a user-owned self-hosted Linux x64 runner labeled ifverse-media, serializes bank access and has a ten-minute job timeout. No scheduler, Google account connection, paid provider or public upload is configured.

**Agent-triggered route:** commit exactly one unique JSON request under media-requests/ on codex/youtube-oauth. Copy the data structure in examples/media-request.json. The push event runs the workflow from that branch, so this route does not require merging the entire feature branch into the default branch. Record the request intent/commit; inspect that commit's workflow run and its ifverse-media-result artifact before retrying. Requests accept fixed operations/data, never shell commands.

**Manual route:** workflow_dispatch provides the same input fields. GitHub must first know the workflow on the default branch for this manual entry. No merge was performed.

Runner prerequisites: current GitHub Actions runner (compatible with the pinned official v7 actions), Python 3.12 with venv, FFmpeg/ffprobe and fonts. Set repository variable IFVERSE_MEDIA_BANK to a persistent private path if desired; default cache is outside the cleaned checkout. For build, set IFVERSE_NARRATION_PATH to the matching private WAV on that runner. A build request supplies story_path under media-stories/ and may set download: true. Enhance requests supply an asset_id returned by find/collect. Do not commit secrets or narration tokens. Output artifacts contain compact results and generated review outputs, not the whole source bank.

The identical request adapter runs locally:

```sh
python scripts/run_media_workflow.py --request examples/media-request.json
```

Current verification: real Tenor keyword search/download succeeded; the repeated collection returned cached. A real 4.6-second clip was enhanced from 640x480 to 960x720 while retaining duration/no-audio status; a rendered frame was inspected. All 43 tests passed, including bogus-download rejection, repeat-download prevention, enhancement audio/duration, cached rendering, request path confinement and the existing media/OAuth/state tests. Workflow YAML/triggers were checked locally. A successful GitHub Actions request execution or online self-hosted runner has **not** been verified. A live YouTube keyword search also returned a VIZ trailer candidate; YouTube media downloading was not reverified and must not be inferred from search metadata.

The installed [Ifverse Media Workflow skill](https://chatgpt.com/skills?skill_id=6ae07b2505b881919bafe480e0d6b819) is a thin instruction layer over this repository. Replacement assistants can use these commands without that personal installation. Source/tool behavior belongs here, so switching assistants does not require rebuilding it. A fixed ChatGPT usage reduction has not been measured.

