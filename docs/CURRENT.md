# Current checkpoint

Documentation audited on **2026-11-20, Asia/Ulaanbaatar** against publishing source commit `280f00eb660e852c34d9fc04032e1b1a300780b9`.

## Source and implementation

Use `codex/ifverse-chatgpt-publishing` for the integrated Site/publisher. [PR #4](https://github.com/Vpermillion/Content_Creating_WorkFlow/pull/4) builds on `codex/chrome-publishing-inventory` and the existing media workflow. The established production branch is `codex/ifverse-workflow`; the default `codex/portable-workspace` is an older snapshot.

| Area | Recorded state |
| --- | --- |
| Media | Ten 61-second anime cuts with sound-only repairs are saved; [batch index](BATCH_61S.md) selects the versions |
| Style | English, `am_michael`, frequent varied roasts and occasional mild/clean swearing; [style prompt](../prompts/script-style.md) |
| Site linking | HTTPS consent callback verifies the destination and saves encrypted grants, partitioned by authenticated Site user ID |
| Publisher bridge | Implemented: the Site refreshes and passes selected access grants to authenticated backend broker routes |
| Backend destinations | Checked-in registry contains only `ifverse-anime`, YouTube ID `UCpB_wi5MlernpSJxUf7zWcw`; Meta and TikTok IDs still need registration |
| TikTok | OAuth/profile verification is available; publication is a Studio handoff |
| Generalization | Free-form story-to-footage planning and Hollywood-branded production remain incomplete |

The bridge is already implemented. Older statements that Site connections cannot reach the publisher are superseded by the November 16 source. The separate GitHub Actions queue continues to use its own secret contract.

## Live setup and verification

The Site is reachable at [Ifverse Publishing](https://ifverse-publishing.idealcoyote1.chatgpt.site). On 2026-11-20 its configured owner setting was aligned with the confirmed ChatGPT Site owner and saved version 4 was redeployed with runtime environment revision 4. Deployment succeeded and the live `ifverse_accounts` call now succeeds; the earlier owner-check 403 is resolved.

Live account status: all four aliases are `not_connected`. YouTube client setup is present and ready to begin consent. Meta and TikTok clients are not configured, so Instagram/Facebook and TikTok OAuth still require provider setup. No publishing backend origin/token is present in the Site's runtime settings. The cloud-browser check reached ChatGPT consent under a different account from the intended Site owner; consent was not accepted.

GitHub, ChatGPT and channel login accounts may differ. `IFVERSE_SITE_OWNER_EMAIL` is matched to the ChatGPT authenticated email; provider callbacks separately check channel identity. Stored grants and pending OAuth sessions belong to the authenticated Site user ID, so changing the owner email alone does not migrate another user's connections.

Provider grants and successful delivery remain unverified; no social account was linked or post published during this repair. Follow [account setup](../sites/ACCOUNT_LINKING.md) to inspect them. Repository records and software tests are not live checks.

## Validation and documentation cleanup

- Latest pre-audit source CI: [Software checks](https://github.com/Vpermillion/Content_Creating_WorkFlow/actions/runs/43793049012), passed at `280f00e`.
- Four focused Site linking/access/broker tests passed locally during the source review; providers were mocked.
- This audit changes documentation and prompts only. It consolidates startup instructions, corrects branch/account/bridge descriptions, and removes repeated historical checklists. See [the audit record](DOCUMENTATION_AUDIT.md) for validation of the cleanup.

## Continue by task

For linking: complete ChatGPT sign-in as the configured Site owner, then connect YouTube. Configure the missing Meta/TikTok clients and backend origin/token before those paths can operate. For production: reuse saved outputs, choose a genuinely new or explicit revision topic, and use the bounded request process in [AUTOMATION.md](AUTOMATION.md). Review/publication decisions follow the current user request and the actual saved evidence.
