# Sound repair handoff — 2026-11-03

Implementation stays on `codex/ifverse-workflow`. The default branch mirrors navigation/handoff documents only. The initial remote checkpoints were implementation `9ab4220e2743b69cc707efc8448e235196872f29` and default `edec52af0b1efd22d39b27ad211f2748cd03ba7b`. The initial checkout was clean on local `work` at `6641117`; no reset, clean, worktree or merge was used.

## Delivered artifacts

[Batch index](BATCH_61S.md) selects the ten new `codex/results/<episode-id>-dubbingai-01` branches, each descended from its previously selected result. The registry preserves those original branches/commits/hashes in `versions`. Corrected video path: `artifacts/<episode-id>/production/sound-effects-dubbingai/video-sfx.mp4`; corrected metadata: `post-settings-dubbingai.json`; corrected result: `batch-result-dubbingai.json`. The older sound-effects folder/packet remains historical. Do not publish from it.

[Validation summary](sound-repair-results.json) pins all corrected commits/hashes and prior selections. Each branch has the bound phrase plan, full sound-mix receipt, mixed PCM and validation receipt. The saved clean narration WAV/JSON, transcription, subtitles and original renders remain unchanged in the parent tree. Titles, descriptions, tags, hashtags, settings and optional YouTube-side music choice are retained except the incorrect Brackeys/public-domain attribution, which is replaced. No music was embedded.

All 17 actual collection recordings are versioned in `assets/sfx/bank/`, with source URLs, project-authored descriptions, bytes, SHA-256, durations, sample metadata and complete FFmpeg decode status in `assets/sfx/dubbingai-bank.json`. The three older frozen source hashes match. Five recordings exceed 2 MB; both acquisition and mixer downloads allow at most 16 MiB per recording. Long music/vocal excerpts are flagged for audition, not treated as interchangeable short effects. Discovery summaries may misdescribe length; actual probed durations take precedence. Rights are not inferred from community hosting.

## Reproduce checks / repair

```sh
python scripts/cache_dubbingai_bank.py
python -m unittest discover -s tests -v
```

`python scripts/repair_batch_sound.py` is the bounded original repair tool. It uses pinned result commits and checks selected remote heads, extracts saved artifacts under ignored `private/sound-repair/`, mixes clean Michael speech with actual bank recordings, and creates new local result branches via a separate Git index. It never invokes TTS, ASR, footage lookup or a picture render. Completed local receipts resume the same operation. On a fresh clone after this repair, consult the current index/receipts first: the registry now selects repaired results, so do not run the original repair operation again against the new selection or create duplicate versions. `--push` is only for the original prepared repair operation after reconciliation; it is not a render trigger.

Validation includes 61.000-second duration, 720×1280 H.264, complete error-fatal decoding, identical packet-stream hashes against both the clean render and previously selected old mix, unchanged narration/receipt/transcription SHA-256, Michael voice receipt hash, exact source hashes and measurable energy in all 40 cue windows. Master gain is 1. Outside cue windows mixed PCM differs from dry voice by at most two integer least-significant bits due to quantization. Effects necessarily overlap some speech; the underlying voice is not regenerated, retimed or filtered. Caption timing is retained via the identical picture stream and transcription. Full human listening/editorial/source-use approval is still pending.

Production defaults now use the bank, with no Brackeys fallback. Historical plans/catalogs remain available explicitly. Batch intake requires actual bank effect IDs; new batch and individual full-render entry points require a recorded real owner choice tied to the exact ordered script hash. New topic reservations are proposals, never approvals. Upload execution also checks actual owner choice, and existing live channel/source-use/audiovisual gates remain. Finalization cannot replace a repaired selection with an older batch result.

Final required regression suite: **112 passed**. [Actual checks and earlier resolved failures](REPAIR_VALIDATION.md).

## Next owner decisions

Read [the topic board](TOPIC_REVIEW_BOARD.md). Choose a concrete fork/timeline; all three proposals remain proposed. Record the actual decision reference and reviewed script hash only after that owner decision. Do not approve the board yourself. Existing ten repaired files remain drafts, with unresolved story reviews.

Read [the platform dashboard](PLATFORM_DASHBOARD.md). The owner privately creates/confirms accounts and connects credentials later. All ten brand/platform rows have unverified account existence and OAuth; YouTube code exists, other publishing integrations are not established. No public posting, new account, scheduler or recurring job was performed or enabled. Keep all passwords/OAuth material out of Git, issues and chat. Only actual provider receipts may advance publication state.
