# Handoff

Start by reading `AGENTS.md` and `PROJECT_STATE.md`. Use the existing checkout supplied by the active environment; its absolute path can differ between accounts and hosts. The uploaded master prompt is in `docs/MASTER_PROMPT.md`.

## Resume now

First read [continuity and channel setup](docs/CONTINUITY.md). Inspect PR #1: these notes are on `codex/operator-handoff`, while the default branch was `codex/portable-workspace` at this checkpoint. Restore or locate authoritative private state before running status. After that, from the active repository root:

```sh
python -m whatif status
docker compose ps
```

The three stable job IDs are `pilot-001`, `pilot-002`, `pilot-003` under `science-provisional`. All are at quality review with completed media checkpoints and four publication drafts apiece. `python -m whatif run JOB_ID` verifies and reuses completed artifacts. No model or remote voice service is required to resume prepared local jobs.

If this is a fresh clone, first restore the safe demonstration snapshot into a **fresh** data directory:

```sh
python scripts/demo_snapshot.py restore artifacts/demo-state.tar.gz --destination data
```

For real/private jobs, restore your private application backup instead; see `docs/BACKUP.md`. Do not seed and regenerate demonstration media if the exact snapshot is available. Do not overwrite an existing data directory.

## Runtime and endpoints

- `docker compose up -d` restarts the retained worker and coordinator; processes are not part of Git and must restart on another machine.
- n8n editor/API: host loopback port 5678, internal service `n8n`; `/healthz` was verified.
- Worker: host loopback port 8090, internal `http://worker:8090`; `/health` was verified. Job routes require the local backend token from ignored `.env`; never print it.
- Imported workflow ID: `whatifPreparedPilot`, inactive, draft only. Credential ID: `whatifWorkerLocal`, name `WhatIf worker`. Actual credential is encrypted in the n8n volume and is not in the workflow export.
- The CLI workflow command in `docs/OPERATIONS.md` uses broker port 5689 to coexist with the editor. It enqueues pilot-002 and reads a checkpoint; no active recurring scheduler exists.
- n8n database: Compose `n8n_data` volume. Application database/media: `data/`. Secret file: ignored `.env`. Private backup: ignored `backups/`.

## Exact next useful actions

1. Review and save the environment network additions in settings, then re-test NASA/NIH URLs. Read the actual sources, record checked dates and claim-level findings, and correct any script defect under a new content version before release.
2. Watch/listen to the safe sample MP4s. Check pronunciation, caption reading pace, full scene transitions, platform UI safe areas and factual framing. None has been approved for publication.
3. If preferred speech quality requires it, connect the authorized Kaggle account or use the documented manual notebook route for **new job versions**. Do not regenerate current speech just to resume. Benchmark rather than promise T4 speed.
4. Connect user-owned output/backup storage. Drive was not callable in this session. Preserve private job state there separately from the source repository.
5. Choose a supported publishing provider only after checking the actual plan, account eligibility and consent scope. Keep draft mode until explicit authorization. Implement `PublishingProvider` transport/status reconciliation; never retry an uncertain upload blindly.
6. For unattended generation, review a persistent host, model API, bounded coordinator polling and monitoring. The current services are development/on-demand only.

## Persistence and configuration record

See the final checkpoint section below for verified remote branch/configuration outcomes. Never infer publication, fresh-task restoration or external connection status merely from a saved draft or local server.

## Verified checkpoint

- Source and safe demonstration artifacts were pushed successfully to `Vpermillion/Content_Creating_WorkFlow`, branch `codex/portable-workspace`. Initial implementation commit: `b0550fc`. Later handoff commits may advance that branch; use `git rev-parse HEAD` and the remote branch for the exact revision. No existing default branch was overwritten.
- Environment draft persistence was confirmed for `install_script`, `start_skill`, and research network domains `science.nasa.gov` / `www.nigms.nih.gov`. Draft saving did not apply or publish these changes. Review/save environment settings and publish an environment snapshot through the product when ready; no public video posting is authorized.
- `sh scripts/install.sh` and repeat n8n credential/workflow import completed successfully. Both service health requests returned HTTP 200 after container refresh. All three pilot resumes reused narration.
- Safe demo restore and private backup restore both succeeded into separate fresh `/tmp` directories. This validates restoration in this machine, not a genuinely independent host or fresh cloud task.
- No Kubernetes/cloud deployment, outside account creation, provider purchase, social posting or external private-data sync occurred.

## Operator prompt checkpoint — 2026-10-26

Seven interchangeable aliases and suggested focuses are documented in `docs/OPERATORS.md`, `operators/registry.json` and `prompts/`. No real email, supplied secret, account login or automatic account rotation is part of this change. Each new assistant needs its own authorized access to the same workspace.

This documentation update inspected the remote source and saved specification. It did not restore private job state, start containers, rerun media tests or verify prior runtime health. Runtime reports above describe the earlier implementation session. Before status checks on a new host, locate or restore the authoritative private data; avoid silently treating an empty new database as restored state.

Next: use `prompts/alpha.md` or `prompts/resume.md` in an authorized environment, restore the correct state, inspect status, then verify the pilot claims and perform the pending audiovisual review. Real Kaggle, storage and publishing connections still require verification.

## Continuity and channel setup checkpoint — 2026-10-26

The owner requires every replacement GPT to understand and resume from durable records. Checkpoint after meaningful steps and record external write intents before execution; reconcile unfinished intents after interruption. See `docs/CONTINUITY.md`.

The owner authorized supplied accounts for YouTube channel setup. Seven alias-only slots are in `channels/youtube-registry.json`; all actual channel identities remain unknown. Hosted Composio reported no active YouTube connection; the first consent flow was initiated and is pending. No channel was created. Next: finish consent, list active connections, verify actual account/channel identity, then resolve supported initial creation if needed. Do not store auth links or secrets in Git. Public video posting remains separately unauthorized.

Repository privacy was discussed only; visibility is unchanged. This is a documentation update, not a runtime recovery or channel-creation test.

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
