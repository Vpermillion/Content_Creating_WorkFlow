# Ifverse automated video workspace

**Script tone:** follow [the owner-approved style addon](prompts/script-style.md): frequent creative roasts, playful trash talk, Gen Z/millennial slang and streetwise banter throughout the narration, with varied comparisons and callbacks. Swearing remains occasional and light. This applies to both English channels.

A portable, user-owned workflow for English what-if videos on **ifverse_anime** and **ifverse_hollywood**. An assistant provides one script and production plan; a finite GitHub-hosted job does the repetitive media work and returns a video plus one compact report.

**New session: read [START_HERE.md](START_HERE.md), [the current checkpoint](docs/CURRENT.md) and [AGENTS.md](AGENTS.md) first.** The current implementation is on **[codex/ifverse-workflow](https://github.com/Vpermillion/Content_Creating_WorkFlow/tree/codex/ifverse-workflow)**. The default `codex/portable-workspace` branch retains older code and routes agents to this branch. Inspect branch state before concluding a feature is missing.

[Copy-ready new-agent prompt](docs/NEW_AGENT_PROMPT.md) · [Project history and decisions](docs/PROJECT_HISTORY.md) · [Original prototype README](docs/archive/README_BEFORE_START_GUIDE.md)

## Intended operation

```mermaid
flowchart LR
    A[One script and scene plan] --> B[Cached online moving footage]
    B --> C[Light cleanup and ordered shots]
    A --> D[Generated or retained narration]
    D --> E[Timed captions]
    C --> F[Render and validate]
    E --> F
    F --> G[Video and compact report]
    G --> H[One assistant review]
```

Footage should illustrate the actual narrated character, action, location or choice. Cuts now support explicit spoken-beat boundaries so an organization shot does not continue over a friends/protection alternative. Canon footage illustrates the invented what-if; it must not be presented as a real episode of that alternate story.

## Working components

| Component | Verified role |
| --- | --- |
| GitHub review job | Finite hosted execution with data-only requests, dependency/model/source caches, validation and versioned results. A personal PC is not required for this path. |
| Media tools | Tenor/optional YouTube lookup, bounded downloads, SHA-256/ffprobe validation and a reusable labeled clip bank. |
| FFmpeg editor | Moving clips, source trims, contain/cover framing, mild denoise/resize/sharpen, single-pass rendering, readable captions and complete audio/video/decode checks. |
| English voice | Kokoro-ONNX `af_heart`, tested on CPU; keep verified speech when revising pictures. |
| Caption timing | faster-whisper `tiny.en`/`base.en`, CPU/int8; recognized-word timing or exact-known-script cross-attention/DTW alignment, grouped into readable phrases. Word times remain estimates and receipts are preserved. |
| Continuity | Source history, safe generated examples, state/checkpoint docs and copy-ready prompts. Credentials and private production data remain separate. |

The latest owner-requested example is a **60-second Naruto roast**, with 24 moving shots, nine traced sources and 50 caption phrases, from successful hosted run `41047895853`. [Watch the one-minute MP4](https://github.com/Vpermillion/Content_Creating_WorkFlow/blob/codex/results/ifverse-anime-roast-20261030-04/artifacts/ifverse-anime-roast-20261030-04/render/video.mp4). It uses the new funny/teasing script preference, a single generated Kokoro voice version and Whisper forced alignment of the exact known script to the final audio. Complete decode, track/duration/hash checks and all shot samples were reviewed. The earlier 44.672-second visual revision remains preserved. See [CURRENT](docs/CURRENT.md) for exact receipts, review limits and next work.

## Current workflow entry

On `codex/ifverse-workflow`, commit **exactly one** new `review-requests/*.json`. [review-video.yml](https://github.com/Vpermillion/Content_Creating_WorkFlow/blob/codex/ifverse-workflow/.github/workflows/review-video.yml) runs the request and writes its output to `codex/results/<request-id>` and the `ifverse-review-video` artifact. Documentation-only commits do not dispatch media. Request selection rejects unrelated result branches; do not resend an uncertain job before reading its saved result.

The runner accepts a validated repository script and its supplied reviewed shot plan; the demonstrated stories are Naruto scenarios. Free-form story intake, stronger automatic semantic selection, automatic source-quality judgments and Hollywood branding are still work. Clip labels and successful file checks are not semantic approval. The original n8n/SQLite science prototype, Google connection work and wider account proposals remain in history; do not rebuild them or revive old rollout plans.

For local development, use Python 3.12+, FFmpeg/ffprobe, DejaVu Sans and `requirements-test-video.txt`. Run `python -m unittest discover -s tests -v` after behavioral changes. Read the current branch's [media tools guide](https://github.com/Vpermillion/Content_Creating_WorkFlow/blob/codex/ifverse-workflow/docs/MEDIA-TOOLS.md) and [visual matching guide](https://github.com/Vpermillion/Content_Creating_WorkFlow/blob/codex/ifverse-workflow/docs/VISUAL_MATCHING.md) for exact commands and timing contracts.

## State, access and remaining limits

The workspace must survive changing assistants. Save code, current branch, requests, output receipts and next actions; restore private state independently. Personal skills, credentials and signed-in accounts do not automatically transfer. Git proxy access does not prove GitHub API access. Preserve the managed runtime's proxy/CA and use supported network settings.

Kaggle is an optional unexecuted voice-batch template, and n8n is optional coordination. No live YouTube channel binding, public upload, continuous scheduler or production host was verified by the test. Keep publishing disabled until current authorization and provider access are verified. A successful MP4 remains a review draft until factual/plot, audiovisual, source-use and platform review. Source cleanup does not reconstruct missing detail or guarantee monetization.

Never commit passwords, OAuth client/token files, account addresses, private databases or the raw conversation PDF. The committed test media/narration is a non-secret fictional review example; real/private jobs require configured private storage. GitHub caches are not backups. Full decisions, tested outcomes and exact next actions are in the entry guides, so a new session can continue without rereading the original chat.
