# EVALUATION

This document records the acceptance **targets** for Motion X Ray and the test layers
that check them. Everything in the "Targets" section below is a target, not a measured
result: no numbers here are claims about current performance. Targets become meaningful
only once the deterministic pipeline is implemented and run against held-out fixtures, and
they will be revised as real data arrives (DECISIONS.md open decisions). Determinism is the
one non-negotiable: identical pose artifacts plus identical config/versions must produce
identical metrics and scores (AGENTS.md rule 2).

## Acceptance targets (targets, not results)

| Area | Target (aspirational) |
| --- | --- |
| Determinism | Re-running the deterministic pipeline on identical inputs yields byte-identical metrics and scores — a hard requirement, verified by regression fixtures. |
| Pose usability (Gate A) | MediaPipe produces usable coordinates with synchronized playback and stable identity on the owned lat-pulldown segment (D005 supersedes the original curl-first gate). |
| Rep segmentation | Detected rep count matches hand-labelled counts on the fixture set within an agreed margin. |
| Scoring stability | Small input perturbations do not cause disproportionate score swings. |
| Coaching groundedness | Coaching references only validated metrics/claims; no invented numbers, with `status=unavailable` on failure. |
| Runtime Nemotron call | One real Token Factory Nemotron inference succeeds at Gate A (D001, D004, owed). |

These are targets pending measurement-specific evidence; dated baseline text below
is historical. T04 pose feasibility and T08 lifecycle checks are recorded separately.
T05.1 (22 October) tests raw angle arithmetic using analytic/high-precision fixtures
and repeat-identical extraction on300 real pose frames. It does not validate landmark
accuracy, rep boundaries, technique standards or scoring. See
`audit/T05.1-raw-observations.md`; human labels and held-out quality checks remain open.

## Test layers

Tests live under `tests/` and run inside containers (CI uses fixtures and never spends
provider credits — AGENTS.md).

| Layer | Directory | What it checks |
| --- | --- | --- |
| Unit | `tests/unit` | Pure deterministic functions (geometry, segmentation, metrics, scoring) in isolation. |
| Contracts | `tests/contracts` | Pydantic models round-trip and JSON Schema export stays stable (`contracts` source of truth). |
| Integration | `tests/integration` | API `/v1` surface and the pose → segment → metrics → score → coach flow with `Fake*` providers. |
| Evaluation | `tests/evaluation` | Held-out fixtures against the acceptance targets above, including determinism regression. |

T02.1 establishes `./scripts/test.sh all`: containerized Ruff, mypy, unit/contract/API
integration tests, web type generation/checking and production build. Sixty-one tests pass;
these validate the baseline and contracts, not movement accuracy. Real pose extraction,
labelled rep/metric evaluation and held-out quality measurements are still pending.

## Upstream integration acceptance matrix (pending)

| Owner / candidate | Required evidence |
| --- | --- |
| T04 primary pose; conditional rtmlib/Sports2D | Same owned segment/offset; known geometry and anatomical sides; PTS synchronization including variable frame rate; coverage/identity; coordinate/3D capability; cold/warm runtime, memory and artifact size. Compare like-dimensional quantities. |
| T04 conditional Norfair | Background entry, crossing, target loss/reacquisition, mirrors, detection reordering and per-video reset. No stale detection or Kalman prediction becomes a current measured joint. |
| T05 geometry/filtering/counter | Aspect-correct 2D angles, degenerate limbs, timestamp gaps, visible-side occlusion, jitter, plateaus, stillness, incomplete excursion, partial clip edges, full return and processing-speed invariance. |
| T06 reference | Rights and technique review separate; compatible view/variant/provider/mapping; stable representative/medoid ties; immutable provenance; experimental/unapproved profiles blocked through API/UI. |
| T07 DTAIDistance wrapper | Identity/known warp, shared multivariate path, strict phases, unequal lengths/band boundaries, partial endpoints, missing samples, cost normalization and deterministic ties. Pin backend; characterize Python/C differences before promotion. |
| T13 optional learned evaluators | Choose exercise before observing true count; no oracle class/result selection. Subject/session-held-out splits. Binary-label F1 does not validate continuous similarity or boundary timing. |

Report count error, missed/spurious reps, boundary timing, partial-rep classification,
coverage, metric agreement and score sensitivity separately. Preserve independent manual
labels; freeze configuration before held-out runs. External skeleton data validates
downstream handling only; it cannot demonstrate phone-video pose quality. Rep-separated
files do not establish continuous-set segmentation performance.

No new benchmark results are asserted by T18–T20. Dataset/model rights and compatible
artifacts must be verified before use. See T19 and D009/D010 for promotion gates.
