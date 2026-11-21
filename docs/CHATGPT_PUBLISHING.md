# Publish Ifverse from ChatGPT

Use [account linking](../sites/ACCOUNT_LINKING.md) for the Site, provider consent and backend configuration. This guide describes the current native Worker plus private Python publisher. `sites/server.mjs` is an alternative Express MCP wrapper; the native build packages `worker.mjs`.

The hosted gateway saves the verified provider identity and encrypted grant. The private publisher uses that identity in reviewed drafts and receives the selected access grants for approved delivery. Site connections are used through the broker routes. The standalone Actions/desktop queue has a separate credential contract.

## Tools

| Tool | Behavior |
| --- | --- |
| `ifverse_accounts`, `ifverse_connect`, `ifverse_verify` | List saved connections, open the hosted gateway, or recheck a destination |
| `ifverse_media_prepare`, `ifverse_media_status` | Run/get one existing checked-in review request through the bounded renderer |
| `ifverse_media_import` | Stage a pinned render from the private repository, optionally exporting a separate Facebook Reel or JPEG |
| `ifverse_prepare` | Save an immutable draft with exact media, account aliases, titles and captions |
| `ifverse_preview` | Retrieve that draft, its snapshot hash and delivery receipts across sessions |
| `ifverse_publish` | Publish only the approved destination subset of the reviewed snapshot |
| `ifverse_status` | Refresh known delivery state through read-only provider checks |
| `ifverse_verify_tiktok` | Verify a post after its Studio handoff using eligible Display access |

## Media and drafts

`ifverse_media_prepare(request_id)` runs an existing `review-requests/ID.json` with its current topic/script checks. Poll status. Repeated calls return the original durable job; they do not silently rerender. Free-form creative input still needs a prepared script and shot plan.

`ifverse_media_import(brand, episode)` fetches the topic registry's selected MP4 at its exact result commit and verifies SHA-256. The backend needs private repository read access. `export=facebook_reel` produces a separate cut within the repository's current 60-second validation limit; `export=jpeg` prepares a cropped frame. Those are implementation limits, not a statement of current platform-wide limits. Review the exported file and its own hash.

For media outside the recorded Git results, an authenticated producer can send binary `POST /media` to the backend. Rendering on the intended deployed host still needs runtime verification.

`ifverse_prepare(brand, destinations)` takes registered account aliases, format, title, caption, `media_sha256` and the existing media manifest. The manifest binds `brand`, `episode`, `master_sha256` and `video_sha256`; actual review evidence is checked before publishing. Use the saved alias from `ifverse_accounts` for a gateway connection. The authenticated Site supplies that exact provider identity to the publisher. Preset aliases come from the checked-in registry. Every post still requires approval of its exact draft.

## Review and delivery

Show `ifverse_preview(draft_id)` with the exact destinations, copy, media and snapshot hash. An explicit “post it” applies to that clear draft and destination set. “Instagram only” selects only its alias. Changed media or copy needs a new draft.

Call `ifverse_publish(draft_id, snapshot_hash, destinations, approved=true)` for the selected subset. The backend checks account binding, media and review evidence again. The trusted owner-only caller conveys conversational approval; the backend does not independently read the conversation.

Successful destinations are skipped on retry. Each destination retains its own receipt and durable intent. `submitted` or `processing` is not `published`. A failed read keeps the last receipt; an uncertain write requires reconciliation. YouTube resumes/probes its original upload session. Meta retains provider/container state. A second draft cannot bypass an already reserved account/episode operation.

TikTok returns `action_required` with a Studio handoff. After manual posting, eligible Display verification or the backend's authenticated browser verification form records the matching post. Studio handoff alone is not a publication receipt.

## Before live use

Check Site ownership, provider setup, exact backend registry IDs, matching backend deployment and private state. Retrieve a draft from a fresh session and verify the intended account. Use one queue per account/episode and reconcile any older delivery state before switching routes. See [CURRENT.md](CURRENT.md) for checks actually observed.
