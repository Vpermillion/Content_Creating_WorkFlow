# Ifverse

A video production and publishing workspace for English what-if stories on **ifverse_anime** and **ifverse_hollywood**. An assistant prepares the script and shot plan; a finite job finds/caches sources, creates narration and captions, renders the video, and saves results for review.

Start with [START_HERE.md](START_HERE.md) and [the current checkpoint](docs/CURRENT.md). Contributors and agents should also read [AGENTS.md](AGENTS.md).

## Implementation

| Component | Entry point | Implemented behavior |
| --- | --- | --- |
| Media production | `scripts/render_test_video.py` | Validated repository scripts and shot plans, Kokoro narration, faster-whisper captions, FFmpeg editing and sound effects |
| Hosted production jobs | `.github/workflows/review-video.yml` | Finite requests on `codex/ifverse-workflow`; versioned outputs on `codex/results/*` |
| Account linking | `sites/accounts.mjs` | Provider consent, destination checks, encrypted connections and supported token refresh |
| ChatGPT tools | `sites/worker.mjs` | Owner access check, account dashboard and calls to the private publisher |
| Drafts and publishing | `whatif/publishing_api.py`, `whatif/publishing_service.py` | Saved previews, exact destination selection, provider adapters and independent delivery receipts |

The complete publishing implementation is on [codex/ifverse-chatgpt-publishing](https://github.com/Vpermillion/Content_Creating_WorkFlow/tree/codex/ifverse-chatgpt-publishing), in [PR #4](https://github.com/Vpermillion/Content_Creating_WorkFlow/pull/4). `codex/ifverse-workflow` contains the established media workflow; the default `codex/portable-workspace` is an older snapshot. Check the branch before comparing capabilities.

## Use the project

- [Link accounts and configure the publisher](sites/ACCOUNT_LINKING.md)
- [Prepare, review and publish from ChatGPT](docs/CHATGPT_PUBLISHING.md)
- [Produce a batch or use the standalone YouTube uploader](docs/AUTOMATION.md)
- [Use the separate GitHub/desktop publishing queue](docs/SOCIAL_PUBLISHING.md)
- [Find completed videos](docs/BATCH_61S.md), [topic history](channels/ifverse_anime-topics.json) and [validation records](docs/REPAIR_VALIDATION.md)
- [Content style](prompts/script-style.md), [sound design](docs/SOUND_EFFECTS.md) and [source/editorial review](docs/MONETIZATION_REVIEW.md)

The owner-selected voice is `am_michael`. Ten 61-second anime cuts and their sound repairs are saved. Hollywood branding and general automatic story-to-footage planning remain incomplete. The renderer currently accepts prepared anime requests.

The Site exposes YouTube, Instagram, Facebook and TikTok linking. The backend's checked-in account registry currently contains only the Ifverse YouTube destination. Other destinations need exact IDs registered before drafting or publishing. TikTok publication uses a Studio handoff.

GitHub access, the ChatGPT Site owner and social-channel consent are separate. Their login emails can differ. Code and test results establish implementation; live connections and publication are established by provider checks and receipts.

## Development

Python/media changes: `python -m unittest discover -s tests -v`.

Site changes: run `npm ci`, `npm test` and `npm run build` in `sites/`.

See [capabilities](docs/INTEGRATIONS.md) for dependencies and [continuity](docs/CONTINUITY.md) for state and recovery. Older project decisions are in [PROJECT_HISTORY.md](docs/PROJECT_HISTORY.md).
