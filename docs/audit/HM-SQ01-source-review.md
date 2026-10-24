# HM-SQ01 Source Review

Scope: bounded review of squat-measure-v2 missing-gap policy and timeline declutter. Files reviewed: packages/movement/movement/profile_squat.py, packages/movement/movement/configs/squat-measure-v1.json, packages/movement/movement/configs/squat-measure-v2.json, packages/movement/movement/review_cycles.py, packages/movement/movement/runtime_exercises.py, apps/web/app/movement-report.tsx. No code changes made.

Test-fixture repairs pending (off-by-one gap bracket, report transition semantics, old v1 profile pins) are not classified as algorithm bugs.

## Source acceptance

profile_squat.py / PROFILE: v2 adds opt-in missing_gap_s = 0.1 s; v1 JSON preserved unchanged alongside v2; _load_profile_config asserts loaded config equals module PROFILE. observe emits five fixed-order AngleObservations per call; unmeasurable geometry yields value None with deterministic reason; no smoothing, segmentation, depth, or technique judgment. Accepted.

review_cycles.py / find_cycles: gap bridging is opt-in (missing_gap_s > 0) and only after the initial HIGH is confirmed. A None run is bridged only when the prior and next observed samples share one threshold band (both high, both low, or both middle) and elapsed time between those valid endpoints is <= missing_gap_s + 1e-9. Missing frames clear the plateau candidate at the first None, never count toward dwell, and are never interpolated. Accepted spans are stored on CandidateResult.cycle_missing_spans, one tuple per cycle, diagnostics metadata only. Cycle retains exactly three fields. Accepted.

runtime_exercises.py: build_exercise_report propagates missing_gap_s into ReviewConfig and records config_sha256, segment_config_version, pipeline_version in provenance. When gaps exist it records missing_observations_policy and missing_spans_trace. Metrics derive only from observed samples; missing values are None with explicit reason; reference_interval and deviation stay None until a valid baseline is applied. Squat COMPARISON_KEYS are knee_angle/estimated_3d bottom/excursion, hip_angle/estimated_3d/bottom, torso_axis_angle/projected_2d/excursion; no knee-to-elbow relabel; curl and press profiles untouched. Accepted.

runtime_exercises.py / apply_reference_assessment: baseline must be exercise-reference-bands-v1 with author false and review unreviewed; bands come only from the exercise primary reference; assessment status is always partial even at 100; no top-level technique score is fabricated. Missing or invalid baseline, or insufficient eligible cycles, leaves assessment unavailable while measurements are still returned. Accepted.

movement-report.tsx: the primary chip strip shows only completed cycles. All partial/excluded fragments appear once in a single Partial / excluded fragments disclosure with timestamps and Play buttons. Active segment follows real source playback via mxr:source-time, preferring a completed interval and falling back to an excluded fragment, then seekTo(rep.start_s). Replay follow preserved. Accepted.

## Limits (not blockers)

- find_cycles is explicitly experimental; cycle candidates are not ground truth; bottom_s is LOW-threshold plateau entry, not a kinematic extremum; detected_rep_count is an automatic candidate count, not human-validated rep accuracy. No source makes that claim.
- Torso axis is image_up_unverified; camera orientation is provisional and unverified.
- Reference comparison is gated on an unreviewed baseline; the 30-degree normalization is an explicit unreviewed hypothesis; coverage is valid samples over window frames, a completeness signal, not accuracy.
- Bridge boundary uses <= missing_gap_s + 1e-9, so the exact 0.1 s boundary is accepted by design. Pending fixture repairs address gap bracket and report transition semantics.
- State sensitivity and validation limits are not calibration approved; existing reference bands are unchanged.

## Blockers

None within the reviewed scope.

## Integration verification update — 24 October

The pending fixture repairs above are now applied. All1,045 Python checks, Ruff,
mypy71 sources and the web typecheck/production build pass in Docker. New tests
retain observed-anchor and gap-bracket assertions with corrected analytic expectations;
no algorithm checks were removed. Existing v1 config remains unchanged and explicitly
compared to v2 geometry. Source review wording was corrected to include the middle
band, which the existing detector already supports. Real retained-artifact repeat
and browser report/replay-follow checks passed locally; no private data is published
in this audit. See HM-SQ01-delivery.md for scope and remaining validation limits.
