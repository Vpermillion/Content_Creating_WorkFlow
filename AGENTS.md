# Operator instructions

Read `docs/CURRENT.md` and `README.md` first. For media work, use `docs/MEDIA-TOOLS.md` and the reusable `python -m whatif.media_tools` commands; prefer cached short JSON results over ad-hoc downloading/edit scripts. Load the detailed historical `PROJECT_STATE.md`, `HANDOFF.md` and project brief `docs/MASTER_PROMPT.md` only when the current summary leaves relevant context unresolved. Keep `docs/CURRENT.md` accurate before ending substantial work. The brief alone does not grant purchases, public posting or credential access; active user/platform authorization controls scope. Read `docs/CONTINUITY.md` and the channel registry when resuming account setup.

- Use this existing checkout. Cloud tasks are already isolated; do not create a worktree unless the user requests one.
- Source code and safe workflow exports belong in this repository. The SQLite job database and actual credentials do not belong in Git. Do not create a competing authoritative code copy elsewhere.
- Run commands from the repository root. `python -m whatif status` shows authoritative current state. Look up the job ID before resuming; do not regenerate approved speech needlessly.
- Claim worker leases through `pipeline.run`. Do not edit SQLite by hand to bypass retries, quality review or publication states. An intentionally requested rebuild must record its reason.
- A failed/uncertain remote upload must be reconciled with the actual provider before retry. Never change a mock/test receipt into a real publication receipt.
- Do not mark a pilot publish-ready without factual and audiovisual review. Synthetic prototype voice and illustrative graphics are explicitly labeled. SRT/ASS timings are sentence boundaries, not word alignment.
- Do not print credentials or put them in job inputs, logs, notebooks, exports or handoff notes. Inspect binding names/status, then test actual authorized operations. Existing variable names do not establish account access.
- Current connected tools must be rediscovered by every replacement assistant. Subscription access, personal plugin connections, task files and tokens do not transfer automatically between accounts.
- Run `python -m unittest discover -s tests -v` after behavioral changes. Exercise affected media operations and inspect a rendered frame for visual changes. Record tests and failures accurately.
- Update `PROJECT_STATE.md`, `HANDOFF.md` and `BACKLOG.md` before ending substantial work. Preserve safe demonstration artifacts and push reviewed source changes to the configured user-owned repository when authorized. Do not claim an unpushed local commit is remotely saved.

- For a replacement operator, read `docs/OPERATORS.md` and the selected `prompts/` file. Seven aliases are interchangeable labels, not authorization or live agents. Do not commit account addresses or secrets. Do not spawn agents merely because profiles exist.
- Locate or restore authoritative private data before invoking status in a fresh clone; status can initialize an empty store. Do not confuse that with recovery of old state.

- Assistant replacement is a core requirement: checkpoint after each meaningful completed step, not only at turn end. Persist source remotely and private job state separately. Before any external write, record a non-secret operation ID and intended target; reconcile an interrupted result before retrying.
- Read `docs/CONTINUITY.md` and `channels/youtube-registry.json` before account/channel setup. Channel slots are intended account associations, not proof that a channel exists. Store only verified non-secret channel metadata in Git; never account passwords or OAuth tokens, even in a private repository.

