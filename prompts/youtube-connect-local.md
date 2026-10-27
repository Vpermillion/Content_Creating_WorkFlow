# Local agent: connect Alpha anime through the owner's browser

```text
Continue Vpermillion/Content_Creating_WorkFlow on codex/youtube-oauth, preserving
existing files, private state and unrelated changes. Use the existing checkout
when available. Read AGENTS.md, PROJECT_STATE.md, HANDOFF.md, docs/CONTINUITY.md,
prompts/youtube-connect.md, docs/YOUTUBE.md, docs/YOUTUBE-CONNECTION-RESULT.md
and channels/youtube-registry.json first. Do not merge PRs or overwrite work.

The owner is considering a local agent because the cloud task could not reach
Google or establish the owner-browser callback. Local execution has not yet
been verified. The owner does not know whether a Google Cloud project/Desktop
OAuth client already exists. Discover that status instead of assuming either
existence or absence, and do not create duplicate projects/clients needlessly.

Goal: read-only verification of Alpha's intended @ifverse_anime channel, then
bind its actual returned canonical ID to alpha-1. No live channel identity was
verified in the cloud attempt. The other accounts and uploads remain deferred.

Inspect the local OS, Python, repository access, network and available browser
tools. The current CLI uses fcntl; use a compatible Linux/WSL environment as
documented. Confirm that the owner's consent browser can reach the same
runtime's 127.0.0.1:8765. WSL-to-host browser forwarding must be checked rather
than assumed. A localhost response tested inside one process is insufficient
to prove a different browser reaches it. Do not start a doomed consent flow.

Inspect only known credential file presence/type and binding names. Keep client
JSON, access/refresh tokens, email mappings and passwords outside Git and chat.
Do not copy this cloud machine's generic credentials, private data or .env as a
substitute for local authorization. Do not initialize an empty job DB or
regenerate media just to connect YouTube.

Using supported browser tools and the owner's authenticated Google Cloud
session when available, inspect the selected user-owned project, YouTube Data
API v3, OAuth consent configuration/test-user requirements and Desktop client.
The existing request authorizes configuring the project/client for this task;
complete routine reversible setup within the local session's actual access.
Ask only for a genuinely missing project/account selection, required sign-in or
provider consent. If no project exists, explain the minimum required setup and
use the owner's selected project or authorized creation route. Do not create
external accounts, purchase services, enable billing or request broad account
scopes. If browser operation is unavailable, give the exact smallest manual step.

Download the real Desktop client privately to private/youtube-client.json (or
use an approved secret mount). Install requirements-youtube.txt in a separate
local virtual environment. Preserve TLS verification. Run the existing connect
command with connection alpha-anime and expected handle @ifverse_anime from
an interactive terminal; do not capture consent/callback URLs in build logs.
Request only youtube.readonly, offline access, PKCE and account selection as the
existing CLI does. Let the owner complete Google sign-in, MFA and consent.

The previous cloud-browser attempt failed ownership verification. Do not retry
that recovery loop, bypass verification or reset credentials. A familiar local
device/browser may be appropriate, but does not guarantee Google's acceptance.
If Google rejects the new supported attempt, stop and record the specific
non-secret result. Do not request passwords or authorization codes in chat.

After successful consent, run check for alpha-anime and verify the actual
channel ID, title and handle. Then use bind with slot alpha-1 and that exact
returned ID. A public page, expected handle, fixture or empty response does not
prove ownership. Commit only verified non-secret metadata; keep credentials in
private storage with a separate encrypted-backup plan. Read-only authorization
does not authorize uploads, public posts or channel creation.

Checkpoint safe progress before external writes and after meaningful results.
Update the connection checkpoint, PROJECT_STATE.md, HANDOFF.md and BACKLOG.md.
Report whether the project/client was actually configured, callback proven,
consent completed, live ID verified and binding saved. Preserve the distinction
between tests and live access. Push safe changes to codex/youtube-oauth when
authorized; report the verified remote revision. Run the documented tests if
behavior changes. Do not claim a connection until YouTube confirms it.
```
