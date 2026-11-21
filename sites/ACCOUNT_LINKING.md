# Link social accounts

Open the [connection gateway](https://ifverse-publishing.idealcoyote1.chatgpt.site/connect). Choose a platform, sign in with the social account you want to use, and approve access. The gateway saves a single authorized account and asks you to choose when the provider returns several. Use **Add another** to link more accounts. **Reconnect** updates access for that exact account. **Remove** deletes the saved connection from your dashboard.

The private Site admits its owner and any visitors shared through Sites access settings. Each signed-in visitor has a separate account list. Site sign-in and provider sign-in may use different emails. The owner has the preset workflow and ChatGPT publishing tools.

The [account manager](https://ifverse-publishing.idealcoyote1.chatgpt.site/) shows saved accounts and preset workflow connections. In ChatGPT, call `ifverse_connect` for the gateway URL, `ifverse_accounts` for destination aliases, and `ifverse_verify` to recheck a connection.

## Provider setup

The site administrator configures each provider app once and registers the exact HTTPS `/oauth/callback` URL returned by `ifverse_accounts`. Account holders use the provider's sign-in screen. Provider app review, eligible accounts, test-user restrictions, and two-factor authentication still apply.

| Private Site setting | Purpose |
| --- | --- |
| `IFVERSE_SITE_OWNER_EMAIL` | ChatGPT account that can use the preset workflow and publishing tools |
| `IFVERSE_SITE_ORIGIN` | Canonical HTTPS dashboard URL |
| `IFVERSE_ACCOUNT_KEY` | Stable 32-byte base64url key used to encrypt grants |
| `IFVERSE_OAUTH_CONFIG` | Existing provider clients keyed by `youtube`, `meta`, and `tiktok` |
| `IFVERSE_META_OAUTH_CONFIG` | Facebook and linked Instagram client with `client_id`, `client_secret`, `graph_version`, and optional `facebook_login_config_id` and `instagram_login_config_id` |
| `IFVERSE_INSTAGRAM_OAUTH_CONFIG` | Optional direct Instagram client with the Instagram app's `client_id`, `client_secret`, and `graph_version` |
| `IFVERSE_TIKTOK_OAUTH_CONFIG` | TikTok Login Kit client with `client_id`, `client_secret`, and optional approved `scopes` array |
| `IFVERSE_FACEBOOK_PAGE_ID` | Exact Page ID for the preset Facebook destination |

The separate provider settings override their matching entries without replacing the saved Google app configuration. Use a Facebook Login for Business user-token configuration for Facebook Pages. For Instagram, configure the direct professional-account login or use the Facebook Page linked to the professional profile. A TikTok Login Kit sandbox can link with `user.info.basic`. Include approved profile and video scopes for handle lookup and video verification. TikTok publishing opens Studio.

Keep the `DB` binding, account key, and existing database across deployments. The schema is in `drizzle/0000_account_connections.sql`. OAuth sessions and saved connections are scoped to the authenticated Site user ID. Changing the owner email alone does not migrate connections.

## GitHub Pages entry point

Enable **GitHub Actions** under **Settings → Pages** on an eligible GitHub plan. Once the workflow is on the default branch, run **Deploy account entry** in Actions. It publishes `sites/pages/`, which opens the private dashboard. The dashboard handles provider callbacks and encrypted token storage.

## Publishing workflow

Deploy the matching `whatif.publishing_api` build using `deploy/Dockerfile.publishing` on a private HTTPS origin with persistent state. Configure `IFVERSE_BACKEND_URL` and `IFVERSE_BACKEND_TOKEN` in the Site, with the token matching the publisher's `IFVERSE_API_TOKEN`. Backend settings include `IFVERSE_STATE`, `IFVERSE_MEDIA_KEY`, and `IFVERSE_PUBLIC_ORIGIN`.

After linking, use the alias returned by `ifverse_accounts` directly in a draft. The authenticated Site sends the verified identity to the publisher when creating the draft and rechecks the binding for publish and status. The draft preview contains the exact destination, media and caption. Publishing still requires approval of that preview. The Site sends only the selected access grants. Refresh tokens and client secrets stay in the Site.

The checked-in [publishing registry](../channels/publishing-accounts.json) serves preset and standalone destinations. Accounts added through the hosted gateway are read from the Site's private database. Deploy the gateway and publisher from the same branch for support for newly linked destinations.

For private render import, give `IFVERSE_GITHUB_READ_TOKEN` Contents read access on the repository. See [ChatGPT publishing](../docs/CHATGPT_PUBLISHING.md) for draft and media operations. The separate Actions queue uses [its own credentials](../docs/SOCIAL_PUBLISHING.md).
