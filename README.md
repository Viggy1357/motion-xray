# Motion X Ray

Convert a short workout video into a rep-by-rep movement report. Record or upload a
set, inspect reconstructed movement as a rotatable 3D skeleton, compare it against a
curated reference trajectory, and read grounded coaching — all with honest limitations.

> This repository is building towards the product described in
> `docs/PRODUCT.md`. It is **not** a validated biomechanics product. Scores express
> *similarity to a selected reference*, not correctness, safety, or effectiveness.

## Intended product (P0)

Capture/upload → pose extraction → rep segmentation → exercise metrics → reference
comparison → deterministic similarity score → grounded Nemotron coaching, shown as
synchronized video + 2D overlay + rotatable 3D skeleton + a shared rep timeline.

Release exercises: cable lat pulldown, standing dumbbell curl, bodyweight squat and
incline dumbbell press. Per `docs/audit/HM057-HM06-delivery.md`, all four now have
implemented measurement profiles plus unreviewed reference-resemblance estimates and
grounded coaching; top-level technique scores stay null. Lateral raise is deferred.

> Latest processing checkpoint: `docs/audit/HM-FAST02-delivery.md` — local env
> `POSE_ANALYSIS_RESIZE=1` enables bounded 720p/1280 resize for all four exercises.
> Canonical policy: `docs/ANALYSIS-PROCESSING.md`.

## Everything runs in containers

This project is designed so that **nothing installs onto your host OS**. Python 3.12,
Node, the pose/ML stack, and FFmpeg all live inside Docker images. Your machine only
needs a container runtime (Docker Desktop).

```bash
# Start the full stack (web + api + worker), nothing touches the host
docker compose -f infra/compose.yaml up --build

# Stop the stack while preserving its state volume
docker compose -f infra/compose.yaml down
```

See `docs/OPERATIONS.md` for the full runbook and `AGENTS.md` for the contract every
coding agent follows before changing code.

## Provider decisions (recorded in DECISIONS.md)

- **Coaching LLM:** NVIDIA Nemotron via Nebius Token Factory (OpenAI-compatible).
  This is the required runtime NVIDIA-model call for the hackathon submission.
- **Pose:** MediaPipe Pose Landmarker is the primary provider for this build
  (CPU-friendly, no GPU entitlement required). GEM-X remains a documented stretch
  goal pending GPU access. See `DECISIONS.md`.
- **Search/evidence:** Tavily, used only on operator-triggered evidence refresh with
  caching — never per analysis.

## Status

22 October2026: the main app at `http://localhost:3000` now supports guest video upload,
real CPU pose processing, status/cancellation, private replay and browser-local workout
history. Clips can be up to60s/100MiB. Start from `.env.example`, configure a persistent
`SESSION_SECRET` and provide the verified local pose checkpoint before starting Docker.
No Google login or cloud account is required for local pose processing.

**828 offline Python tests**, Ruff/mypy and web typecheck/production build pass.
Main app reports are currently pose-only; detected reps, metrics and scores remain
unavailable there. A separate diagnostic provides synchronized overlays/estimated3D.
The new bounded NVIDIA coaching adapter passed one synthetic live test, but is not yet
connected to uploaded-set reports. Default `ALLOW_LIVE_COACHING=false` keeps it off.

Next: HM04 runtime measurement/quality/report integration, set-evidence coaching and
HM02 durable logs. [Build evidence](docs/audit/HM-first-app-build.md),
[remaining delivery plan](docs/HACKATHON-EXECUTION-PLAN.md).

Run a local pose diagnostic with an existing worker image and the pinned local model:

```bash
./scripts/pose-smoke.sh --video demo/lat_pulldown.mp4 --start-s 10 --duration-s 10 --repeat
```

See [pose validation and limitations](docs/audit/T04-resumed-pose-batch.md) and the
[recorded checkpoint](data/pose_models/mediapipe-full-v1.json). Private footage,
checkpoints and generated diagnostics remain ignored; an owned set is not a reference.

The worker now runs a durable pose-only daemon. Signed-session clients can upload,
enqueue, poll, cancel, delete and retrieve validated reports through the API. Configure
the pinned local model as described in [OPERATIONS](docs/OPERATIONS.md). Artifact
streaming, physical cleanup and the browser analysis flow remain pending; reports
currently have null scores and no exercise measurements. See the
[lifecycle checkpoint](docs/audit/T08.1b.3-lifecycle.md).

Run `./scripts/test.sh all` for the actual offline checks. See `docs/OPERATIONS.md`
for setup, local startup and contract-generation commands.

- [Audit and verified progress](docs/AUDIT-2026-10-19.md)
- [Step-by-step delivery workflow](docs/DELIVERY.md)
- [Current tasks](TASKS.md)
- [MVP token allocations and cost forecast](docs/TOKEN-BUDGET.md)
- [Upstream methods and exact integration plan](docs/INTEGRATION-REVIEW-2026-10-20.md)
- [Repository and dataset screening](docs/REUSE-SCREEN-2026-10-19.md)
- [Full original specification](docs/SPECIFICATION-v2.0.md) (later decisions apply)
- [Project delivery skill](skills/motion-xray-delivery/SKILL.md)

The current goal is a usable personal training MVP. Codex leads implementation;
Kiro and other agents support bounded tasks/reviews with one writer per checkout.

## Reuse plan

Keep MediaPipe primary. Adapt Sports2D geometry/filtering and Good-GYM counter patterns
inside our canonical pipeline; evaluate DTAIDistance as the T07 alignment kernel.
Norfair tracking and rtmlib inference are conditional on a measured baseline failure.
ALEX/PoseRAC learned assessors and restricted research datasets remain deferred.
These are implementation directions, not installed integrations or benchmark results.
See D009/D010 and the delivery work packages for the required checks.

## Verified commands

Exact, verified commands are recorded in `docs/OPERATIONS.md` after each capability is
implemented. Do not assume a command works until it is listed there.
