# Ifverse multi-account publishing

The repository registry maps each alias to one brand, platform and provider account ID. The desktop dashboard and local queue support multiple accounts on the same platform. GitHub Actions handles one due YouTube Short or Instagram Reel per reviewed request. The production workflows still create the videos and result branches.

## Register and connect an account

1. Add an alias to [`channels/publishing-accounts.json`](../channels/publishing-accounts.json) with `brand`, `platform`, `account_id` and an optional public `handle`. Run `python -m scripts.publishing_dashboard accounts` to list the bindings. The existing `ifverse-anime` alias records the observed YouTube channel ID. A registry entry records the intended destination; a live verification checks the grant.
2. Authorize each account on your own computer using the provider's consent page. Keep passwords, OAuth client files and tokens in private storage.
   - **YouTube.** Enable YouTube Data API v3 in Google Cloud and use a Desktop OAuth client. Run the command below in Linux, or in an environment where your browser can reach its loopback listener. Supply the intended channel ID and select that exact channel during consent. For hosted use, the full saved `private/youtube-publish/ALIAS.json` record becomes `youtube_connection` under the same alias in the private Actions secret.
   - **Instagram.** The hosted binary upload uses Meta's Facebook Login publishing route. Use a professional Instagram account linked to the intended Facebook Page. Configure your Meta app for that Page and Instagram profile and grant the required scopes, including `instagram_basic`, `instagram_content_publish`, and `pages_read_engagement`, with the appropriate Page access and app access level. Store the Page access token, Page ID and Graph API version under the Instagram alias. Verification checks both the authorized Page and the linked Instagram account before posting.
3. Create the repository Actions secret `IFVERSE_PUBLISH_ACCOUNTS` with one JSON entry per alias you intend to publish to. Add it through GitHub Settings. For local runs the desktop queue reads Meta and Snap grants from the ignored `private/publishing/accounts.json` file, mode `0600` on POSIX. Local YouTube verification uses the saved OAuth record. Existing local jobs without aliases keep their previous configuration.

```sh
python -m pip install -r requirements-youtube.txt
python -m whatif.youtube_publish --connection ifverse-anime --expected-handle @ifverse_anime \
  connect --client-secrets private/google-desktop-client.json \
  --expected-channel-id UCpB_wi5MlernpSJxUf7zWcw
python -m scripts.publishing_dashboard verify-account ifverse-anime
```

The secret has this structure. Replace placeholders privately with your own values, and omit any alias you have not connected.

```json
{
  "ifverse-anime": { "youtube_connection": {} },
  "anime-instagram": { "token": "PAGE_ACCESS_TOKEN", "page_id": "FACEBOOK_PAGE_ID", "graph_version": "vNN.N" }
}
```

Replace the empty `youtube_connection` object with the complete saved OAuth JSON object for that alias.

GitHub calls the APIs using these grants after consent. Provider permissions, app access, token expiry, quota, media eligibility and runner connectivity still affect the result. [Google authorization](https://developers.google.com/youtube/data/guides/authentication) · [Meta Instagram API](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api) · [Meta's file-upload example](https://github.com/fbsamples/reels_publishing_apis/tree/main/insta_reels_publishing_api_sample) · [GitHub Actions secrets](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions)

## Submit a reviewed post from GitHub

The workflow runs after it is present on `codex/ifverse-workflow`. The agent reads the account registry and the brand's `channels/<brand>-topics.json`. Commit account bindings and any documented owner review first. After the owner has authorized the exact post and the audiovisual and source-use reviews are recorded, commit and push **one new** `social-publish-requests/<request-id>.json` by itself to that branch. Each request selects one account. Submit another push for an additional destination. Use a due time with an explicit UTC offset. Future scheduling is available in the local queue via `python scripts/publishing_app.py` and its watch worker.

| Request field | Value |
| --- | --- |
| `schema_version` | `1` |
| `brand`, `episode` | The brand and selected topic ID |
| `platform`, `account`, `account_id` | `youtube` or `instagram`, the registered alias and its exact provider ID |
| `owner_requested_publication`, `scheduled_for` | Actual owner authorization and a due ISO 8601 timestamp |
| `result_branch`, `result_commit`, `video` | The selected result branch and exact commit from the topic registry, plus its episode MP4 path |
| `master_sha256`, `video_sha256` | The current registry master hash and the exact export hash |
| `title`, `caption`, optional `tags` | Post metadata. YouTube uses `caption` as its description and accepts `tags`. |
| `review` | `source_use` and `audiovisual` set to `approved` after real review, `reviewed_by`, `evidence`, `approved_video_sha256`, `audience` (`made_for_kids` or `not_made_for_kids`), and boolean `synthetic_disclosure` |

Run `python -m scripts.publish_social --request social-publish-requests/<request-id>.json` to check a proposed request and its Git media locally. This does not use provider credentials. In Actions, the worker checks the registered identity live and sends the verified MP4. The same post should enter through one queue so the GitHub and desktop workers do not process it independently.

## Follow a result

The Actions log reports the provider state and the `codex/social-receipts/<hash>` branch. The branch's `receipt.json` stores account, episode, exact video hash and provider ID or checkpoint. `submitted` and `processing` can be checked by rerunning the same workflow run. An interrupted write leaves a `working` receipt. Inspect the saved checkpoint and the platform's own dashboard before acting on that post. The worker holds an uncertain write rather than submitting a second copy. A provider-confirmed public post is recorded as `published`.
