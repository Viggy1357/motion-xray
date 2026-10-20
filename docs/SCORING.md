# SCORING

Scoring in Motion X Ray is deterministic and explainable. A user's measured metric is
compared against an approved reference interval `[L, U]` with a tolerance `T`, producing a
per-metric 0-100 similarity score. Per-metric scores are combined using the per-exercise
weights from the exercise specs to produce an overall score. This document records the
formula verbatim, the provisional weights, and the missing-data policy. Scores express
*similarity to a selected reference*, not correctness or safety. The scoring math is
deferred in the current scaffold (TODO(T07) in `packages/scoring/scoring/core.py`); the
formula and weights below are the committed contract.

## Formula

For a measured value `x` against reference interval `[L, U]` and tolerance `T`:

```
d = max(L - x, 0, x - U); s = 100 * max(0, 1 - d/T)
```

`d` is the signed-clamped deviation outside the band (zero when `x` lies within
`[L, U]`), and `s` is the 0-100 per-metric score. The per-metric scores are combined with
the component weights below to yield the overall score, and the inputs/outputs are stored
in a `ScoreBreakdown` (`packages/contracts/contracts/scoring.py`) so every score is
auditable.

## Weights (provisional)

These weights are **provisional** — they are the committed starting values in the
exercise specs and are subject to review before any config freeze (DECISIONS.md open
decisions). Each column matches the `weights` map in the corresponding
`data/exercise_specs/*.yaml` and sums to exactly 1.0.

| Component | dumbbell_curl | lateral_raise | squat | lat_pulldown |
| --- | --- | --- | --- | --- |
| elbow_rom | 0.25 | — | — | 0.25 |
| upper_arm_drift | 0.25 | — | — | — |
| arm_elevation | — | 0.25 | — | — |
| side_difference | — | 0.20 | — | — |
| knee_rom | — | — | 0.25 | — |
| hip_descent | — | — | 0.20 | — |
| shoulder_drive | — | — | — | 0.25 |
| torso_sway | 0.20 | 0.20 | — | — |
| torso_lean | — | — | 0.20 | 0.20 |
| phase_tempo | 0.15 | 0.15 | 0.15 | 0.15 |
| trajectory_error | 0.15 | 0.20 | 0.20 | 0.15 |
| **Total** | **1.00** | **1.00** | **1.00** | **1.00** |

`bilateral_difference` is defined for `lat_pulldown` but is **informational-only** at the
diagonal/side view (far arm occluded); it is not a scored component and carries no weight.

## Alignment implementation requirements (T07; not yet implemented)

DTAIDistance is the preferred numerical-kernel candidate under D009. Wrap it inside
the scoring package; it supplies a path, not a percentage, exercise policy or approved
reference. Require compatible variant/view/provider/mapping before alignment.

- Normalize using a stable set-level body transform/scale, preserving original motion
  for sway and lean. Do not normalize each rep to its own ROM or erase reduced excursion.
- Use a shared multivariate feature path, explicit feature scales/weights and separate
  anchored outbound/return alignment. Preserve dwell handling and original index/time
  maps. Compute tempo from original timestamps, never the warped sequence.
- Translate the provisional fractional band into tested library semantics, including
  unequal-length behaviour. Disable endpoint relaxation for complete reps; gaps and
  partial endpoints cannot disappear through alignment. Validate the final path.
- Define path-normalized feature cost explicitly rather than using the library's raw
  rooted cumulative distance as a comparable score. For squared-Euclidean cost,
  coordinate weighting uses square-root weights.
- Pin the implementation/backend and record source/config/reference hashes, feature
  order, normalization, cost and tie rules. Do not silently switch Python/C backends.
  Verify determinism on frozen pose artifacts; cross-backend parity is separate evidence.

T06 builds a reviewed representative trajectory or deterministic medoid from eligible
reps. A medoid does not establish scalar tolerance intervals or technique validity.
Typed alignment/provenance and report breakdowns require coordinated contract migration
before API/UI exposure. Details and exact function boundaries are in the T19 review.

## Required missing-data behaviour

Each spec sets `missing_required_metric: null_overall_score`. When a required metric has
no value, the overall score is **null**, not a fabricated number: `ScoreBreakdown` leaves
`displayed_score=None` and records the cause in `missing_reasons` (AGENTS.md rule 3). Null
means "no value, with a machine-readable reason"; a measured zero is a real zero.
Insufficient scorable reps likewise yield an honest partial result with a reason rather
than a padded score.
