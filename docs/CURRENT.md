# Current checkpoint

Documentation audited on **2026-11-20, Asia/Ulaanbaatar** against publishing source commit `280f00eb660e852c34d9fc04032e1b1a300780b9`.

## Source and implementation

Use `codex/ifverse-chatgpt-publishing` for the integrated Site/publisher. [PR #4](https://github.com/Vpermillion/Content_Creating_WorkFlow/pull/4) builds on `codex/chrome-publishing-inventory` and the existing media workflow. The established production branch is `codex/ifverse-workflow`; the default `codex/portable-workspace` is an older snapshot.

| Area | Recorded state |
| --- | --- |
| Media | Ten 61-second anime cuts with sound-only repairs are saved; [batch index](BATCH_61S.md) selects the versions |
| Style | English, `am_michael`, frequent varied roasts and occasional mild/clean swearing; [style prompt](../prompts/script-style.md) |
| Site linking | The hosted gateway at `/connect` lets the Site owner link several accounts per platform. The callback verifies each destination and stores its encrypted grant. |
| Publisher bridge | The Site sends verified owner-scoped bindings for newly linked accounts to the private publisher. The publisher validates the exact destination during draft creation and approved delivery. |
| Backend destinations | Gateway aliases come from the Site database. The checked-in registry still supplies preset and standalone aliases. |
| TikTok | OAuth/profile verification is available; publication is a Studio handoff |
| Generalization | Free-form story-to-footage planning and Hollywood-branded production remain incomplete |

The separate GitHub Actions queue continues to use its own secret contract.

## Live setup and verification

The [Social Account Manager](https://ifverse-publishing.idealcoyote1.chatgpt.site/connect) was updated on 2026-11-21, Asia/Ulaanbaatar. Connect, reconnect, and remove accounts from the hosted dashboard. The Site owner and any invited signed-in visitors each get a separate account list. The existing ChatGPT publishing workflow is owner-only. GitHub Pages is currently disabled on the repository.

YouTube verified the two saved channels after refreshing their grants. Facebook and Instagram still require configuration of the existing Meta app and its Site runtime secret. Direct Instagram Login supports professional accounts without a linked Facebook Page when the Instagram OAuth client is configured. TikTok still requires developer registration and Login Kit credentials. The Site has no publishing backend origin or token configured.

GitHub, ChatGPT, and social provider logins can use different emails. Each provider callback is tied to the signed-in Site user who started the request. See [account setup](../sites/ACCOUNT_LINKING.md) for runtime settings and the publisher connection.

## Validation and documentation cleanup

- Eleven Site tests and fifteen Python publishing tests passed locally. Site tests covered visitor isolation, exact-account reconnects, both Instagram routes, consent, and publishing grant brokering. Provider calls in these tests were mocked. The two YouTube connections were also verified against the live provider.

- Latest pre-audit source CI: [Software checks](https://github.com/Vpermillion/Content_Creating_WorkFlow/actions/runs/43793049012), passed at `280f00e`.
- Four focused Site linking/access/broker tests passed locally during the source review; providers were mocked.
- This audit changes documentation and prompts only. It consolidates startup instructions, corrects branch/account/bridge descriptions, and removes repeated historical checklists. See [the audit record](DOCUMENTATION_AUDIT.md) for validation of the cleanup.

## Continue by task

For linking, sign in to the hosted dashboard and choose a platform. Configure the Meta and TikTok clients to enable their Connect buttons. For production: reuse saved outputs, choose a genuinely new or explicit revision topic, and use the bounded request process in [AUTOMATION.md](AUTOMATION.md). Review/publication decisions follow the current user request and the actual saved evidence.
