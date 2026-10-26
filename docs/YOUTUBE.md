# Connect the actual YouTube channels

The repository now has an optional **read-only OAuth connection CLI**. It can authorize one channel, retain refresh credentials privately, verify that YouTube returns the intended channel, and write verified public metadata into the channel registry. It does not create channels, upload, publish, schedule, edit channel branding or activate n8n.

This project connection is independent of ChatGPT/Composio and of a cloud-browser login. Google authorization must be completed for this project's OAuth client. An account email, a public channel URL, a GitHub secret name or a successful software test is not proof of authorized channel access.

## What the cloud agent needs

1. Use `codex/youtube-oauth`, based on `codex/operator-handoff`. The latter contains the latest Alpha-only entertainment plan and is the base of this feature. Inspect the PR/default-branch state before switching a checkout; preserve unrelated work. Do not merge without the owner's instruction.
2. Use Linux/Python 3.12+ and a private persistent credentials directory. These commands use `fcntl` file locks and are not native Windows commands; WSL/Linux is suitable.
3. In a user-owned Google Cloud project, enable **YouTube Data API v3**, configure the OAuth consent application and permitted test users as applicable, then create a **Desktop app** OAuth client. Keep its downloaded client JSON in `private/youtube-client.json` or another private secret mount. Existing securely configured credentials may be used if they are the correct client type; inspect presence and type without printing values. A GitHub connector cannot read repository secret values back.
4. Provide a reachable loopback callback from the user's consent browser to the machine running this command. The CLI binds only `127.0.0.1:8765`, times out after five minutes and uses PKCE. It does not implement a publicly hosted web callback or the deprecated copy/paste authorization-code flow.

Install the optional Google SDK dependencies in the runtime's virtual environment. Do not run interactive OAuth through GitHub Actions or save its authorization/callback URLs in build logs:

```sh
python -m pip install -r requirements-youtube.txt
```

The standard worker has no new mandatory dependency. These packages are not installed into the existing Docker worker by this change; run the connection CLI in the prepared host/virtual environment. Do not assume that building the existing worker image also installs them.

## Callback on a cloud machine

An authorization URL can open in the owner's familiar local browser, but its redirect to `127.0.0.1:8765` must reach the waiting CLI. When SSH is available, the owner can forward the local port to the cloud machine before authorizing:

```sh
ssh -N -L 8765:127.0.0.1:8765 YOUR_CLOUD_HOST
```

Use the actual approved host. The connection command must use the same port. Another valid arrangement runs both the CLI and browser on the same supported Linux environment. A browser-only public Codespaces port URL is not automatically a valid loopback callback.

If this environment has neither a usable tunnel nor a supported same-machine browser, stop at `callback_unreachable` in the handoff. Choose a reachable runtime or separately implement a registered HTTPS Web-app OAuth callback. Do not claim that this loopback implementation is deployed as a public web service, ask for authorization codes in chat, or use an OOB workaround.

Google consent, MFA, identity verification and account eligibility still apply. This does not bypass the earlier Alpha sign-in rejection. OAuth applications in testing or with revoked/expired grants can require reconnection; offline credentials are not a promise of permanent access.

## Connect Alpha's channels separately

These are the owner's requested/planned handles, not verified live identifiers. Adjust an expected handle to an actual user-confirmed handle if necessary. The third category/name remains provisional between Marvel-only and wider Hollywood; do not silently rename it.

```sh
python -m whatif.youtube connect --connection alpha-anime --client-secrets private/youtube-client.json --expected-handle @ifverse_anime
python -m whatif.youtube connect --connection alpha-cartoon --client-secrets private/youtube-client.json --expected-handle @ifverse_cartoon
python -m whatif.youtube connect --connection alpha-marvel --client-secrets private/youtube-client.json --expected-handle @ifverse_marvel
```

Start with `alpha-anime` and one sample video. Run authorization sequentially, selecting the intended channel/Brand Account on Google's screen. One Google login does not establish access to all three channels. If the user instead selected `ifverse_hollywood`, use that actual handle and a suitable alias after checking the plan.

