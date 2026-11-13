## ChatGPT publishing implementation — 2026-11-13

Branch `codex/ifverse-chatgpt-publishing` builds on PR #3 head `cf4be82` / `codex/chrome-publishing-inventory`, whose parent history includes current workflow `de64824`. PR merge ref confirms workflow as base. The older portable branch is not the implementation base. See [Chrome setup, callable tools and limits](docs/CHATGPT_PUBLISHING.md).

Added private durable immutable drafts/media/receipts, exact destination-subset approval, per-account retry/reconciliation, hosted web OAuth, media-job bridge and an authenticated MCP wrapper. Reuses registry, renderer, review gates, Meta clients and original-session YouTube uploader. TikTok uses Studio action-required handoff plus authorized ownership query; no Direct Post. Carousel is documented supported by Meta but rejected as unwired here. No provider grant, Sites entitlement, deployment or public post is verified. No public publication was performed or authorized by this code task.

Validation pending final CI receipt; all publishing tests use mocks. Existing rendered batch, narration, review decisions and historical results are preserved. Next: finish software CI, deploy privately if owner selects a host, complete provider consent and verify exact accounts, retrieve a draft from a fresh chat, then await approval of that specific preview before public writes. Do not run the old social queue and hosted queue for the same account/job.

## Multi-account publishing — 2026-11-11

Pending live setup: authorize each selected account, set the Actions secret, install the draft workflow on the implementation branch and verify one owner-reviewed destination. [Setup guide](docs/SOCIAL_PUBLISHING.md).

## Direct publishing implementation — 2026-11-05

The [publishing dashboard](docs/PLATFORM_DASHBOARD.md) documents the repository-owned queue and desktop controls for all five Chrome destinations. The worker uses direct YouTube, Meta and Snapchat integrations. TikTok stays in the queue as a manual Studio step. The worker is available but has not been enabled. Owner review, platform OAuth and a live verification pass remain pending. Snapchat also requires app allowlisting.

## Current repair checkpoint — 2026-11-03

The ten 61-second anime Shorts now have **sound-only DubbingAI corrections**. [Batch videos and posting packets](docs/BATCH_61S.md) · [Topic review board](docs/TOPIC_REVIEW_BOARD.md) · [Platform dashboard](docs/PLATFORM_DASHBOARD.md) · [Repair handoff and validation](docs/SOUND_REPAIR_HANDOFF.md).

Final regression suite: **112 passed**; all 17 bank recordings and all ten corrected media paths passed real decoding/integrity checks. [Validation report](docs/REPAIR_VALIDATION.md).

All 17 actual collection recordings are cached, hashed and fully decoded in the saved bank. All ten corrections preserve Michael narration, H.264 pictures and caption timing. Older Brackeys versions remain history. No music, new TTS, footage search or story regeneration was used. The owner must choose/review topics before new full renders or posting; all proposals remain unapproved. No accounts/OAuth connections or public posts are verified; no scheduler is enabled. This checkpoint supersedes historical posting authorization and old sound-default claims below.

# Backlog

## Ten-video batch and optional upload automation — 2026-11-03

The owner authorized ten creative English `ifverse_anime` Shorts and posting this specific batch, then clarified that upload automation was not yet implemented. Final duration is **61 seconds**, not the first 75-second plan. They will add optional **Meaningful Love - Silo** piano through YouTube themselves; omit piano from the files and do not let that optional step block posting. If posting is unavailable, they explicitly accept completed videos prepared in GitHub and asked us to continue while they are away.

**All ten 61-second cuts are rendered and preserved.** All 109 local tests pass; all ten selected files independently passed 61-second/720×1280/1,830-frame/full-decode, real voice-hash, exact-script-caption, cue and metadata checks. Every selected shot midpoint was visually inspected. These checks do not invent full listening approval or rights clearance. Read [BATCH_61S](docs/BATCH_61S.md) for selected video links and individual posting packets, [AUTOMATION](docs/AUTOMATION.md) for one-request production/upload setup, and `channels/ifverse_anime-topics.json` before choosing another topic. The ten premises are Naruto clone strike, Lee/Rinnegan, Shikamaru's day running Konoha, Luffy without a fruit, Zoro navigation, Light's explanations to L, Vegeta's peaceful week, Levi's cleaning drill, powerless Gojo and Tanjiro hearing demon thoughts. Historical Naruto/Akatsuki and Goku/Avengers premises are also marked taken. Reservations, script revisions, actual render receipts and eventual provider publication receipts are separate states. This covers repository history; live channel catalog import is not established.

