# Motion X Ray Product and Software Specification

Version 2.0 | 15 October 2026 | Product owner Vignesh | For Codex Hero Bob and other coding agents

## 1 Product objective and governing decisions

Build a web application that converts a short workout video into a rep-by-rep movement report. A person training between personal trainer sessions can replay their set, inspect reconstructed movement, compare it with a selected reference and understand the measured differences. The principal demonstration is synchronized video, a rotatable 3D skeleton and a reference trajectory with deviation highlights.

This specification replaces the condensed version 1.0. It defines the intended build, not an already implemented or validated product. MUST denotes a release requirement; SHOULD denotes a planned enhancement; MAY denotes a later option. Numerical defaults marked provisional are engineering starting points to test, not biomechanical standards or accuracy claims.

### Product boundaries

- Target users are adults recording their own training and trainers supplying a reference. Support one visible athlete, a fixed camera and one selected exercise per clip.
- Launch with simultaneous standing dumbbell curl, bilateral standing lateral raise and bodyweight squat. Treat alternating curls, cable variations, presses, loaded squat variants and rehabilitation as unsupported variants until separately specified and evaluated.
- Measure movement relative to an explicit reference. Do not diagnose injury, infer pain, prescribe rehabilitation, estimate muscle activation or claim that a similarity score establishes safety.
- Train no pose model for this release. Reuse pretrained perception and implement movement analysis, reference comparison and scoring in deterministic code.

### Priority and release policy

P0 MUST include capture/upload, exercise and view selection, pose extraction, rep segmentation, exercise metrics, a curated reference, deterministic scoring, grounded Nemotron coaching, source cards, video playback, 3D rep inspection and a working hosted build. A preloaded authorized example must demonstrate the complete flow.

P1 SHOULD add trainer-approved reference uploads, personal-best comparison, local session history, browser framing preview and Tavily evidence refresh. Preserve contracts for these features from the start. Trainer mode is a reference workflow, not a separate dashboard.

P2 MAY add equipment identification, automatic exercise recognition, voice feedback, live GPU streaming, social-video discovery/ingestion, multi-user accounts and a trainer dashboard. Begin P2 only after P0 passes its release checks.

If GEM-X is infeasible, a fallback may preserve a useful demo. Removing true 3D or an exercise is an explicit scope change recorded in DECISIONS.md and the submission; it does not silently satisfy the original P0 requirement.

### Reading order

Sections 2–3 define behavior; 4–10 define processing and scoring; 11–14 define contracts and operations; 15–18 define implementation, evaluation and release. Section 19 lists verified technical resources and the earlier research candidates. Appendix A specifies runtime settings and orchestration.

## 2 Functional requirements and acceptance map

Each implementation task must cite one or more requirement IDs. Acceptance evidence belongs in tests or a recorded manual check, linked from TASKS.md.

| ID | Required behavior | Acceptance evidence |
| --- | --- | --- |
| FR01 | Record a clip or upload a supported local file; preview before analysis | Camera permission denial, upload and playback tested |
| FR02 | Select exercise, variant, camera view and reference | Unsupported combinations blocked with a reason |
| FR03 | Create a durable analysis job and show actual processing stages | Refreshing the page retains status and job ID |
| FR04 | Extract timestamped 2D joints and estimated 3D joints with provenance | Adapter fixture checks mapping, timing and coordinates |
| FR05 | Count complete movement cycles and retain partial or unscorable segments | Labelled clips distinguish completed, partial and uncertain reps |
| FR06 | Compute the exercise metrics in section 8, gated by visibility and capability | Known-geometry tests and held-out clip results |
| FR07 | Compare compatible normalized reps with a selected reference | Repeated input yields identical comparison output |
| FR08 | Produce metric, rep and set scores only when coverage rules pass | Missing data cannot improve a comparable overall score |
| FR09 | Return 2–3 coaching observations supported by metric and rep IDs | Invalid or unsupported statements rejected |
| FR10 | Synchronize video, 2D overlay, 3D playback, charts and rep selection | Scrub, pause, speed and rep looping remain aligned |
| FR11 | Show reference identity, source links, limitations and deletion controls | Sources open; deleting a session revokes its artifacts |
| FR12 | Run NVIDIA model inference through the real application on Nebius | Redacted request metadata and deployed smoke test |

### Required analysis output

AnalysisResult must contain exercise and variant; detected complete count; partial/uncertain counts; per-rep start, turnaround and end times; available metrics and units; score or explicit null reason; best/worst scorable rep; reference and score versions; coaching status; source IDs; capability and visibility warnings. Pose arrays are separate artifacts, not duplicated in every status response.

A completed cycle means the movement returned to its starting phase. It does not mean the rep met a competition rule or a technique standard. Use “completed rep,” “partial movement” and “insufficient visibility” consistently in the UI.

### Planned enhancement acceptance

Trainer references require a selected rep, stated exercise/view, reviewer identity and explicit approval. Personal-best references require user selection; an algorithmic “best rep” must never automatically become an expert-approved reference. History compares only compatible provider, exercise, reference and scoring versions.

A missing optional service must not remove the measured report. A missing required perception output must yield a clear partial result or failure, never a convincing fabricated skeleton or numeric score.

## 3 User experience and visual specification

### Capture and upload

Present a short explanation, exercise selector and “Record” / “Upload” actions. Ask for the supported camera view using a simple diagram or example frame. Advise a fixed phone, good light and the joints needed for that exercise in frame. Request camera permission only when recording starts. Camera denial leaves upload available.

Show a preview, duration, file size and a re-record action. Obtain consent before transferring video; explain the upload destination and retention period. Do not upload in the background while the user is only previewing. Stop camera tracks when capture ends or the screen closes. Client preview mirroring must not change anatomical left/right in stored data.

### Processing

Show stages such as validating, extracting pose, finding reps, comparing and preparing coaching. Report elapsed time and job state; use indeterminate progress when actual progress is unknown. Offer cancellation and a return-to-result link. Poll every two seconds initially, backing off to five seconds for longer jobs; stop polling on terminal states.

### Results and rep inspector

- Desktop: video and overlay beside the 3D viewer; metrics and coaching alongside or below; a shared rep timeline across the bottom. Mobile: video first, then a switchable skeleton view, rep chips, metrics and coaching.
- Display measured values with units and reference ranges. Label the overall value “Reference similarity” and show coverage. Keep observation quality separate from score. Never present null as zero.
- Selecting a rep seeks video to its start and highlights its metrics. Support play/pause, frame step, 0.5×/1× speed and loop selected rep. Use one video clock; interpolate pose only between valid adjacent frames.
- The 3D viewer MUST rotate, zoom and reset; draw the athlete and reference in distinct styles, label estimated 3D, and show relevant joint paths. A static image is insufficient for FR10.
- User playback follows real time. Reference overlay follows normalized rep phase. Show this mapping so phase alignment is not mistaken for equal movement speed.
- Use joint highlights plus text/icons, never color alone. Low-quality intervals are muted or hidden; do not draw confident-looking trajectories through long gaps.

