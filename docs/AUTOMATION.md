# Ifverse batch production and optional YouTube uploads

The owner requested ten creative English `ifverse_anime` Shorts, later specifying **61 seconds**. They authorized posting this batch, clarified that upload automation was not yet implemented, and accepted completed videos in GitHub if posting is unavailable. They will handle optional **Meaningful Love - Silo** music in YouTube. The exported files contain narration and comedy effects, with no piano embedded. No recurring scheduler is authorized.

## One request, ordinary software does the repeated work

1. Read [the topic registry](../channels/ifverse_anime-topics.json), [the latest batch index](BATCH_61S.md), CURRENT and the script-style prompt before choosing any premise. Compare the actual premise and development as well as the wording. The registry covers repository history; live YouTube catalog import has not been performed.
2. Prepare one bounded JSON under `batch-requests/`: one to ten distinct episodes, exact scripts, character-specific source queries, reasons for each visual, exact spoken-phrase sound anchors, and per-video posting metadata.
3. Reserve the topics **before rendering** with `python -m whatif.topics reserve --batch batch-requests/FILE.json`. An explicitly requested unpublished revision uses `revise_batch` and keeps previous hashes/history. A failed or reserved topic is still taken; resume it instead of creating a duplicate episode.
4. Commit exactly one batch request on `codex/ifverse-workflow`. [anime-batch.yml](https://github.com/Vpermillion/Content_Creating_WorkFlow/blob/codex/ifverse-workflow/.github/workflows/anime-batch.yml) runs up to three episodes at a time, reuses model caches, bounds source lookups, narrates with Michael, aligns captions, edits, mixes effects, decodes and saves results plus contact sheets. No language-model API is called inside this job.
5. Read the saved results once. Preserve successful files; explicit retries can reuse hash-verified footage from pinned earlier result commits. Do not regenerate reviewed narration for picture/effect changes. Changed script text requires new speech and timing. Result branches use `codex/results/EPISODE-ID`, then `-r2`/`-r3`/`-r4` for explicit revisions; earlier outputs remain intact.
6. Record actual outcomes in the topic registry and batch index. A topic becomes **published** only from a verified YouTube video ID/channel/status receipt. A render never proves publication, copyright permission, YPP approval or a completed listening review.

The production job avoids repeated per-stage chat work. GitHub runner minutes/storage and setup/review still have costs; no chat-allowance percentage or universal free-service promise is made. There are no automatic indefinite retries or scheduled mass uploads.

## Posting packets

Every final result has `post-settings.json`: its own title, description, relevant hashtags/tags, English language/audio, Entertainment category, intended public visibility, audience/disclosure proposals with reasons, music handoff and the final video hash. Descriptions identify the hypothetical fan scenario and AI-assisted narration. Source URLs provide provenance and attribution, not permission. English captions are burned in; the supplied SRT is separate and is not claimed to be an uploaded native CC track.

Title length, description byte length, hashtag syntax/count, final vertical aspect ratio/duration and media decoding are checked. Actual source-use, audience and audiovisual decisions remain explicit review fields. Do not turn a metadata proposal into evidence that someone approved the video. See [MONETIZATION_REVIEW](MONETIZATION_REVIEW.md).

YouTube's upload API has no parameter for attaching a Shorts-library song. The owner will choose the requested piano inside YouTube if available and permitted, keeping it very quiet below the narration. Music is optional for this batch and is not a reason to withhold the exported videos or an otherwise authorized/cleared post. Song allowances vary; a 61-second video is not a copyright workaround.

## One-time upload connection setup

The browser tab does not supply API credentials. The existing `whatif.youtube` connector remains **read-only**. The separate `whatif.youtube_publish` connector requests `youtube.readonly` to verify ownership plus `youtube.upload` to upload, and verifies both the canonical channel ID and `@ifverse_anime` before writes.

On a trusted machine where the owner can complete Google's browser consent, enable YouTube Data API v3 in the owner's Google Cloud project, configure a Desktop OAuth client and install the optional requirements. Keep the client file private. Run:

```sh
python -m pip install -r requirements-youtube.txt -r requirements-youtube-publish.txt
python -m whatif.youtube_publish connect \
  --client-secrets private/google-desktop-client.json \
  --expected-channel-id UC_REPLACE_WITH_REAL_CHANNEL_ID
```

Replace the example with the real canonical `UC...` channel ID from YouTube Studio. Complete consent on the machine running the loopback listener; do not paste OAuth codes, client secrets or tokens into chat. The command saves an owner-only connection at `private/youtube-publish/ifverse-anime.json` and does not upload anything.

For GitHub-hosted uploads, configure these **repository Actions settings**, not committed files:

- Secret `YOUTUBE_UPLOAD_CONNECTION`: the saved private connection JSON, entered directly through GitHub's secret UI.
- Secret `YOUTUBE_UPLOAD_STATE_KEY`: a Fernet encryption key, generated privately with `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'` and entered into the secret UI. Retain it securely; losing/changing it can prevent reconciliation of an interrupted upload.
- Variable `IFVERSE_ANIME_CHANNEL_ID`: the verified real channel ID.

No upload connection or these settings have been verified in this task. Some OAuth test-mode refresh tokens expire, API quotas can interrupt a batch, and some YouTube API projects restrict uploads to private until additional review. Honor actual provider results. Never invent credentials, use another channel, or claim that configured code establishes live access.

For local/cloud API use, `www.googleapis.com`, `oauth2.googleapis.com` and `accounts.google.com` are required destinations. An additive environment draft preserves existing domains and adds these; saving a draft does not activate it. The configuration tool requires Environment settings review/save and publication. GitHub-hosted runners have their own network; changing the cloud allowlist does not create Google consent or GitHub secrets.

## Bounded upload request

After actual review, prepare a JSON under `publish-requests/` using [the draft packet](../publishing/ifverse-anime-ten-61s.draft.json) as the shape. Supply the exact completed result commit/branch, final mixed video path/hash, real review evidence, audience decision and synthetic-disclosure decision. Pending reviews must remain pending. The current third-party footage is not automatically cleared by the owner's posting authorization.

```sh
python scripts/youtube_upload_batch.py --request publish-requests/REVIEWED.json
python scripts/youtube_upload_batch.py --request publish-requests/REVIEWED.json \
  --expected-channel-id UC_REPLACE_WITH_REAL_CHANNEL_ID --publish
```

The first command is a plan; the second performs verified uploads. Committing exactly one reviewed request triggers [youtube-publish.yml](https://github.com/Vpermillion/Content_Creating_WorkFlow/blob/codex/ifverse-workflow/.github/workflows/youtube-publish.yml). There is no automatic render-to-public shortcut. The owner authorized this batch; no redundant posting permission question is needed once the necessary connection and genuine review evidence exist.

Uploads use a private resumable journal. A lost response is reconciled through the same session. A completed receipt returns the original video ID rather than creating another upload. Changed media/metadata/channel, unverifiable completion or expired/unknown delivery stops for reconciliation. Actual private/processing status is not reported as public success.

The hosted job preserves journals as **authenticated ciphertext** on `codex/youtube-upload-state`; plaintext session URLs/tokens stay out of Git and artifacts. Non-secret video receipts and merged topic status are written back to `codex/ifverse-workflow` without replacing other topics. This metadata-only commit does not render or upload again. Keep the encryption key and connection out of source control. Local uploads also require preserving private journal storage across sessions.

The upload implementation has offline provider fixtures and a real generated-media preflight test. A live public upload has not been demonstrated without the owner's configured OAuth connection. Check actual receipts before reporting any posts as published.