The first engineering batch produced one complete 75-second cut; other outcomes exposed long-script retiming and a final-sound boundary error. The shorter final scripts all passed at 61 seconds, with new Michael speech/alignment and frozen footage reused. Completed visual repairs fix a Naruto/Sasuke mismatch, replace contextual Bulma name-matches with an actual Bulma clip, and remove unrelated burned-in Gojo meme text. Selected cuts use Naruto/Gojo `-r3`, Vegeta `-r4`, and the other seven `-r2` branches, preserving the exact completed 61-second narration/caption bytes. A retained-voice/result-folder collision was diagnosed and regression-tested; failed attempts remain preserved separately. See the index/receipts for the currently selected versions rather than rebuilding any prior attempt.

No upload connection exists in the current private connection store. The separate resumable uploader and GitHub publication workflow are implemented with channel/scope/hash checks, real review prerequisites, encrypted retry journals and non-secret topic/publication receipts. They have offline/provider and real-media preflight tests, not a live-upload demonstration. Optional setup needs the owner's Google consent, repository upload secrets and verified channel ID. A saved additive cloud network draft adds the three Google OAuth/API hosts; the configuration tool requires settings review/save/publication to activate it. This cannot create credentials. Existing publishing profile flags stay false; the user has already authorized these ten posts, so do not ask redundant posting permission once the actual prerequisites are satisfied.

The delivered files use four described public-domain effects each, matched to actual spoken words. Third-party footage use remains unverified and full listening/editorial approval is not invented; technical success is not source-use clearance or YPP approval. Source/code/results remain on `codex/ifverse-workflow`; the default branch routes new sessions there. No recurring schedule, purchase, account recovery or unrelated upload is authorized.

## Official policy verification follow-up — 2026-11-03

The owner supplied two further texts asking for deeper monetization requirements. Public YouTube Help access is now active and twelve official articles were fetched successfully. Read `docs/POLICY_FACT_CHECK.md`, `docs/MONETIZATION_REVIEW.md` and `docs/youtube-policy-verification.json`; earlier blocked-fetch notes below are history. Verified distinctions cover channel-level substantive variation, reused content versus copyright, claims versus strikes, audience factors for anime, contextual profanity rules, current general YPP tiers, unsupported shadow-ban claims and notice-specific appeal routes. In an appeal, do not follow the pasted delete-first advice: the official appeal page says not to delete videos before submitting. No actual notice/channel metrics were supplied.

Keep Michael, the roast style and automation. Next: use the editorial brief to develop distinct episodes, document an actual rights/use basis for every visual/audio source, review the finished audiovisual file and proposed catalog, then verify real channel eligibility when needed. Ten footage assets and three recordings in the Goku demo still have unresolved rights; no editorial approval or YouTube decision was invented. This follow-up changes documentation/audit metadata only, with publishing disabled and saved media untouched. It adds no executable approval gate.

## Monetization preparation concern — 2026-11-03

The owner supplied an AI overview about low-effort channels and clarified there is no actual YouTube rejection notice being addressed. Added MONETIZATION_REVIEW and an episode editorial-brief template, preserving Michael/v2 humor and the existing automation. Corrected the human-voice mandate, fixed safe-clip-duration/scanner-evasion claims, assumed trailer/raw-source permission and unsupported 2027 threshold prediction. The current Goku test has original script/commentary evidence but ten footage assets and three community sound recordings with unverified source-use rights, no recorded full human listening/editorial approval and no verified channel Earn eligibility. Its evidence audit is saved with the test. It is a technical demonstration, not certified monetization-ready content.

