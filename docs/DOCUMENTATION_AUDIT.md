# Documentation audit — 2026-11-20

Scope: instructions, prompts and descriptions on `codex/ifverse-chatgpt-publishing`, reviewed against source commit `280f00eb660e852c34d9fc04032e1b1a300780b9`. No renderer, account binding, credential or publishing behavior is changed.

| Finding | Correction |
| --- | --- |
| Startup files repeated older results and directed publishing work to an older branch | Short component/branch map and one current checkpoint |
| Guides disagreed about the OAuth-to-publisher bridge | Documented existing selected-grant broker routes and their runtime configuration |
| Site's four aliases looked like four configured backend destinations | Distinguished Site targets from the YouTube-only checked-in backend registry |
| Account guidance mixed GitHub, ChatGPT and social logins | Explained independent identities, owner check and user-ID-bound grant storage |
| Generic YouTube setup prescribed desktop/WSL steps | Made hosted consent the normal route; kept local utilities as optional routes |
| Entry prompts repeated batch details, old permission language and seven-account tasks | One short resume prompt; optional operator labels |
| Several files required duplicate progress logs | CURRENT holds active progress; other summaries link to it |
| Old product/capability descriptions omitted working tools or called the selected voice undecided | Updated implementation and content defaults |
| Historical reports read like current instructions | Explicit historical context; detailed receipts remain available |

Earlier expanded checkpoints remain available in Git history at the source revision above. Saved media, topic records, scripts and detailed validation reports are retained.

Validation: all local Markdown links and heading references checked against the repository tree, with no unresolved links; `git diff --check` passed; four documented YouTube command examples parsed against the actual CLI definitions; 22 shell examples passed syntax checks. Usage signatures containing placeholders were treated as reference notation rather than runnable commands. Only Markdown files changed, so no media production, OAuth or publishing job was run for this cleanup.

The edited documentation contains about 58% fewer words. The pre-audit source CI passed, and the earlier focused Site tests passed with mocked providers; neither establishes live channel consent.
