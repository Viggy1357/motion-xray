# HM-FAST01 — upload analysis decode resizing

23 October2026 · FR02/03/04/07/08/12 · D020. Owner authorizes Nebius-led implementation.

## Delivered and active scope

MediaPipe receives RGB analysis frames resized during FFmpeg decoding: shortedge<=720,
longedge<=1280, no upscaling, aspect preserved within nearest integer pixel. Dimensions
are rotation-aware and shared between decoder byte framing and model input reshape.
Original private upload and playback proxy path are unchanged. No extra encoded analysis
file, FPS/setpts filter, interpolation, model or scoring threshold change. Actual30Hz
sample selection uses original source PTS and frame indices. Original upload transfer
size is unchanged; this accelerates processing rather than the network upload itself.

Local `.env` POSE_ANALYSIS_RESIZE=1 now affects **dumbbell_curl only**. Template default0
and provider defaultFalse allow rollback. Squat, lat and inclinepress remain original
resolution. `analysis-decode-720-v1`, enabledflag, scope and dimensions enter versionhash.
No public schema changes, new dependencies or host runtimes. Existing reports/video
artifacts remain retained; only new uploads/jobs use the active recipe.

Operational switch: ensure no queued/running jobs, edit flag, recreate API and worker
together. Both use the same versioned configuration. Changing only one service can
mislabel queued work; this rollout checked empty queue before every flag/scope switch.
A per-job immutable recipe execution fence is not added by this narrow change.

## Real full-path curl timing

The new `scripts/benchmark_upload_analysis.py` gets a real guest session, uploads raw
original bytes through Next `/api/videos`, creates/polls the job, and fetches both legacy
pose-only and movement reports. No forged sessions, third-party calls or paid coaching.
It requires real movement metrics and null technique score, and fails on partial/no
measurable-cycle assessments rather than passing an empty placeholder. Intended as an
operator benchmark for known demo clips, not a claim all partial results are fabricated.

| Run | Upload | Queue/worker | Reports | Total |
| --- | --- | --- | --- | --- |
| Original30Hz | 0.349s | 95.408s | 0.251s | 96.071s |
| Initial resized30Hz | 0.245s | 90.181s | 0.229s | 90.740s |
| Final scoped resized30Hz | 0.287s | 92.281s | 0.229s | 92.882s |

Create/session remainder included in total. Observed end-to-end reduction3.3–5.5%,
**not** HM-PERF01's2.8x pose-only improvement. Baseline/first candidate overlapped brief
offline checks; final candidate did not. One baseline/two candidate runs on local Docker
network, not statistical latency validation or a WAN/judge-hosting estimate. Further
stage profiling is needed before attributing the remaining latency or claiming a large
speedup. No new stage-specific timers or internal timing claims were fabricated.

All curl runs619pose frames,4detected/usable candidates,128metric entries; elbow signal
coverage97.5767% original vs97.2536% resized. Provisional resemblance83.3347 vs83.3880.
Both resized runs identical pose SHA and measurements despite different scopeversion
hash. These are model-derived provisional measurements, not independent accuracy labels.
Existing reference bands unchanged/unreviewed; technique score null.

## Global rollout rejected

A real resized squat upload succeeded through pose publication but had0complete cycles,
no per-rep metrics and null resemblance. Prior original squat artifact had1candidate
and43.0162 resemblance. The acceptance runner correctly failed its measurement gate;
no lower threshold/made-up score used to force a pass. Local aggregate evidence records
this honest partial result. Global flag was switched off, then Nebius added versioned
curl-only scope and tests. Press/lat were not newly resized after this rejection.

The failed benchmark job remains a private owner-scoped local test artifact under normal
retention. Do not treat its absence of metrics as fake perception: the error text is a
benchmark acceptance failure for the known clip, not a user-facing model judgment.

## Checks and delegation

-1032 full offline Python tests; Ruff and mypy71sources pass. One existing Starlette/
AnyIO deprecation warning. Provider smokes dry-run only; no frontend code/build changes.
- Tests cover rotation/aspect/odd/small dimensions, strict boolean options, scaled byte
framing and original PTS/index retention, nofpsfilter, flag/scope hashing and child wiring.
- Four-call batch: direct Nebius K3 implementation/tests, independent guestbenchmark,
small contract fix, focused fixture/QC repair. First checks caught portrait fixture swaps
and new recipe hash snapshots; fixed expectations retain exact hash/threshold assertions.
- After reported squat failure, one Nebius scope worker limited resizing to curls and
added scope/hash regressions. Integrator changed a test's unsupported overhead_press
name to actual incline_chest_press, applied allowlisted edits, checked and documented.
- All coding contexts source-only. No raw private media/pose arrays/credentials sent.
No extra Tavily, paid product runtime or hosting calls. Usage retained in separate ledger.
- One nested repair JSON string contained literal control newlines. Strict=False parsing
recovered its complete reviewed list; path allowlist and unique old substring checks
applied before any edits. No model-supplied shell commands executed.

## Reproduce

Existing local Compose stack, same flag in API/worker, queue empty when switching.
Run inside existing API image on motion-xray_default network with repo mounted/workdir
`/workspace` (httpx already pinned):

```sh
python scripts/benchmark_upload_analysis.py \
  --video '/workspace/data/demo/Bicep Curls.MOV' \
  --exercise dumbbell_curl --variant standing_both_arms \
  --label curl-decode720 --output artifacts/development/upload-check.json
```

This creates an actual new guest upload/job; it does not call coaching. Check report
provenance processing_version against local flag/scope recipe. Published aggregate
`HM-FAST01-upload-comparison.json` contains all successful timings and the squat partial.
No raw private media/pose committed. Full checks use the existing Docker entrypoint
`scripts/check-python.sh` with fakeLLM/cachedsearch.

Next: profile proxy/metadata/decode/inference stages separately. Current modest gain is
insufficient evidence for a large latency promise. Validate other exercises independently
before expanding scope, preserving missing-data/reference confidence labels.
