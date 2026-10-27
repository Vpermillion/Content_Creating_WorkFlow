# What If video workspace

## Review the anime online-media edit

The latest Alpha sample uses 12 online Naruto stills in 16 ordered shots with camera motion, original narration and overlaid captions. See [the video and reproducible source plan](docs/ONLINE-MEDIA-EDIT.md). A separate image/video import editor is implemented and tested; this actual cut uses stills only. Source-still reuse permission is unverified and publication remains disabled.

A portable, on-demand workspace for original hypothetical science videos. Python owns the jobs, SQLite checkpoints the work, FFmpeg creates the media, and n8n can coordinate the worker through a private API. Your channel settings and progress live in files, not in a conversation.

**Working prototype, not a production deployment.** Three provisional English pilots are included. They use original diagrams, a local synthetic voice, and sentence-level captions. Live research, stock search, Kaggle, Drive, social publishing and analytics are not connected. No post has been published or scheduled. See [PROJECT_STATE.md](PROJECT_STATE.md) for measured results and [HANDOFF.md](HANDOFF.md) to resume.

## Connect YouTube when ready

A separate optional read-only OAuth CLI is now implemented. See [YouTube setup](docs/YOUTUBE.md) and [the cloud-agent prompt](prompts/youtube-connect.md). It verifies an intended channel and can save its non-secret metadata; actual Google authorization is still required. Live uploads/publication remain disabled. Run `python -m whatif.youtube status` for cached connection metadata without initializing the job database.

## Try it without accounts

Requirements: Python 3.12+, FFmpeg/ffprobe with `flite`, `libass`, `librsvg` and `libx264`, plus DejaVu Sans. No Python packages or model API key are needed for the local prototype. Debian/Ubuntu: install `ffmpeg fonts-dejavu-core` through your system package manager. The Docker worker packages these requirements.

From this repository's root:

```sh
python -m whatif init
python -m whatif pilots
python -m whatif run pilot-001
python -m whatif drafts pilot-001
python -m whatif status
python -m unittest discover -s tests -v
```

The rendered file is `data/jobs/pilot-001/video.mp4`. That folder also contains the script, research assumptions, SVG scene assets, narration, SRT/ASS captions, edit manifest and automated quality report. `data/jobs.sqlite3` is the application's private job store. It is separate from n8n's database.

Run the same job again to resume from verified checkpoints. Completed speech is retained after a rendering failure. Checksum mismatches stop a resume; they do not silently approve changed inputs. To intentionally regenerate downstream outputs during development:

```sh
python -m whatif rebuild pilot-001 --from-stage captions --reason 'Explain the layout change'
```

Rebuilding invalidates draft publication records and review approval. A job with an attempted remote delivery cannot be rebuilt under the same version. Edit approved content by creating a new job ID. Repeated topic titles within a channel are rejected.

## Start n8n and the worker

Docker Compose is optional for direct CLI use. It is the tested way to run the coordinator and private worker together.

```sh
python scripts/configure_local.py  # only once; refuses to overwrite .env
docker compose up -d --build
python scripts/configure_n8n.py
docker compose ps
```

Set up your local n8n owner through its editor if you want interactive editing. The imported workflow is inactive and contains no credentials. The helper separately imports a local worker credential into n8n's encrypted credential store and deletes the plaintext transfer file. Keep `.env` private. Reusing the same n8n encryption key is essential for restoring its credentials.

The local editor listens on port 5678 and the worker on port 8090, both bound to loopback on the host. There is no user-facing preview link in this cloud task. The worker exposes `GET /health`, authenticated `GET /jobs/{id}`, and authenticated `POST /jobs/{id}/run`. It accepts only existing validated job IDs and cannot publish or execute arbitrary commands.

`workflows/prepared-pilot.v1.json` submits pilot-002, waits five seconds, and reads its checkpoint. It is a finite manual starter, not an activated production scheduler. A returned `running` status requires another status check. Worker retries are bounded; the workflow retries transient request failures up to three times. See [docs/OPERATIONS.md](docs/OPERATIONS.md) before adding unattended schedules or remote access.

## Channels, providers and approvals

`profiles/science-provisional.json` is an editable demonstration profile, not your confirmed brand or language choice. `pilots/` contains three distinct assistant-prepared scripts. All sources require editorial verification before release. The local writer does not invent new queued content while no model is connected; `whatif/adapters.py` defines replacement boundaries for a model, licensed stock provider and publisher.

The current implementation consumes prepared scripts and original diagrams. Stock footage import/crop, background music, sound effects, automatic research and richer model-driven planning remain backlog items. Language, narrator, tone, styles and platform choices are explicit configuration; the local voice path currently accepts English only.

Drafts cover YouTube, TikTok, Instagram and Facebook as candidate targets. They contain per-platform metadata, null metrics and no provider receipts. Unsupported metrics remain `null`, never zero. Public posting is disabled even after quality approval. A future adapter needs a verified connection, platform eligibility, explicit authorization and reconciliation for uncertain uploads.

The `approve` command records a human's explicit factual, audiovisual and platform review. Do not use it merely because automated checks passed. It does not grant publishing permission.

## Speech batches and portability

See [kaggle/README.md](kaggle/README.md) for the finite Kokoro notebook and matching-run import/export. It has **not** run on Kaggle. Account access, voice/model rights and actual CPU/GPU performance must be checked there. No paid fallback is enabled.

See [docs/BACKUP.md](docs/BACKUP.md) for private application backups, safe demonstration exports, n8n backups and migration. Keep real/private data and credentials outside Git. The bundled demonstration snapshot contains only the three public-test fixtures and generated media, with no SQLite database or secrets.

The repository stores the software. A machine runs it. Development sessions stop when their machine stops. Continuous generation needs a suitable independent host and an available model/provider for new writing. Costs, quotas and remaining connections are in [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md).

## Switch GPT accounts

Start with [the operator guide](docs/OPERATORS.md). Seven public aliases have copy-ready prompts; each can resume the whole workspace. They are separate from video channel profiles. [The universal prompt](prompts/resume.md) works for any authorized replacement assistant. Reconnect repository access and restore private state on a new host; profiles do not log in or transfer personal connections automatically.

See [continuity and channel setup](docs/CONTINUITY.md) for the latest owner instructions, unmerged branch checkpoint and private-repository considerations. [YouTube setup registry](channels/youtube-registry.json) records Alpha's three active planned channels and the deferred account proposals; no live channel or connection is implied.


