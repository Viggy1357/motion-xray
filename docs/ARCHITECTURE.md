# ARCHITECTURE

Motion X Ray is a Python monorepo of installable packages plus a FastAPI API service, an
isolated pose worker, and a Next.js/TypeScript web client, all orchestrated with Docker
Compose. This document describes the processing pipeline, the provider boundaries that
keep deterministic work separate from external calls, and the container topology taken
from `infra/compose.yaml`. The central design rule (AGENTS.md rule 2) is that
deterministic processing stays strictly separate from LLM output: identical pose
artifacts plus identical config/versions must produce identical metrics and scores.

## Processing pipeline

```
capture/upload → pose → segment → metrics → compare → score → coach
```

1. **capture/upload** — A video asset is registered with verifiable metadata
   (`VideoAsset`). Bytes live in object storage; the pipeline reasons over metadata.
2. **pose** — A `PoseProvider` produces a canonical, timestamped `PoseSequence`; large
   per-frame data (`PoseFrame`/`JointObservation`) is stored out of band and referenced
   by `frames_artifact_key`.
3. **segment** — Repetitions and phase boundaries are detected from the exercise's
   normalised phase signal, producing `Rep` records.
4. **metrics** — Per-rep `Metric` values are measured. A metric that cannot be measured
   stores `value=None` with a machine-readable `reason` — never a fabricated number.
5. **compare** — Measured metrics are normalised and temporally aligned (DTW) against an
   approved `ReferenceProfile`.
6. **score** — Deterministic per-component scoring produces a `ScoreBreakdown` and an
   overall similarity score, or an honest null with `missing_reasons`.
7. **coach** — An `LLMProvider` turns the validated, deterministic evidence bundle into a
   short `CoachingResult`. The model never sees raw video, never produces scores, and
   never invents numbers; on failure it returns `status=unavailable`.

Stages 2 through 6 are fully deterministic. Only stage 7 involves an LLM, and it is
downstream of and separate from every number the product displays.

## Provider boundaries

Provider interfaces are `typing.Protocol` definitions in `packages/providers`, so
downstream code depends on the contract, not on a concrete SDK:

- **`PoseProvider`** (`providers/pose/protocol.py`) — `capabilities()` + `infer()`.
  Primary implementation is MediaPipe (`mediapipe_provider.py`, a stub raising
  `NotImplementedError` in this scaffold); GEM-X is a documented stretch (D002).
- **`LLMProvider`** (`providers/llm/protocol.py`) — `coach()`. Implemented by the Nebius
  Token Factory provider (`nebius_provider.py`, stub) for the required runtime NVIDIA
  Nemotron call (D001, D004).
- **`SearchProvider`** (`providers/search/protocol.py`) — `search()` + `extract()`. The
  default `cached` provider reads local records (zero spend; approval filtering remains
  T10 work). Tavily search/extract is partially implemented, but the API blocks live
  selection until operator/spend controls exist. Discovery does not approve claims.

Each interface ships a deterministic `Fake*` double that returns canned, valid contract
objects for tests, so CI never spends provider credits.

## Container topology

Everything runs in containers; nothing installs on the host beyond Docker Desktop
(D003). The Compose build context is the repo root (`..`) with Dockerfiles under
`infra/`. Defined in `infra/compose.yaml`:

| Service | Image (Dockerfile) | Role | Ports |
| --- | --- | --- | --- |
| `web` | `infra/web.Dockerfile` | Next.js client | 3000 |
| `api` | `infra/api.Dockerfile` | FastAPI `/v1` surface | 8000 |
| `worker` | `infra/worker.Dockerfile` | Claims pipeline jobs from the durable queue; no exposed port | — |

Pose ML dependencies (mediapipe) are an isolable extra pulled **only** by the worker
image, never by the api image, so an ML dependency conflict can never break the API.

Named volumes:

| Volume | Purpose |
| --- | --- |
| `state` | SQLite DB + private artifacts; durable across restarts, removed with `-v`. |
| `models` | Downloaded pose checkpoints, verified by revision/checksum. |
| `web_node_modules` | Web dependencies kept inside the container, off the host. |

`web` depends on `api`; `worker` depends on `api`. The worker does not expose a port — it
leases jobs from the durable queue. See `docs/OPERATIONS.md` for the runbook.