### Reference and source controls

Allow selecting a curated reference and inspecting its exercise, view, reviewer, date and source. P1 adds upload/select rep/approve/save for trainers and explicit “Use as my reference” for personal comparison. Surface provenance without exposing private reviewer contact details.

### Visual direction and accessibility

Use the X-Ray concept through a dark neutral viewer, clear skeletal lines and restrained cyan/amber highlights. Keep instructions, metrics and source cards readable with strong contrast. Provide keyboard controls, accessible labels, visible focus, responsive layout and text alternatives for charts. Preserve normal video playback if WebGL fails, with an explicit 3D-unavailable message and retry action.

## 4 System architecture and technology choices

```text
Browser camera or upload
  -> FastAPI upload validation -> private media storage
  -> durable analysis record -> worker claims job
  -> pose adapter -> canonical pose artifact
  -> movement metrics -> reference comparison -> deterministic scores
  -> coaching adapter with approved evidence -> validated report
  -> browser video overlay, 3D viewer and rep timeline

Evidence refresh -> Tavily -> candidate sources -> review -> reference library
```

### Component responsibilities

| Component | Chosen starting point | Responsibility |
| --- | --- | --- |
| Web | Next.js and TypeScript | Capture, upload, job polling and result screens |
| Presentation | Tailwind, shadcn/ui, Canvas, React Three Fiber | Accessible UI, 2D overlay and 3D skeleton |
| API | FastAPI and Pydantic | Validation, ownership, job lifecycle and schemas |
| Worker | Python, NumPy, SciPy and FFmpeg | Decode, normalize, segment, measure and score |
| Perception | GEM-X isolated runtime | Preferred post-set estimated 3D pose |
| Runtime language model | Nemotron via Nebius Token Factory | Coaching from structured measurements |
| Search | Tavily adapter | Source discovery/extraction, cached and reviewed |
| Persistence | SQLite and private artifact storage | Metadata and durable media/results |
| Delivery | Docker, uv, pnpm, GitHub Actions | Reproducible builds and checks |

Pin resolved dependency versions and model revisions after the feasibility spike. Use Python 3.12 initially if the selected pose stack supports it; isolate its environment from the API if requirements conflict. PostgreSQL becomes necessary only when deployment needs multiple API writers, replicas or database features SQLite cannot safely supply. No Redis, Kafka, Kubernetes or vector database is required for the first single-host build.

### Job execution

Run the worker as a separate process. Persist a queued record before dispatch. A worker atomically claims a job with a lease and heartbeat; do not hold a database transaction during inference. Expired leases may retry once if no cancellation or deletion exists. Publish results atomically only if the worker still owns the lease. Idempotent stages reuse artifacts with matching input and version hashes.

On a single host, SQLite on a persistent local disk can back this queue. Across cloud services, use the cloud job scheduler and durable metadata; do not share a SQLite file over object storage or assume ephemeral containers preserve it. Cancellation, timeout and restart behavior must be tested in the chosen topology.

## 5 Model providers and feasibility specification

### Provider roles

GEM-X is the preferred video-to-3D provider. Its repository describes a 77-joint SOMA representation and separate code/model governing terms [S1]. Inspect the pinned artifact format before implementing the adapter; “77 joints” does not establish accuracy on gym footage. Use its raw predictions to derive canonical coordinates rather than trying to recover coordinates from rendered video.

MediaPipe Pose Landmarker is the preview and fallback candidate. Its web guide exposes landmarks and world landmarks, and notes synchronous inference can block the UI; run preview inference in a worker when practical [S2]. Its estimated coordinates are not automatically interchangeable with GEM-X coordinates. MMPose RTMW3D is a reserve 3D candidate if integration is demonstrably easier [S3]. Do not implement three full stacks by default.

Nemotron MUST run through Token Factory in the intended submission path. Discover the exact model ID through the account catalog and test inference and structured output; listing models alone does not prove billing/inference access [S4]. Choose a small supported NVIDIA model first. Escalate model size only if measured coaching quality warrants it.

### Provider contracts

```python
class PoseProvider(Protocol):
    def capabilities(self) -> PoseCapabilities: ...
    def infer(self, video: VideoAsset) -> PoseSequence: ...

class LLMProvider(Protocol):
    async def coach(self, evidence: CoachingInput) -> CoachingResult: ...

class SearchProvider(Protocol):
    async def search(self, query: EvidenceQuery) -> list[SourceCandidate]: ...
    async def extract(self, urls: list[str]) -> list[SourceCandidate]: ...
```

These are interface sketches. Implement typed models from section 11 and export OpenAPI/JSON schemas. Capabilities declare 2D, estimated 3D, world translation, calibration, joint availability and confidence semantics. Absence of a native 3D confidence score must not be replaced with a fabricated probability.

### Day one feasibility gate

Use an authorized 10–20 second curl clip. Run the upstream example first; then extract timestamped coordinates, map canonical joints, render a simple skeleton and verify correct anatomical sides. Record hardware, model revision, cold/warm runtime, peak memory, artifact size and dependency licenses. Test one real Token Factory coaching request and one cloud job if AI Cloud deployment is planned.

Timebox the initial spike to one working day. Pass only if usable coordinates, synchronized playback and stable body identity are demonstrated. If not, isolate the failure and test a fallback. Record the selected provider, lost capabilities and scope effect before building downstream scores. Apple Silicon ONNX is a documented local option [S5], not proof that this application has passed the gate.

## 6 Video ingestion and canonical pose processing

### Provisional input limits

Accept MP4, MOV and WebM containers only when FFmpeg can decode their actual codecs. Start with 5–30 seconds, at most 100 MB, at most 1920×1080 input and one athlete. Prefer 720p/30 fps capture. These are product defaults; verify actual browser capture combinations on target devices. Return 413 for size, 415 for unsupported media and 422 for invalid duration/content.

Probe duration, dimensions, rotation and presentation timestamps server-side. Do not trust file extensions or browser metadata. Normalize orientation, create a 720p review proxy and remove audio. Preserve a timestamp map from each inference sample to the proxy/source timeline. For variable-frame-rate clips, never use frame index divided by nominal fps as the sole time source.

Use 30 Hz as the initial analysis sampling target; record the actual sampling rate. Retain original timestamps and do not invent extra measurement precision by interpolation. Run decoders in an isolated process with size, memory and duration limits. MVP accepts uploaded bytes, not arbitrary remote video URLs.

### Canonical skeleton

