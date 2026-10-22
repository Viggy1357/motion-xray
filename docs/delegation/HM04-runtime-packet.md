# HM04 runtime report — agreed interfaces and boundaries

22 October2026. Reuse existing checked pose artifacts, not video re-extraction or
private data in coding prompts. Benchmark research is held. Three independent direct
Nebius drafts at most; one integrating writer;200k cumulative tokens per bounded task.
Prior aggregate commitment$9.30149165 includes unknown-history contingency, not a
verified balance; active ceiling$70/protected$30 remain. Initial batch guard<=USD1.80.

## Interface fixed before dispatch

`movement.runtime_lat.build_movement_report(frames: Sequence[PoseFrame], *,
analysis_id: str, exercise_id: str, variant: str, width: int, height: int,
pose_sha256: str, processing_version: str) -> PrototypeAnalysisResult`.

Pure deterministic arithmetic, no I/O except package-owned versioned config load.
Only lat has an implemented movement profile in this slice. Curl/squat/press return
typed unavailable measurement/count with explicit `exercise_profile_unavailable`,
not a fabricated0. Existing lateral-raise legacy pose requests stay compatible;
new derived route may reject unsupported exercise IDs clearly.

`GET /v1/analyses/{analysis_id}/movement-report` returns existing standalone0.3 model.
Use existing private manifest/secure-FD/hash/owner/retention helpers. Verify original
pose bytes, monotonic frames, original oriented dimensions and mapping before math.
Recheck owner/job/raw access after computation. No filesystem write/publication, no
pose reinference, no LLM/search call. Missing/expired required pose => explicit404/503.
This first read-only derived surface depends on raw pose retention. Do not promise
seven-day persistent derived metrics; durable report cache follows separately.

Keep old `/result` unchanged. OpenAPI and generated TS must include new report route.
No global0.2 version bump; old strict pose-only artifact models stay intact.

## Engine policy

Versioned package config `movement/configs/lat-runtime-v1.json`: existing trial
low100/high135/dwell0.1/max-gap0.1; estimated3D elbow signal. Whole-set side chosen by
valid signal samples, left wins ties. Never average occluded arms or switch mid-rep.
Reuse `find_cycles`, `measure_frame`, `measure_torso_frame`, `measure_rep`; automatic
RepWindow inputs are arithmetic containers, not human-labelled ground truth.

Retain non-overlapping positive partial spans as partial/excluded motion fragments;
count only completed cycles. No bridging invalid/gap spans. Timestamp-ordered fixed
IDs; missing values plus reasons; no current-time/random values in numerical report.
Per-metric coverage = valid supporting observed samples / expected sampled frames.
Global quality explicitly refers to segmentation-signal visibility. No probability of
correct technique. Both XY and estimatedXYZ stay separate; torso axis is uncalibrated
image-up, not measured gravity/lumbar angle.

Frozen `lat-component-policy-v1` stays unapproved: assessment unavailable, scores null,
required torso/arm/bar families explicit. No made-up reference intervals, tolerated
degrees, weights, bar/chest contact, activation, injury/safety or technique verdict.

## UI

New component fetches the derived report after pose success, handles abort/retry/error,
shows estimated completed cycles, signal/per-metric coverage, rep times and measured
values/reasons, explicit partial/profile/reference limits. Preserve private video and
manual log. Detected vs logged counts distinct; no automatic overwrite of ten reps.
Use generated TS. Hide stale pose-only 'no metrics calculated' copy when actual derived
report is present. Unsupported profiles degrade clearly. No extra dependencies.
