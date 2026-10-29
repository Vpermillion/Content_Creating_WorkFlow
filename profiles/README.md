# Channel profiles

`ifverse_anime.json` and `ifverse_hollywood.json` record the user's two confirmed initial channel topics, English language and online-video sourcing requirement. Their `configuration_status` is `planning_only`: they are requirements/configuration records, not connected YouTube accounts or executable production jobs. Null settings are still unconfirmed. They are not job files for `python -m whatif pilots --from-dir`.

`science-provisional.json` is the older runnable demonstration profile. Existing fixture jobs embed their own render profile in `pilots/*.json`; the worker does not currently load these channel files automatically. Adding a profile therefore does not enable search, clip editing, voiceover or publishing.

See [the current Ifverse brief](../docs/IFVERSE_BRIEF.md) for the intended production flow and the branch audit. Existing online footage tools and a GitHub media workflow live on `codex/youtube-oauth`, beyond this environment's selected `codex/portable-workspace` revision. Reuse those tools; do not rebuild them because this older checkout lacks them. The proposed vertical preset is inherited from the demo and can change after channel-format selection. Evaluate an English production narrator and channel-aware branding. Never put account tokens in these files.
