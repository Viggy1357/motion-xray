# EXERCISES

Motion X Ray launches with four exercises: the standing dumbbell curl, the standing
dumbbell lateral raise, the bodyweight squat, and the cable lat pulldown (added per
DECISIONS.md D005 and the first exercise to validate end-to-end). Each is defined by a
declarative exercise spec under `data/exercise_specs/*.yaml` (the source of truth for the
phase signal, segmentation thresholds, and scoring weights). This document defines the
per-rep metrics named in those specs. The metric formulas are deterministic and geometric; in the
current scaffold the math is deferred (TODO(T05)/TODO(T07)), so treat the formulas below
as the intended definitions, not validated biomechanics measurements.

All four specs share the same provisional segmentation shape (normalised phase signal with
`low: 0.2`, `high: 0.8`, `dwell_s: 0.15`) and require the `estimated_3d` and `timestamps`
capabilities. A rep is scored only if its required metrics are present; a missing required
metric nulls the overall score with a reason rather than inventing a value.

## Shared implementation requirements (T05; D010)

Implement a complete-cycle state machine with start/turnaround/return boundaries in
source video seconds. Adapt Good-GYM's hysteresis concept, not its wall-clock counter,
bilateral averaging or threshold values. Use a consistently visible side; change of
side or identity within a rep is not silent continuity. Keep partial/uncertain cycles.

Segmentation needs reviewed calibration for excursion/noise and explicit duration/gap
rules. This is independent of approved scoring-reference acquisition. If unavailable,
show raw angles or uncertain candidates; never normalize each tiny movement to a full
rep. Filter contiguous valid signals only, retain raw values and interpolation labels,
and do not create turnarounds from fillers. Before 2D angles, restore the image aspect
ratio. Projected 2D and estimated 3D metrics retain distinct dimensionality.

These are pending implementation requirements, not newly validated thresholds. Any
functional config change requires a version bump and regression fixtures. Incline bench
chest press remains T17 intake only, not one of the four planned supported profiles.

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
This is the first exercise scheduled for full-pipeline validation; no pass is claimed.

View note: the authorized test clip is filmed from a diagonal, predominantly side angle.
That angle is intended for visible-side elbow motion and torso lean, pending real
validation; the far arm is occluded. `bilateral_difference` is informational-only and
unavailable when required joints cannot be observed; it is never scored at this view.

| Metric | Definition |
| --- | --- |
| `elbow_rom` | Range of visible-side elbow-flexion angle through the pull; not measured bar travel. |
| `shoulder_drive` | Intended upper-arm motion relative to the torso. T05 must define joint subset, angle convention and view validity before scoring; not lat activation or measured scapular depression. |
| `torso_lean` | Backward torso lean from a set-level upright baseline across the rep. |
| `phase_tempo` | Pull vs. controlled-return phase durations relative to the reference tempo band. |
| `trajectory_error` | DTW-aligned deviation of the wrist/elbow trajectory from the reference path. |
| `bilateral_difference` | Informational only; report a value only when both sides are observable, otherwise null with an occlusion/coverage reason. |

The weights applied to these metrics are listed in `docs/SCORING.md` and must match the
`weights` maps in the YAML specs (each map sums to exactly 1.0).
