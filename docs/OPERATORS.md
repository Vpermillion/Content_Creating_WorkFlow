# Resume with any authorized GPT account

This workspace has seven operator labels corresponding to the seven account numbers supplied by the owner. Labels do not prove account ownership, GitHub access, platform access or a running assistant. The repository is public; real email addresses and supplied secrets are intentionally absent.

## Choose a prompt

| Account label | Alias | Suggested focus | Copy-ready prompt |
| --- | --- | --- | --- |
| 1 | alpha | Workspace coordination | [alpha](../prompts/alpha.md) |
| 2 | beta | Research and scripts | [beta](../prompts/beta.md) |
| 3 | delta | Visuals and scene planning | [delta](../prompts/delta.md) |
| 4 | epsilon | Voice and captions | [epsilon](../prompts/epsilon.md) |
| 5 | zeta | Rendering and quality | [zeta](../prompts/zeta.md) |
| 6 | eta | Workflow and reliability | [eta](../prompts/eta.md) |
| 7 | theta | Publishing drafts and analytics | [theta](../prompts/theta.md) |

These focuses are suggested starting points, not seven required workers. Any authorized operator can resume the entire workflow. One active operator is the default. Operator identities are separate from the one-to-ten topic brands or social accounts the video system may eventually manage. Adding seven GPT profiles does not create seven video channels.

Use [the universal prompt](../prompts/resume.md) when switching assistants without a specialist task. [The registry](../operators/registry.json) contains only public labels and prompt paths; it is documentation, not an automatic login or dispatch service.

## First handoff

1. In the new GPT account, authorize repository access through its available GitHub connection or approved environment setup. Connect the same repository and choose the desired branch explicitly. Do not paste passwords into prompts.
2. Copy the chosen prompt. The assistant reads the project instructions and current handoff before making changes.
3. Restore the correct private application backup and secure runtime configuration if this is a new host. Code alone does not restore the job database, outputs, n8n credentials or encryption key. See [BACKUP.md](BACKUP.md). Use the bundled safe demo snapshot only to demonstrate the included pilots.
4. Inspect the real status and resume existing job IDs. Never interpret a newly initialized empty database as the authoritative previous workspace.
5. Save the completed step and remote source changes before handing off again.

Authentication may need a manual approval or reconnect. No supplied password or token was used to log into Google, ChatGPT, Kaggle or GitHub. This change adds profiles and prompts only; it does not activate those accounts, configure a model API or keep production running between sessions.

## Private identity and credential configuration

If you need a local address mapping, copy [the example](../operators/private-mapping.example.json) to `private/operator-accounts.json`. The whole `private/` directory is ignored by Git. Fill addresses privately on the machine you control; leave them out of public documentation and backups intended for public sharing. This file is optional and no current program consumes it. Ignoring a path does not remove a previously tracked file.

Keep passwords out of that mapping too. Use the provider's supported OAuth/connection flow or a private secret manager for required application tokens. Do not commit credentials, embed them in prompt files or put them in logs. Preserve encrypted n8n credentials and their encryption key through the separate private backup process. Replace any active secrets that were previously shared in chat.

## Concurrency and durable handoff

Prefer one active operator editing a shared checkout. If the owner explicitly assigns simultaneous work, agree on tasks and use separate branches/checkouts as appropriate to that environment's instructions. Existing worker leases protect processing of a job; they do not merge code changes or coordinate editor access. Do not duplicate render, research or publishing work because an assistant changes.

Before ending substantial work, update `PROJECT_STATE.md`, `HANDOFF.md` and `BACKLOG.md`. Use this record:

```text
Date/time (include timezone):
Operator alias:
Repository branch and revision:
Job IDs / content versions affected:
Completed changes and saved artifact references:
Checks actually run and results:
Failures / reconnect requirements:
Exact next task:
Private backup reference (non-secret identifier only):
Remote commit/PR:
```

For private job details use private state/handoff storage; public Markdown should contain only safe summaries. Do not copy raw provider responses that might contain credentials.

## Start with the existing work

The last saved implementation reports three pilots awaiting factual and audiovisual review. Begin by verifying the current state rather than treating that historical report as a live runtime check. Suggested sequence: Alpha inspects the queue, Beta verifies claims, Delta improves relevant visuals, Epsilon handles voice/captions when needed, Zeta checks the final render, Eta closes reliability gaps, and Theta prepares authorized publishing drafts. The same person or assistant may perform all these tasks sequentially.

Switching an assistant preserves progress only when source, private state, outputs and required secrets are available to the replacement environment. This setup provides handoff instructions; a separately configured runner/model is still needed for unattended fresh production.