Required named joints are left/right shoulder, elbow, wrist, hip, knee and ankle. Derive pelvis and shoulder midpoint explicitly from paired joints and mark them as derived. Keep heel/toe joints optional. Retain native joints separately for diagnostics; document mapping by anatomical name, not a guessed shared numeric index.

Store image coordinates normalized to width/height with x right and y down. Store canonical camera 3D as x image-right, y up and z toward the viewer, with a documented adapter transformation. Record handedness, units, native coordinate frame and scale status. Validate transforms with a known fixture before using the 3D viewer.

For reference shape comparison, center on the pelvis, use a robust median torso length as scale and use one stable set-level body orientation. Preserve the unnormalized camera-space series for sway and translation. Re-aligning each frame can erase the very torso movement the app needs to measure. Unknown world scale stays unknown; report body-length ratios rather than centimeters.

### Observation quality

Keep native confidence/visibility values and the method that produced them. A provisional adapter-specific valid mask may start at visibility 0.6 and 80% required-joint coverage per rep; tune on labelled clips and freeze by adapter version. These values are not calibrated probabilities across models.

Interpolate only short internal gaps up to 0.1 seconds; label interpolated samples and do not use them to create rep turnaround events. Longer gaps break segments. If a person track changes, critical joints disappear or depth is unstable, suppress affected metrics and explain why. Do not stitch different people into one set. Low quality may still allow playback without allowing an overall score.

## 7 Movement analysis and repetition segmentation

### Geometry and smoothing

For joints A, B and C, let u=A−B and v=C−B. Compute angle ABC as degrees(acos(clamp(dot(u,v)/(norm(u)×norm(v)), −1, 1))). Reject near-zero segment lengths. Preserve whether the angle came from 2D or estimated 3D; a projected angle must not be described as a physical 3D joint measurement.

Filter only contiguous valid samples. Start with a short median filter and a Savitzky–Golay smoother, approximately 0.15–0.25 seconds total smoothing at the recorded sample rate; document the actual window and edge behavior. Preserve raw series. Derivatives use real seconds, not frame units. Smoothness/acceleration are exploratory outputs until their sensitivity to sampling and noise has been evaluated.

### Exercise phase signals

Curl uses elbow flexion, defined as 180° minus shoulder–elbow–wrist interior angle. Lateral raise uses the angle between upper-arm and downward torso vectors. Squat uses knee flexion, 180° minus hip–knee–ankle angle. Use the selected visible side for single-side analysis; use bilateral consensus only when both sides meet quality gates.

Map the phase signal to progress using the approved reference excursion. Provisional thresholds are low=0.2 and high=0.8 of that excursion, with at least 0.15 seconds dwell and a 0.8–12 second cycle duration. Values are segmentation defaults, not prescribed exercise range or tempo. Require a configured minimum excursion above observed noise. Do not normalize every candidate rep to its own range, which would promote tiny oscillations into full reps.

### Finite state machine

```text
READY -> OUTBOUND -> TURNAROUND -> RETURN -> COMPLETE
                    | low quality or timeout -> UNCERTAIN
Clip starts or ends inside a cycle -> PARTIAL
```

Define a complete cycle from a valid low-region start through a high-region turnaround back to the low region. Record start, peak/turnaround interval and end using original video seconds. For curls/raises, outbound is lifting; for squats it is descent. Preserve named concentric/eccentric durations separately. Pauses belong to explicit dwell intervals; do not double-count them in both phase durations.

Debounce each transition. A plateau yields one turnaround interval, not repeated peaks. Reversals caused by noise do not open new reps. Standing still counts zero. A clip beginning mid-rep preserves the first segment as partial and starts counting at the next full cycle.

Return both cycle candidates and scorable reps. Complete reps can remain unscorable because a metric or reference is unavailable. For mismatched bilateral timing, retain per-side boundaries and flag the mismatch; do not average two unrelated peaks. Release one synchronized exercise variant first; alternating sequences require their own specification.

## 8 Exercise metric specifications

Compute metrics per side and per rep where applicable. Angles use degrees, phase durations use seconds, and displacement uses torso-length ratios unless validated calibration exists. A metric MUST carry its dimensionality, available views, confidence/coverage and missing-data reason.

### Simultaneous standing dumbbell curl

Preferred capture is a near-side view for elbow flexion and torso lean, with a shallow diagonal view only if the chosen provider passes validation. Bilateral symmetry requires both arms to remain visible; a strict side view may therefore have no symmetry output.

| Metric ID | Computation | Interpretation and limits |
| --- | --- | --- |
| elbow_rom | Max minus min elbow flexion within rep | Compare with approved excursion; no universal ideal angle |
| upper_arm_drift | Range of upper-arm angle relative to torso | Measures change during the rep, relative to reference |
| torso_sway | Range of torso tilt from a fixed set-level upright baseline | Requires stable camera; suppress translation if uncalibrated |
| phase_tempo | Lift, top dwell, lowering and bottom dwell durations | Use real time; do not obtain tempo from warped sequences |
| trajectory_error | Phase-aligned elbow/wrist path error in body units | Compare only compatible provider and reference data |
| bilateral_difference | Absolute left/right ROM difference and peak-time offset | Report degrees and seconds; omit if one arm is hidden |

### Bilateral standing lateral raise

Preferred view is frontal with hips, shoulders, elbows and wrists visible. Lock the supported raise variant and elbow bend in the reference profile; do not compare a bent-arm raise with a straight-arm reference.

| Metric ID | Computation | Interpretation and limits |
| --- | --- | --- |
| arm_elevation | Peak and excursion of shoulder-to-elbow versus torso-down vector | Estimated 3D if reliable; frontal 2D otherwise labelled |
| side_difference | Left/right peak elevation difference and time offset | Requires visible paired joints throughout the event |
| torso_sway | Torso tilt excursion in the frontal or valid 3D frame | Do not confuse camera movement with body sway |
| elbow_bend_change | Range of shoulder–elbow–wrist angle | Variation relative to selected raise variant |
| phase_tempo | Raising, dwell and lowering duration | No automatic claim that a slower rep is better |
| trajectory_error | Elbow and wrist path deviation after phase alignment | Retain dimensionality and coordinate provenance |

### Bodyweight squat

Preferred capture is side-on with shoulder, hip, knee and ankle visible. A separate frontal capture profile may report projected bilateral movement but cannot inherit the side-view overall score without its own validation.

| Metric ID | Computation | Interpretation and limits |
| --- | --- | --- |
| knee_rom | Peak and excursion of hip–knee–ankle flexion | Compare with the person/reference; no automatic 90° rule |
| hip_descent | Pelvis vertical excursion divided by torso length | Requires fixed camera or stable estimated 3D |
| torso_lean | Shoulder-midpoint to pelvis angle relative to set upright | A pose proxy; does not measure spinal curvature |
| phase_tempo | Descent, bottom dwell and ascent duration | Preserve pauses and partial reps |
| trajectory_error | Hip/knee/ankle paths relative to reference | Do not infer load or bar path from body joints |
| side_difference | Left/right ROM and timing difference if observable | Frontal-only metrics need a separate scoring profile |

