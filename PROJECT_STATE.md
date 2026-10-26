# Project state — 2026-10-26

The full uploaded specification is preserved in `docs/MASTER_PROMPT.md`. This is a working on-demand prototype. It is not a continuous production deployment. Read this file together with `HANDOFF.md` before resuming.

## Latest Alpha connection attempt — 2026-10-26

Actual result: **not connected**. On `codex/youtube-oauth`, the optional Google SDK was installed into `/workspace/scratch/youtube-oauth-venv` and all 23 tests passed. The real CLI reports no saved connections and `check alpha-anime` returns `not_connected`. No Desktop client JSON exists at the documented private path; no Alpha token is present. Google OAuth/token/YouTube endpoint probes returned proxy CONNECT 403, and no owner-browser-to-runtime callback route is verified (`callback_unreachable`). A local-only port-8765 listener test passed but does not establish that route.

The required Google domains and `api.github.com` were saved in the environment draft, preserving NASA/NIH entries; the save did not apply or publish policy. No consent, token exchange, project/client creation or Google recovery/login retry was attempted. The registry is unchanged byte-for-byte, with no verified channel ID or binding. See `docs/YOUTUBE-CONNECTION-RESULT.md` and `channels/youtube-connection-checkpoint.json` for exact blockers, checks and continuation. Existing jobs/media/private configuration were preserved; no publishing scope was requested.


## YouTube connection implementation — 2026-10-26

Feature branch: `codex/youtube-oauth`, based on `codex/operator-handoff` (which includes the current Alpha-only entertainment plan). `whatif/youtube.py` adds optional read-only Google OAuth: per-channel aliases, loopback consent with PKCE/offline access, restricted private credential files, refresh, `mine=true` channel-ID checks and explicit registry binding. Cached status is labeled as unverified until a live API check succeeds. Wrong-channel, insufficient-scope and provider failures do not claim success. The job DB is not initialized by these separate commands.

Start with `prompts/youtube-connect.md` and `docs/YOUTUBE.md`. Prepare the user-owned Google Desktop OAuth client and a reachable loopback callback, then connect/check `alpha-anime` and bind its actual returned ID to `alpha-1`. Actual names/IDs remain unverified. If this cloud environment lacks a callback route, record that blocker and use a supported reachable runtime; do not substitute an OOB/code-paste flow. Other accounts remain deferred.

Validation in a source snapshot matching the remote branch: 23 unit/integration tests passed (existing state/FFmpeg tests plus 12 new connection tests). An offline smoke check with real google-auth-oauthlib 1.5.0 and google-auth 2.62.0 verified PKCE S256, readonly/offline consent construction, loopback timeout support and fixture-token loading. No real Google client/token exchange, authenticated channel lookup or n8n call was performed. The callback route has not been exercised end-to-end with Google.

Private tokens are permission-protected JSON, not application-encrypted. Preserve them through a private encrypted volume/secret deployment and separate backup. `.gitignore` and `.dockerignore` exclude default private credentials and common OAuth client filenames. Do not run interactive OAuth through Actions logs. The existing publisher stays draft-only; a separately authorized upload adapter/private test/resumable recovery/receipt reconciliation remains future work. No channel created, video published or service deployed.

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

## Private repository and authentication checkpoint — 2026-10-26

The owner made the repository private and requested account/channel preparation with minimal manual work. Authenticated GitHub metadata confirms private=true and continued repository read/write access in this session. This does not grant Google-account access.

YouTube connection lookup returned no active connection; the Alpha connection remained initializing. A direct cloud-browser visit to YouTube account settings redirected to Google sign-in. The browser requires the secure browserAuth flow for sign-in values; credentials previously pasted in chat cannot be entered through lower-level tools. The secure sign-in request was declined, so authentication was stopped without retry or a new handoff. No Google account was signed in, no channel was created and no video was published.

