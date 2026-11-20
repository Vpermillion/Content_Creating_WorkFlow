# Link Ifverse accounts

Open [Ifverse Accounts](https://ifverse-publishing.idealcoyote1.chatgpt.site/) as the Site owner. Select the platform's **Add account** button, choose the provider login, and approve access. If several channels, Pages, or profiles are available, select the one to save. Repeat to add another account. Choosing a destination again updates its existing connection.

The GitHub login manages source code. The ChatGPT login opens the private dashboard. Each social login grants access to its own channel, Page, or profile. The emails can all differ.

Use **Publishing workflow** to reconnect an existing preset Ifverse destination. For a new connection, `ifverse_accounts` returns the saved alias and exact provider ID. Use `ifverse_verify` to recheck a connection.

## Provider setup

Configure each provider app once and register the exact HTTPS `/oauth/callback` URL returned by `ifverse_accounts`. Account holders use the provider's sign-in screen. Provider app review, eligible accounts, test-user restrictions, and two-factor authentication still apply.

| Private Site setting | Purpose |
| --- | --- |
| `IFVERSE_SITE_OWNER_EMAIL` | ChatGPT account allowed to manage connections |
| `IFVERSE_SITE_ORIGIN` | Canonical HTTPS dashboard URL |
| `IFVERSE_ACCOUNT_KEY` | Stable 32-byte base64url key used to encrypt grants |
| `IFVERSE_OAUTH_CONFIG` | Provider clients keyed by `youtube`, `meta`, and `tiktok`, with `client_id` and `client_secret` |
| `IFVERSE_FACEBOOK_PAGE_ID` | Exact Page ID for the preset Ifverse Facebook destination |

Meta also needs a supported `graph_version` and may need `login_config_id`. The Instagram flow uses a Facebook Page linked to a professional Instagram profile. TikTok linking needs an eligible Login Kit and Display API app. TikTok publishing opens Studio.

Keep the `DB` binding, account key, and existing database across deployments. The schema is in `drizzle/0000_account_connections.sql`. OAuth sessions and saved connections are scoped to the authenticated Site user ID. Changing the owner email alone does not migrate connections.

## GitHub Pages entry point

Enable **GitHub Actions** under **Settings → Pages** on an eligible GitHub plan. Once the workflow is on the default branch, run **Deploy Ifverse account entry** in Actions. It publishes `sites/pages/`, which opens the private dashboard. The dashboard handles provider callbacks and encrypted token storage.

## Publishing workflow

Deploy the matching `whatif.publishing_api` build using `deploy/Dockerfile.publishing` on a private HTTPS origin with persistent state. Configure `IFVERSE_BACKEND_URL` and `IFVERSE_BACKEND_TOKEN` in the Site, with the token matching the publisher's `IFVERSE_API_TOKEN`. Backend settings include `IFVERSE_STATE`, `IFVERSE_MEDIA_KEY`, and `IFVERSE_PUBLIC_ORIGIN`.

Register each new account's saved alias and provider ID in [the publishing registry](../channels/publishing-accounts.json) before creating drafts for it. The checked-in registry currently contains only the preset Ifverse YouTube channel. Linking an account leaves the registry and draft approval under your control. For approved operations, the Site refreshes and sends only the selected access grants to the authenticated backend. Refresh tokens and client secrets stay in the Site.

For private render import, give `IFVERSE_GITHUB_READ_TOKEN` Contents read access on the repository. See [ChatGPT publishing](../docs/CHATGPT_PUBLISHING.md) for draft and media operations. The separate Actions queue uses [its own credentials](../docs/SOCIAL_PUBLISHING.md).