## 9 Reference library and evidence specification

### Three distinct reference types

Evidence benchmark stores reviewed technique characteristics, permitted variants and sources. It may specify broad ranges or cues; it is not automatically a single ideal trajectory. Curated demonstration trajectories are separate artifacts with their own permissions and reviewer provenance.

Trainer reference stores one or more recorded reps approved for an individual. Record the selected rep interval, exercise, variant, camera profile, intended tempo/ranges, review date and reviewer display name. Approval is a human action; the app must not imply certification that has not been checked.

Personal reference stores a user-selected prior rep or set. “Personal best” means selected for comparison; neither its score nor its selection proves technically correct form. Label it distinctly from reviewed guidance.

### Creating and approving references

1. Obtain authorized footage and permission for its intended use. Run the same pose provider, mapping, filtering and metric pipeline used for athlete analyses.
2. Select complete, adequately visible reps. Inspect overlay and raw video; reject tracking errors, severe occlusion and unsupported variants.
3. Store exercise, variant, side, view, provider/model revision, coordinate/scale convention, source, reviewer and processing versions.
4. Save approved metric ranges and a normalized trajectory. Keep reference version immutable; edits create a new version.
5. Confirm compatibility at analysis time. If the requested reference is incompatible, offer an eligible alternative; do not silently substitute one.

For one approved rep, use its trajectory directly. For several, choose a deterministic medoid reference or an explicitly reviewed representative, keeping the same choice for reruns. Do not average unaligned trajectories. Metric tolerances must be reviewed and versioned; ranges estimated from a tiny set must not be presented as population norms.

### Spatial and temporal comparison

Normalize translation and body scale with the stable transform in section 6. Compare a declared joint/angle subset rather than every native landmark. Use phase-aware dynamic time warping with monotonic ordering, phase anchors and a provisional ±10% alignment band. Normalize cumulative distance by path length and feature scales. Reject incompatible or unstable paths.

Compute tempo from original timestamps. A warping algorithm can align a fast and slow rep and therefore cannot establish that their tempo matched. Preserve alignment indices for the UI and per-phase deviation highlights. Cross-person raw position comparison and cross-provider history remain disabled unless mapping and normalization are validated.

### Source quality and ingestion

Prioritize professional/scientific guidance, then identifiable qualified coaching and manufacturer instructions. Creator posts are discovery candidates. Tavily discovers/extracts pages; it does not certify technique or grant access to every social platform [S6]. Automated extraction produces a draft source record, never a published benchmark. Cache approved evidence by exercise/variant/version; search does not run for every set.

## 10 Deterministic scoring and exercise configuration

### Score semantics and formula

The displayed score is experimental similarity to a selected reference. Higher similarity does not establish safety, effectiveness or suitability. Store measurements separately so a future scoring change does not overwrite the original values.

For metric i with value x, approved interval [L,U] and tolerance T>0, define d=max(L−x, 0, x−U). Define s=100×max(0, 1−d/T). Thus a value inside the interval scores 100 and a deviation of at least T scores 0. For a lower-is-better error, use an interval starting at zero. All intervals/tolerances are specific to exercise, view, provider and reference version.

Use a fixed scoring profile whose component weights sum to 1. Rep score is sum(w_i×s_i), rounded once for display. Keep unrounded values for comparisons. Set score is the arithmetic mean of scorable complete reps. Report scorable/complete counts, score spread and the number excluded. Best/worst are the maximum/minimum scorable scores; ties choose the earlier rep. Return null for both if none qualify.

If a required score component is missing, overall score is null; show available component metrics. Do not renormalize remaining weights and present the result as equivalent. A separate partial profile may exist only with its own ID, label and validation. Confidence is a visibility/measurement indicator, not a score multiplier or probability of correct technique.

### Provisional component weights

| Profile | Components and weights |
| --- | --- |
| Curl side 3D | elbow_rom 25%, upper_arm_drift 25%, torso_sway 20%, phase_tempo 15%, trajectory_error 15% |
| Raise front 3D | arm_elevation 25%, side_difference 20%, torso_sway 20%, phase_tempo 15%, trajectory_error 20% |
| Squat side 3D | knee_rom 25%, hip_descent 20%, torso_lean 20%, phase_tempo 15%, trajectory_error 20% |

These are product hypotheses; review sensitivity and freeze before held-out evaluation. Each metric family expands into scalar Metric records. Default subweights are 50/50 for phase_tempo lifting/lowering (squat ascent/descent), arm_elevation peak/excursion, side_difference amplitude/timing and knee_rom peak/excursion. Dwells remain informational. The reference must supply ranges and tolerances for every scored scalar. Missing any required scalar makes that family and the overall score null. Other unweighted outputs remain informational.

### Exercise configuration example

```yaml
exercise_id: dumbbell_curl
variant: standing_simultaneous
spec_version: 0.1.0
scoring_profile_id: curl_side_3d_v1
supported_view: side
required_capabilities: [estimated_3d, timestamps]
phase_signal: elbow_flexion_deg
segmentation: {low: 0.2, high: 0.8, dwell_s: 0.15}
metric_rules_from: reference_profile_version
weights: {elbow_rom: 0.25, upper_arm_drift: 0.25,
          torso_sway: 0.20, phase_tempo: 0.15,
          trajectory_error: 0.15}
missing_required_metric: null_overall_score
```

Worked engineering example: interval [0,5] degrees, T=10 and x=8 gives d=3 and s=70. These numbers illustrate the formula only; they are not a prescribed curl threshold. A reference without reviewed ranges/tolerances can show raw comparison but cannot produce an overall score.

## 11 Domain models and persistence contracts

Pydantic models in the API/domain package are the canonical schema source. Generate frontend types and JSON schemas from OpenAPI; reject additional fields on write requests where appropriate. Schema examples in this document define intent and must become checked, versioned contracts before integration.

