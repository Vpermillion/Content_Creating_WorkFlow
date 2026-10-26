# Continuity and YouTube setup

Recorded 2026-10-26, Asia/Ulaanbaatar. This is durable project context for a replacement assistant.

## Owner's requirements

- The workspace must survive loss of a chat, assistant, subscription or task machine. A new authorized GPT should understand the goal, current work, failures and exact next action without the old conversation.
- The seven supplied Google-account labels may also be used for YouTube channel setup. Operator profiles and YouTube channels remain separate concepts; the owner has authorized using these accounts for channel creation, subject to verified ownership, supported login and any required provider consent.
- Save channel metadata and setup progress in this repository. Save credentials through a secure connection/secret store separately.
- The owner asked about making the repository private. This was a question, not an instruction to change visibility. No visibility change was made.

Authorization above covers channel setup; it does not authorize video publication, purchases, changing repository visibility, or bypassing verification. Do not request the same channel-setup permission again solely because the original master prompt predated it. Verify the signed-in identity and resolve channel name/handle before creating a public channel.

## Authoritative source and branch

Repository: Vpermillion/Content_Creating_WorkFlow.
At this checkpoint, the default branch is `codex/portable-workspace`. Handoff changes are on `codex/operator-handoff` in [PR #1](https://github.com/Vpermillion/Content_Creating_WorkFlow/pull/1), still open and unmerged when inspected.
Inspect the live PR and branch state before taking over. A default-branch checkout alone may lack these changes. Do not silently merge the PR or start a competing project.

Read AGENTS.md, PROJECT_STATE.md, HANDOFF.md, README.md, docs/MASTER_PROMPT.md and docs/OPERATORS.md. Use the universal prompt in prompts/resume.md.

## What exists and what remains

The earlier implementation reports three prepared pilot jobs awaiting factual and audiovisual review. This session inspected remote documentation; it did not run the worker, restore private data, watch the pilots or reverify past tests. Treat historical runtime claims accordingly.

Actual private job state, media, n8n database and encryption key are separate from Git. Locate or restore the authoritative backup before a status command that could initialize a new empty database. No remotely synced private backup was verified here.

YouTube discovery through hosted Composio found no active connection. One initial connection request was initiated under the label `whatif-alpha`; consent is pending. The label is not verified identity. Do not preserve its short-lived authorization URL in Git. On a later turn, list connections and verify active status and actual account/channel identity before any operation. If expired, initiate a fresh supported connection.

The ordinary YouTube Data API channel resource supports list and update, with no ordinary channel-creation method. The discovered connector can inspect channels; no channel-creation tool was established. Initial creation needs YouTube's supported signed-in setup flow. Request only the necessary user login/verification handoff when required; never pretend an OAuth connection created a channel.

No Google login with a supplied password, YouTube channel creation, live upload or public post occurred in this session. Seven intended slots are recorded in channels/youtube-registry.json with unknown identifiers. Do not interpret unknown as nonexistent.

## Durable progress protocol

1. After each meaningful step, save the stage result, job/content version, artifact locations and errors to authoritative private state. Commit safe source/docs updates and verify their remote revision.
2. Before an external write, persist a non-secret intent record with target, operation ID, desired result and status. After completion, save the returned provider ID/receipt. After interruption, reconcile with the provider before retrying.
3. Keep HANDOFF.md and PROJECT_STATE.md current, with timestamp/timezone, branch/revision, completed checks, blockers, private backup identifier and exact next task. Never include secrets.
4. If the assistant vanishes mid-step, use the last durable checkpoint and pending intents. Do not assume the vanished assistant completed its final notes.
5. Private backup storage and an independently authorized replacement environment still need real verification. Documentation alone does not prove recovery.

## Channel metadata

Use channels/youtube-registry.json for public-safe account-number aliases, verified channel IDs, handles, URLs and setup status. It is documentation only; the worker does not consume it.
Keep email mappings and private provider binding details in secure private configuration. Keep passwords, refresh tokens, cookies and encryption keys outside Git, whether public or private.
Never infer a channel ID from an email address. Check the actual channel associated with each authorized connection, including Brand Account selection, before recording it. Inspect for existing channels before creating new ones.

## Private repository decision

A private repository keeps source, prompts, Git history and handoff available to authorized collaborators and authorized integrations. Each new GPT environment must have repository access; a public URL is no longer enough.
GitHub Free private repositories have limited features. GitHub Pages is unavailable on Free private repositories, standard hosted Actions consume the owner's included quota, and protected branches/code owners/wikis and some advanced security features depend on plan/license.
At inspection this repository was public and reported no Pages site, zero forks, zero stars and zero watchers. The billing plan was not inspected.
Making private does not erase earlier downloads or previously disclosed secrets. It also does not supply hosting or transfer social-account authorization.

References checked 2026-10-26:
- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility
- https://docs.github.com/en/get-started/learning-about-github/githubs-plans
- https://docs.github.com/en/billing/concepts/product-billing/github-actions
- https://developers.google.com/youtube/data/reference/rest/v3/channels

## Exact next steps

1. Complete supported YouTube authorization for the intended first Google account, then list connections and verify actual account/channel identity.
2. Inspect for an existing channel. If none, resolve name/handle and use supported signed-in creation, with manual identity/verification handoff where required.
3. Save verified metadata and status in the registry; proceed sequentially for the remaining account labels.
4. Restore/verify private job state and complete the existing pilots' factual and audiovisual review. Publication remains a separate authorization.
