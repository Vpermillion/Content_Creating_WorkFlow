# Cloud agent: finish the repository-owned YouTube connection

```text
Continue Vpermillion/Content_Creating_WorkFlow on codex/youtube-oauth.
Read AGENTS.md, PROJECT_STATE.md, HANDOFF.md, docs/CONTINUITY.md,
docs/YOUTUBE.md and channels/youtube-registry.json first. The feature is based
on codex/operator-handoff; inspect branch/PR status and preserve other work.

Current goal: one Alpha anime example first. Anime/cartoon/Marvel-or-Hollywood
are the three planned Alpha slots. Other accounts are deferred. No live channel
identity has yet been established by this project; do not treat the owner's
report of creation or a stored name as API verification.

Use the existing runtime. Inspect only the presence/type of private Google
configuration, never print its values. Enable/use a user-owned YouTube Data API
project and Desktop OAuth client when authorized. Install requirements-youtube.txt
in the runtime environment. Establish the loopback callback route documented
in docs/YOUTUBE.md before starting consent. If no such route exists, record the
specific callback blocker and prepare a supported reachable runtime; never use
OOB codes, chat passwords, or an artificial login bypass.

Run the alpha-anime connect command with the actual expected handle or canonical
channel ID. Let the owner complete Google's consent/verification. This project's
credentials are independent of ChatGPT/Composio connections and browser cookies.
One authorization does not prove access to other channels. Do not request broad
Google account access or upload scopes for this read-only verification task.

After consent, run check and verify the returned channel ID/name/handle against
the intended channel. Then bind the actual ID to alpha-1. Review and commit only
the safe metadata. Preserve the private token file separately with encrypted
storage/backups; never commit it or expose it in logs. Record the actual check
timestamp, result, branch/revision and exact next step in the handoff.

If Google rejects ownership verification again, stop that attempt and report its
specific non-secret error. Do not restart a recovery loop, reset credentials or
claim success from an empty response. A cloud agent may complete independent
sample-video work while authorization is blocked.

Run python -m unittest discover -s tests -v after behavioral changes. The current
OAuth implementation is read-only. The existing publisher remains draft-only;
uploads, public posting, purchases and continuous deployment are separate work.
Do not merge PRs or change repository visibility merely to finish this task.
```