| Model | Required fields and constraints |
| --- | --- |
| VideoAsset | id, owner_session_id, storage_key, sha256, mime, bytes, duration_s, width, height, rotation, timestamp_map_key, created_at, expires_at |
| PoseSequence | schema_version, video_id, provider/model revision, native skeleton, joint_mapping_version, sample rate, units, coordinate_system, capabilities, quality_method, frames_artifact_key |
| PoseFrame | frame_index, timestamp_s, subject_track_id, joints keyed by canonical name; coordinates may be null |
| JointObservation | xy, xyz, native_quality, valid, interpolated, quality_method; xyz null if unsupported |
| Rep | id, ordinal, side, start_s, turnaround_start_s, turnaround_end_s, end_s, completion_status, scorable, excluded_reasons |
| Metric | id, rep_id, side, value/null, unit, dimensionality, reference_interval, deviation/null, coverage, quality_method, status, reason |
| ReferenceProfile | id/version, type, owner/public scope, exercise/variant/view, provider compatibility, approved_by/date, source_ids, pose key, metric rules, approval_status |
| ScoreBreakdown | profile/version, reference version, component values/weights, raw_score/null, displayed_score/null, coverage and missing reasons |
| AnalysisResult | schema/version, analysis_id, exercise/variant, reps, metrics, score, best/worst IDs, source IDs, coaching, warnings, provenance |
| SourceRecord | id, canonical URL, title, publisher, retrieved_at, source tier, relevant claims, review status, reviewer/date, reuse terms |
| AnalysisJob | id, owner, state, stage, attempt, lease_owner, lease_until, cancel_requested, input/version hashes, timestamps, error, result_key |

Use UTC ISO 8601 timestamps for stored events; the UI formats local time. Video intervals use seconds from proxy-video zero, with end-exclusive intervals. Nullable measurements must have a machine-readable reason; zero means an actual measured zero. Reject NaN/infinity in JSON and persistence.

### Storage design

Keep relational metadata in SQLite initially: assets, analyses/jobs, references, source records, reference-source links and session ownership. Store larger immutable pose/result artifacts and video in private filesystem directories or object storage. Do not embed large frame arrays in database rows. Use migrations from the first schema; publish a restore procedure.

Use random object keys and an artifact manifest linking original, proxy, pose and report. Compute input hashes and record code commit, model revision, mapping version, exercise spec, reference version, scoring profile and coaching prompt version. A rerun creates a new analysis linked to the old one; it must not erase historical evidence.

Deletion must revoke access immediately, stop/cancel pending work and remove derived artifacts as well as raw media. References reused by other analyses require an explicit policy: remove private media, preserve only non-sensitive provenance needed to explain existing reports, and mark unavailable assets rather than leaving dangling public URLs.

## 12 API specification and error behavior

Prefix endpoints with /v1. Use secure session cookies for browser ownership, CSRF protection on mutations and an idempotency key on uploads/job creation. Public curated examples are read-only. Administrative reference approval and evidence refresh require an operator credential or a local script.

| Method and path | Request | Response |
| --- | --- | --- |
| GET /exercises | Optional view filter | 200 exercise specs and supported profiles |
| POST /videos | Multipart file, consent_version | 201 asset ID and validated metadata |
| GET /references | exercise_id, variant, view | 200 compatible visible references |
| POST /analyses | video_id, exercise_id, variant, view, side, reference_id/version | 202 analysis ID, state and status URL |
| GET /analyses/{id} | Owned analysis ID | 200 state, stage, warnings and result link |
| GET /analyses/{id}/result | Owned completed analysis | 200 report; 409 if not ready |
| GET /analyses/{id}/artifacts/{kind} | Authorized media/pose request | 200 stream or short-lived URL |
| POST /analyses/{id}/cancel | No body | 202 cancel request or 200 already terminal |
| DELETE /analyses/{id} | Optional cascade flag for owned upload | 202 deletion receipt; idempotent |
| POST /references | P1 asset ID, selected rep, metadata | 201 draft reference |
| POST /references/{id}/approve | Operator reviewer/rules | 200 immutable approved version |
| POST /evidence/refresh | Operator exercise/variant | 202 reviewable candidates |

```json
{
  "video_id": "vid_demo_01",
  "exercise_id": "dumbbell_curl",
  "variant": "standing_simultaneous",
  "view": "side", "side": "right",
  "reference_id": "ref_curl_demo", "reference_version": 1
}
```

Jobs transition queued → running → succeeded, failed or cancelled. Running stages are validate, pose, segment, metrics, compare and coach. A report with unavailable coaching may still succeed with warnings; pose failure yields failed or an explicitly labelled limited report. “No complete reps found” is a valid result with no score. Cancellation is terminal only after work has stopped or is prevented from publishing.

Use an error envelope with code, message, retryable, request_id and optional field_errors. Codes include INVALID_MEDIA, UNSUPPORTED_VARIANT, INCOMPATIBLE_REFERENCE, INSUFFICIENT_VISIBILITY, PROVIDER_TIMEOUT, RATE_LIMITED and JOB_EXPIRED. Return 404 for missing/unowned resources; 409 for state conflicts; 429 with Retry-After for limits; 502/503 for upstream failure. Never expose provider keys or raw stack traces.

A repeated idempotency key with the same owner and request hash returns the existing resource; a changed payload returns 409. Do not deduplicate across owners in a way that reveals another person’s media. API-to-worker traffic uses a service credential and private object access.

## 13 Coaching and exercise evidence implementation

### Coaching input and output

Send Nemotron only the selected exercise/reference, validated metrics, deviations, rep intervals, visibility limits, deterministic scores and reviewed technique claims. Raw video and face images are unnecessary for text coaching. Token Factory exposes an OpenAI-compatible API [S4]; configure the endpoint and exact model ID after a real smoke test.

```json
{
  "summary": "Your last two measured reps differed most from the reference.",
  "observations": [{
    "rep_ids": ["rep_5", "rep_6"],
    "metric_ids": ["rep_5.upper_arm_drift", "rep_6.upper_arm_drift"],
    "text": "Upper-arm movement increased compared with the selected rep.",
    "source_ids": ["source_reviewed_01"]
  }],
  "next_set_cue": "Use the reference playback to check upper-arm position.",
  "limitations": ["The left arm was not visible enough for comparison."]
}
```

This illustrates response shape, not a recorded result. Require 2–3 observations only when that many distinct supported findings exist; allow fewer rather than fabricate issues. Each observation must cite valid metric/rep IDs. Technique advice needs an approved claim/source; purely descriptive measurement comparisons can omit external sources if clearly labelled as observations.

### Prompt and validation rules

Use a versioned system prompt instructing concise, neutral coaching. Prohibit medical diagnosis, invented numbers, unsupported causal explanations and unobserved load/fatigue claims. Do not turn a late-set deviation into a claim that fatigue caused it. Return JSON only, limited to allowed fields and bounded text lengths.

Use native structured output if supported by the tested model, otherwise parse and validate JSON. Check types, allowed IDs, numeric values against inputs and prohibited unsupported assertions. Allow one bounded repair request. On failure return coaching.status=unavailable with an optional deterministic factual summary. Do not regenerate scores. Record model ID, prompt version, latency, usage and validation status without retaining sensitive prompts by default.

### Evidence refresh

