# Components and dependencies

This inventory describes checked-in code on `codex/ifverse-chatgpt-publishing`. [CURRENT.md](CURRENT.md) records runtime checks. Historical availability from an old chat is not a current connection check.

| Component | Implemented role | Runtime requirement |
| --- | --- | --- |
| Python and FFmpeg | Media preparation, editing, sound, validation and publishing backend | Python 3.12+ for the documented development/hosted setup, FFmpeg/ffprobe and fonts |
| Kokoro-ONNX | English CPU narration; selected voice `am_michael` | Pinned dependencies/models in `requirements-test-video.txt` and the runtime cache |
| faster-whisper | CPU recognition or known-script alignment | Matching models; timestamps remain estimates |
| Source tools | Tenor/optional YouTube lookup, bounded downloads and cached assets | Source connectivity and actual usage/provenance records |
| GitHub Actions | Finite source/render jobs and software checks; separate publishing workflows | Workflow installed on its configured branch, runner access and route-specific secrets |
| Sites Worker and database | ChatGPT tools, owner check, OAuth consent and encrypted grants | Site deployment, owner setting, stable storage key and provider clients |
| Private publisher | Media import, durable drafts, receipts, provider adapters | HTTPS host, persistent private state and matching Site/backend credential |
| GitHub media import | Fetch pinned selected render bytes and verify their hash | Backend read-only access to this private repository |
| YouTube/Meta | Verified destination access and supported upload adapters | Provider app setup, exact destination IDs and valid consent |
| TikTok | OAuth/identity checks and Studio publication handoff | Login Kit/Display setup for OAuth, or manual Studio route |
| n8n/legacy SQLite worker | Optional earlier coordination and prepared science fixtures | Separate local/container state; not required by the current hosted review job |
| Kaggle | Optional notebook/export templates | Not established as the current execution path |

No general analytics or unattended fresh-writing API integration is established. ChatGPT supplies the creative plan; the media job performs the repeated software work.

## Setup guides

- [Account linking and backend deployment](../sites/ACCOUNT_LINKING.md)
- [ChatGPT drafts and publishing](CHATGPT_PUBLISHING.md)
- [Separate Actions/desktop publishing](SOCIAL_PUBLISHING.md)
- [Local read-only YouTube utility](YOUTUBE.md)
- [Legacy worker operation](OPERATIONS.md)

Hosting, storage, runner limits and provider eligibility depend on the selected services. The repository does not establish a universal free tier or a live production deployment.
