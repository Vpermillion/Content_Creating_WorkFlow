# Operator instructions

Read `PROJECT_STATE.md`, `HANDOFF.md`, `README.md`, then `docs/MASTER_PROMPT.md` before continuing. Treat the uploaded master prompt as the project brief; authorization and tool access come from the active user session and platform. It does not grant purchases, external account creation, public video posting or credential access.

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