Owner preference: the assistant should perform channel preparation and routine supported operations after authentication, with user involvement limited to required sign-in/consent/verification. Each intended account still needs independently authorized access. Do not claim unrestricted account control or automatic connection transfer to a replacement GPT. Next dependent step is a user-requested supported authentication attempt; respect the declined flow until the owner elects to resume.

## Alpha authentication result — 2026-10-26 (Asia/Ulaanbaatar)

The owner asked to proceed with secure account sign-in. Google accepted the email step and advanced after secure password submission to identity verification. The owner selected the offered alternative twice; Google opened account recovery and accepted a last-password submission through browserAuth. Google then displayed 'Couldn’t sign you in', explaining that there was insufficient information to verify ownership and suggesting a previously used device/network. This is an identity-verification rejection, not evidence of an incorrect password or a bot-detection block. No successful YouTube sign-in was observed.

Stop this browser login attempt; do not loop, bypass verification or reset credentials. No channel was created, no channel metadata was verified, no security setting was changed and no video was published. The other six intended accounts remain unverified and were not attempted in this turn. No authentication secrets or session URLs are recorded here.

Next: the owner must resolve the account's Google verification requirement through a supported method. A supported YouTube OAuth connection, completed by the owner, can be checked independently; do not assume it authenticates the cloud browser. Reinspect actual connection status and provider-authorized scopes before claiming access. Repository/handoff remains private on codex/operator-handoff, PR #1; no pipeline code or media tests changed in this authentication-only turn.

## Two channels per Google account — 2026-10-26

The owner expanded capacity to up to two YouTube channels per each of seven Google accounts (up to 14 total), superseding the original one-to-ten-channel capacity target for future planning. This is capacity, not a requirement to launch all fourteen now. `channels/youtube-registry.json` schema version 2 contains two planned slots per owner alias, stable slot IDs and suggested Ifverse names/handles/topics. Suggestions are not verified channel metadata; availability is unchecked. Actual IDs, handles and display names stay null. Preserve the Alpha identity-verification blocker; no new sign-in was attempted and no channel was created.

Pairs: Alpha Space/Physics; Beta Earth/Oceans; Delta Wild/Evolution; Epsilon Future/Machines; Zeta Human/Mind; Eta History/Civilizations; Theta Worlds/Myths. Keep existing first-channel suggestions and add one related topic for each second slot. Start with one pilot channel and expand in phases. Operator labels remain distinct from channel identities. Any publisher must bind each verified channel ID to its correct authorization; a Google-account login alone does not prove both channel connections work.

YouTube officially supports multiple channels through one Google Account: https://support.google.com/youtube/answer/3046356 and https://support.google.com/youtube/answer/4642409 . Features and initial creation remain subject to actual account verification. Registry/documentation only; JSON parses and all 14 slot IDs are unique, two per owner. No worker code changed or media tests rerun.

## Latest scope: Alpha entertainment pilot — 2026-10-26

The owner slowed the rollout and selected Alpha for an initial example: `ifverse_anime`, `ifverse_cartoon`, and a Marvel-focused channel. This supersedes Alpha's two-channel cap: three planned slots are now allowed for Alpha. The wider seven-account rollout is deferred; do not resume mass setup by default. The earlier science names Space/Physics are replaced only as plans; retain existing science demo jobs/artifacts unchanged.

Registry schema version 3 records Alpha's three active planning slots and preserves the other accounts' proposals as deferred. `ifverse_marvel` is a suggested name for the requested third category. The owner's Hollywood/American parenthetical may imply a broader entertainment scope: if so, `ifverse_hollywood` is a suggested alternative, not an approved rename. Do not treat Marvel as a label for all American movies. Names/handles remain unchecked; verified channel fields stay null.

Next editorial example: one anime what-if video, proposed topic 'What if Naruto joined the Akatsuki?' Test one video before expanding. This topic is a proposal, not an approved script or publication. Alpha's Google identity-verification blocker remains unresolved. No sign-in retried, channel created, public post made or production job regenerated. JSON/unique slot IDs/three active slots checked; source behavior unchanged, no media tests rerun.

