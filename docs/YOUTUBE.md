# YouTube connection utilities

For ordinary ChatGPT/browser linking, use the [hosted Site flow](../sites/ACCOUNT_LINKING.md). It verifies the recorded Ifverse channel and requests read/upload access. No local WSL or loopback command is needed for that route.

Two optional Python utilities remain for standalone/local use:

| Module | Scope | Store |
| --- | --- | --- |
| `whatif.youtube` | Read-only identity check and legacy registry binding | `private/youtube` |
| `whatif.youtube_publish` | Read/upload connection for the standalone publisher | `private/youtube-publish` |

These stores are separate from Site connections. The backend broker can use selected Site access grants for approved delivery; the standalone Actions uploader uses its configured secret contract.

## Read-only utility

Use the current implementation branch with Linux/POSIX file-lock support and the optional Google requirements. A Desktop OAuth client and a consent browser that can reach the CLI's `127.0.0.1:8765` callback are required.

```sh
python -m pip install -r requirements-youtube.txt
python -m whatif.youtube connect --connection ifverse-anime \
  --client-secrets private/google-desktop-client.json \
  --expected-channel-id UCpB_wi5MlernpSJxUf7zWcw
python -m whatif.youtube check --connection ifverse-anime
```

`status` reads cached metadata. `check` verifies provider access and refreshes when supported. `bind` can write verified public metadata into an existing slot in `channels/youtube-registry.json`; that legacy planning registry is separate from the publisher's `channels/publishing-accounts.json`.

The read-only utility does not upload or create channels. Keep its credential directory private and backed up separately from source.

## Standalone upload connection

```sh
python -m whatif.youtube_publish --connection ifverse-anime --expected-handle @ifverse_anime \
  connect --client-secrets private/google-desktop-client.json \
  --expected-channel-id UCpB_wi5MlernpSJxUf7zWcw
python -m whatif.youtube_publish --connection ifverse-anime --expected-handle @ifverse_anime \
  verify --expected-channel-id UCpB_wi5MlernpSJxUf7zWcw
```

See [AUTOMATION.md](AUTOMATION.md) for the standalone batch uploader and [SOCIAL_PUBLISHING.md](SOCIAL_PUBLISHING.md) for the separate multi-account queue. Verify the chosen destination after consent; different Google accounts can authorize different channels.

[YOUTUBE-CONNECTION-RESULT.md](YOUTUBE-CONNECTION-RESULT.md) records an earlier unsuccessful connection attempt. Its old network, callback and account-plan blockers are historical, not prerequisites for the hosted Site flow.