No code, renderer, saved speech/video or publishing behavior was changed; publishing flags remain false. The new guide/profile fields are planning/review metadata, not an executable policy gate or YouTube decision. Direct official Help reads were blocked; a saved network draft adds support.google.com for live verification once the user activates/publishes it. Do not encode the third-party future threshold claim as official policy. Next: distinct episode development and original/licensed or genuinely reviewed case-specific source-use evidence, followed by actual audiovisual/editorial and channel review before commercial publication.

## Completed new Michael/crossover test

Owner-selected `am_michael` is now preferred and tested in `ifverse-michael-goku-avengers-01`, hosted run `41468364961`, source `c491b62c4d25372f91185cd2b9049ebe7f96e879`, result branch `codex/results/ifverse-michael-goku-avengers-01`. Delivered `/workspace/Ifverse_Michael_Goku_Avengers_Test.mp4`: a new 190-word, 19-beat Goku/Avengers roast, 60 seconds, 26 shots from ten new sources, 48 caption phrases and 11 actual DubbingAI Vine Boom/faaah/Rizz cues. Fresh Michael speech/caption alignment were generated; this is not reused Heart audio or the old Naruto script. Voice SHA `429a3378da2b9bb64533666f233e8ce8d663864ddbe6939fa59d34f0de71324c`; video SHA `570541c183163dec5de432ed488982866c2f549b965ca8a01ea6694131f6106c`.

All 80 local tests and hosted regression gates passed. Full decode/coverage, complete caption wording, real-source fingerprints, cue timing/energy and SFX-stage picture copying were verified; all 26 shot samples were reviewed. Decoded sample peak -1.727 dBFS. Full listening/editorial/source-use review remains separate. First-source preparation preserved eight clips/three sounds but rejected two searches; the bounded retry completed the missing characters and Thanos replacement. All partial/retry records and prior Heart versions are retained. See CURRENT before reruns and reuse the saved Michael voice/captions for visual-only revisions. No YouTube posting.

## Current voice and requested meme-source follow-up

The pinned Kokoro voice bundle was inspected: 28 English IDs exist, Heart/Michael are enabled in the current review runner and only Heart has been review-rendered. VOICE_OPTIONS and the machine-readable options catalog distinguish available, enabled and tested. The owner has not chosen a replacement voice; approved speech is preserved.

The supplied DubbingAI article was read successfully and its 17 embedded media URLs/descriptions indexed in assets/sfx/dubbingai-discovery.json. The real audio is on dvi.dubbingai.io, which returned a proxy tunnel 403. An additive saved network draft includes that exact media host, but requires user activation/publication. The decoder/download provider is prepared with strict HTTPS/source pattern/checksum checks; no actual DubbingAI audio or replacement video is falsely marked downloaded/rendered. After activation, download/probe/hash selected Vine Boom/faaah recordings and render a new review cut. See CURRENT for exact state; preserve the older video and all voice/caption hashes.

## Completed sound-effects review

Hosted request `ifverse-anime-sfx-review-01` succeeded in run `41199650499`, source `f85dbada1876fa222efdace47130f299dce6d0d8`, result branch `codex/results/ifverse-anime-sfx-review-01`. Delivered `/workspace/Ifverse_Anime_60s_Sound_Effects.mp4`: 60 seconds, nine phrase-anchored cues across four effect types, unchanged source voice/50 captions, 24 moving shots. Public-domain source catalog, cache, descriptions, cue reasons, speech ducking and saved mix receipts are implemented in the review pipeline. All 74 final-source local tests passed; the hosted demonstration passed its then-current 73 regression gates. Full decode, all cue-energy windows, unchanged waveform/transcript/SRT hashes, video-stream copying and decoded sample peak -0.510 dBFS were verified. Sound stage 3.698s; whole media run 28.181s excluding setup and reusing voice/captions. Full listening/editorial judgment remains separate. This SFX-only test retains the earlier v1 narration; new scripts must use denser v2 banter. Read CURRENT/SOUND_EFFECTS before retries. No public posting.

## Latest style clarification — 2026-10-30

