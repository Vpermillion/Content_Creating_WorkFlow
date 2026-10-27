# Current checkpoint

Updated 2026-10-27, Asia/Ulaanbaatar. Read this concise state first; older detailed reports remain in PROJECT_STATE.md and HANDOFF.md.

- Repository: Vpermillion/Content_Creating_WorkFlow, private. Working feature branch: codex/youtube-oauth, PR #2 based on codex/operator-handoff. Do not merge or discard existing work implicitly.
- Goal: portable original what-if video production. Current rollout is Alpha's ifverse_anime example; ifverse_cartoon/Marvel are planned, other accounts deferred. Channel names/IDs and live connections remain unverified.
- Current review video: What if Naruto joined the Akatsuki?, 46.975 seconds, 18 moving MP4 excerpts from 15 sources, zero still shots, original narration retained. Saved pilot ID libfile_9922c2295e588191b8a12be471c82e88, version 2, Ifverse_Anime_Video_Only.mp4. See docs/VIDEO-ONLY-EDIT.md. Copyright reuse, complete listening and editorial review remain pending; no public upload.
- Latest owner instruction: make labeled search/downloading, caching, FFmpeg enhancement and editing reusable tools for agents, including a skill and GitHub workflow. Use python -m whatif.media_tools and docs/MEDIA-TOOLS.md. Collect returns short JSON, caches successes/failures, validates downloads; build reuses narration/results. Light enhancement cleans/resizes/sharpens without promising restored detail.
- Personal skill: Ifverse Media Workflow is installed and its saved content was verified. It calls this repo; it does not duplicate the implementation. Personal installation does not transfer automatically to other accounts.
- GitHub entry: .github/workflows/media-tools.yml, request commits under media-requests/ on the configured feature branch; self-hosted Linux/x64 runner labeled ifverse-media. No runner availability or completed GitHub run is verified. Commands work in the current runtime; workflow source is not a running host.
- Validation: all 43 tests passed; real Tenor keyword search, clip download/cache reuse and enhancement succeeded. YouTube search/download capability is separate from Google OAuth. Do not infer a valid video from downloader success alone.
- Private state: existing review narration/database in private/review-pilot-state, new footage catalog in private/media-bank. These are ignored and not backed up by Git. Locate/restore actual state before status/init on another host; do not create an empty store and call it recovered.
- Google setup: owner says they found the earlier connection problem and will explain later. No new login/recovery was attempted. Await that explanation; keep tokens/client secrets outside Git. Read docs/YOUTUBE.md and docs/CONTINUITY.md only when resuming that setup.
- Code is portable; credentials, local cache, personal skills, compute and signed-in accounts do not automatically transfer. No production deployment, scheduler, merge, purchase or publishing authorization is implied.