Search with exercise, variant and the specific technique question. Tavily Search/Extract provide discovery and page extraction [S6]. Limit returned sources, use a domain allowlist when suitable and treat all page content as untrusted data. Strip instructions, scripts and irrelevant text; never allow retrieved pages to modify tool permissions or executable code.

Store claim text, supporting source, applicable variant, retrieval date and review status. Operator review promotes a candidate to approved. Cache by exercise/variant/source version; provisional refresh interval is seven days with manual refresh. If search fails, retain reviewed cached evidence and show its date. If no evidence exists, allow measurements but omit general technique advice.

Discovery of social content is P2: identify the original creator, assess expertise and permissions, review the clip, run the pose pipeline, approve trajectories and record provenance. Saving only derived skeletons does not remove the need to check reuse rights.

## 14 Deployment security privacy and operating limits

### Deployment topology

Local development runs web, API and a separate worker through Compose, with persistent metadata/artifact volumes. Put the pose stack in its own image/environment; download approved weights with revision/checksum verification. The first hosted topology may be one persistent host plus a GPU worker; externalize media when the GPU runtime is ephemeral.

Prefer an asynchronous Nebius Serverless Job for the short post-set workload, with status/result handoff. An HTTP Endpoint is an alternative if measured cold starts and request duration fit the service. Nebius documents these container-based services [S7]. Confirm account entitlement, region, storage access, GPU availability and current limits during the spike; this document does not guarantee a deployment shape or price.

The public app’s text coaching must call Token Factory in the submission configuration. Do not confuse a coding agent using Nebius with the product making a runtime call. Local developer tools can change independently from deployed inference.

### Provisional operational defaults

One concurrent GPU analysis per worker; one active job per anonymous session; a small global queue of ten; upload limit 100 MB; job deadline five minutes plus bounded queue wait. Token Factory request timeout 30 seconds, at most one transient retry with backoff; total coaching budget 60 seconds. Search timeout 15 seconds with cached fallback. Measure and revise these defaults before the hosted release.

Record stage timings, queue wait, peak memory, provider errors, token counts, search credits and estimated spend using current configured rates. Warn when budget approaches the approved cap. On budget exhaustion, reject new costly uploads clearly and retain authorized read-only demo examples. Do not leave GPUs idle or assume serverless always means zero idle charge.

### Ownership and privacy

Use HTTPS, private storage, short-lived artifact URLs, restricted CORS and rate limits. Every job/result/reference lookup checks ownership. Anonymous sessions need secure HttpOnly SameSite cookies and an explicit expiry; no login does not mean no access control. Operators alone can approve globally visible references.

Default user media/pose retention is 24 hours; metadata/report retention is seven days unless the user deletes sooner. State this before upload and test an hourly cleanup task. Approved public demo assets have separate written permission and retention. Browser history stores only owned report IDs; do not persist footage in local storage. Session loss and cleanup behavior must be explained.

Delete access immediately and finish physical removal within an hour, including derived artifacts and pending worker output. Document any backup delay; exclude transient user footage from backups for MVP. Logs contain IDs and timings, not raw video, API keys, signed URLs or full coaching inputs.

Keys remain server-side in environment/secret storage. Do not use public frontend environment prefixes for keys. Scan commits for secrets. Reject arbitrary fetch URLs, path traversal and unsafe serialized uploads; internal model artifacts are trusted outputs only. Run media decoding with constrained permissions and keep dependencies patched.

## 15 Repository structure and coding agent instructions

```text
motion-xray/
  apps/web/                    capture, processing, results, rep inspector
  services/api/                routes, ownership, jobs and migrations
  services/pose/               isolated model runtime and export adapter
  packages/contracts/          Pydantic models and generated TS schemas
  packages/movement/           geometry, filtering, phases and metrics
  packages/scoring/            normalization, DTW and scoring profiles
  packages/benchmarks/         reference compatibility and provenance
  packages/providers/          llm/, pose/, search/ and test doubles
  data/exercise_specs/          versioned YAML configuration
  data/references/              manifests; authorized small assets only
  data/demo/                    consented examples or download manifests
  tests/                       unit/, contracts/, integration/, evaluation/
  scripts/                     analyze, evaluate, curate and cleanup tools
  infra/                       images, Compose and cloud deployment
  docs/                        product, architecture, API and runbooks
  AGENTS.md  TASKS.md  README.md  LICENSE  .env.example
```

Exclude raw private footage, model weights, caches, .env and generated large artifacts from Git. Keep model/data download instructions and hashes in manifests. Choose an open-source project license compatible with dependencies; preserve upstream attributions and separate model/data terms.

### Required repository documents

PRODUCT.md defines scope and FR IDs; ARCHITECTURE.md records topology and provider boundaries; DATA_MODEL.md and API.md document contracts; EXERCISES.md records metric formulas; SCORING.md records versions and tolerances; EVALUATION.md records splits/results; OPERATIONS.md covers deployment, keys, spend and deletion; DECISIONS.md records design changes. TASKS.md contains current status, acceptance criteria, dependencies, evidence and next action.

### AGENTS contract

Every agent reads AGENTS.md, PRODUCT.md, ARCHITECTURE.md, TASKS.md and relevant decisions before changes. Claim one bounded task. Keep deterministic processing separate from LLM output. Preserve public contracts or update schema version and consumers together. Never alter thresholds without exercise/scoring config and regression updates. Justify dependencies; avoid unrelated refactors.

Run lint/type checks and tests relevant to the changed behavior. Commit small coherent increments when repository workflow allows. End each handoff with changed files, checks and outcomes, unresolved blockers, configuration assumptions and the next task ID. The Git repository must be sufficient to resume in Codex, Hero or Bob without reconstructing conversation history.

Provide script entrypoints for setup, local startup, an offline analysis, unit tests, evaluation, demo seeding, provider smoke checks and cleanup. Separate paid integration checks from offline CI; paid calls run only in authorized environments. Record exact commands in README after implementation rather than documenting imaginary working commands.

Coding-agent access and runtime credentials are separate concerns. A generic OpenAI-compatible runtime adapter does not prove that a particular IDE accepts Nebius keys or that its subscription credits transfer. Configure each coding tool according to its own supported settings; keep the repository/tool-neutral workflow intact.

## 16 Delivery plan and implementation work packages

All dates are Malaysia time, 2026. Dependencies determine order; a date does not make an unfinished task complete. Build the first usable curl flow before visual polish or additional exercises.

