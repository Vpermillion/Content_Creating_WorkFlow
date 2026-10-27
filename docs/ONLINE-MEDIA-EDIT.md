# Online-media anime review edit

Historical still-edit record. The owner requested a moving-clips-only revision; the current output and source plan are in [VIDEO-ONLY-EDIT.md](VIDEO-ONLY-EDIT.md).

Recorded 2026-10-27 UTC, branch `codex/youtube-oauth`.

The owner requested internet images and videos matched to the story, ordered editing and overlaid captions. The resulting review cut uses **12 distinct official Naruto stills in 16 ordered shots**, subtle camera motion and sentence captions over the retained 46.975-second narration. It contains **no downloaded moving video footage**. Existing canon scenes illustrate an invented alternate timeline; they do not depict an actual episode where Naruto joins the Akatsuki.

[Open the saved video](https://chatgpt.com/library?file_id=libfile_9922c2295e588191b8a12be471c82e88&account_id=personal). This revises the existing pilot file in place; the original storyboard renderer and prepared source inputs remain available.

## Reproduce

`edits/alpha-anime-online.v1.json` contains source/download URLs, SHA-256 checksums, usage status, narration timing, framing and the reason for every shot. Source images are private local rendering inputs, excluded from Git.

```sh
python -m whatif.media_edit edits/alpha-anime-online.v1.json \
  --assets-root private/footage-edit --fetch
python -m whatif.media_edit edits/alpha-anime-online.v1.json \
  --assets-root private/footage-edit \
  --narration /path/to/retained/alpha-anime-001/narration.wav \
  --output private/footage-edit/render-v1
```

Restore the matching original narration privately first; its required hash is pinned in the plan. Do not regenerate voice just to resume an edit. The CLI does not access the job database, alter worker checkpoints or publish. Fetch is bounded to the recorded official image host and checksum-pinned bytes. For other permitted local images/video, record their source, usage basis and hash in a new edit plan. Local video imports support `type: video` and `trim_start`, require enough video for the shot, and omit source audio. This path was exercised with generated video fixtures; production moving-footage selection remains pending.

## Measured result

Output: 720x1280 H.264/AAC, 46.975 seconds, 4,380,611 bytes. SHA-256: `46fb848df36649c5651d003642850f0dec2f5987b1147240608cbe69e48e5edb`.

All 31 unit/integration tests pass, including a mixed image/video cut and bounded recovery of a locally truncated shot. The full production output decodes and its video/audio tracks cover the narration. Eight sampled output frames, including the final scene, were inspected for framing and caption legibility. Captions retain measured narration segment boundaries; they are not word aligned. Full listening/pronunciation and publication review remain pending.

Two initial local assemblies had shortened video tracks and were rejected. Intermediate files were found invalid after earlier checks; the cause was not established. The editor now revalidates all intermediates immediately before assembly, re-renders an invalid local shot at most once, and rejects any still-invalid result. Final production rendering repaired two shots; the quality record names them. No incomplete output was saved over the user's video.

## Provenance and status

Sources are the official Naruto recap and official episode pages, linked per asset in the plan. Images are copyrighted official stills; permission for republication or monetization has not been verified. This is a fan-commentary review draft, with fan-what-if and source labels. No assertion of licensed-stock status or publication approval is made.

No YouTube upload, channel binding, OAuth change, account recovery, purchase or merge occurred. The owner says they found the earlier connection problem's cause and will explain later. Continue editorial work from this cut and wait for that information before resuming authentication troubleshooting.

