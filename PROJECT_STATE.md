# Project state — 2026-10-26

The full uploaded specification is preserved in `docs/MASTER_PROMPT.md`. This is a working on-demand prototype. It is not a continuous production deployment. Read this file together with `HANDOFF.md` before resuming.

## Prior implementation validation — 2026-10-25

- Python standard-library worker and application SQLite database, distinct from n8n state.
- Stable immutable job inputs/content hashes, per-channel topic-title history, worker leases/heartbeats, stale-owner checkpoint protection, explicit failures/backoff, verified checkpoints and intentional downstream rebuilds.
- Three original English pilot scripts with explicit scenario assumptions and reference candidates. This language/profile is provisional, not inferred from location.
- Scene-linked original SVG diagrams, local CMU SLT synthetic narration through FFmpeg/libflite, exact concatenated scene audio boundaries, editable SRT/ASS captions, center zooms/cuts, H.264/AAC MP4 output.
- Full output decoding, resolution/aspect/codec/audio/duration/peak checks, checksum manifests and retained quality reports. The provisional format is 720x1280 at 30 FPS, 30–60 seconds.
- Real separate Docker worker and n8n 2.44.6 containers, loopback health responses, workflow/credential import, authenticated workflow execution against pilot-002. The finite manual starter reads one checkpoint; it is inactive and does not constitute an unattended production coordinator.
- Twelve local publication drafts (three jobs × four candidate platforms), unique idempotency keys, uncertain-delivery protection and per-platform state isolation. No live publishing transport or authorization.
- Kaggle input/output manifest export/import, strict wrong-run/incomplete-output rejection, and manual-audio contract. Valid input import/render tested using a locally synthesized fixture, **not a Kaggle run**.
- Private checksummed state backup/restore and a safe demo-only JSON/media export without a private SQLite DB. Restored jobs resume without regenerating verified speech.

## Pilot status

| Job | Question | Completed | Release status |
| --- | --- | --- | --- |
| pilot-001 | What if the Moon vanished? | Script, diagrams, local speech, captions, render, automated QC, 4 drafts | Quality review; source verification/listening/platform review pending |
| pilot-002 | What if a day lasted 48 hours? | Same path, submitted through real n8n workflow, 4 drafts | Quality review; source verification/listening/platform review pending |
| pilot-003 | What if sunlight switched off? | Script, diagrams, local speech, captions, render, automated QC, 4 drafts | Quality review; source verification/listening/platform review pending |

Exact durations, hashes and check results are in `artifacts/validation.json`. Sample MP4s, editable SRTs and frame captures are in `artifacts/`. The safe demonstration snapshot is `artifacts/demo-state.tar.gz`. Current-instance authoritative state is `data/jobs.sqlite3`; the DB and actual `.env` are ignored by Git.

## Validation and diagnosed failures

Eleven standard-library tests passed with no failures or skips. These include real FFmpeg rendering, failed-render resume retaining speech, checkpoint corruption detection, concurrent lease exclusion, stale-owner fencing, bounded retries, authenticated worker access, private backup/restore, archive traversal rejection, duplicate/uncertain-delivery protection and synthetic batch-audio import. See `tests/test_workspace.py` and the safe retained `artifacts/tests.txt`.

An initial visual review found excessive subtitle scaling. The renderer now writes an explicit 720x1280 ASS canvas; pilot-001 was rebuilt from captions without regenerating speech, and a corrected frame was inspected. Sampled frames were inspected; the whole videos have not been visually watched or audibly auditioned. Automated audio analysis confirms a nonzero audio stream and peak below full scale, not pronunciation or listening quality.

Docker initially exposed source ownership incompatible with its non-root worker; `COPY --chown` fixed it. A real n8n request initially received proxy `Domain forbidden`; lowercase `no_proxy` lacked the internal Docker service names. Both proxy-exclusion forms now retain inherited exclusions and add only internal services. n8n CLI execution needed a separate broker port alongside its editor. These fixes were followed by successful actual workflow execution.

## Blocked or not yet integrated

- Factual source checks: a NASA request returned proxy 403. Draft network additions for `science.nasa.gov` and `www.nigms.nih.gov` were saved. Saving did not apply runtime policy. Source `checked_at` values remain null; editorial approval remains false.
- No callable Google Drive/Sheets, Metricool, Composio or Kaggle integration was discovered. Present generic Google credential metadata is not evidence of Drive authorization. No external storage sync, publishing, metrics collection or provider refresh-token flow was run.
- The Kokoro notebook is unexecuted. Kaggle authentication, quotas/GPU access, model/voice licenses and actual performance remain prerequisites. No model weights were downloaded here.
- No model API is connected for unattended fresh writing; the current assistant supplied the three prepared scripts. No stock search/download adapter is connected. Procedural graphics are working local inputs.
- Richer footage framing, music/SFX, word alignment, automatic research, bounded coordinator polling/notifications and production monitoring are backlog items.
- No continuous host, public URL, external account, paid service, public post or production scheduler was created.

## Persistence

Source, safe sample artifacts and the handoff are in this repository. Remote Git push to `codex/portable-workspace` succeeded. Saved `install_script`, `start_skill` and research-domain draft updates were confirmed; they are not applied/published configuration. Details are in `HANDOFF.md`. Local private backup: `backups/initial-private-state.tgz` (ignored; not remotely synced). Real/private deployments need user-owned external backup storage and separate secure n8n volume/key backup.

## Operator handoff documentation — 2026-10-26

- Added seven account-number aliases (alpha, beta, delta, epsilon, zeta, eta, theta), interchangeable roles, a universal resume prompt and seven focused copy-ready prompts.
- Added a public registry and a blank private-mapping example. Real addresses and supplied credentials are excluded. `private/` is ignored; no account connection was attempted.
- Updated README/operator instructions and made the handoff independent of one absolute checkout path.
- Scope is documentation/configuration only. JSON, prompt coverage, local link targets and candidate content were checked. The prior media/container/test results above were not rerun or reverified in this session.
- Current GitHub repository access was verified. That does not establish access from the other seven GPT accounts or a live production deployment. Publishing remains unconfigured and unauthorized.

## Continuity and YouTube setup — 2026-10-26

- Owner requires durable takeover without prior chat. Added an explicit per-step checkpoint/external-intent protocol and branch/PR discovery instructions in `docs/CONTINUITY.md`.
- Owner authorized the supplied accounts for YouTube channel setup; actual identity, name/handle, consent and supported setup remain prerequisites. Publication is a separate authorization.
- Added seven intended channel slots in `channels/youtube-registry.json`, with null IDs/handles and unverified status. No emails, passwords, tokens or short-lived connection URLs were saved in Git.
- This session discovered callable hosted Composio tools; earlier capability reports above describe another session. YouTube had no active connection. An initial supported consent request was initiated, awaiting user completion; no channel was created or inspected through an authenticated YouTube call.
- Repository was public, with no Pages site. No visibility change was requested or made, and account billing plan was not inspected. Private-repository tradeoffs are documented.
- Scope: documentation/configuration only. No media/worker/container tests rerun, no private state restored, no social post published. A genuinely independent takeover still needs verification.