| Task | Date | Implementation and completion evidence |
| --- | --- | --- |
| T01 Feasibility | 16 Oct | GEM coordinates/overlay, model terms, one Nemotron inference, measured runtime; provider decision |
| T02 Scaffold | 16–17 Oct | Repository, locked environments, Compose skeleton, contracts, CI and sample environment |
| T03 Ingestion | 17 Oct | Upload validation, preview/proxy, consent, ownership and timestamp mapping tests |
| T04 Pose adapter | 17–18 Oct | Canonical joints/capabilities, tracking and coordinate fixtures; JSON export |
| T05 Curl engine | 18–19 Oct | Geometry, filtering, state machine and curl metric output on labelled clips |
| T06 References | 20 Oct | Reviewed curated curl profile, immutable versions and compatibility rejection |
| T07 Scoring | 20–21 Oct | DTW, component formulas, missing-data policy and deterministic score tests |
| T08 Jobs and cloud | 21–22 Oct | Durable queue/leases, cancellation, hosted worker and restart smoke checks |
| T09 Coaching | 22 Oct | Real Nemotron output, schema/grounding validation and failure fallback |
| T10 Evidence | 23 Oct | Reviewed source records, cached evidence and optional Tavily refresh action |
| T11 X Ray UI | 23–25 Oct | Real video/skeleton sync, rep timeline, 3D comparison and error states |
| T12 Other exercises | 25–26 Oct | Raise/squat configs, approved references and independently checked metrics |
| T13 Evaluation | 27–28 Oct | Frozen configs, held-out results, browser/device checks and defects triaged |
| T14 Release | 29 Oct | Fresh-clone startup, public demo build, documentation and license inventory |
| T15 Submission | 30 Oct | Working links, public video, final release tag and submission verification |

### Milestone gates

Gate A proves usable pose and NVIDIA/Nebius inference. B produces a traceable curl report. C displays that real report in the hosted 3D UI. D adds evaluated raise and squat. E passes release acceptance and reproducible judge access. A mocked UI does not pass C.

Build wireframes against frozen schemas; replace fixtures with real outputs before acceptance. Multiple agents are not required.

### Scope contingency

Remove P1 first if needed; retain curated references. Any P0 reduction requires an explicit decision and updated copy, tests and submission claims. Publish only demonstrated capabilities.

## 17 Testing evaluation and release acceptance

### Test corpus and evaluation protocol

Collect 10–20 curl development sets first. Aim for at least 30 authorized clips across the three release exercises, multiple people and supported views before submission, including partial reps, holds, occlusion and poor framing. Separate people between tuning and held-out evaluation where possible; never put transformed versions of the same clip in both sets. If the available sample is smaller, publish its size and limitations.

Annotate exercise/variant/view, complete/partial count, rep boundaries/turnaround, occluded intervals and observable deviations. Have a second person check ambiguous annotations; record disagreements. A video annotation is not motion-capture ground truth for 3D coordinates. Use known synthetic geometry to verify formulas; validate reconstructed movement empirically without claiming laboratory biomechanics accuracy.

### Proposed acceptance targets

- Rep count within ±1 on at least 90% of eligible held-out clips; report exact count accuracy and mean absolute count error as well, including per-exercise results and numerator/denominator.
- Median matched boundary error no greater than 0.5 seconds. Match predicted/labelled reps one-to-one and report missed/spurious reps separately; unmatched reps must not vanish from the evaluation.
- No complete rep counted on the stationary control; incomplete edge reps labelled partial; unsupported views and insufficient visibility produce honest limitations.
- Identical pose artifacts/configuration produce identical deterministic metrics and scores. Floating-point geometry fixtures meet documented numeric tolerances.
- Video/pose alignment within one analysis sample interval on the tested proxy timeline. Seeking, speed changes and rotation must not desynchronize the 2D overlay.
- Target a warm 20-second clip report within 60 seconds on selected hardware, excluding upload, and within the five-minute configured deadline including cold processing. Measure and publish actual latency; revise this target after Gate A if needed.

These targets are proposed product gates, not results. A failure needs a fix, a documented limitation or an explicit scope change before release.

### Test layers

Unit tests cover angles, degenerate limbs, units, transforms, gaps, phase events, plateaus, partial cycles, DTW constraints, score weights and null behavior. Contract tests cover adapter capabilities, schema generation, IDs, units and provider fallback. Integration tests cover upload → report → deletion, idempotency, leases, cancellation/restart, 429/timeouts, invalid coaching and cache fallback.

UI checks cover camera denial, file upload, upload failure, mobile/desktop layouts, keyboard navigation, WebGL loss and empty/no-score results. Test current Chrome desktop, Android Chrome and iOS Safari before declaring support; upload fallback remains available when recording is unsupported. Security checks cover cross-session access, CSRF, private assets, malicious files and key exposure.

Release requires all P0 requirements traced to evidence, zero unresolved data-exposure or materially misleading-result defects, a real deployed NVIDIA/Nebius smoke test, clean startup from a fresh clone, verified deletion, documented limitations and EVALUATION.md containing observed results. CI uses fixtures; paid model calls are a separate controlled check.

## 18 Release submission and decision register

### Hackathon submission requirements

Recommended track is Best Apps and Agents. The official rules require an NVIDIA open-source model plus a runtime Token Factory call or execution on Nebius AI Cloud. Deadline is 30 October 2026 at 10:00 AM PDT, or 31 October at 1:00 AM Malaysia time. Submit on 30 October MYT [S8].

Provide a working demo/test build with access instructions; public source repository with an open-source license, assets and setup instructions; English project description; public YouTube demonstration under three minutes; selected track; tooling feedback; and an explanation of prior-project changes if relevant. Document NVIDIA/Nebius use. Maintain free judging access through 15 December 2026 at noon Pacific [S8].

If choosing Physical AI, the rules permit a project without hardware but require at least one minute showing key modules in action; hardware is not an absolute eligibility requirement. Keep the default track unless the product and evidence justify changing it [S8].

Tavily has a bonus award [S9]. Demonstrate an actual useful runtime search/extraction and verify current award conditions before claiming eligibility; do not rely on pre-generated source files as proof of runtime integration.

### Demonstration and release package

Aim for 2 minutes 45 seconds: 15 seconds on the training problem; 25 on capture/upload and actual processing; 50 on rep selection, metrics and 3D reference overlay; 30 on grounded coaching and visibility limits; 25 on architecture and real provider usage; 20 on evaluation and next steps. Label any processing time cut or cached example. Avoid implying prerecorded output is live.

Tag the release commit and record model/config/reference versions. Include an architecture diagram, screenshots, sample input instructions, evaluation report, dependency/model/data terms, deployment runbook and known limitations. Verify demo, code and video links in a fresh browser; keep keys out of screen recordings. Test build restoration before submission and keep permitted demo assets available through judging.

### Decisions that must be closed during implementation

