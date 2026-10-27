# Story inputs

Commit only non-secret JSON scene plans here. Supply the matching private narration path on the runner through `IFVERSE_NARRATION_PATH`; never commit audio credentials or tokens.

The schema is the existing edit plan's `id`, `title`, `narration_sha256`, optional `width`/`height` and `scenes`. For each scene retain `start`, `end`, `text`, `label`; replace `shots` with `visual_queries`, one to four exact catalog labels. At most six distinct queries are allowed in a single download/build batch. Search matches produce review drafts, not editorial or publication approval.
