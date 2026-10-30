# Current checkpoint

## Start and branch

Read `START_HERE.md`, `README.md` and `AGENTS.md`. Current development is **`codex/ifverse-workflow`**, based on the full tested result checkpoint `3fae323` from `codex/ifverse-test-result-20261029-04`. The older default branch `codex/portable-workspace` is a documentation router and legacy application snapshot. Preserve existing work before selecting a branch; do not implicitly merge/reset older branches.

## Goal

English YouTube what-if videos for `ifverse_anime` and `ifverse_hollywood`. One assistant production plan → one finite autonomous GitHub job → cached online footage, narration, caption timing, ordered rendering and validation → one compact result/review. Match actual spoken characters/actions/locations as closely as the available footage permits. Keep invented events explicitly illustrative.

## Current owner style and one-minute request

The owner requested funny, teasing, sarcastic fan narration, exaggerated complaints and occasional clean-swear wordplay such as “motherflicker” or “mother father.” This applies to **both English channels** and supersedes the older neutral writing tone. Read [the permanent addon](../prompts/script-style.md) before drafting. It is linked from the root guides, agent instructions, both continuation prompts and both channel profiles.

New request `ifverse-anime-roast-20261030-01` targets **60 seconds** with a new 196-word, 21-beat Naruto/Akatsuki roast, selected from nine previously reviewed moving sources. Fresh narration/captions are required because the script changed. Existing approved videos and their exact audio remain preserved. The selected runner change accepts bounded `pilots/*.json` script input plus a matching supplied edit plan and can fit newly generated speech to a duration with bounded pitch-preserving retiming. Automatic new-story clip discovery/semantic matching and Hollywood rendering remain incomplete. Check the saved result branch `codex/results/ifverse-anime-roast-20261030-01` before any retry; execution/review status will be recorded here when completed.

## Latest completed video: closer visual matching

- Request `ifverse-anime-visual-match-20261030-01` **succeeded** in hosted run `41022041729`, from source `86300d83e7d7b004747b3d21940199a3e933360e` on `codex/ifverse-workflow`.
- Result branch: `codex/results/ifverse-anime-visual-match-20261030-01`; directory `artifacts/ifverse-anime-visual-match-20261030-01/`. [Watch/download the latest MP4](https://github.com/Vpermillion/Content_Creating_WorkFlow/blob/codex/results/ifverse-anime-visual-match-20261030-01/artifacts/ifverse-anime-visual-match-20261030-01/render/video.mp4).
- **44.672 seconds, 22 moving shots from 14 traced online sources, 27 caption phrases.** Nine Tails appears on its name, Akatsuki on the organization/motive, the Leaf on the village threat, and friends on the protection alternative. See `docs/VISUAL_MATCHING.md` for every reviewed beat and source reason. Invented actions remain illustrative.
- The exact Kokoro-ONNX `af_heart` speech and corrected faster-whisper caption timing were retained. Narration SHA-256: `2eea93b20f0187a0a7aa25444a49f439f2d00d5b276dfefdea68a3cb97bf8fcc`.
- Video SHA-256: `87de8da1c8f43e8320d9364c8ce6af4d790e20b75bc322ae51c55fe93d877b7f`. Complete decoding, track coverage, byte-identical narration/captions, motion in all 22 shots and -0.5 dBFS peak reverified locally; all 22 shot-midpoint frames were visually reviewed. Full listening/editorial/source-use approval remains separate.
- Media execution: **24.715 seconds**, including 1.084 footage, 0.003 retained voice, 0.004 retained captions, 22.867 render/decode. This excludes installation/queueing and reuses audio/captions; it is not a fresh TTS/ASR throughput benchmark. Local regression suite: **42 passed**. Hosted regression gate also passed before rendering.
- Delivered cloud files: `/workspace/Ifverse_Anime_Script_Matched.mp4` and `.srt`. GitHub result branch and `ifverse-review-video` run artifact preserve the output independently of those machine paths. Read the existing result before rerunning.

## Earlier baseline

The prior delivered test (18 shots, same 44.672-second voice, 27 captions) remains on `codex/ifverse-test-result-20261029-04`, hosted run `40846229359`. Older 46.975-second edits and the science fixtures remain historical engineering stages. Do not overwrite or regenerate them to resume the current version.

## Exact next work

The tested runner still uses the prepared Naruto story. Generalize validated new-story/channel input and Hollywood branding, improve automated semantic clip selection without losing concrete beat reasons, and harden stage resume/private media storage. Do not rebuild working download, voice, ASR or render tools. Publishing/account setup is a separate task with no verified live binding here.

## Commands and status limits

Use current-branch `docs/MEDIA-TOOLS.md`, `scripts/render_test_video.py` and `.github/workflows/review-video.yml`. Commit exactly one new review-request JSON on `codex/ifverse-workflow` to trigger a finite job; result branches do not rerender. Documentation-only commits do not dispatch media. Keep request IDs unique and reconcile earlier results before retrying.

This cloud snapshot's enforced egress policy allows Git/package hosts, not Tenor/Hugging Face. Preserve its proxy and CA settings; do not bypass destination restrictions. The demonstrated workflow executes on the authorized GitHub-hosted runner. Native Git proxy access works; GitHub API/`gh` access is not established here. No secrets/outbound identities are configured in the runtime metadata inspected for this task.

The legacy SQLite science fixtures are separate from the standalone media test. Restore authoritative private state before running commands that initialize a fresh store. Actual private caches/account tokens do not transfer through Git. No live YouTube binding, upload, new account, paid service, scheduler or production host was established. Do not revive old login/recovery attempts; read the continuity records only when that work is actually requested.
