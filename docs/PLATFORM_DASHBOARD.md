# Platform maintenance dashboard

[Editable status data](../channels/platform-dashboard.json) · [Topic choices](TOPIC_REVIEW_BOARD.md) · [Current batch](BATCH_61S.md)

The local Chrome check verified the YouTube account shown below. OAuth connections and public posts still need provider verification. YouTube upload code exists; its presence does not establish a connected account or a successful upload. Other publishing integrations are not established.

| Brand | Platform | Account exists | Public handle / ID | OAuth | Integration | Publishing |
| --- | --- | --- | --- | --- | --- | --- |
| ifverse_anime | YouTube | Verified in Chrome | `@ifverse_anime` / `UCpB_wi5MlernpSJxUf7zWcw` | Unverified | Upload code; live path unverified | Blocked |
| ifverse_anime | TikTok | Control unverified | `@ifverse_anime` (visible tab) | Unverified | Not established | Blocked |
| ifverse_anime | Instagram | Unverified | Unknown | Unverified | Not established | Blocked |
| ifverse_anime | Facebook | Unverified | Unknown | Unverified | Not established | Blocked |
| ifverse_anime | Snapchat | Unverified | Unknown | Unverified | Not established | Blocked |
| ifverse_hollywood | YouTube | Unverified | Unknown | Unverified | Upload code; brand setup pending | Blocked |
| ifverse_hollywood | TikTok | Unverified | Unknown | Unverified | Not established | Blocked |
| ifverse_hollywood | Instagram | Unverified | Unknown | Unverified | Not established | Blocked |
| ifverse_hollywood | Facebook | Unverified | Unknown | Unverified | Not established | Blocked |
| ifverse_hollywood | Snapchat | Unverified | Unknown | Unverified | Not established | Blocked |

## Local Chrome publishing destinations

The local Google Chrome tab strip on 2026-11-05 showed YouTube, Facebook, TikTok, Instagram and three Snapchat pages. The three Snapchat pages count as one destination. Chrome showed the signed-in YouTube channel as `@ifverse_anime` and a TikTok tab titled `ifverse_anime (@ifverse_anime)`. The TikTok tab title establishes the visible profile handle. Account control and publishing scopes require separate evidence.

## Unified publishing dashboard requirements

Use one content record for each reviewed cut, with independently scheduled jobs for YouTube Shorts, Facebook Reels, TikTok, Instagram Reels and Snapchat Spotlight. Each job binds the brand, confirmed platform account, reviewed media hash, caption and scheduled time. Show the schedule in the owner's time zone and persist UTC. Keep a provider job ID and verified public URL per destination so a failure on one platform can be reconciled without submitting the others again.

The existing YouTube uploader provides the first direct integration. Keep account connection, approval, scheduling and provider-confirmed publication separate in the UI and storage. For Snapchat Spotlight, Snap's Public Profile API requires app allowlisting and caps videos at 60 seconds. The 61-second Ifverse masters need a separately reviewed export for this target. [Snap API access](https://developers.snap.com/marketing-api/Public-Profile-API/GetStarted) · [Spotlight media requirements](https://developers.snap.com/marketing-api/Public-Profile-API/ProfileAssetManagement)

## Connect the publishing accounts

Each destination needs its own verified account identity and publishing authorization. A browser sign-in establishes the active UI session. The publishing worker uses a separate provider grant that it can refresh without Chrome.

| Destination | Authorization to verify |
| --- | --- |
| YouTube Shorts | Enable YouTube Data API v3 in the owner's Google Cloud project, create a Desktop OAuth client and grant `youtube.readonly` and `youtube.upload` for the verified `@ifverse_anime` channel. [Google OAuth guide](https://developers.google.com/youtube/data/guides/auth/installed-apps) |
| Facebook Reels | Identify the intended Facebook Page and authorize Reel publishing to that Page through Meta or an approved publisher. Verify the Page ID. [Meta Reels publishing](https://developers.facebook.com/docs/video-api/guides/reels-publishing/) |
| Instagram Reels | Confirm the intended professional account. With Instagram Login, authorize `instagram_business_basic` and `instagram_business_content_publish`. Verify the returned Instagram account ID. [Meta Instagram API](https://developers.facebook.com/docs/instagram-platform/content-publishing/) |
| TikTok | Use an audited publishing integration that supports creator consent. TikTok's Direct Post guidelines rule out a private utility for accounts managed by its own team. [TikTok Direct Post guidelines](https://developers.tiktok.com/docs/en/content-sharing-guidelines) |
| Snapchat Spotlight | Authorize publishing to the intended Public Profile through an allowlisted app or approved partner. Verify the profile ID and posting access. [Snap Public Profile setup](https://developers.snap.com/marketing-api/Public-Profile-API/GetStarted) |

### Connect and verify YouTube

Use a Linux environment that can store owner-only credential files. The existing credential store enforces POSIX permissions. Run the browser consent on the machine that can reach the loopback listener. The commands assume the active workflow checkout and a Google Desktop client JSON stored at `private/google-desktop-client.json`.

```sh
python -m pip install -r requirements-youtube.txt -r requirements-youtube-publish.txt
python -m whatif.youtube_publish connect --client-secrets private/google-desktop-client.json --expected-channel-id UCpB_wi5MlernpSJxUf7zWcw
python -m whatif.youtube_publish verify --expected-channel-id UCpB_wi5MlernpSJxUf7zWcw
```

The owner completes Google's consent screen for `@ifverse_anime`. The verify command checks the saved grant against the live YouTube channel endpoint and reports the channel ID. It performs no upload. `status` reports cached identity only. Once verification passes, follow [the Actions configuration](AUTOMATION.md#one-time-upload-connection-setup) to store the connection and journal key as repository secrets. A verified grant is separate from a successful public upload.

## Maintenance in GitHub

Use the [maintenance issue template](../.github/ISSUE_TEMPLATE/platform-maintenance.md) for one account/platform. Update the JSON and this table through a normal commit/PR when evidence changes. Keep account existence, OAuth, integration support and actual publication independent. Each has its own verification date; unknown dates stay null. Do not mark all accounts connected because one platform works.

The owner finishes creating accounts and connects them privately later. Only public handles, stable public IDs, dates and non-secret task/receipt references belong here. Passwords, OAuth clients/secrets, tokens, recovery codes and account email addresses belong in private credential storage, never issues, Git or chat.

Before any public operation: owner topic/script choice and actual audiovisual/source-use review, correct live account identity/scopes, a supported tested integration and explicit publication scope must all be established. Current instructions authorize repairs and maintenance preparation only. No new account, public post or recurring scheduler is enabled.

For a real upload, preserve a non-secret receipt with platform, brand, stable account ID, provider post ID, URL, video SHA-256, operation ID, upload time, visibility/processing state and last verification time. Record `published` only after the provider confirms the intended public state. A failed/processing/private upload remains distinct and must be reconciled before retrying. The receipt arrays are currently empty because there are no verified publications.