The CLI requests only `youtube.readonly`, offline access and account selection. It asks YouTube for `channels.list(mine=true)`, checks the returned ID/handle, and saves credentials only after a match. A wrong selected channel, absent channel, refused scope or missing refresh token produces a blocked result. It never chooses a first channel merely because one was returned.

Prefer `--expected-channel-id UC...` once the actual canonical ID is known. IDs remain stable through channel renames. A connection alias cannot silently be replaced with a different channel. `--replace` permits explicit reauthorization of the same saved channel only.

## Check access and save channel metadata

```sh
python -m whatif.youtube status
python -m whatif.youtube check --connection alpha-anime
```

`status` only inspects saved non-secret metadata and labels it `stored_not_live_checked`. `check` performs an actual API request, refreshes expired credentials when permitted, and verifies the saved channel ID again. Only successful `connect`/`check` results say `verified_readonly`. Google errors are summarized without echoing tokens or raw exception details. Refresh failures can be caused by network or authorization problems; they are not automatically treated as proof of revocation.

After a successful live check, use the returned ID to bind the intended registry slot. Replace the placeholder with the real ID; do not copy this example literally:

```sh
python -m whatif.youtube bind --connection alpha-anime --slot alpha-1 --expected-channel-id UC_ACTUAL_22_CHARACTER_SUFFIX
```

Alpha slots: `alpha-1` anime, `alpha-2` cartoon, `alpha-3` proposed Marvel/Hollywood. `bind` performs another live check and refuses conflicting or duplicate channel IDs. It writes only ID, display name, handle, URL and verification timestamp/status into `channels/youtube-registry.json`. It does not grant publishing authorization. Review and commit this safe metadata after verifying that the slot/content topic matches the selected channel.

## Credentials and recovery

- Default storage: `private/youtube/CONNECTION.json`, containing channel metadata and **secret access/refresh credentials**, with directory mode 0700 and file mode 0600. Use `YOUTUBE_CREDENTIALS_DIR` or the global `--credentials-dir` option for a persistent private mount. Root directory permissions are checked rather than silently broadened.
- These JSON files are permission-protected, not encrypted by this application. Keep them in encrypted private storage or a suitable secret-management deployment and back them up securely. Git and Docker build contexts exclude the default private paths and common downloaded client/token filenames. Do not override this by force-adding files.
- Separate files and per-connection OS locks avoid overlapping refresh/reauthorization. Registry writes also use a lock and atomic replacement. Processes must use the same credential directory to share a connection.
- A replacement authorized agent needs the same private credential backup and client configuration as appropriate. The repository alone cannot restore tokens. The standard application backup covers `data/`, not this separate credentials directory.
- Do not print client JSON, credentials, environment values, cookies or SDK HTTP-debug logs. Never commit short-lived consent links/callback URLs. CLI output uses an allowlist for non-secret connection summaries.
- No revoke/delete command is added. The owner can revoke the OAuth grant through Google's account settings when desired. Losing or revoking credentials leaves the job/media checkpoints intact.

## Remaining work after successful authorization

The next feature is a YouTube upload provider integrated with the existing job/publication state machine: a separately authorized upload scope, a private test upload, resumable upload recovery, actual receipt IDs and uncertain-delivery reconciliation. Public publication/scheduling needs its own explicit scope and platform checks. A read-only connection does not enable any of these actions.

After the first channel/sample works, add the other Alpha channels. The other six Google accounts remain deferred. Automatic stock selection, Kaggle execution, durable external backups, narration quality and production hosting remain separate backlog items.

## Validation and references

The tests use synthetic credentials and mocked provider responses for wrong-account rejection, refresh failure, scope denial, pagination, concurrent access, private storage and registry binding. Passing them does not establish a live Google connection. A separate local smoke check used the real Google SDK to build a PKCE/readonly/offline authorization URL and load a fixture credential without sending a Google request.

Official references checked during implementation:

- https://developers.google.com/identity/protocols/oauth2/native-app
- https://developers.google.com/youtube/data/guides/auth/server-side-web-apps
- https://developers.google.com/youtube/data/reference/rest/v3/channels/list
- https://support.google.com/youtube/answer/4642409

No real OAuth client, token exchange, channel ID, upload, host deployment or n8n connection has been verified in this development environment.
