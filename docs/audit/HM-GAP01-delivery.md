# HM-GAP01 — curl short-gap retention

23 October2026 · FR04/05/07/08/12 · D019. User explicitly authorizes Nebius-led work.

## Delivered

Versioned curl-measure-v2 opt-in, same80/140degree thresholds/dwell0.1/maxgap0.1.
New optional missing_gap_s0.1 applies only to curl. `ReviewConfig` defaults0, preserving
strict existing consumers. A run of explicit missing angles can retain confirmed
anchors only across same-band valid endpoints<=0.1s apart (+1e-9 floating tolerance).
Missing time does not count dwell: current dwell is cleared immediately and restarts
on the next observed sample. Gaps across bands, excessive endpoint duration, implicit
large timestamp jumps and trailing missing samples do not bridge. All anchors observed.

No imputation/interpolation. Raw pose bytes unchanged. CandidateResult carries internal
per-cycle missing spans while Cycle retains original three fields for compatibility.
Runtime retains actual valid/window-frame coverage and null metrics, adds public rep
reason contains_unmeasured_gap and an explicit report warning/provenance span trace.
Geometry/scoring formula unchanged. Public contracts unchanged. Existing curlv1 config
retained, module/profile/version fixture intentionally moved to v2. Other profiles stay
strict. No new dependencies or host runtimes installed.

## Retained local curl artifacts

| Recipe | Strict candidates | New candidates | New provisional estimate |
| --- | --- | --- | --- |
| Original30Hz | 2 | 4 | 83.3347 |
| 720p30Hz | 1 | 4 | 88.2809 |
| 720p15Hz | 1 | 1 | 87.4161 |

Actual second-cycle observation gap around18.6s is bracketed by valid samples
18.566667..18.633333 at30Hz, within0.1s and the same middle band. Missing right arm
is still missing.15Hz bracket18.533333..18.666667 exceeds0.1s, so is rejected.
Report warnings mark2 gapped original cycles and3 gapped resize30 cycles. These are
provisional candidates, not user-confirmed repetitions or good-form classifications.
Changed subsets alter the reference estimate; unchanged reference bands remain
unreviewed. Top-level technique score stays null. No human ground-truth calibration,
new inference, input optimisation adoption, or other-exercise expansion claimed.

## Verification and delegation

- Direct Nebius Kimi-K3 low-reasoning draft and targeted repair produced source/tests.
- First run exposed new-fixture decimal dwell rounding and Cycle dataclass tuple-shape
  incompatibility. Nebius repaired fixtures with binary-exact timing and moved metadata
  to CandidateResult. Existing strict detector tests were not edited or weakened.
- Full Docker scripts/check-python.sh passed:991 tests, Ruff and mypy71sources.
  One existing Starlette/AnyIO deprecation warning. Provider smokes dry-run only.
- New regressions cover strict defaults, same-band accepted/rejected gaps, no fake
  dwell/anchors, multiple/trailing/long gaps, implicit jumps, metadata isolation,
  input immutability and deterministic repeat. Current public runtime tests pass.
- Real artifact evaluation uses hash-checked frames, actual dimensions/PTS, existing
  build_exercise_report/apply_reference_assessment, and recorded new warning/coverage.
  Two complete serialized comparisons byte-identical. Reproducer local ignored
  artifacts/development/hm_gap01_acceptance.py adapts HM-PERF02 trace with the explicit
  new ReviewConfig option. Aggregate published as HM-GAP01-real-comparison.json.
- Extra Nebius QC/test draft hit completion limit and returned malformed/incomplete
  JSON. Entire response rejected; no tests/claims from it applied; no retry. Accepted
  implementation/targeted repair and container verification form the delivered gate.
- Usage ledger records all three calls, including rejectedQC; no private footage/pose
  arrays/credentials were sent to coding models. No Tavily or product runtime spend.

No frontend changes. API restart activates derived curl report policy; stored pose
manifests remain0.2 and video processing remains original resolution/30Hz. Coaching
uses report/evidence/version-derived keys, so new explicit requests are separate from
old report cache. No paid calls triggered by this rollout. Next: user review, then
broader labelled validation before wider policy/input optimisation adoption.
