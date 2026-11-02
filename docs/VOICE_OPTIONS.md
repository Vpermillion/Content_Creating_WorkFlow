# English narration voice options

The workflow uses Kokoro-ONNX 0.6.1 with the pinned Kokoro v1.0 model and voice file. The exact voice bundle was inspected; its SHA-256 matches the completed narration receipts: `bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d`. It contains **28 English voice IDs**, listed with enabled/tested status in `assets/voices/kokoro-options.json`.

## Currently enabled in the review runner

| Voice | ID | Category | Evidence |
| --- | --- | --- | --- |
| Heart | `af_heart` | American English, female | Used in the completed Naruto review videos. |
| Michael | `am_michael` | American English, male | Accepted by the runner and present in the pinned bundle; a review with this voice has not yet been generated here. |

Other built-in choices include **Adam** (`am_adam`), **Puck** (`am_puck`), **Emma** (`bf_emma`) and **George** (`bm_george`). Their IDs are verified in the same file, but the current request validator has not enabled them. A selection can be enabled without changing TTS providers or buying a service. Do not describe an unauditioned voice as having a particular emotional performance merely from its name.

The full English set comprises 11 American female IDs, nine American male IDs, four British female IDs and four British male IDs. These are model labels; actual tone, cadence, pronunciation and comic delivery should be auditioned. Provider/model licensing remains as recorded in the existing third-party documentation; inspecting the bundle is not a new speaker-cloning operation.

## Choosing and preserving narration

A useful first comparison is the existing Heart voice against Michael, since both are already accepted. Preserve the approved Heart WAV and render comparison clips into a new version. Do not silently replace a channel's voice preference: the profile still records that a final voice choice is unconfirmed.

Changing voice requires new speech, new final-waveform caption alignment, revised scene timing and newly bound sound-effect cues. Reusing another voice's waveform or timestamps is invalid. For new productions, `script_sha256` can bind the cue plan to the final generated waveform within the same job; for retained speech use the exact waveform hash. The current test uses one voice for the whole narration, not separate character voices for a dialogue.

Reference implementation: [Kokoro-ONNX](https://github.com/thewh1teagle/kokoro-onnx). The voice list above comes from the actual pinned [voice bundle](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin), rather than assuming every voice advertised by another website is available to this workflow.
