# Platform maintenance dashboard

[Editable status data](../channels/platform-dashboard.json) · [Topic choices](TOPIC_REVIEW_BOARD.md) · [Current batch](BATCH_61S.md)

The local Chrome check verified the YouTube account shown below. OAuth connections and public posts still need provider verification. YouTube upload code exists; its presence does not establish a connected account or a successful upload. The repository has direct Meta and Snap adapters with live verification pending.

| Brand | Platform | Account exists | Public handle / ID | OAuth | Integration | Publishing |
| --- | --- | --- | --- | --- | --- | --- |
| ifverse_anime | YouTube | Verified in Chrome | `@ifverse_anime` / `UCpB_wi5MlernpSJxUf7zWcw` | Unverified | Upload code; live path unverified | Blocked |
| ifverse_anime | TikTok | Control unverified | `@ifverse_anime` (visible tab) | Unverified | Manual Studio step | Owner action required |
| ifverse_anime | Instagram | Unverified | Unknown | Unverified | Direct adapter; live test pending | Blocked |
| ifverse_anime | Facebook | Unverified | Unknown | Unverified | Direct adapter; live test pending | Blocked |
| ifverse_anime | Snapchat | Unverified | Unknown | Unverified | Direct adapter; allowlisting required | Blocked |
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
| Facebook Reels | Identify the intended Facebook Page and authorize Reel publishing to that Page through Meta. Verify the Page ID. [Meta Reels publishing](https://developers.facebook.com/docs/video-api/guides/reels-publishing/) |
| Instagram Reels | Confirm the intended professional account. With Instagram Login, authorize `instagram_business_basic` and `instagram_business_content_publish`. Verify the returned Instagram account ID. [Meta Instagram API](https://developers.facebook.com/docs/instagram-platform/content-publishing/) |
| TikTok | Use TikTok Studio for this private workflow. TikTok's Direct Post guidelines rule out a private utility for accounts managed by its own team. [TikTok Direct Post guidelines](https://developers.tiktok.com/docs/en/content-sharing-guidelines) |
| Snapchat Spotlight | Authorize publishing to the intended Public Profile through an allowlisted app. Verify the profile ID and posting access. [Snap Public Profile setup](https://developers.snap.com/marketing-api/Public-Profile-API/GetStarted) |

### Connect and verify YouTube

Use a Linux environment that can store owner-only credential files. The existing credential store enforces POSIX permissions. Run the browser consent on the machine that can reach the loopback listener. The commands assume the active workflow checkout and a Google Desktop client JSON stored at `private/google-desktop-client.json`.

```sh
python -m pip install -r requirements-youtube.txt -r requirements-youtube-publish.txt
python -m whatif.youtube_publish connect --client-secrets private/google-desktop-client.json --expected-channel-id UCpB_wi5MlernpSJxUf7zWcw
python -m whatif.youtube_publish verify --expected-channel-id UCpB_wi5MlernpSJxUf7zWcw
```

The owner completes Google's consent screen for `@ifverse_anime`. The verify command checks the saved grant against the live YouTube channel endpoint and reports the channel ID. It performs no upload. `status` reports cached identity only. Once verification passes, follow [the Actions configuration](AUTOMATION.md#one-time-upload-connection-setup) to store the connection and journal key as repository secrets. A verified grant is separate from a successful public upload.

## Run the repository-owned queue

Run `python scripts/publishing_app.py` for the desktop controls. Use Python 3.10 or later with Tk and `ffprobe`. The [queue worker](../scripts/publishing_dashboard.py) runs on a machine you control and sends uploads directly to each platform. There is no publishing service subscription. The existing YouTube uploader requires a Linux environment with POSIX permissions and an authenticated checkout.

| Destination | Queue behavior | Private setup |
| --- | --- | --- |
| YouTube Shorts | Calls the existing reviewed batch uploader for one episode and uses its resumable journal and receipt. | Set `IFVERSE_ANIME_CHANNEL_ID` and complete the direct YouTube connection above. |
| Facebook Reels | Verifies the intended Page, uploads the reviewed MP4 directly to Meta and checks the Reel status. | Set `IFVERSE_FB_PAGE_ID`, `IFVERSE_FB_PAGE_TOKEN` and the app's `IFVERSE_META_GRAPH_VERSION`. Grant Page publishing access. |
| Instagram Reels | Verifies the professional account, uploads the MP4 to Meta's resumable container and publishes once processing finishes. | Set `IFVERSE_IG_ID`, `IFVERSE_IG_TOKEN` and `IFVERSE_META_GRAPH_VERSION`. Use Instagram Login with the publishing grant. |
| Snapchat Spotlight | Encrypts the MP4, uploads it directly to Snap and tracks the Spotlight through moderation. | Install `cryptography`. Obtain app allowlisting and profile publishing access, then supply `IFVERSE_SNAP_PROFILE_ID` and a valid `IFVERSE_SNAP_ACCESS_TOKEN`. |
| TikTok | Shows a manual action and opens TikTok Studio at the scheduled step. | Complete the post in TikTok Studio. TikTok excludes private utilities for accounts your team manages from Direct Post. |

Keep tokens in the worker's private environment. Meta and Snap credentials come from the owner-controlled developer apps. Keep tokens current according to each provider's expiry and renewal rules. The repository checks the supplied account before writing. Use **Check account** or `python scripts/publishing_dashboard.py verify PLATFORM ACCOUNT_ID`. The Facebook and Snapchat destinations need separately reviewed vertical exports of 60 seconds or less from the 61-second masters. [Meta Facebook Reels API](https://www.postman.com/meta/facebook/documentation/r56bjfd/facebook-api) · [Meta Instagram Content Publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing/) · [Snap Public Profile setup](https://developers.snap.com/marketing-api/Public-Profile-API/GetStarted) · [TikTok guidelines](https://developers.tiktok.com/docs/en/content-sharing-guidelines)

Put one destination or an array of up to five distinct destinations for one episode in an ignored `private/publishing/reviewed.json`. This example is a shape only. Use the actual owner decision, exact artifact hashes and review evidence before queueing.

```json
{
  "brand": "ifverse_anime",
  "episode": "TOPIC_ID",
  "platform": "facebook",
  "account_id": "CONFIRMED_PAGE_ID",
  "scheduled_for": "2027-01-01T19:00:00+08:00",
  "video": "artifacts/EPISODE/approved-reel.mp4",
  "master_sha256": "SELECTED_MASTER_SHA256",
  "video_sha256": "EXACT_UPLOAD_SHA256",
  "title": "Reviewed episode title",
  "caption": "Reviewed caption",
  "review": {
    "source_use": "pending",
    "audiovisual": "pending",
    "reviewed_by": null,
    "evidence": null,
    "approved_video_sha256": null,
    "audience": null,
    "synthetic_disclosure": null
  }
}
```

For a YouTube job use the same `brand`, `episode`, `platform`, `account_id` and `scheduled_for` fields. Supply `request` and `request_sha256` for a local one-episode reviewed manifest under `publish-requests/`. Leave the request uncommitted when using this queue so the separate push-triggered YouTube workflow does not also dispatch it.

```sh
python scripts/publishing_dashboard.py queue private/publishing/reviewed.json
python scripts/publishing_dashboard.py watch
python scripts/publishing_dashboard.py dashboard --refresh
```

The watch worker checks for due jobs once a minute and catches up when restarted. Keep the host awake while it runs. `run-due` handles one pass for an existing local scheduler. `dashboard` writes the local HTML view to `private/publishing/dashboard.html`. The desktop app can queue work and run one pass. Its window does not start a background worker automatically.

Preserve `private/publishing/direct-posts.sqlite3`. If a send is interrupted after the worker claims it, verify the result in the platform's dashboard using the saved resource ID before attempting another upload. Jobs marked `working` or `needs_reconciliation` are held for that check. Provider acknowledgement alone is not public visibility. No live connection or upload was used in testing.

## Maintenance in GitHub

Use the [maintenance issue template](../.github/ISSUE_TEMPLATE/platform-maintenance.md) for one account/platform. Update the JSON and this table through a normal commit/PR when evidence changes. Keep account existence, OAuth, integration support and actual publication independent. Each has its own verification date; unknown dates stay null. Do not mark all accounts connected because one platform works.

The owner finishes creating accounts and connects them privately later. Only public handles, stable public IDs, dates and non-secret task/receipt references belong here. Passwords, OAuth clients/secrets, tokens, recovery codes and account email addresses belong in private credential storage, never issues, Git or chat.

Before any public operation: owner topic/script choice and actual audiovisual/source-use review, correct live account identity/scopes, a supported tested integration and explicit publication scope must all be established. Current instructions authorize repairs and maintenance preparation only. No new account, public post or recurring scheduler is enabled.

For a real upload, preserve a non-secret receipt with platform, brand, stable account ID, provider post ID, URL, video SHA-256, operation ID, upload time, visibility/processing state and last verification time. Record `published` only after the provider confirms the intended public state. A failed/processing/private upload remains distinct and must be reconciled before retrying. The receipt arrays are currently empty because there are no verified publications.
