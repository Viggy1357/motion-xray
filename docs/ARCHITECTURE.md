# ARCHITECTURE

Motion X Ray is a Python monorepo of installable packages plus a FastAPI API service, an
isolated pose worker, and a Next.js/TypeScript web client, all orchestrated with Docker
Compose. This document describes the processing pipeline, the provider boundaries that
keep deterministic work separate from external calls, and the container topology taken
from `infra/compose.yaml`. The central design rule (AGENTS.md rule 2) is that
deterministic processing stays strictly separate from LLM output: identical pose
artifacts plus identical config/versions must produce identical metrics and scores.

## Processing pipeline

Latest23 October checkpoint: `audit/HM057-HM06-delivery.md`. Four exercise movement
profiles now run on checked retained pose, with partial unreviewed reference resemblance.
New curl/squat/press baselines derive from actual reference videos, not invented target
ranges. An explicit owner/CSRF-gated coaching POST uses NVIDIA candidate-ID selection,
durable SQLite reservations/cache and fixed daily/lifetime quotas. No paid calls from
GET/render; old0.2 pose manifests and `/result` remain unchanged. Top-level technique
scores stay null. HM02 durable workout/profile logs and HM09 overlay/hosting QA follow.

Earlier22 October assessment checkpoint: `audit/HM04.1-experimental-assessment.md`.
Owner-scoped additive0.3 `/movement-report` derives lat metrics and a partial,
unreviewed experimental QMotion resemblance estimate from checked pose artifacts.
No paid calls/writes from GET; access rechecked after calculation. Legacy0.2 `/result`
stays pose-only; other exercise movement profiles remain unavailable. Main technique
score stays null. HM06 evidence-bound coaching remains the next integration boundary.

Earlier22 October application checkpoint: `audit/HM-first-app-build.md`. Main Next.js
app now has guest upload/status/replay and browser-local logs. Four catalogue entries
and60s intake are implemented. Additive0.3 product models and the bounded standalone
coaching adapter exist; uploaded-set reports still remain strict0.2 pose-only. HM04
report assembly and actual set-evidence coaching are the next integration boundary.

22 October checkpoint: private owner-scoped artifact streaming now supports proxy
byte ranges plus pose JSONL/timestamps. Conservative manual retention removes expired
known completed payloads/reports, with durable cleanup receipts for partial filesystem
failures. Cancelled/ambiguous attempts remain deferred until process reaping is known.
Internal event-level comparison and manual endpoint geometry are implemented; public
reports remain pose-only. Benchmark assessment is frozen per D015 while the owner
discusses the hackathon product flow (`HACKATHON-MVP-DIRECTION.md`).

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

Stages 3 through 6 must reproduce identical metrics/scores from identical frozen pose
artifacts and config/implementation versions. Perception is recorded separately by model,
backend, hardware and transform versions; identical inference across hardware is not
assumed. Only stage 7 involves an LLM, downstream of every displayed measurement/score.

## Integration boundaries (mixed implementation status)

T04 canonical mapping, immutable artifact read/write and the local MediaPipe adapter
are implemented and exercised on owned clips (20 October). T08.1a SQLite metadata/leases
and T03a signed-session private HTTP uploads are implemented (21 October). Original
files remain private under VIDEO_ROOT. Standalone proxy/actual PTS mapping is implemented
and verified on owned footage. T08.1b.1 supervision and T08.1b.2 real child publication
now work through the Store on owned lat/squat inputs. Private typed manifests bind
actual proxy/pose bytes and source timestamps before fenced publication; reports are
explicitly pose-only, with no metrics or score. The worker daemon and authenticated
HTTP lifecycle/report routes are implemented; artifact streaming and physical cleanup
remain pending. Unreviewed drafts are not active.
The API uses pinned FFmpeg tooling for bounded metadata validation, without ML imports.
T05.1 adds pure internal `movement.observations` raw elbow/upper-arm/torso angle
extraction from canonical PoseFrame objects. It preserves anatomical side and original
PTS, gates each metric/space independently and keeps projected2D separate from
estimated3D. It is not wired into public reports; rep segmentation/calibration,
per-rep metrics and comparison/scoring remain pending. No schema or threshold changed.

