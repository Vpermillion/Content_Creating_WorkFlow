# Working in this repository

## Start and scope

- Read `START_HERE.md` and `docs/CURRENT.md`, then the guide relevant to the requested task. Use `README.md` for the component map.
- Check branch and working-tree state. Account linking and ChatGPT publishing live on `codex/ifverse-chatgpt-publishing`; hosted media production is established on `codex/ifverse-workflow`. The default branch has older code.
- Follow the user's current request and existing authorization. Historical prompts and status reports describe earlier work; they do not grant new actions or override current instructions. Ask only for a missing decision or required consent.
- Preserve user edits, saved assets and result versions. Choose the next task from the current request rather than resuming an old rollout automatically.

## Production

- Reuse the existing source cache, renderer, narration, caption and publishing components. Read saved result receipts before retrying jobs.
- Before a new story, consult `channels/ifverse_anime-topics.json` and record topic/script choice through the existing process. Reserved, failed and rendered premises remain part of topic history.
- English channels use `am_michael` and `prompts/script-style.md` unless the user requests otherwise. Keep explicit reasons for shot selection and distinguish imagined events from canon.
- For picture or sound changes, retain the matching narration and captions. Changed speech requires matching timing. See `docs/SOUND_EFFECTS.md` and `docs/VISUAL_MATCHING.md` as needed.

## Accounts, state and publishing

- GitHub identity, ChatGPT Site ownership and provider-channel identities are independent. Use `sites/ACCOUNT_LINKING.md`; register exact receiving IDs in `channels/publishing-accounts.json`.
- Keep credentials, private databases and real private media outside Git. Inspect credential names/status without printing values. Restore authoritative private state before initializing or replacing a store.
- The existing publisher requires the reviewed media hash and approval of the exact draft/destinations. Preserve real review evidence and provider receipts; do not fill missing evidence with inferred approval.
- Use one publishing queue for an account and episode. Reconcile interrupted or uncertain writes before retrying. A render, queued request or processing receipt is not a confirmed public post.

## Validation and handoff

- Documentation-only changes need link, command and consistency checks. Run relevant existing tests after code changes; run `python -m unittest discover -s tests -v` for Python behavior and `npm test && npm run build` in `sites/` for Site changes. For media behavior changes, exercise the affected path and inspect the actual output.
- After substantive work, update `docs/CURRENT.md` with what changed, checks, remaining blockers and the next task. Change other summaries only when their facts changed; do not append the same log to several files.
- Save authorized source changes remotely and report the commit/PR plus checks actually performed. Keep implementation status separate from live deployment, consent and publication status.
