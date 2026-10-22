# HM04 runtime movement report checkpoint

22 October 2026. Personal prototype; benchmark policy remains pending.

The main application now derives a standalone 0.3 movement report from the
existing immutable pose artifact. The old 0.2 `/result` and strict pose manifest
remain unchanged. `GET /v1/analyses/{id}/movement-report` is owner-scoped, verifies
the pose hash, secure file access, mapping and estimated-3D capability, then
rechecks access after calculation. No model/search call, write or pose reinference
occurs on this endpoint. Published empty/corrupt artifacts fail clearly; the pure
engine separately supports an empty-input unavailable report.

## Measurements and limits

Lat pulldown uses existing deterministic geometry and cycle arithmetic with the
versioned trial thresholds 100/135 degrees, 0.1s dwell and 0.1s maximum gap.
The whole-set side has the most valid estimated-3D elbow samples, left on ties.
Completed cycles produce 32 component entries each, including missing values with
reasons. Partial fragments remain excluded from the completed count. No threshold
was adjusted to force the owner's ten manually counted reps.

The UI presents cycle timing, arm/torso values, per-metric visibility, private
video seek controls and expandable details. Manual logs remain independent.
Visibility is observed signal coverage, not accuracy probability. Estimated 3D
is uncalibrated; camera-plane torso axis is not gravity or lumbar posture.
All scores, reference intervals and deviations remain null under frozen pending
`lat-component-policy-v1`. No bar/chest contact or technique verdict is inferred.

Curl, squat and incline press return typed `exercise_profile_unavailable` reports
with null count and no copied lat policy or metrics. This is not four-exercise
movement support. Derived reports currently require retained raw pose (up to 24h);
there is no durable seven-day derived-report cache yet.

## Verification

- Container Python checks: Ruff clean, mypy 65 sources, **858 tests passed**.
  Existing upstream Starlette/AnyIO warning remains. Provider smoke runs are dry-run.
- Container web typecheck and production build pass; regenerated OpenAPI/TS include
  the additive report endpoint. No new dependency installed.
- Real local artifact reuse: lat 1,651 frames, 1,530 valid selected elbow samples,
  **five completed candidates, 18 partial fragments, 160 component entries**, five
  windows with both elbow excursion and torso excursion available. Browser shows
  93% rounded visibility and preserves the separate ten-rep history entry.
- All four real pose artifacts were processed by the pure report function twice;
  serialized reports matched exactly. Other three return profile unavailable.
  Aggregate evidence: `HM04-real-acceptance.json`. No private frames are published.
- Route tests cover real analytic cycles, zero-vs-null, capability rejection,
  owner isolation, session/TTL/deletion/revocation, hash corruption, symlink/traversal,
  mapping, duplicate timestamps, empty publication and legacy compatibility.
- Independent Nebius QC found only minor issues. Removed dead helper, made unsupported
  variants deterministic 422, and documented/tested empty-publication rejection.

Seven direct K3 calls, at most three concurrent: 152,419 tokens and conservative
guard cost **$1.008801**. Two malformed output envelopes were retained as failures;
exact allowlisted source strings were recovered and reviewed locally. Account
balance remains unverified. Aggregate commitment $10.31029265 includes the historic
$1 unknown-call contingency once; $70 active/$30 protected ceilings unchanged.
No product runtime paid calls, Tavily spend or paid hosting activation in this run.
See `../development-usage-HM04-2026-10-22.json`.

## Next

HM06: connect bounded coaching to actual validated report evidence, with durable
deduplication/cache and global spend controls before enabling live uploaded-set
calls. Then HM02 durable guest logs/ownership continuity and HM05/HM07 additional
exercise profiles. HM09 overlay, hosting, remote judge acceptance and submission
remain. Benchmark research and calibration expansion stay held.
