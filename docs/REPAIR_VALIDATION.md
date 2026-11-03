# Repair validation — 2026-11-03

Final required command: `python -m unittest discover -s tests -v` — **112 tests passed in 20.373 seconds**. The emitted failed-source JSON is the intentional partial-acquisition failure fixture; the suite exit code is 0. New regression coverage checks owner-evidence/script matching, the >2 MB / 16 MiB download boundary, and preservation of corrected selections/links during old-batch finalization.

Earlier runs: the first 109-test run failed one validation-order expectation after adding the owner gate; corrected before the 111-test passing run. A newly added finalization regression then exposed old output links; the generator was fixed and the final 112-test run passed. No failing tests remain. `git diff --check` passed.

Actual media checks, separate from unit tests:

- 17/17 published-source recordings acquired, SHA-256 registered, audio probed and fully decoded with FFmpeg `-xerror`. Three prior frozen hashes matched. Five files exceed 2 MB; all are below 16 MiB.
- 10/10 corrected videos: 61 seconds, 720×1280 H.264, complete error-fatal decoding, matching audio/video coverage.
- 10/10 H.264 packet-stream hashes match both their clean render and previously selected old mix. This preserves every burned-in caption and picture without re-encoding.
- 10/10 retained narration WAV/JSON and transcription hashes match; voice receipts say `am_michael` and match the WAV hash. No TTS/ASR/retiming occurred.
- 40/40 new cues match the bank source hash and retained spoken anchor, with measured nonzero difference in the intended window. Master voice gain is 1 for every mix; differences outside cue windows are at most two PCM LSB from quantization. No old audio track, custom synthesized bass or substitute catalog is mixed.
- 10/10 batch links select corrected videos and corrected posting packets. Titles/settings/hashtags remain; attribution is corrected in both packet and corrected batch-result metadata.

[Per-video exact hashes, commits and measurements](sound-repair-results.json). The ten new result branches preserve plans, source fingerprints, PCM/mix receipts and validation receipts. Older result branches/files remain unchanged.

Not claimed: human full listening, canonical/source-use clearance, owner approval of topics/scripts, commercial rights, monetization approval, connected social accounts or successful public uploads. No new video stories, accounts, public posts or recurring scheduler were created.
