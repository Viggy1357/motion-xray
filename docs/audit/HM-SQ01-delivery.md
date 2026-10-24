# HM-SQ01 — conservative squat candidate recovery

Delivered24 October2026 · FR04/05/07/08/12 · D023.

## Cause and change

Squat used strict missing-sample resets. A dropped estimated-3D knee-angle sample
could discard confirmed phase anchors mid-cycle even when both bracketing observed
samples stayed in the same phase band. Source diagnosis and a local read-only replay
supported a bounded trial of the already implemented curl gap policy.

Nebius produced squat-measure-v2 with missing_gap_s0.1 and a matching versioned JSON.
Low100/high150/dwell0.1/max-gap0.1 and all measured geometry remain unchanged. The
v1 JSON is untouched. The shared detector itself was not changed. Missing observations
are not filled, do not count dwell and remain absent from metric coverage. Longer,
cross-band and trailing gaps still reject attempts. Completed candidates retain gap
reasons/warnings/provenance. Reference bands stay unreviewed and unchanged; top-level
technique score stays null. No model, inference, resize or public-contract change.

Separately, the UI main timeline now shows only completed cycles. Exact partial and
excluded fragments remain in one native disclosure with real timestamps, active
playback state and Play controls. Zero-cycle reports explain that analysis finished
without identifying a complete repetition; visibility is still not accuracy.

## Verification

- Container scripts/check-python.sh passes:1,045 unit/contract/integration tests;
  Ruff clean; mypy71 sources clean. One existing AnyIO deprecation warning.
  Nebius/Tavily product smoke commands stayed dry-run, with no paid runtime calls.
- Web pnpm typecheck and pnpm build pass in the existing container check image.
- New analytic tests cover short same-band recovery, strict-policy comparison,
  rejected cross-band/overlong/trailing gaps, missing dwell, preserved null samples,
  gap reasons, deterministic repeat and other profiles remaining unchanged.
- First test run exposed two fixture expectation errors and two historical version
  pins. Nebius repaired exact expectations and version assertions, adding an immutable
  historical v1 geometry comparison; no checks were suppressed or removed.
- Local retained affected pose recovers completed candidates; full derived reports
  serialize identically on repeat. Two retained public squat samples retain their
  previous strict candidate counts. These are sensitivity/regression observations,
  not independent ground truth or a general accuracy benchmark.
- API restarted only after confirming no queued/running jobs. Browser reload of the
  actual owned report shows recovered completed cycles, remaining partial fragments,
  measured evidence and optional coaching. Segment seek/playback-follow verified.
  No video re-upload or new pose inference was needed. Coaching was not generated.

The read-only local diagnostic also needed its retained-file loader corrected: the
actual layout is a PoseSequence manifest, probe dimensions/rotation in diagnostic.json,
and hash-checked frames_artifact_key read via read_pose_frames. Raw observations,
owner identifiers, screenshots and diagnostic payloads remain ignored and local.

## Delegation and resume

Five bounded development calls: Kimi diagnosis, UI cleanup, squat policy/tests,
focused fixture/diagnostic repair, and independent NVIDIA Super VL source review.
All substantive application implementation and test drafts came through Nebius;
Codex applied, checked, recorded and pushed outputs. Only source/tests were provided
as model context. Usage and conservative guard accounting are in
../delegation/HM-SQ01-usage.json; backup not activated, balance unverified.

HM-SQ02 should use broader independently labelled squat sets before any exact-count
or accuracy claim. Do not widen gaps, change thresholds, impute joints or recalibrate
reference bands merely to recover more candidates. HM-UX06 real-device recording and
remaining mockup acceptance are separate and still open. Existing draft PR remains
unmerged. This repair is source/local candidate acceptance, not clinical validation.
