# Connect Ifverse publishing accounts

Open the private Ifverse Publishing Site as its owner. The dashboard shows YouTube, Instagram, Facebook and TikTok, whether consent is recorded, and which settings are missing. Select **Connect** for the platform you want. The provider asks you to choose an account and approve its requested permissions. The callback verifies the intended destination and saves the encrypted connection. The same connections are reported by `ifverse_accounts` in ChatGPT.

Register the Site's HTTPS callback `/oauth/callback` once with each provider app. The exact URL appears in `ifverse_accounts`. In the private Site settings, set the owner's email and keep `IFVERSE_ACCOUNT_KEY` as a stable 32-byte base64url secret. Put provider clients in the `IFVERSE_OAUTH_CONFIG` secret. Each provider entry contains `client_id` and `client_secret`. The Meta entry also needs `graph_version` and, if applicable, `login_config_id`. Set `IFVERSE_FACEBOOK_PAGE_ID` to the exact intended Page ID when enabling the Facebook dashboard button.

| Destination | Connect request | Provider setup |
| --- | --- | --- |
| YouTube | Connect Ifverse YouTube | Enable YouTube Data API and grant read and upload scopes. Choose the `@ifverse_anime` channel. |
| Instagram | Connect Ifverse Instagram | Use a professional account linked to the intended Facebook Page. The callback matches `@ifverse_anime` in the authorized assets. |
| Facebook | Connect the Ifverse Facebook Page with its Page ID | Use the Meta app with Page publishing permission. The callback binds that exact Page. |
| TikTok | Connect the intended TikTok handle with OAuth | Use an eligible Login Kit and Display API app. For Studio, ask for the Studio link. A Studio handoff does not create an OAuth connection. |

Use `ifverse_verify` after a provider rejects an operation or to recheck the live connection. A saved connection shows that the callback verified the destination when it was saved. Provider consent, permission changes, and any platform review remain separate from Site setup.

The repository's hosted publisher consumes these connections for approved drafts, delivery status checks, and TikTok Display verification. Deploy the matching `whatif.publishing_api` version on your own HTTPS host and configure `IFVERSE_BACKEND_URL` and `IFVERSE_BACKEND_TOKEN` in the Site. The token must match the publisher's `IFVERSE_API_TOKEN`. Register each exact receiving account ID in `channels/publishing-accounts.json` before creating drafts for it. The Site refreshes grants and sends only the selected accounts' provider access tokens to the publisher over the authenticated request. Refresh tokens and OAuth client secrets stay in the Site. The publisher uses the grants only for that request and checks each account against the repository registry and reviewed draft.

The older standalone GitHub Actions job has a separate credential contract described in [Social publishing](../docs/SOCIAL_PUBLISHING.md). Use one publishing queue for a given account and episode. TikTok uses a Studio handoff for publication.
