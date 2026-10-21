# OPERATIONS

## Local pose diagnostic (T04, 20 October)

With the existing worker image, owned footage in `data/demo/` and the exact local
checkpoint described in `data/pose_models/mediapipe-full-v1.json`:

```bash
./scripts/pose-smoke.sh --video demo/lat_pulldown.mp4 --start-s 10 --duration-s 10 --repeat
./scripts/pose-smoke.sh --video 'demo/Bicep Curls.MOV' --start-s 0 --duration-s 10 --output-dir /out/pose-smoke/curl
```

The wrapper disables container networking and provides no credentials. It mounts code,
media and the model read-only, and writes only to ignored `artifacts/`. It does not
silently build images or download models. `manifest.json`, `diagnostic.json` and
`diagnostic.html` describe actual poses, original source timestamps, coverage and limits.
An explicit segment of a longer source is a diagnostic; it does not bypass the
product's 30-second upload rule. The daemon now runs queued full eligible videos;
artifact streaming and the browser analysis flow remain unfinished.

Open a generated HTML locally and choose its original source video. The viewer checks
the source SHA256 before displaying it. For loopback serving of the lat example:

```bash
mkdir -p artifacts/pose-smoke/lat-pulldown/media
docker run -d --name motion-xray-pose-diagnostic -p 127.0.0.1:8765:8765 \
  -v "$PWD/artifacts/pose-smoke/lat-pulldown:/served:ro" \
  -v "$PWD/data/demo:/served/media:ro" --entrypoint python motion-xray-worker \
  -m http.server 8765 --bind 0.0.0.0 --directory /served
```

Visit `http://localhost:8765/diagnostic.html`. The preview loads the source locally as
a blob so seeking works without a range-capable server. Playback and the slider use
the original source clock; only valid joints are drawn. Drag the 3D canvas to rotate.
No source is uploaded. Stop/remove only this disposable server when finished:

```bash
docker rm -f motion-xray-pose-diagnostic
```

This viewer is an inspection artifact, not T11 product completion. Identity/depth
accuracy, measurements, reference eligibility and scores need their later gates.

**21 October status:** container builds/checks, T04 local pose inference, T08.1a metadata
store and T03a private HTTP upload/session checks pass. Audio-free proxy/PTS mapping,
worker integration, job HTTP lifecycle and physical deletion/retention remain pending.
The worker service entrypoint is still a stub. Live evidence refresh is
disabled. The dated audit is a historical baseline, not the current test result.

For ingestion, set a persistent random `SESSION_SECRET` (at least32 bytes) in the
gitignored `.env`; an empty value returns503. `APP_ORIGIN` must match the browser origin.
See API.md for GET/session, CSRF and binary-upload protocol. API and worker share
`VIDEO_ROOT=/state/media`; raw files are private0600. The API image reuses FFmpeg
7:5.1.9-0+deb12u1 for bounded metadata probing and contains no pose ML dependencies.
Raw metadata expires after24h by default; no physical janitor or original-media route is
enabled yet. Signed anonymous identities currently expire after24h; recovery/renewal
needs review before release, independently of the planned seven-day report retention.

This is the runbook for operating Motion X Ray locally. Everything runs in containers so
nothing installs on the host beyond Docker Desktop (DECISIONS.md D003). It covers the
Compose commands, environment and secret handling, the data-retention and deletion policy,
and a per-component license / model-terms inventory. Commands are listed here only once
they are verified; do not assume a command works until it appears in this file.

## Compose commands

The Compose build context is the repo root (`..`) with Dockerfiles under `infra/`.

```bash
# Build images, copying .env.example only if .env does not already exist
./scripts/setup.sh

# Start local web/API (pipeline worker is not functional yet)
./scripts/dev.sh -d api web

# Actual CI checks: hashes/frozen installs at build; runtime checks have no network/keys
./scripts/test.sh all
# Focused checks: ./scripts/test.sh python  OR  ./scripts/test.sh web

# Regenerate API/JSON schemas and frontend types inside containers
./scripts/export-contracts.sh

# Validate the compose file without starting anything
docker compose -f infra/compose.yaml config

# Build the api, worker, and web images
docker compose -f infra/compose.yaml build

# Stop services while retaining state/model volumes
docker compose -f infra/compose.yaml down

# Explicit full reset only: also deletes state, models and web_node_modules volumes
docker compose -f infra/compose.yaml down -v
```

`web` is bound to `127.0.0.1:3000`, `api` to `127.0.0.1:8000`. Browser `/api/*` rewrites
to the private API `/v1/*`. The worker exposes no port and does not claim jobs yet.
`test.sh` uses separate `infra/checks.yaml`, never runtime `.env` or state volumes.
Python locks live in `infra/requirements`; regenerate with `scripts/lock_python.py`
inside the test container. Web uses the checked-in pnpm lockfile with frozen installs.
Build tools/images are pinned. Debian package dependencies still follow the pinned base
image's configured repositories; recorded image IDs identify tested artifacts.

Unimplemented analyze/evaluate/cleanup/seed commands return exit code 2, never a false
success. Do not interpret health checks or a successful build as a working analysis.

## Environment and secrets

Runtime configuration is read from a `.env` file (copy `.env.example` → `.env`). `.env` is
gitignored and MUST NOT be committed. Secrets are server-side only, read from environment
variables, never behind a public frontend prefix, and never hardcoded. The build must fail
clearly when a selected provider needs an unset credential rather than silently switching
models (AGENTS.md; `.env.example`).

