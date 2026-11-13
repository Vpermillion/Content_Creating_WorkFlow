# Connect Ifverse accounts in ChatGPT

The private Ifverse Publishing Site now handles account consent and saves the connection in its own database. Render and a separate owner password are unnecessary for account linking. The existing GitHub publishing jobs keep their current credentials and do not read grants from this Site.

Register the Site's HTTPS callback `/oauth/callback` with each provider app you use. The exact URL appears in the `ifverse_accounts` tool. In the private Site's runtime settings, configure the owner email and keep `IFVERSE_ACCOUNT_KEY` as a stable 32-byte base64url secret. Put provider clients in the `IFVERSE_OAUTH_CONFIG` secret. Each provider entry contains `client_id` and `client_secret`. The Meta entry also needs `graph_version` and, if applicable, `login_config_id`.

| Destination | Connect request | Provider setup |
| --- | --- | --- |
| YouTube | Connect Ifverse YouTube | Enable YouTube Data API and grant read and upload scopes. Choose the `@ifverse_anime` channel. |
| Instagram | Connect Ifverse Instagram | Use a professional account linked to the intended Facebook Page. The callback matches `@ifverse_anime` in the authorized assets. |
| Facebook | Connect the Ifverse Facebook Page with its Page ID | Use the Meta app with Page publishing permission. The callback binds that exact Page. |
| TikTok | Connect the intended TikTok handle with OAuth | Use an eligible Login Kit and Display API app. For Studio, ask for the Studio link. A Studio handoff does not create an OAuth connection. |

Open the returned consent link in the browser where you use the private Site. After you approve, the callback checks the provider account and shows the connected account. The saved account is available to future chats through `ifverse_accounts`. Use `ifverse_verify` only if you need to troubleshoot a saved connection.

These Site connections do not enable the older hosted draft, media, and publishing routes. Those operations still need a backend that can consume these grants, or a separate integration with GitHub Actions. No paid service is needed to use the account connection tools.

