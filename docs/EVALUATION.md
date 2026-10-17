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
| Pose usability (Gate A) | MediaPipe produces usable coordinates with synchronized playback and stable body identity on a real curl clip (D002, owed at Gate A). |
| Rep segmentation | Detected rep count matches hand-labelled counts on the fixture set within an agreed margin. |
| Scoring stability | Small input perturbations do not cause disproportionate score swings. |
| Coaching groundedness | Coaching references only validated metrics/claims; no invented numbers, with `status=unavailable` on failure. |
| Runtime Nemotron call | One real Token Factory Nemotron inference succeeds at Gate A (D001, D004, owed). |

These are targets pending measurement. None has been validated in this scaffold.

## Test layers

Tests live under `tests/` and run inside containers (CI uses fixtures and never spends
provider credits — AGENTS.md).

| Layer | Directory | What it checks |
| --- | --- | --- |
| Unit | `tests/unit` | Pure deterministic functions (geometry, segmentation, metrics, scoring) in isolation. |
| Contracts | `tests/contracts` | Pydantic models round-trip and JSON Schema export stays stable (`contracts` source of truth). |
| Integration | `tests/integration` | API `/v1` surface and the pose → segment → metrics → score → coach flow with `Fake*` providers. |
| Evaluation | `tests/evaluation` | Held-out fixtures against the acceptance targets above, including determinism regression. |

Host-level scaffold validation (Python 3.9, no Docker) is limited to `py_compile`, JSON/
YAML parsing, and gated dry-run smokes. Container-level checks (pytest, ruff, mypy, pnpm
`tsc --noEmit`) run once Docker Desktop is available — see `docs/OPERATIONS.md`.