T05.2b adds internal `movement.posture` for signed projected shoulder/hip axis angles
and strict timestamped window statistics. `scripts/reference_posture_review.py` runs
offline hash-verified diagnostics; it is not the job/report pipeline. Raw ranges stay
per metric/space/window. Public-reference ROI experiments exposed and partly reduced
gross landmark errors; confidence masks alone do not establish geometric accuracy.
Per-rep calibration, bar/chest measurement and valid scoring remain pending. See
`audit/T05.2b-posture-observations.md`; no public schema or existing threshold changed.

T05.2c adds internal explicit-label per-rep observations and an offline review runner.
Measured event angles remain separate from complete-span ROM; invalid spans stay null.
Reference observed ranges stay per source, not pooled across camera views. A controlled
user-crop diagnostic raises all-current-component coverage from4/8 to7/8 selected reps,
with no new score or public-report integration. See `audit/T05.2c-rep-review.md` and
`measurement/T05.2c-rep-protocol.md`; reference compatibility, scoring calibration and
bar/chest localization remain pending. Production HTTP reports remain pose-only.

| Boundary | Owner / planned integration |
| --- | --- |
| Decode → canonical pose | T04 `mediapipe_provider.py`; preserve PTS and actual observations. Conditional `subject_tracking.py` associates detections; conditional `rtmlib_provider.py` implements the same protocol. |
| Pose manifest → numerical input | T04/T05 validated artifact reader: resolve `frames_artifact_key` into immutable frames/timestamps/quality masks. A `PoseSequence` header is not a frame array. |
| Numerical input → reps/metrics | T05 `movement/core.py`: typed signal/config context, aspect-correct geometry, contiguous filtering and full-cycle state machine; adapt methods, not upstream application defaults. |
| Compatible reference → alignment | T06 compatibility/provenance gates; T07 proposed `scoring/alignment.py` wraps a verified DTAIDistance kernel, with phase anchors, original index mapping and explicit cost semantics. |
| Alignment/metrics → score/report | T07 existing scoring policy plus typed alignment artifacts and per-rep/set breakdowns; coordinated schema evolution before public exposure. |

Proposed helper files live under the existing package directories, not new runtime
services. Keep raw observations separate from processed signals. Body-scale/orientation
normalization is stable at set level; preserve unnormalized motion for sway/lean metrics.
Tempo is computed before warping. See `INTEGRATION-REVIEW-2026-10-20.md` and D009/D010.

## Provider boundaries

Provider interfaces are `typing.Protocol` definitions in `packages/providers`, so
downstream code depends on the contract, not on a concrete SDK:

- **`PoseProvider`** (`providers/pose/protocol.py`) — `capabilities()` + `infer()`.
  Primary implementation is MediaPipe (`mediapipe_provider.py`), with verified local
  checkpoint, original PTS, rotation-aware decoding and qualified observation masks.
  No/multiple detections produce gaps; identity remains explicitly unverified.
  GEM-X is a documented stretch (D002). The service job loop now runs pose-only jobs.
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
| `web_node_modules` | Web dependencies kept inside the container, off the host. |

`web` depends on `api`; `worker` depends on `api`. The worker does not expose a port — it
leases jobs from the durable queue. See `docs/OPERATIONS.md` for the runbook.

The worker mounts repository `models/` read-only at `/models`; checkpoint bytes are
SHA256-verified at startup. API and worker derive the same processing-version hash
from checkpoint revision and the pose recipe. A queued job with a mismatched version
fails explicitly. The daemon runs one supervised child at a time; SIGTERM/SIGINT reap
the child, leaving interrupted work reclaimable after lease expiry. A publication
interruption reconciles the committed job before removing attempt files.