The owner clarified the style after the first roast: **frequent, varied, creative roasts across the whole narration**, with modern Gen Z/millennial slang, streetwise banter, mock praise, comparisons and callbacks. A single recurring insult is insufficient. Roasts are frequent; mild/clean-swear profanity remains occasional. See `prompts/script-style.md` (preference v2). The completed 60-second video predates this density clarification; no new render was requested in this follow-up.

## Owner style update and new one-minute example — 2026-10-30

Completed request `ifverse-anime-roast-20261030-04`, hosted run `41047895853`, result branch `codex/results/ifverse-anime-roast-20261030-04`: exactly 60.000 seconds, 24 moving shots, nine traced sources, 50 caption phrases. New speech was generated once; the first whole-audio ASR agreement gate failed, then the exact speech was retained for scene-window recognition; both tiny.en and base.en recognition drafts still altered words, so the final pass directly aligns the known script to the final waveform. All 67 current-source local regression tests passed. Local full decode/duration/track/hash checks, clean-swear caption check and every shot sample were reviewed. Full listening/editorial/source-use approval remains separate. Delivered `/workspace/Ifverse_Anime_60s_Roast.mp4`; no public upload. General repository script intake is now implemented; automatic new-story footage planning and Hollywood branding remain next work. Read CURRENT for exact receipts before retrying.

The owner explicitly requested funny teasing/roasting, exaggerated complaints, modern conversational energy and occasional clean-swear wordplay (e.g. motherflicker or mother father) for both English channels. `prompts/script-style.md` is the durable addon, linked from root guides, AGENTS, resume prompts and both profiles. No racial imitation or particular real-person voice is needed. Prior neutral-tone guidance is superseded. Clean substitutions are not a promise of platform acceptance.

New request `ifverse-anime-roast-20261030-01`: a 196-word Naruto/Akatsuki script, 21 filmable beats, nine reviewed moving sources, 60-second target, new Kokoro narration and new Whisper timing. Source files are `pilots/ifverse-anime-roast-60-v1.json` and matching `edits/ifverse-anime-roast-60-v1.json`. The runner accepts a bounded repository script plus its reviewed plan and supports bounded pitch-preserving retiming of newly generated narration. Previous audio/videos are preserved. Execution/review receipt and exact next work are in `docs/CURRENT.md`. No public posting requested.

## Current continuation entry

Start with `START_HERE.md`, `docs/CURRENT.md` and `README.md`. Current development is `codex/ifverse-workflow`; the default `codex/portable-workspace` is the old code snapshot and now contains the same entry guides. User-approved scope is English ifverse_anime and ifverse_hollywood. The original 44.672-second voiced/captioned test is complete; a closer visual revision now uses 22 explicitly timed spoken beats from 14 moving sources, preserving the exact approved voice and caption record. See `docs/VISUAL_MATCHING.md`. Request ifverse-anime-visual-match-20261030-01 completed successfully in hosted run 41022041729; result branch codex/results/ifverse-anime-visual-match-20261030-01 contains the 44.672-second, 22-shot revised MP4 and complete records. All 22 shot samples and final decode/stream/audio checks passed. Voice and caption bytes are unchanged. Retained-media execution took 24.715 seconds, excluding setup/queueing and first-time speech/caption inference. The delivered file is /workspace/Ifverse_Anime_Script_Matched.mp4. Read the existing result before resubmission. Local checks after interval/request changes: 42 passed. Current local media runner supports a supplied repository edit plan and verified audio/caption reuse. This remains a prepared-Naruto-story test, not an arbitrary-story semantic selection engine. No public upload or account operation is part of this task.

The next agent should inspect the current request/result first, use one plan and one finite job, and update the concise checkpoint. Do not rebuild existing components, regenerate saved speech or continue older account rollout plans. Preserve all earlier result versions. The historical detail below is retained for diagnosis; current instructions above take priority.


## Latest requested test video

