# services/pose — isolated pose runtime

This service is the **pose worker**: the only place in Motion X Ray that runs the
heavy ML stack (MediaPipe) plus `ffmpeg`. It is deliberately kept in its own
Docker image (`infra/worker.Dockerfile`), separate from the API service's image
(`infra/api.Dockerfile`).

## Why it's isolated

- **A pose dependency conflict can never break the API.** The ML stack
  (MediaPipe and its transitive native/numeric dependencies) is pinned and
  installed only in the worker image. The `api` image never pulls those extras,
  so an upgrade or conflict in the pose runtime cannot take down request
  serving. This mirrors the isolable `pose` extra in
  `packages/providers/pyproject.toml` and the service split in
  `infra/compose.yaml` (`api` vs `worker`).
- **It matches the recorded decision.** See `DECISIONS.md` D002 (MediaPipe as the
  primary pose provider) and D003 (everything runs in containers). The worker
  claims jobs from the durable queue and does not expose a port.

## How it runs

Per `infra/compose.yaml`, the `worker` service mounts `../services`, `../packages`,
`../data`, the shared `state` volume (SQLite db + private artifacts) and a
`models` volume (downloaded pose checkpoints). It reads config from `.env` and
`DATABASE_URL` / `ARTIFACT_ROOT` env vars — no secrets are baked into the image.

The entry point is `worker.py`, which runs a job loop: it claims a queued
`AnalysisJob`, runs perception followed by deterministic measurements, honours the
job's lease and cancel flag, and writes a result. In this scaffold `worker.py`
only logs `pose worker started`; the pipeline stages are pseudocode comments to
be implemented by their owning tasks (T04 pose, T05 metrics, T07 scoring, T08
jobs, T09 coaching).

## Reuse boundaries (D009/D010; implementation pending)

MediaPipe stays primary. Conditional rtmlib inference and Norfair subject association
belong inside isolated worker experiments, not the API image. Check selected model
coordinates, rights and dependency locks before promotion. Tracker predictions/stale
detections are not observed joints; static export depth is not estimated 3D anatomy.

Resolve canonical frame artifacts explicitly before movement processing. Preserve
original PTS, selected identity and quality masks. Deterministic replay starts from a
frozen pose artifact; record perception model/backend/runtime separately. See the T19
integration review and T04/T05 work packages for exact methods and acceptance checks.
