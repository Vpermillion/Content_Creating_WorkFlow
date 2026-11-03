# Platform maintenance dashboard

[Editable status data](../channels/platform-dashboard.json) · [Topic choices](TOPIC_REVIEW_BOARD.md) · [Current batch](BATCH_61S.md)

As of 2026-11-03, no live account or OAuth connection is verified. Brand names below are planned names, not verified public handles. YouTube upload code exists; its presence does not establish a connected account or a successful upload. Other publishing integrations are not established.

| Brand | Platform | Account exists | Public handle / ID | OAuth | Integration | Publishing |
| --- | --- | --- | --- | --- | --- | --- |
| ifverse_anime | YouTube | Unverified | Unknown | Unverified | Upload code; live path unverified | Blocked |
| ifverse_anime | TikTok | Unverified | Unknown | Unverified | Not established | Blocked |
| ifverse_anime | Instagram | Unverified | Unknown | Unverified | Not established | Blocked |
| ifverse_anime | Facebook | Unverified | Unknown | Unverified | Not established | Blocked |
| ifverse_anime | Snapchat | Unverified | Unknown | Unverified | Not established | Blocked |
| ifverse_hollywood | YouTube | Unverified | Unknown | Unverified | Upload code; brand setup pending | Blocked |
| ifverse_hollywood | TikTok | Unverified | Unknown | Unverified | Not established | Blocked |
| ifverse_hollywood | Instagram | Unverified | Unknown | Unverified | Not established | Blocked |
| ifverse_hollywood | Facebook | Unverified | Unknown | Unverified | Not established | Blocked |
| ifverse_hollywood | Snapchat | Unverified | Unknown | Unverified | Not established | Blocked |

## Maintenance in GitHub

Use the [maintenance issue template](../.github/ISSUE_TEMPLATE/platform-maintenance.md) for one account/platform. Update the JSON and this table through a normal commit/PR when evidence changes. Keep account existence, OAuth, integration support and actual publication independent. Each has its own verification date; unknown dates stay null. Do not mark all accounts connected because one platform works.

The owner finishes creating accounts and connects them privately later. Only public handles, stable public IDs, dates and non-secret task/receipt references belong here. Passwords, OAuth clients/secrets, tokens, recovery codes and account email addresses belong in private credential storage, never issues, Git or chat.

Before any public operation: owner topic/script choice and actual audiovisual/source-use review, correct live account identity/scopes, a supported tested integration and explicit publication scope must all be established. Current instructions authorize repairs and maintenance preparation only. No new account, public post or recurring scheduler is enabled.

For a real upload, preserve a non-secret receipt with platform, brand, stable account ID, provider post ID, URL, video SHA-256, operation ID, upload time, visibility/processing state and last verification time. Record `published` only after the provider confirms the intended public state. A failed/processing/private upload remains distinct and must be reconciled before retrying. The receipt arrays are currently empty because there are no verified publications.
