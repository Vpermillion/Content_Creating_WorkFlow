# First Ifverse anime sample

[Watch the 47-second storyboard draft](https://chatgpt.com/library?file_id=libfile_9922c2295e588191b8a12be471c82e88&account_id=personal)

Question: **What if Naruto joined the Akatsuki?** Eight original procedural scenes, local synthetic narration and editable sentence-level captions. This is a fan-created alternate timeline, not a canon episode or official release. No third-party clips, images or music were used. The source premise was checked against the official Naruto overview and Kurama database; URLs and claim-level support are in `pilots/alpha-anime-001.json`. All later plot choices are invented assumptions.

The source is intentionally a storyboard/pipeline demonstration. The current voice is a prototype, not a final narrator. Actual channel ownership, audible pronunciation, full editorial review and publication remain unverified. Nothing was uploaded to YouTube.

## Saved files

- `pilots/alpha-anime-001.json`: immutable source input and original script/scenes.
- `whatif/anime_visuals.py`: original vector renderer.
- `artifacts/alpha-anime-001-script.md` and `artifacts/alpha-anime-001-captions.srt`: editable text outputs.
- `artifacts/alpha-anime-001-quality.json`: automated media checks; approval remains false.
- `artifacts/alpha-anime-001-artifact.json`: saved video ID/hash and review status.

## Reproduce or resume

First locate existing `alpha-anime-001` state. This turn's isolated prototype state is `private/review-pilot-state/` in its source snapshot; do not overwrite it or confuse it with the other cloud task's authoritative science state. If restoring this exact state, call run for the existing ID. If reproducing the demo on a genuinely fresh empty state, run from the repository root:

```sh
python - <<'PY'
import json
from pathlib import Path
from whatif.store import Store
from whatif import pipeline
store=Store('private/review-pilot-state')
spec=json.loads(Path('pilots/alpha-anime-001.json').read_text())
store.add(pipeline.validate_spec(spec))
print(pipeline.run(store,spec['id']))
PY
```

The finished video persists at the link above. Code and manifests do not by themselves preserve the private job database or raw WAV files; cross-host backup of this new sample state is not yet verified. Reproduction is different from restoring verified checkpoints.

## Rendering defect fixed during QA

The first render had an invalid final scene clip even though FFmpeg returned zero, leaving an audio-only tail. The earlier validation checked container duration, audio and decoding but not video-track coverage. The underlying transient failure was not identified. The renderer now allocates frames from cumulative audio boundaries, probes each clip, and checks video/audio track durations. The corrected output has 1409 video frames at 30 fps (46.966667 seconds), matching 46.975 seconds of audio within one frame. The final frame was inspected. Rebuild used an explicit reason and retained narration. Resume subsequently retained video/audio hashes and timestamps.

All 27 tests passed, including corrupt-clip and missing-tail regressions. Frame sampling and automated decoding do not constitute a complete visual/listening review. Generic publication drafts still contain the pipeline's Science hashtags; configure appropriate anime metadata before any delivery. Public posting remains disabled.