The user requested an actual sample after reviewing the complete shared conversation. The confirmed channels are ifverse_anime and ifverse_hollywood, both English. Final test ifverse-anime-test-20261029-04 succeeded in GitHub run 40846229359: 44.672 seconds, 18 moving shots, Kokoro-ONNX af_heart CPU narration, 27 faster-whisper CPU/int8 caption phrases, and complete media validation. Source branch codex/ifverse-test-video-20261029-01 at 0ddeaab; completed outputs are on this result branch under artifacts/ifverse-anime-test-20261029-04/. Read docs/TEST_VIDEO.md and docs/CONVERSATION_DECISIONS.md before rerunning. This is a fixed-story production test using the existing traced Naruto footage, not arbitrary-story semantic selection or live YouTube delivery. Narration was generated once and preserved through diagnosed decoder/reporting fixes. Current measured retained-audio media work was 33.255 seconds, excluding setup and first-time voice generation. Do not regenerate the existing test or revive old broader account plans. Keep source credentials/private state separate; no default branch merge or public posting occurred.


## GitHub-hosted trial — 2026-10-27, Asia/Ulaanbaatar

The owner asked to test hosted execution and compare usage. The corrected media workflow now runs on ubuntu-24.04, restores/saves footage/tool caches, and supports a timed preview operation. GitHub run 40491183923 succeeded: job 36 seconds, media work 3.845 seconds, cached lookup 0.002 seconds. Tooling/footage caches saved; cross-run restoration not benchmarked. Zero model calls inside the worker; this chat still uses allowance and its percentage is inaccessible to the agent. The first hosted trial failed after six seconds due to missing FFmpeg; the pinned installer fixed it. All 47 local tests and actionlint passed. Full evidence: artifacts/hosted-media-trial-20261027.json and docs/MEDIA-TOOLS.md. No publication, OAuth change or merge.

## Reusable media tools and workflow — 2026-10-27, Asia/Ulaanbaatar

The owner clarified that tools should be reusable through this project and a personal workflow skill, including GitHub orchestration. Added labeled YouTube/Tenor search, bounded verified downloads, persistent SHA-256 footage catalog, cached keyword results/failure cooldown, non-AI FFmpeg enhancement and cached single-pass draft builds. `docs/MEDIA-TOOLS.md` is the compact operator guide. `docs/CURRENT.md` now supplies the short startup checkpoint; historical reports remain preserved and are loaded when relevant.

All 43 tests passed. Real Tenor search/download and repeat-cache reuse succeeded; a real 4.6-second clip was enhanced from 640x480 to 960x720 with unchanged duration/no-audio status and a sampled frame inspected. Enhancement does not claim restored detail. The GitHub workflow and fixed-data request adapter are implemented, with YAML/triggers validated locally. Jobs require a user-owned self-hosted Linux runner labeled ifverse-media; no online runner or completed GitHub request run has been verified. No job was submitted merely to save the source. No public posting, OAuth change or merge occurred.

## Current review: video-only cut — 2026-10-27, Asia/Ulaanbaatar

Owner feedback: the still-image edit was too static; use moving internet clips only, tied to the narration. Completed: 18 ordered MP4 anime excerpts from 15 sources, zero still shots, retained 46.975-second narration and overlaid sentence captions. Saved over the same pilot identity: Library `libfile_9922c2295e588191b8a12be471c82e88`, filename `Ifverse_Anime_Video_Only.mp4`, version 2. [Sources, checks and reproduction](docs/VIDEO-ONLY-EDIT.md); input is `edits/alpha-anime-video.v2.json`. Earlier still/storyboard plans remain historical.

All 33 tests pass. Complete output decode and video/audio coverage pass; one frame per shot inspected and all source excerpts show sampled motion. A new single-pass option avoids damaged intermediate MP4s encountered during assembly. Captions are scene-segment timing, not word alignment. Full listening/editorial review and source reuse permission review remain pending. No publication or authentication change occurred. Await the owner's explanation of their connection fix; do not restart Google recovery.

## Latest: review the ordered online-media cut — 2026-10-27 UTC

