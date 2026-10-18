# EXERCISES

Motion X Ray launches with four exercises: the standing dumbbell curl, the standing
dumbbell lateral raise, the bodyweight squat, and the cable lat pulldown (added per
DECISIONS.md D005 and the first exercise tested end-to-end). Each is defined by a
declarative exercise spec under `data/exercise_specs/*.yaml` (the source of truth for the
phase signal, segmentation thresholds, and scoring weights). This document defines the
per-rep metrics named in those specs. The metric formulas are deterministic and geometric; in the
current scaffold the math is deferred (TODO(T05)/TODO(T07)), so treat the formulas below
as the intended definitions, not validated biomechanics measurements.

All three specs share the same segmentation shape (normalised phase signal with
`low: 0.2`, `high: 0.8`, `dwell_s: 0.15`) and require the `estimated_3d` and `timestamps`
capabilities. A rep is scored only if its required metrics are present; a missing required
metric nulls the overall score with a reason rather than inventing a value.

## Dumbbell curl (`dumbbell_curl`, standing both arms)

Phase signal: `elbow_flexion_angle` (side view).

| Metric | Definition |
| --- | --- |
| `elbow_rom` | Range of elbow-flexion angle from rep start to turnaround, per arm. |
| `upper_arm_drift` | Movement of the upper-arm segment away from the torso during the rep. |
| `torso_sway` | Deviation of the torso axis from vertical across the rep. |
| `phase_tempo` | Concentric/eccentric phase durations relative to the reference tempo band. |
| `trajectory_error` | DTW-aligned deviation of the joint trajectory from the reference path. |

## Lateral raise (`lateral_raise`, standing both arms)

Phase signal: `shoulder_abduction_angle` (front view).

| Metric | Definition |
| --- | --- |
| `arm_elevation` | Peak shoulder-abduction (arm elevation) angle reached in the rep, per arm. |
| `side_difference` | Left/right asymmetry between the two arms' elevation. |
| `torso_sway` | Deviation of the torso axis from vertical across the rep. |
| `phase_tempo` | Raise/lower phase durations relative to the reference tempo band. |
| `trajectory_error` | DTW-aligned deviation of the joint trajectory from the reference path. |

## Squat (`squat`, bodyweight)

Phase signal: `knee_flexion_angle` (side view).

| Metric | Definition |
| --- | --- |
| `knee_rom` | Range of knee-flexion angle from standing to the bottom of the squat. |
| `hip_descent` | Vertical descent of the hip relative to standing height. |
| `torso_lean` | Forward lean of the torso axis at the bottom of the rep. |
| `phase_tempo` | Descent/ascent phase durations relative to the reference tempo band. |
| `trajectory_error` | DTW-aligned deviation of the joint trajectory from the reference path. |

## Lat pulldown (`lat_pulldown`, cable seated bilateral)

Phase signal: `elbow_flexion_angle` (diagonal/side view). Added per DECISIONS.md D005.
This is the first exercise exercised through the full pipeline.

View note: the authorized test clip is filmed from a diagonal, predominantly side angle.
That angle reads pull depth and torso lean well but occludes the far arm, so
`bilateral_difference` is informational-only (reported with low confidence), not scored.

| Metric | Definition |
| --- | --- |
| `elbow_rom` | Range of elbow-flexion angle through the pull (bar-travel proxy). |
| `shoulder_drive` | Shoulder adduction/depression excursion during the pull (lat-engagement proxy). |
| `torso_lean` | Backward torso lean from a set-level upright baseline across the rep. |
| `phase_tempo` | Pull vs. controlled-return phase durations relative to the reference tempo band. |
| `trajectory_error` | DTW-aligned deviation of the wrist/elbow trajectory from the reference path. |
| `bilateral_difference` | (Informational only at this view) left/right pull asymmetry; low confidence when the far arm is occluded. |

The weights applied to these metrics are listed in `docs/SCORING.md` and must match the
`weights` maps in the YAML specs (each map sums to exactly 1.0).
