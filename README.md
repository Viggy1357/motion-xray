# Motion X Ray

Convert a short workout video into a rep-by-rep movement report. Record or upload a
set, inspect reconstructed movement as a rotatable 3D skeleton, compare it against a
curated reference trajectory, and read grounded coaching — all with honest limitations.

> This repository implements the intended build described in
> `docs/PRODUCT.md`. It is **not** a validated biomechanics product. Scores express
> *similarity to a selected reference*, not correctness, safety, or effectiveness.

## What it does (P0)

Capture/upload → pose extraction → rep segmentation → exercise metrics → reference
comparison → deterministic similarity score → grounded Nemotron coaching, shown as
synchronized video + 2D overlay + rotatable 3D skeleton + a shared rep timeline.

Launch exercises: simultaneous standing dumbbell curl, bilateral standing lateral
raise, bodyweight squat.

## Everything runs in containers

This project is designed so that **nothing installs onto your host OS**. Python 3.12,
Node, the pose/ML stack, and FFmpeg all live inside Docker images. Your machine only
needs a container runtime (Docker Desktop).

```bash
# Start the full stack (web + api + worker), nothing touches the host
docker compose -f infra/compose.yaml up --build

# Tear everything down, leaving no host-level packages behind
docker compose -f infra/compose.yaml down -v
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

Scaffolded. The feasibility spike (Gate A) is the next step: prove MediaPipe produces
usable coordinates with synchronized playback, and run one real Token Factory
Nemotron inference. See `TASKS.md`.

## Commands

Exact, verified commands are recorded in `docs/OPERATIONS.md` after each capability is
implemented. Do not assume a command works until it is listed there.
