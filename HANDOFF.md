# Handoff

Start by reading `AGENTS.md` and `PROJECT_STATE.md`. The authoritative code checkout is `/workspace/Content_Creating_WorkFlow`; use it directly, without a new worktree. The uploaded master prompt is in `docs/MASTER_PROMPT.md`.

## Resume now

```sh
cd /workspace/Content_Creating_WorkFlow
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
