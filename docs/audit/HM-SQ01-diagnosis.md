# HM-SQ01: Squat fragmentation diagnosis (source-only audit)

Scope: static audit of the squat measurement/segmentation source plus a
local-only read-only diagnostic CLI (`artifacts/development/sq01_diagnostic.py`).
No runtime behavior was observed for this audit; no private poses/videos were
provided; no provider calls are made. All count statements below refer to
segmentation **candidates**, never validated reps.

## Grounded likely causes of fragmentation

1. **Strict per-sample missing reset (primary suspect).**
   `profile_squat.PROFILE` has **no `missing_gap_s` key**, so
   `build_exercise_report` builds `ReviewConfig(..., missing_gap_s=0.0)`.
   In `find_cycles`, any `None` angle with `missing_gap_s == 0` takes the
   `_reset(...)` branch: the active HIGH-LOW-HIGH attempt is discarded and
   only a partial span is retained. A single dropped knee-3D sample anywhere
   between the confirmed initial HIGH and the confirmed return HIGH
   fragments one squat into two partials. The curl profile
   (`curl-measure-v2`) carries `missing_gap_s: 0.1` and bridges same-band
   endpoint-capped gaps; squat does not. This asymmetry is the most likely
   structural cause of squat-specific fragmentation.

2. **Missing samples also clear the dwell plateau.** Even where bridging is
   enabled, `plateau_start` is cleared at the first `None` and dwell restarts
   at the next valid sample. With `dwell_s = 0.1` and typical frame spacing
   near 0.033-0.1 s, one missing frame inside a threshold plateau can push a
   plateau below the dwell requirement, delaying or preventing
   HIGH/LOW confirmation and turning would-be cycles into partials.

3. **`max_gap_s = 0.1` timestep jumps reset attempts.** Any inter-sample
   timestamp jump `> max_gap_s` (dropped decoded frames, VFR timestamp
   irregularities) triggers `_reset` before band logic runs. At ~30 fps a
   single dropped frame produces a ~0.067 s step (survivable), but two
   consecutive drops (~0.1 s) sit exactly at the boundary and anything more
   resets the attempt.

4. **Signal choice: `knee_angle / estimated_3d`.** The segmentation signal is
   the estimated-3D knee angle, which depends on three landmarks
   (hip/knee/ankle) with valid 3D. Occlusion at the bottom of a squat
   (thigh-to-calf contact, arms crossing, leaving the frame edges) plausibly
   produces `None` runs exactly mid-cycle, where cause (1) converts them into
   attempt resets. Side selection picks the side with more valid signal
   samples, but the *losing* side's misses are irrelevant — fragmentation is
   driven by the chosen side's gaps.

5. **Resized-pose sensitivity (possible, unverified).** Dimensions used for
   measurement come from `artifacts.proxy.source_width/source_height`. If the
   pose artifact was produced on resized frames while dimensions are reported
   for a different scale, projected-2D features would be affected; the
   estimated-3D signal is less scale-sensitive but landmark quality on
   resized input can still raise the missing-sample rate. This is a
   sensitivity hypothesis, not an observed defect.

6. **Threshold geometry is not the issue to touch.** `low=100, high=150` are
   segmentation trial bounds. Jitter around thresholds already cannot inflate
   counts (covered by unit tests), and intermediate angles reset only the
   dwell candidate, not the phase. No threshold or gap loosening is proposed
   unconditionally.

## What the diagnostic measures (per run, aggregate only)

- frame count; chosen side; per-side valid/missing signal counts;
- consecutive same-band run count/duration aggregates (high/mid/low/missing);
- missing-gap duration buckets: bracketed-same-band vs bracketed-different-band
  vs unbracketed (trailing), with count/total/max;
- cycle/partial candidate counts under the **current** squat policy
  (`missing_gap_s = 0`) versus the **existing conservative curl policy**
  (`missing_gap_s = 0.1`) applied experimentally and **not adopted**;
- bridged-span count under the experimental policy.

Interpretation guide:
- If experimental cycles > current cycles and bridged gaps are overwhelmingly
  `sameband` with `max_s <= 0.1`, fragmentation is consistent with cause (1)
  and the curl-style bridge is a targeted fix candidate.
- If gaps are mostly `differentband` or `unbracketed`, bridging will not help;
  investigate pose quality/occlusion (cause 4/5) instead.
- If both policies yield zero cycles with large `missing` band-run share, the
  signal itself is too sparse; segmentation changes are premature.

## Actionable repair plan (ordered, no unconditional loosening)

1. **Run the diagnostic** on the affected job (`--job UUID`) or retained pair
   (`--pose-dir PATH`) and classify gaps per the guide above. Keep the
   detailed output local (`--save-detailed`); stdout stays aggregate.
2. **If same-band short gaps dominate:** propose adding
   `missing_gap_s: 0.1` to `profile_squat.PROFILE` (matching the existing
   conservative curl policy), bumping the profile `version`, and adding unit
   tests mirroring the curl gap-bridging cases (same-band bridge accepted;
   different-band/overlong/trailing rejected; missing never counts dwell).
   This is a *conditional* repair gated on step 1 evidence, not an
   unconditional loosening.
3. **If different-band or long gaps dominate:** do not change segmentation.
   Investigate pose capture quality for the squat bottom (occlusion, frame
   cropping, camera angle) and confirm proxy/source dimension consistency
   before any policy change.
4. **Preserve honesty invariants in any change:** missing samples stay
   `None` (no interpolation), never count toward dwell, partial spans remain
   recorded and excluded from counts, `Cycle` keeps its three fields, and
   `cycle_missing_spans` stays additive diagnostics metadata.
5. **Reporting:** keep surfacing `MISSING_OBSERVATIONS_RETAINED` and
   `PARTIAL_MOTION` warnings; never present candidate counts as validated
   reps; no accuracy claims without reviewed reference calibration.

## Non-goals / guarantees

- No code in `packages/`, `services/`, or `tests/` is modified by this change.
- The CLI performs no network, auth, pose inference, storage writes, or job
  deletion/reset; it reuses `find_cycles`, `profile_squat.observe`,
  `Store`, and `_load_validated`/`_open_secure`/`_read_file` rather than
  copying their algorithms, and SHA-validates the pose artifact.
- The experimental curl-policy comparison is diagnostic only and is not
  adopted by this change.