Completed the Naruto review edit with 12 sourced stills, 16 ordered shots, camera motion, retained narration and sentence captions. [Result, source plan and checks](docs/ONLINE-MEDIA-EDIT.md). Full listening/editorial review and permission review remain. Moving-video imports are tested but no online moving footage was included. The owner will explain the connection issue they solved; await that information before resuming OAuth work. No publication or account changes occurred.

## Latest priorities — first sample completed

- Review `docs/ALPHA-ANIME-PILOT.md` and the saved sample. Tune narration/pronunciation and visual style from actual review; nothing is publish-ready.
- Resolve the offline authorized Desktop Commander agent, then inspect/setup the real Google Desktop client and reachable callback through the supported local workflow. No automatic login bypass or repeat recovery loop.
- Correct the generic Science draft hashtags/description for anime before any authorized delivery.
- Preserve the new sample private-state/raw-audio backup on a verified user-owned durable route before claiming cross-host resume. Retain the original science state separately.
- The render-tail integrity defect is fixed and covered by regression tests; 27 tests passed. No further broad test reruns are needed without a new change/failure.

## Current next step: repository-owned YouTube OAuth

Owner may use a local agent; project/Desktop-client status is unknown to the owner. Follow `prompts/youtube-connect-local.md` to inspect existing Google setup and verify a local callback before consent. Do not infer that the proposed runtime is already available or that a missing cloud file means no project exists elsewhere.

Latest runtime check: Alpha anime remains `not_connected`. Missing Desktop client, Google endpoint proxy 403, and `callback_unreachable` prevent consent. Optional dependencies are installed and 23 tests passed; original registry preserved. Resolve the private client and callback-capable owner runtime, then apply saved network requirements if using this cloud task. See `docs/YOUTUBE-CONNECTION-RESULT.md`; do not start uploads or other-account setup while the first connection is unverified.

Read `docs/YOUTUBE.md` and `prompts/youtube-connect.md` on `codex/youtube-oauth`. Connection code is implemented and offline-tested; configure the real Google Desktop client and reachable loopback callback, obtain the owner's read-only consent for the intended first Alpha channel, then live-check and bind the actual ID. OAuth alone does not implement uploading. Next implement a separately authorized private-test upload adapter with resumable delivery recovery and receipts. Other accounts remain deferred.


1. Verify cited NASA/NIH facts when network settings apply; replace inaccurate or unsupported prose with new content versions.
2. Complete full visual/listening/editorial review; tune narration and captions from actual feedback.
3. Connect private durable storage and scheduled private backups, including n8n volume and encryption key.
4. Execute the finite Kaggle notebook on an authorized account, verify weights/voice licenses, benchmark and implement bounded authenticated submission/status/retrieval if useful.
5. Add bounded n8n status polling, explicit failure/blocked routing, authorized notifications and production queue monitoring.
6. Implement licensed stock search/import and generic crop/framing/music/SFX paths with mandatory rights manifests; keep original illustrative graphics as an option.
7. Connect a replaceable writing/research model adapter, semantic topic-history checks and claim verification. API budget is separate from chat subscriptions.
8. Implement one authorized publishing transport with real status reconciliation, reconnect/refresh handling, platform disclosures and receipts. Then add other platforms without duplicating successful deliveries.
9. Add actual analytics import, preserving unavailable metrics as null, before using performance feedback for editorial decisions.
10. Harden and deploy on a chosen persistent host; review image updates, HTTPS/access controls, backup retention and service quotas. Test restored runtime on a genuinely separate host/task before claiming deployment portability is proven.
11. Scale beyond the provisional brand only after the first channel's production/review/publishing path is reliable.

## Operator portability follow-through

- Use the new prompts in a separately authorized GPT environment; restore the correct private state and verify existing pilot checkpoints. A real cross-account/host handoff remains untested.
- Configure secure private output/state backups and supported service connections before claiming unattended continuity. The operator registry is not a credential manager or account-switching service.

## Latest owner instruction: continuity and YouTube setup

