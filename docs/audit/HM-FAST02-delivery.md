# HM-FAST02 — shared analysis resize rollout

23 October2026 · FR02/03/04/07/08/12 · D021. Owner explicitly authorizes all-four scope
with known squat partial-result limitation. This supersedes the earlier scope gate,
not measured historical evidence. Two direct Nebius workers own scope/tests and docs;
Codex applies reviewed manifests, verifies, activates and records results.

## Delivered

All four current release exercises use the same bounded decode-resize policy when
POSE_ANALYSIS_RESIZE=1: curl,lat,squat,incline dumbbell press. Template1/local1,
unset-codefallback0. Unknown/deferred lateralraise excluded. Explicit0 rollback retained.
Scope changed in processing_config, exact recipe hash fixtures and child scope tests;
underlying decoder/30Hz sampling/model/geometry/thresholds/reference bands unchanged.
No new workout-routine features or unsupported exercise inference added.

Active guidance updated: README, worker README, PRODUCT, ARCHITECTURE, DELIVERY,
OPERATIONS, motion-xray-delivery skill and new canonical ANALYSIS-PROCESSING guide.
Dated audits remain intact. Original source/private replay retained. No upscaling;
sourcePTS/frameindices preserved; old saved reports not reprocessed. Other background
work `.mockups/` and HM09 design brief preserved/uncommitted by this task.

## Checks and actual runtime

- Full Docker scripts/check-python.sh:1034 tests, Ruff/mypy71sources pass. One existing
  Starlette/AnyIO deprecation warning. Provider smokes dry-run; no frontend changes.
- Scope tests assert all four exercise child paths True whenflag1, unsupported False,
  rollback False, exact stable unique scope and changed recipe hash. No quality-gate
  suppression or threshold edits to force an assessment.
- Emptyqueue checked before restarting API+worker. Both live flag/scope/version hashes
  identical. Rollout JSON records the actual source configuration and press job hash.
- Fresh guest press upload through Next/API/worker/report succeeds:122.406s total,
  1197frames,4complete/usable candidates,128metric entries, null technique score,
  partial reference estimate59.9962. Prior original estimate53.4859 from HM057. No
  fresh original press latency baseline, no cross-run accuracy/percentage-speed claim.
- Curl previous paired full-path timings96.071s original vs90.740/92.882s resized,
  approximately3–6% improvement. No new curl reinference for a scope-only change.
- Prior resized squat actual job succeeded in pose but had0cycles/no per-rep metrics,
  null resemblance versus original1cycle. Owner chooses broad scope with this disclosed
  limitation. No automatic original-resolution fallback or synthetic score introduced.
- Lat source464x832 is below bounds; no-upscale tests verify pass-through, but no fresh
  lat guest upload performed in this task. Do not claim all four rebenchmarked.

Evidence: HM-FAST02-rollout.json, prior HM-FAST01-upload-comparison.json; local ignored
hm-fast02-press.json/log and full check log. Existing benchmark CLI is reproducible
inside the API image on local Compose network with mounted repository. No secret,
private video or raw pose arrays committed or sent to coding providers.

## Usage and follow-up

Two Nebius Kimi-K3 low-reasoning calls; complete drafts reviewed/applied via path and
unique-substring checks. Docs writer used scoped public-source snippets. Minor factual
updates after checks/press result applied by integrator. Usage ledger preserves both
calls; no paid coaching/Tavily/hosting calls. Balance unverified, active70USD/protected30
unchanged. Canonical current policy docs/ANALYSIS-PROCESSING.md; D021 records trade-off.

Proceed with the remaining MVP workflow. Broader labelled accuracy and stage-by-stage
latency profiling remain future work; do not reinterpret common policy as equal measured
speed or equal assessment quality across exercises.
