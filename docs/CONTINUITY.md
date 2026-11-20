# Continuity and recovery

Use [CURRENT.md](CURRENT.md) for the current branch, results, checks and next task. [START_HERE.md](../START_HERE.md) routes to task-specific guides; historical reports are optional context.

## What persists where

| State | Location |
| --- | --- |
| Source, requests, public destination IDs and topic history | Git repository |
| Completed review media and render receipts | Selected `codex/results/*` commits and workflow artifacts; see [batch index](BATCH_61S.md) |
| Site OAuth grants and pending consent sessions | Site database, encrypted with `IFVERSE_ACCOUNT_KEY`, keyed by authenticated Site user ID |
| Hosted drafts, media, delivery receipts and resumable journals | Private `IFVERSE_STATE` volume |
| Standalone publisher credentials | Private local files or the relevant Actions secrets |
| Optional legacy worker/n8n state | Separate application/database volumes and encryption configuration; [BACKUP.md](BACKUP.md) |

Source access does not restore private runtime state. Keep the Site encryption key and backend state through redeployments. An owner-email change does not transfer grants saved under another authenticated user ID.

## Resume an interrupted task

1. Inspect the selected branch and existing edits. Retrieve the request, topic/result commit or saved draft ID for the task.
2. Read the existing outcome before retrying. Reuse completed media; preserve verified narration/captions for visual-only work.
3. For publication, inspect per-destination receipts. Reconcile an uncertain provider write using its existing session/checkpoint rather than submitting a new post.
4. If moving hosts, restore the authoritative private store before commands that initialize a new one. Verify restoration without overwriting existing state.
5. Save changes and a concise CURRENT entry: result IDs, checks, unresolved blocker and next action. Update other documentation only when its facts changed.

## Account access

Each replacement ChatGPT session needs authorized repository and Site access. GitHub login, Site owner and social-channel login may differ. Provider consent checks exact destination IDs; a public handle or a browser tab alone does not grant publishing access. Use [account linking](../sites/ACCOUNT_LINKING.md) for the current flow.

The old account-recovery attempts and operator rollout in [PROJECT_HISTORY.md](PROJECT_HISTORY.md) describe past sessions. Resume them only when the current request calls for that work.