| Decision | Owner and closure point |
| --- | --- |
| Pose provider, hardware, model revision and 3D capability | Implementer at Gate A; product owner accepts any scope reduction |
| Valid camera profiles, confidence masks and supported variants | Implementer and reference reviewer before held-out testing |
| Reference rights, reviewer and metric tolerances | Product owner/reference reviewer before publishing scored profiles |
| Exact Nemotron ID, JSON behavior, endpoint and credits | Implementer with actual account access at Gate A |
| GPU/storage entitlement, budget cap and retention implementation | Product owner and implementer before paid deployment |
| Score weights and experimental claims | Product owner/reference reviewer before configuration freeze |

Version 2.0 restores explicit 3D requirements, exercise formulas, three reference modes and implementation contracts. It adds provisional engineering defaults and evaluation targets. The earlier claim that code and model weights necessarily share one Apache license is superseded by the governing terms recorded in S1. Keep any later change in DECISIONS.md.

## 19 Technical resources and reuse decisions

Sources below were checked on 15 October 2026. Pin exact revisions and recheck terms when integrating. A public repository or accessible dataset is a research lead, not automatic permission to bundle its contents. Formulas, priorities and provisional defaults in this specification are project design choices unless attributed otherwise.

### Primary implementation references

[S1] NVIDIA GEM-X repository and governing terms. Preferred pretrained 3D perception candidate; code is Apache 2.0 while associated model use is governed by the NVIDIA Open Model License Agreement. Inspect downloaded components and attributions separately.
https://github.com/NVlabs/GEM-X

[S2] Google MediaPipe Pose Landmarker web guide. Preview/fallback candidate; validate world-coordinate meaning, visibility and browser performance before scoring.
https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker/web_js

[S3] OpenMMLab MMPose. Reserve implementation, including RTMW3D; framework, checkpoint and dataset terms must be checked for the selected model.
https://github.com/open-mmlab/mmpose

[S4] Nebius inference API reference and official Token Factory guide. Use account-visible model IDs and a live inference test; do not hardcode a catalog assumption.
https://api.tokenfactory.nebius.com/docs
https://github.com/nebius/token-factory-cookbook/blob/main/start-here/README.md

[S5] GEM-X demo/output and Apple Silicon setup guides. Inspect raw prediction structure and exact runtime requirements at the pinned commit.
https://github.com/NVlabs/GEM-X/blob/main/docs/DEMO.md
https://github.com/NVlabs/GEM-X/blob/main/docs/INSTALL_MACOS.md

[S6] Tavily Search and Extract API references. Use for bounded source discovery/extraction, with review and cache policy.
https://docs.tavily.com/documentation/api-reference/endpoint/search
https://docs.tavily.com/documentation/api-reference/endpoint/extract

[S7] Nebius serverless developer entry point and service introduction. Validate the chosen Jobs/Endpoints deployment in the actual account.
https://dev.nebius.com/serverless
https://nebius.com/blog/posts/introducing-serverless

[S8] Official hackathon rules. Governs deadlines, runtime, repository, video and judging access.
https://nebiusglobalaihackathon.devpost.com/rules

[S9] Official hackathon overview. Tracks, evaluation categories and Tavily award listing.
https://nebiusglobalaihackathon.devpost.com/

### Research datasets and example applications

[S10] Fitness-AQA covers back squat, barbell row and overhead press; dataset use is explicitly non-commercial. Study the assessment approach; do not make it a required bundled product dependency.
https://github.com/ParitoshParmar/Fitness-AQA

[S11] RepCount and TransRAC. Research lead for counting and temporal annotation; exercise mix and data terms need checking before use.
https://github.com/SvipRepetitionCounting/TransRAC

[S12] CFRep. Research lead for view-dependent repetition validation; competition rep/no-rep labels are not a universal definition of training technique.
https://github.com/lc-leonardo/CFRep

[S13] WorkoutVision. Reference for browser capture, counting and testing patterns; inspect its current code/license before reuse and evaluate independent performance.
https://github.com/david-dabert/workout-vision

The earlier “form-check” project name was not uniquely identified. Do not depend on or copy it until the exact repository, maintainer and applicable license are verified. No external dataset is required to ship the planned MVP; authorized self-recorded fixtures and reviewed reference footage are the primary data path.

## Appendix A Runtime configuration and orchestration

These are proposed application-owned environment names for .env.example. Empty secrets are intentional. The build must fail clearly when the selected provider needs an unset credential. Never ship a working secret or silently switch to a different model.

```dotenv
APP_ENV=development
APP_ORIGIN=http://localhost:3000
API_INTERNAL_URL=http://api:8000
SESSION_SECRET=
DATABASE_URL=sqlite:////state/motion_xray.db
ARTIFACT_BACKEND=filesystem
ARTIFACT_ROOT=/state/artifacts
POSE_PROVIDER=gem
POSE_MODEL_REVISION=
POSE_CHECKPOINT_PATH=/models/gem_soma.ckpt
LLM_PROVIDER=nebius
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1
NEBIUS_MODEL_ID=
NEBIUS_API_KEY=
SEARCH_PROVIDER=cached
TAVILY_API_KEY=
MAX_UPLOAD_MB=100
MAX_VIDEO_SECONDS=30
WORKER_CONCURRENCY=1
JOB_TIMEOUT_SECONDS=300
RAW_MEDIA_TTL_HOURS=24
REPORT_TTL_DAYS=7
```

Confirm the precise SDK endpoint against the real account/API before freezing configuration [S4]. Cloud compute credentials are separate from the Token Factory key. Add storage bucket, cloud region and service-account settings only for the selected deployment. SEARCH_PROVIDER=cached uses reviewed local records; selecting tavily enables runtime discovery and requires its key. A generic alternate LLM adapter may exist for development, but the submission profile must select a tested NVIDIA model on Nebius.

### Processing orchestration sketch

```python
def run_analysis(job):
    claim_with_lease(job)
    validate_owner_input_and_reference(job)
    video = decode_with_timestamp_map(job.video)
    pose = pose_provider.infer(video)
    save_immutable_pose(pose)
    reps = segment_reps(pose, job.exercise_spec)
    metrics = compute_observable_metrics(pose, reps)
    comparison = compare_compatible_reference(metrics, pose, job.reference)
    scores = score_or_return_null(comparison, job.scoring_profile)
    coaching = coach_with_bounded_fallback(metrics, scores)
    publish_if_lease_owned_and_not_cancelled(job, metrics, scores, coaching)
```

The sketch omits infrastructure details intentionally: implementation must add stage checkpoints, heartbeat renewal, deadlines, error envelopes and cleanup. After each expensive stage, recheck cancellation/deletion before persisting or publishing. Include reference compatibility and rights checks before paid inference where possible.

### Principal implementation risks

Unstable pose or occlusion requires restricted camera profiles and quality gating. GPU access/cost failure requires an early account smoke test and an honest reduced-capability fallback. Provider drift requires pinned model/config versions and regression fixtures. Weak reference evidence requires withholding scores or general technique advice, rather than filling missing thresholds with plausible numbers.
