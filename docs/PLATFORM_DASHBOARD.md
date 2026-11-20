# Publishing destinations

The private [Ifverse Site](https://ifverse-publishing.idealcoyote1.chatgpt.site) is the current account dashboard. It reports missing setup and saved connection status. Use [account linking](../sites/ACCOUNT_LINKING.md) for setup and [CURRENT.md](CURRENT.md) for runtime checks actually observed.

| Platform | Native Site alias | Implemented formats | Checked-in backend binding |
| --- | --- | --- | --- |
| YouTube | `ifverse-anime` | Short | `UCpB_wi5MlernpSJxUf7zWcw`, `@ifverse_anime` |
| Instagram | `ifverse-instagram` | Reel, single JPEG | Not registered |
| Facebook | `ifverse-facebook` | Reel, Page photo feed | Not registered |
| TikTok | `ifverse-tiktok` | Studio handoff; eligible OAuth verification | Not registered |

The Site currently exposes fixed Ifverse targets, one per platform. Register exact IDs in `channels/publishing-accounts.json` before drafting for additional destinations. That registry can hold multiple named accounts; the Site target map needs corresponding implementation for more aliases.

## Status meanings

- A configured alias identifies the intended destination.
- A saved connection means consent previously verified that destination; recheck it when troubleshooting provider access.
- A prepared draft records media/copy and destination choices.
- A provider-confirmed delivery receipt establishes publication. Pending or uncertain states keep their own receipts.

These states do not establish one another. See [ChatGPT publishing](CHATGPT_PUBLISHING.md) for the exact draft/delivery contract.

## Other routes and brands

The [desktop/Actions queue](SOCIAL_PUBLISHING.md) and standalone [YouTube batch uploader](AUTOMATION.md) remain available with separate credentials and receipts. Use one queue for an account/episode.

Snapchat adapters exist in the legacy direct queue but are not exposed by the native Site tools. Hollywood remains a confirmed content brand without a checked-in publishing destination. Earlier browser-tab inventories in [project history](PROJECT_HISTORY.md) are historical observations, not current consent or ownership checks.

The topic board is [TOPIC_REVIEW_BOARD.md](TOPIC_REVIEW_BOARD.md); completed media is indexed in [BATCH_61S.md](BATCH_61S.md). `channels/platform-dashboard.json` retains the earlier recorded inventory and is not the live Site connection store.
