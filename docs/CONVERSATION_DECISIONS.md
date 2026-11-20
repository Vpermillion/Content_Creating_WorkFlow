> Historical record. Read [CURRENT.md](CURRENT.md) for active status and [START_HERE.md](../START_HERE.md) for current task guidance. Earlier branch pointers, runtime checks and action requests below describe their recorded sessions.

# Final agreement from the shared conversation

Read from the user-supplied `Automated-Video-Workflow-Complete.pdf`: 38 pages, with a guide, 134 chronological messages and a source/link register. The final agreement is in messages 130–134 (pages 32–34). Earlier proposals are historical; the current user's two English channels, `ifverse_anime` and `ifverse_hollywood`, take priority over the older three-channel and seven-account plans.

Subsequent implementation has now produced the voiced/captioned 44.672-second test and the current visual-beat revision. Continue on `codex/ifverse-workflow` and read `docs/CURRENT.md`; the remaining-work statements below describe the historical end of the supplied conversation, not a claim that later CPU TTS/caption work is absent.

## Operating contract

The assistant prepares **one production-plan JSON**, submits **one autonomous GitHub job**, and reviews **one compact final result**. Ordinary software completes the intermediate work. The purpose is to reduce repeated agent interaction, not merely to move individual tool calls to GitHub while the assistant still directs every step.

The production plan carries the script, ordered scenes, footage searches, narration choice/input and caption style. The job checks caches, searches/downloads matching moving clips, validates source quality, applies appropriate FFmpeg cleanup, generates or reuses narration, prepares timed captions, renders in narrative order, validates the completed video, and saves the MP4 plus one success/failure report. Cache footage and models, bound retries, retain completed work and open detailed logs only when diagnosis requires them. Do not repeatedly poll or inspect each successful stage through GPT.

**Captioning decision:** evaluate `faster-whisper` on CPU with int8 precision. Measure actual speed, memory use and name/timestamp accuracy on the chosen GitHub runner. It does not require GPU VRAM in this configuration, but model loading/inference still uses CPU/RAM and runner time. Preserve known script text and reconcile recognition errors, especially character names. Existing measured sentence boundaries remain a valid cheaper timing path when sufficient; word timing is not already implemented.

**Voiceover is a separate component:** faster-whisper recognizes speech; it does not generate narration. Kokoro is the earlier English TTS candidate. Reusing existing narration or accepting an input audio file is supported conceptually, but a tested automatic production TTS step and secure hosted audio handoff are still needed for a fully integrated new-script run. The Kaggle template is a finite-batch option, not an established automatic service.

## Existing work and unfinished work

Continue from `codex/youtube-oauth`, preserving its source and private-state continuity. Downloader/cache, light enhancement, ordered media editor, captions and a GitHub-hosted tool workflow already exist. The 46.975-second Naruto review cut uses 18 moving shots from 15 downloaded sources. The recorded 36-second hosted trial measured one clip's collection/cache lookup/enhancement, not complete-video runtime. Recorded tests/runs are historical evidence, not a new execution of this PDF review.

The next build is **integrated one-request production orchestration and CPU captioning**, reusing those components, followed by an end-to-end benchmark. Do not describe the successful small tool test as the finished pipeline. Improve scene relevance and avoid excessive enlargement of low-resolution portrait crops; sharpening alone cannot restore missing detail. Adapt the current Anime branding for Hollywood.

GitHub-hosted jobs are the demonstrated on-demand route; the user's PC need not stay on for that path. n8n is optional coordination, not a prerequisite to the next milestone. A workflow definition and its runner are distinct. Cache restoration, private audio transfer, full-run resource use and restoration of private job/media state need their own validation.

The assistant cannot read or promise a reduction in the user's ChatGPT allowance percentage. GitHub execution and local model inference do not require intermediate ChatGPT model calls, but planning, dispatch interaction, diagnosis and review still use allowance. Measure the complete job separately from the previous short trial.

The workspace must survive an assistant/account change: save non-secret instructions, branch/checkpoint, commands, completed work and exact next actions; preserve private state separately from Git. Planned channel names and local OAuth tests do not prove live account access. The PDF does not establish successful channel binding or public publishing. Old authentication links are not current credentials, and historical consent does not establish new access.

The raw PDF/transcript contains account information and must not be committed. This summary deliberately excludes account identifiers, credentials and authorization-link values. This review did not merge branches, run a production job, connect accounts or publish anything.

