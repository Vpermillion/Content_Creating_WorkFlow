# Current checkpoint

## Start and branch

Read `START_HERE.md`, `README.md` and `AGENTS.md`. Current development is **`codex/ifverse-workflow`**, based on the full tested result checkpoint `3fae323` from `codex/ifverse-test-result-20261029-04`. The older default branch `codex/portable-workspace` is a documentation router and legacy application snapshot. Preserve existing work before selecting a branch; do not implicitly merge/reset older branches.

## Goal

English YouTube what-if videos for `ifverse_anime` and `ifverse_hollywood`. One assistant production plan → one finite autonomous GitHub job → cached online footage, narration, caption timing, ordered rendering and validation → one compact result/review. Match actual spoken characters/actions/locations as closely as the available footage permits. Keep invented events explicitly illustrative.

## Latest completed video

- Naruto test: 44.672 seconds, 18 moving shots, Kokoro-ONNX `af_heart` CPU speech, 27 faster-whisper CPU/int8 phrase captions.
- Hosted run `40846229359` succeeded. Completed MP4, captions, script, source plan and receipts are on `codex/ifverse-test-result-20261029-04`, under `artifacts/ifverse-anime-test-20261029-04/`.
- Speech SHA-256: `2eea93b20f0187a0a7aa25444a49f439f2d00d5b276dfefdea68a3cb97bf8fcc`. Preserve it for visual-only revisions.
- Final video SHA-256: `ecaf34229de3a645779c4b6518749b71a64e655079cdadd8803172c603f2d13a`. Full decode, track coverage, motion in all 18 shots and -0.5 dBFS peak were independently rechecked. Full listening/editorial/source-use approval remains pending.
- Measured retained-audio media work: 33.255 seconds; excludes setup and first-time voice generation. See `docs/TEST_VIDEO.md` for failures/fixes and the complete record.

## Current visual revision

The user approved that test and requested closer script-to-picture matching plus complete GitHub handoff instructions. `edits/ifverse-anime-naruto-visual-v3.json` contains **22 explicit spoken-beat shot intervals from 14 moving sources**. It replaces equal scene splitting: Nine Tails on its name, Akatsuki on the organization/motive, Leaf on the threatened village, friends on the protection alternative. The unchanged speech and captions are reused. Local suite: **42 passed** after interval/request changes.

Request `ifverse-anime-visual-match-20261030-01` is prepared in `review-requests/`. It is not a completed new result until its `result.json` reports success. Expected result branch: `codex/results/ifverse-anime-visual-match-20261030-01`. Inspect that result before any resubmission.

## Commands and status limits

Use current-branch `docs/MEDIA-TOOLS.md`, `scripts/render_test_video.py` and `.github/workflows/review-video.yml`. Commit exactly one new review-request JSON on `codex/ifverse-workflow` to trigger a finite job; result branches do not rerender. Documentation-only commits do not dispatch media. Keep request IDs unique and reconcile earlier results before retrying.

This cloud snapshot's enforced egress policy allows Git/package hosts, not Tenor/Hugging Face. Preserve its proxy and CA settings; do not bypass destination restrictions. The demonstrated workflow executes on the authorized GitHub-hosted runner. Native Git proxy access works; GitHub API/`gh` access is not established here. No secrets/outbound identities are configured in the runtime metadata inspected for this task.

The legacy SQLite science fixtures are separate from the standalone media test. Restore authoritative private state before running commands that initialize a fresh store. Actual private caches/account tokens do not transfer through Git. No live YouTube binding, upload, new account, paid service, scheduler or production host was established. Do not revive old login/recovery attempts; read the continuity records only when that work is actually requested.