- Follow `docs/CONTINUITY.md`; persist checkpoints after meaningful steps so an unexpected session loss is recoverable.
- Complete supported YouTube consent for the first intended account; verify active status and actual channel identity. Resolve initial channel creation and name/handle if needed, then record verified metadata in `channels/youtube-registry.json` and repeat sequentially. Setup is authorized; public posting remains a separate scope.
- Verify access from a replacement environment if the owner later makes the repository private. Do not change visibility based only on the privacy question.

## Alpha authentication result — 2026-10-26 (Asia/Ulaanbaatar)

The owner asked to proceed with secure account sign-in. Google accepted the email step and advanced after secure password submission to identity verification. The owner selected the offered alternative twice; Google opened account recovery and accepted a last-password submission through browserAuth. Google then displayed 'Couldn’t sign you in', explaining that there was insufficient information to verify ownership and suggesting a previously used device/network. This is an identity-verification rejection, not evidence of an incorrect password or a bot-detection block. No successful YouTube sign-in was observed.

Stop this browser login attempt; do not loop, bypass verification or reset credentials. No channel was created, no channel metadata was verified, no security setting was changed and no video was published. The other six intended accounts remain unverified and were not attempted in this turn. No authentication secrets or session URLs are recorded here.

Next: the owner must resolve the account's Google verification requirement through a supported method. A supported YouTube OAuth connection, completed by the owner, can be checked independently; do not assume it authenticates the cloud browser. Reinspect actual connection status and provider-authorized scopes before claiming access. Repository/handoff remains private on codex/operator-handoff, PR #1; no pipeline code or media tests changed in this authentication-only turn.

## Two channels per Google account — 2026-10-26

The owner expanded capacity to up to two YouTube channels per each of seven Google accounts (up to 14 total), superseding the original one-to-ten-channel capacity target for future planning. This is capacity, not a requirement to launch all fourteen now. `channels/youtube-registry.json` schema version 2 contains two planned slots per owner alias, stable slot IDs and suggested Ifverse names/handles/topics. Suggestions are not verified channel metadata; availability is unchecked. Actual IDs, handles and display names stay null. Preserve the Alpha identity-verification blocker; no new sign-in was attempted and no channel was created.

Pairs: Alpha Space/Physics; Beta Earth/Oceans; Delta Wild/Evolution; Epsilon Future/Machines; Zeta Human/Mind; Eta History/Civilizations; Theta Worlds/Myths. Keep existing first-channel suggestions and add one related topic for each second slot. Start with one pilot channel and expand in phases. Operator labels remain distinct from channel identities. Any publisher must bind each verified channel ID to its correct authorization; a Google-account login alone does not prove both channel connections work.

YouTube officially supports multiple channels through one Google Account: https://support.google.com/youtube/answer/3046356 and https://support.google.com/youtube/answer/4642409 . Features and initial creation remain subject to actual account verification. Registry/documentation only; JSON parses and all 14 slot IDs are unique, two per owner. No worker code changed or media tests rerun.

## Latest scope: Alpha entertainment pilot — 2026-10-26

The owner slowed the rollout and selected Alpha for an initial example: `ifverse_anime`, `ifverse_cartoon`, and a Marvel-focused channel. This supersedes Alpha's two-channel cap: three planned slots are now allowed for Alpha. The wider seven-account rollout is deferred; do not resume mass setup by default. The earlier science names Space/Physics are replaced only as plans; retain existing science demo jobs/artifacts unchanged.

Registry schema version 3 records Alpha's three active planning slots and preserves the other accounts' proposals as deferred. `ifverse_marvel` is a suggested name for the requested third category. The owner's Hollywood/American parenthetical may imply a broader entertainment scope: if so, `ifverse_hollywood` is a suggested alternative, not an approved rename. Do not treat Marvel as a label for all American movies. Names/handles remain unchecked; verified channel fields stay null.

Next editorial example: one anime what-if video, proposed topic 'What if Naruto joined the Akatsuki?' Test one video before expanding. This topic is a proposal, not an approved script or publication. Alpha's Google identity-verification blocker remains unresolved. No sign-in retried, channel created, public post made or production job regenerated. JSON/unique slot IDs/three active slots checked; source behavior unchanged, no media tests rerun.
