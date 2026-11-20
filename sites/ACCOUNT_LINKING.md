# Link Ifverse accounts

Open the private [Ifverse Publishing Site](https://ifverse-publishing.idealcoyote1.chatgpt.site) with the ChatGPT account configured as its owner. Choose **Connect**, select the provider account, and approve access. The callback verifies the intended destination and saves an encrypted connection automatically. `ifverse_accounts` reports the same saved connections; use `ifverse_verify` to recheck one when troubleshooting.

## Three independent identities

| Identity | Used for |
| --- | --- |
| GitHub repository access | Reading source and pinned render results; maintaining code and workflow requests |
| ChatGPT Site owner | Calling the private tools, opening the dashboard and completing the Site callback |
| Social provider account | Granting access to the intended YouTube channel, Instagram profile, Facebook Page or TikTok identity |

The login emails can differ. `sites/worker.mjs` compares the authenticated ChatGPT email with `IFVERSE_SITE_OWNER_EMAIL` and requires an authenticated user ID. It does not compare social-account email with the GitHub or ChatGPT email.

**Owner-check 403:** inspect the configured owner setting and the authenticated identity supplied to the Site. The error happens before channel lookup; it does not reveal whether a channel is connected. Connections and pending consent sessions are partitioned by Site user ID. Changing the owner email alone does not migrate another user's connections.

## Configure the Site

| Setting | Purpose |
| --- | --- |
| `IFVERSE_SITE_OWNER_EMAIL` | ChatGPT account allowed to use the Site |
| `IFVERSE_SITE_ORIGIN` | Canonical HTTPS Site origin used to build the callback |
| `IFVERSE_ACCOUNT_KEY` | Stable 32-byte base64url key used to encrypt saved grants |
| `IFVERSE_OAUTH_CONFIG` | Provider clients: `youtube`, `meta` and/or `tiktok`, each with `client_id` and `client_secret` |
| `IFVERSE_FACEBOOK_PAGE_ID` | Exact intended Page ID; required for the dashboard's Facebook button |
| `IFVERSE_BACKEND_URL` | Private publisher's HTTPS origin |
| `IFVERSE_BACKEND_TOKEN` | Credential matching the publisher's `IFVERSE_API_TOKEN` |

The Meta client also needs `graph_version` and optionally `login_config_id`. Keep client secrets and the storage key in private Site settings. The Site uses the `DB` database binding declared in `.openai/hosting.json`; apply `drizzle/0000_account_connections.sql` and retain that database/key across deployments. `build.mjs` packages the native Worker and account module.

Register the exact Site `/oauth/callback` URL with each provider app. `ifverse_accounts` returns it after owner access succeeds. This hosted flow uses registered web callbacks; it does not require WSL or the desktop loopback CLI.

## Destination checks and limits

| Alias | Current target | Consent behavior |
| --- | --- | --- |
| `ifverse-anime` | YouTube `UCpB_wi5MlernpSJxUf7zWcw`, `@ifverse_anime` | Checks channel ID and handle; requests read/upload and offline access |
| `ifverse-instagram` | Instagram `@ifverse_anime` | Checks the professional profile linked to an authorized Facebook Page |
| `ifverse-facebook` | Configured Page ID | Binds that exact authorized Page |
| `ifverse-tiktok` | `@ifverse_anime`, or the handle supplied to `ifverse_connect` | OAuth checks identity/profile/video access; `method=studio` returns a manual handoff |

The Site's target map is in `accounts.mjs`. It currently exposes one alias per platform, not an arbitrary channel picker. Different provider login accounts can authorize these destinations. Changing or adding YouTube/Instagram targets requires a deliberate target-map update as well as backend registration.

Provider app setup and applicable permissions must be available. TikTok OAuth requires an eligible Login Kit/Display setup; Studio does not create an OAuth connection. TikTok publication remains a Studio handoff.

## Connect the publisher

Deploy the matching `whatif.publishing_api` version on an HTTPS host with persistent private state. `deploy/Dockerfile.publishing` is the supplied container. Backend settings include `IFVERSE_STATE`, `IFVERSE_API_TOKEN`, `IFVERSE_MEDIA_KEY` and `IFVERSE_PUBLIC_ORIGIN`; keep the API and media-signing keys independent. The optional browser owner forms use a separate `IFVERSE_OWNER_PASSWORD`.

Set the Site's backend origin/token to match. For approved publishing, status checks and TikTok Display verification, the Site refreshes selected grants and sends their access tokens to authenticated `/broker/*` routes. Refresh tokens and provider client secrets remain in the Site. The backend validates each account against the registry/draft and uses the access grants for that request.

Register exact receiving IDs in [`channels/publishing-accounts.json`](../channels/publishing-accounts.json) before creating drafts. **The checked-in registry currently contains only YouTube.** Instagram, Facebook and TikTok need their own bindings; Site consent does not automatically write them into Git.

For existing private render import, configure `IFVERSE_GITHUB_READ_TOKEN` on the backend with Contents read access to this repository. See [ChatGPT publishing](../docs/CHATGPT_PUBLISHING.md) for the draft/media contract.

The separate Actions/desktop queue uses its own credentials, described in [SOCIAL_PUBLISHING.md](../docs/SOCIAL_PUBLISHING.md). Select one publishing queue per account/episode; there is no automatic cross-queue migration.
