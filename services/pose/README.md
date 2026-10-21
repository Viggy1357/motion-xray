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

The entry point `worker.py` is still startup-only; its daemon loop and shutdown
integration are T08.1b.3 work. The internal `app.pose_jobs.run_pose_once` bridge now
uses the real Store and supervisor to launch `child.py`, run proxy/original-video
MediaPipe processing and publish validated pose-only artifacts. It needs
`services/api` alongside the first-party packages on `PYTHONPATH` inside the worker
container. No ML runtime is installed in the API image.

The internal flow passed on an owned lat excerpt and the full squat clip. Reports
explicitly lack segmentation, measurements, scoring and coaching; HTTP lifecycle/
artifact routes, the app viewer and physical retention are not connected yet. See
`docs/audit/T08.1b.2-real-pose-child.md` for exact checks, limits and the next tasks.

The T04 provider is implemented separately and can be exercised locally with
`./scripts/pose-smoke.sh --video demo/lat_pulldown.mp4 --start-s 10 --duration-s 10 --repeat`
from the repository root. It uses the existing worker image with mounted source,
network disabled and no credentials. Model provenance is in
`data/pose_models/mediapipe-full-v1.json`; place the matching local checkpoint in
`models/`. Output is an immutable pose artifact plus a private diagnostic, not a
durable analysis job or a completed exercise report. No runtime download occurs.

## Reuse boundaries (D009/D010; implementation pending)

MediaPipe stays primary. Conditional rtmlib inference and Norfair subject association
belong inside isolated worker experiments, not the API image. Check selected model
coordinates, rights and dependency locks before promotion. Tracker predictions/stale
detections are not observed joints; static export depth is not estimated 3D anatomy.

Resolve canonical frame artifacts explicitly before movement processing. Preserve
original PTS, selected identity and quality masks. Deterministic replay starts from a
frozen pose artifact; record perception model/backend/runtime separately. See the T19
integration review and T04/T05 work packages for exact methods and acceptance checks.