Keys used by the providers:

| Variable | Purpose | Secret? |
| --- | --- | --- |
| `NEBIUS_BASE_URL` | Token Factory OpenAI-compatible endpoint | No |
| `NEBIUS_MODEL_ID` | NVIDIA Nemotron model id (discover from the account catalog) | No |
| `NEBIUS_API_KEY` | Token Factory credential | **Yes** |
| `TAVILY_API_KEY` | Enables operator-triggered evidence refresh | **Yes** |
| `SESSION_SECRET` | Server session signing secret | **Yes** |
| `POSE_PROVIDER` / `POSE_CHECKPOINT_PATH` | Pose provider selection + checkpoint location | No |

Other operational knobs (provisional, revise before hosted release): `MAX_UPLOAD_MB=100`,
`MAX_VIDEO_SECONDS=30`, `WORKER_CONCURRENCY=1`, `JOB_TIMEOUT_SECONDS=300`.

## Retention and deletion

| Data | TTL | Env var |
| --- | --- | --- |
| Raw uploaded media | 24 hours | `RAW_MEDIA_TTL_HOURS=24` |
| Analysis reports / derived artifacts | 7 days | `REPORT_TTL_DAYS=7` |

Deletion flow: raw media expires 24 hours after upload; reports and derived artifacts
expire 7 days after creation. Expiry is reflected in the contracts via `expires_at`
(`VideoAsset`), and a request against expired data returns the `JOB_EXPIRED` error code
(`docs/API.md`). A user can delete an analysis and its private artifacts on demand via
`DELETE /v1/analyses/{analysis_id}`. All durable state lives in the `state` volume, which
`docker compose down -v` removes entirely, leaving no host-level data behind.

## License / model-terms inventory

Each third-party component's license and usage terms must be confirmed against its current
upstream terms before a hosted release; the summary below is for orientation, not legal
advice.

| Component | Role | License / terms (verify upstream) |
| --- | --- | --- |
| MediaPipe Pose Landmarker | Primary pose provider | Apache-2.0 (library); confirm model-asset terms. |
| NVIDIA Nemotron via Nebius Token Factory | Runtime coaching LLM | NVIDIA open-model license + Nebius Token Factory terms; credits metered. |
| Tavily | Operator-triggered evidence search | Tavily API terms of service; retrieved content treated as untrusted. |
| Next.js | Web client framework | MIT. |
| FastAPI | API framework | MIT. |

Paid provider calls (Token Factory, Tavily) run only in authorized environments; CI uses
fixtures and never spends credits (AGENTS.md).

## Upstream experiment and promotion runbook (planned)

No T19 candidate is installed by this documentation update. Record candidate revision,
code notices, checkpoint/body-model/data terms, checksum, tested image/platform and
bounded question before execution. Use isolated Docker images and verified local model
paths; do not inherit upstream TLS bypasses or uncontrolled checkpoint downloads.

Keep ML-only alternatives in optional worker experiments, not API dependencies. Resolve
NumPy/ONNX/OpenCV compatibility and exact hashes; avoid conflicting OpenCV distributions.
DTAIDistance belongs to the scoring runtime only after wrapper tests and lock updates.
Do not install Sports2D's full application stack just to obtain angle/filtering methods.

| Candidate | Adoption state / owner |
| --- | --- |
| Sports2D / Good-GYM | Methods only; T05 must record exact copied/adapted source and notices if any code is reused. |
| DTAIDistance | Preferred T07 kernel candidate; Apache-2.0 code screened, selected revision/backend not yet pinned or benchmarked. |
| Norfair | Conditional T04 association helper; BSD-3-Clause code screened; no prediction-as-measurement use. |
| rtmlib | Conditional T04 provider; Apache-2.0 code screened, selected checkpoints and dependency terms still require review. |
| AIFit/Fit3D | Method reference; restricted assets are not approved product inputs. |
| ALEX / PoseRAC / other learned assessors | Deferred evaluation candidates; model/data compatibility and rights not established. |

After promotion, update this inventory with exact adopted artifacts, lockfiles, container
placement, checks and rollback path. T19 holds source links and limitations. A permissive
wrapper licence does not grant rights to its datasets/models.
# Pose daemon checkpoint (21 October 2026)

The worker entrypoint now runs the durable pose-only queue. Compose mounts local
`models/` read-only at `/models`; set POSE_CHECKPOINT_PATH to
`/models/pose_landmarker_full.task` and POSE_CHECKPOINT_SHA256 to
`5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1`.
Startup rejects a missing/mismatched checkpoint. WORKER_CONCURRENCY must be1;
WORKER_POLL_SECONDS must be less than a third of WORKER_LEASE_SECONDS. Defaults:
lease60s, poll1s, idle1s, job timeout300s. `--once` processes one claim or exits idle.
SIGTERM/SIGINT reap child process groups and leave interrupted jobs reclaimable after
lease expiry. An already committed result survives shutdown. Configuration/runtime
failures log constant codes without provider credentials or media paths.

Physical TTL/deletion cleanup and artifact streaming are pending. Do not describe
logical revocation as secure physical erasure. No paid coaching call is part of this
daemon acceptance check.
