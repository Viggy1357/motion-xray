# HM00/HM01/HM03/HM08 — first application checkpoint

22 October2026, Malaysia time. Implementation checkpoint, not submission-ready MVP.

## Delivered

- Four-screen responsive Next.js app: dashboard, new set, results and browser history.
  Guest session establishment, raw-body upload with real byte progress, status polling,
  cancellation errors, private playback, local rep/load/notes logging and report reopening.
  Completed result can be reopened with a same-owner browser result URL; no auth tokens
  are put in URLs or localStorage. Empty state starts empty, not with invented user data.
- Four-entry typed catalogue with actual request support: lat pulldown, curl, squat,
  incline dumbbell press. Catalogue only advertises implemented pose capability.
- Coherent60s media limits across API config, ingest, Store, proxy, MediaPipe and
  PoseJobInput; versioned recipe invalidates old processing configuration caches.
- Additive product/profile/workout/routine/quality/prototype-report models with null
  semantics, finite values, cross-reference validation and explicit0.2/0.3 dispatch.
  Generated JSON schemas, OpenAPI and TypeScript updated. Strict old manifest unchanged.
- Async bounded NVIDIA coaching adapter replaces the stub. Locally validated candidate
  IDs only, no model-generated metric/score. Lazy SDK, explicit live flag,35s deadline,
 500-token output, zero SDK retries,128-entry per-instance cache/dedup and call quota.
  It is not yet invoked by the uploaded-set pipeline.

## Verification

- `sh scripts/check-python.sh` in `motion-xray-checks-python` with mounted source and
  explicit PYTHONPATH: **828 passed**, Ruff clean, mypy63 files. Existing upstream
  Starlette/AnyIO deprecation warning remains; no new ignored/skipped tests.
- `pnpm typecheck && pnpm build` in web checks image against regenerated API types:
  pass. Main route roughly7.86kB/110kB first-load JS. No new library installed.
- Browser: original55.111678s lat upload -> real separate CPU pose worker -> succeeded
  -> owner-private replay/result. User-confirmed10 reps saved manually in history;
  missing detected count stays null. Fresh tab reload reads the saved10-rep log.
- Browser review caught and corrected typography specificity, missing populated-dashboard
  action, false capability copy, pose-only zero count, stale result persistence,
  cancelled request errors, generated JSX and video deletion/retention wording.
- Additional full-length input/owner isolation acceptance is recorded separately in
  `HM-full-set-acceptance.json`; do not interpret pose success as scored technique proof.
  Full-length pose samples: lat1651, curl619, squat425, press1197. Press recovery,
  including upload/processing/private-artifact checks, took169.38s on this local CPU.
  It verifies completion, not a fast universal processing-time guarantee.
- Standalone Nano adapter: one synthetic fixture,208 input/20 output tokens, validated
  output at1.067s. `HM-runtime-adapter.json`. No private media/pose arrays sent.

## Delegation and review

Twelve direct Nebius calls, at most three concurrent. K3 provided source/contracts/UI and
focused repair. Lightning drafted readiness notes; review corrected its false6.70MB
upload-limit claim and misleading credit assumptions. One K3 repair exhausted its
completion budget; its cost is retained and one larger bounded repair succeeded.
No numerical Codex-savings percentage is claimed.

Development198,624 tokens, conservative guard cost$1.339722; standalone runtime guard
cost$0.000516. Aggregate commitment$9.30149165 includes historic$1 unknown-call contingency.
These are not invoice rates or verified account balance. $70 active/$30 protected
ceilings unchanged. No Tavily spend or paid infrastructure activation.

Full-set testing exposed a real press timestamp-probe failure. The first decoder-budget
hypothesis did not resolve it and was rolled back. An isolated actual source probe
then raised `TimeoutExpired` at30.03s. The final versioned fix increases only that probe
budget to90s; decoder120s and job300s bounds remain. Four new timestamp-budget cases
cover finite budget, no hidden retry, invalid PTS and unchanged metadata limits.

## Remaining before the submission

1. **HM04 next:** runtime automatic candidate reps/actual metric report assembled from
   immutable pose artifacts, versioned observation coverage and frozen reference output;
   wire the report into the existing UI. Public reports currently remain pose-only.
2. Connect validated report evidence to the adapter, durable cache/global quota and real
   uploaded-set NVIDIA call. The synthetic test is not that end-to-end proof.
3. HM02 durable server profile/workout store and durable anonymous ownership continuity;
   migrate the intermediate local-only history without data loss.
4. HM05/HM07 exercise-specific measurements, with honest unavailable metrics/view handling.
   Pose support does not establish exercise-specific scoring or accurate rep counts.
5. HM09 synchronized pose overlay/estimated3D and rep timeline. Current illustrative
   silhouette is an exercise-target graphic, not a reconstruction of the user.
6. Optional routines/3D muscle polish after core loop passes; final hosting, real remote
   judge uploads, retention scheduling/quotas, release QA and submission material.

Benchmark research remains frozen. Hosting selection deferred under owner direction.
