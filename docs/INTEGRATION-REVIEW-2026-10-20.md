# Shortlisted methods: compatibility and integration review

20 October 2026 · T19 · FR04/05/07/08/10/11/12.

## Outcome and evidence

Keep the current pipeline and MediaPipe baseline. Reuse narrowly: a numerical DTW
kernel, geometric/filtering methods, counter design ideas and evaluation methodology.
Consider another pose provider or tracking library only for a demonstrated failure.
No shortlisted application replaces the product's full workflow.

This is a source-level design assessment, consolidated from three user-authorized
read-only reviews and direct inspection of our current implementation. It is not a
runtime benchmark, dependency approval or claim that integration is complete. Upstream
links below point at branch snapshots checked during this review, not pinned adoption
revisions. Pin revisions, checkpoint hashes and governing terms before copying code or
introducing a dependency. No runtimes, checkpoints or datasets were installed/downloaded.

Current implementation inspected: pose adapter, movement, comparison and scoring are
explicit stubs; the worker loop and analyze/evaluate commands are scaffold-only.
The executable baseline validates contracts and infrastructure, not movement accuracy.
Use current D002/D005/D006/D007 and DELIVERY over the older archived exercise order.

## Integration map

All paths are repository-relative. **Existing** means present but not necessarily
implemented; **proposed** means a future file/interface, not a delivered feature.

| Method | Decision | Exact integration boundary | Gap closed; remaining limit |
| --- | --- | --- | --- |
| Sports2D geometry/quality/filtering workflow | Adapt methods; isolated diagnostic comparison | Existing `packages/movement/movement/core.py::compute_angle`, `smooth_series`; T04/T05 | A useful external check of 2D signal quality; does not supply our 3D reference or complete reps |
| Good-GYM threshold-state counter | Adapt the design, not its implementation wholesale | Existing `packages/movement/movement/core.py::segment_reps`; versioned `data/exercise_specs/lat_pulldown.yaml`; T05 | Starting pattern for hysteresis/debouncing; still requires full-cycle phases and valid timestamps |
| DTAIDistance multivariate path kernel | First dependency candidate, pending narrow verification | Existing `packages/scoring/scoring/core.py::dtw_align` called by `normalize_and_align`; T07 | Avoids writing the numerical DTW kernel; does not supply normalization or score policy |
| Norfair observation association | Conditional identity helper | Proposed `packages/providers/providers/pose/subject_tracking.py`; existing `PoseFrame.subject_track_id`; T04 | Keeps the selected person consistent; does not measure missing joints |
| rtmlib model inference | Conditional alternate adapter | Proposed `packages/providers/providers/pose/rtmlib_provider.py` implementing existing `PoseProvider`; T04 | Alternative detection/pose coverage; 2D mode cannot satisfy current 3D-required profiles |
| AIFit/Fit3D comparison methodology | Study and adapt design; no bundled data | Existing `packages/benchmarks/benchmarks/core.py`, scoring normalization, future reference builder; T06/T07/T13 | Informs representative reference selection and deviation evaluation; permissions and reviewed reference remain open |
| ALEX-GYM-1 learned assessment | Defer runtime reuse | Possible later offline evaluator behind `scripts/evaluate.py`; T13/P1 | Example learned assessor; not a compatible pretrained single-camera lat-pulldown engine |
| PoseRAC / rehabilitation segmentation | Secondary research baselines | Future evaluation adapters behind `scripts/evaluate.py`; T13 | Counting/irregular-motion comparison; no evidence yet of better P0 accuracy |

## 1. Pose processing: useful methods, incompatible defaults

**Sports2D.** Reviewed `setup_video`, `compute_angle`, `compute_angles_for_person` and
postprocessing. It assumes planar motion, rounds nominal FPS, supports long-gap fills,
uses facing-based coordinate flips and changes TLS verification globally. Borrow the
confidence-gated angle/filter/diagnostic approach, not these defaults. A diagonal gym
view is a weaker fit than its ideal perpendicular capture. Its export helper also uses
static depth offsets: these must never become our measured or estimated subject XYZ.
Sources: [processing](https://github.com/davidpagnon/Sports2D/blob/main/Sports2D/process.py),
[export helpers](https://github.com/davidpagnon/Sports2D/blob/main/Sports2D/Utilities/common.py).

Importing the full package would also introduce Pose2Sim and a larger processing stack.
Keep a comparison tool isolated from the application worker; if methods are transplanted,
review their actual dependency/source provenance. Its code is BSD-3-Clause, with separate
model/dependency review still needed. [Package definition](https://github.com/davidpagnon/Sports2D/blob/main/pyproject.toml),
[licence](https://github.com/davidpagnon/Sports2D/blob/main/LICENSE).

**rtmlib.** A conditional adapter can map named image joints into our `xy`, with native
quality semantics. Its greedy IoU tracker and exception-to-empty paths need testing;
they do not prove stable identity. The reviewed 3D postprocessor treats crop-space XY
and depth differently and also returns separate image-space points. Do not enable 3D
capabilities until the exact model's coordinate transform is established. Configure
verified local checkpoints instead of runtime auto-downloads. Sources:
[Body](https://github.com/Tau-J/rtmlib/blob/main/rtmlib/tools/solution/body.py),
[PoseTracker](https://github.com/Tau-J/rtmlib/blob/main/rtmlib/tools/solution/pose_tracker.py),
[3D postprocessor](https://github.com/Tau-J/rtmlib/blob/main/rtmlib/tools/pose_estimation/rtmpose3d.py),
[BaseTool](https://github.com/Tau-J/rtmlib/blob/main/rtmlib/tools/base.py).

Python version compatibility alone is insufficient: resolve exact NumPy, ONNX Runtime
and OpenCV dependencies inside the Linux/aarch64 worker experiment. Do not combine
headless/non-headless OpenCV distributions casually. Keep these dependencies out of the
API image. Apache-2.0 code terms do not establish model-weight rights.
[Packaging](https://github.com/Tau-J/rtmlib/blob/main/pyproject.toml),
[licence](https://github.com/Tau-J/rtmlib/blob/main/LICENSE).

**Acceptance:** same owned input and source offset; selected-person continuity; correct
anatomical sides; original presentation timestamps; joint coverage and invalid samples;
coordinate/units fixtures; cold/warm runtime, memory and artifact size. Compare projected
2D angles with projected 2D angles, not with estimated 3D as interchangeable truth.
No provider switch until it materially fixes a measured baseline failure without hiding
lost capabilities. Under existing profiles, a 2D-only provider means measurements-only
where supportable and null 3D-dependent metrics/scores, unless scope is explicitly revised.

## 2. Counting: preserve the idea, implement our contract

Good-GYM's extreme-state transitions are a useful hysteresis example. Its reviewed
counter uses elapsed wall time, combines arm angles and does not emit our complete
start/turnaround/end record. That is insufficient for uploaded-video tempo, far-arm
occlusion or full-cycle completion. Source detail is listed in the review ledger below.
Reviewed functions: `calculate_angle`, `smooth_angle`, `check_rep_timing`,
`count_exercise`, `count_leg_exercise` in
[exercise_counters.py](https://github.com/yo-WASSUP/Good-GYM/blob/master/exercise_counters.py).
Its [catalogue](https://github.com/yo-WASSUP/Good-GYM/blob/master/data/exercises.json)
has native joint indices and raw-degree thresholds: pullup is not a validated lat-pulldown
profile. The [MIT code terms](https://github.com/yo-WASSUP/Good-GYM/blob/master/LICENSE)
remain separate from model-weight terms.

Implement the existing specification's `READY → OUTBOUND → TURNAROUND → RETURN → COMPLETE`
state machine in `movement/core.py::segment_reps`. Use the selected visible side; only
use bilateral consensus when both sides pass quality gates. Emit `Rep` with original
seconds, turnaround interval, completion status, scorable state and exclusion reasons.
Retain partial and uncertain cycles. Count completion on valid return, not merely reaching
one extreme. Freeze dwell, excursion/noise gates and duration limits in versioned config.

The improvement is observable and testable: a single full rep produces one completed
interval; a clipped rep stays partial; a static athlete produces zero; plateaus do not
multiply reps; processing speed does not alter tempo. No claim of measured accuracy yet.

## 3. Alignment: integrate a kernel, retain product policy

Use DTAIDistance behind a small internal adapter, not throughout application code.
The reviewed API supports a shared multivariate path; its window semantics need explicit
translation, and its default distance is not our final path-normalized trajectory error.
Sources: [multivariate implementation](https://github.com/wannesm/dtaidistance/blob/master/src/dtaidistance/dtw_ndim.py),
[DTW implementation](https://github.com/wannesm/dtaidistance/blob/master/src/dtaidistance/dtw.py).

Proposed adapter: `packages/scoring/scoring/alignment.py` with a typed internal
`AlignmentResult` containing status/reasons, original sample index pairs, feature order,
cost definition, path length and config/backend/version identifiers. Existing
`dtw_align(user, reference)` currently accepts scalar sequences and returns `Any`; evolve
this deliberately to carry the multivariate and phase context. Preserve exports/callers.

Required wrapper behaviour:

1. Verify variant, view, provider/mapping and feature compatibility before alignment.
2. Use stable set-level translation/orientation and body-scale normalization; preserve
   original camera-space motion for torso sway. Never realign away the movement being scored.
3. Scale features by reviewed dimensional scales. Fit one joint/feature path together;
   independent joint paths could conceal poor coordination.
   With squared-Euclidean local cost, apply `sqrt(weight)` to features to obtain the
   intended cost weights; scaling by `weight` would square those weights.
4. Align outbound and return separately between established phase anchors, then map path
   indices back to the original timeline. Treat dwell explicitly; refuse unsupported gaps.
5. Convert our provisional ±10% phase band into tested library semantics. For equal
   lengths, `window=1` is diagonal-only; unequal lengths introduce additional slack.
   Do not assume a library window equals our fractional band. Validate final paths.
6. Explicitly forbid relaxed endpoints for complete-rep comparison unless separately
   specified. Do not let truncated movement disappear through endpoint skipping.
7. Recompute the documented path-normalized feature error from the chosen pairs.
   The library's rooted cumulative distance must not silently replace our cost definition.
8. Compute tempo from unwarped seconds; DTW can align motion shape despite different speed.

Keep the existing interval/tolerance formula in `score_rep` and required-component null
policy in `score_set`. A DTW distance is neither a percentage nor a correctness judgement.
No automatic reference tolerance or weight changes are justified by a library choice.

**Acceptance:** identical series; known warp; differently timed same shape; unequal lengths;
anchor violations; excessive warping; missing joints/long gaps; truncated endpoints;
deterministic tie handling. Use the Python backend as an initial inspectable baseline;
benchmark the compiled backend only after its numerical/path behaviour is characterised.
Pin the selected backend; do not silently change it between runs. Same frozen pose,
config and implementation must reproduce serialized metrics/scores. Cross-backend equality
is a separate test, not an assumption. Candidate terms: [Apache-2.0 licence](https://github.com/wannesm/dtaidistance/blob/master/LICENSE).

## 4. Tracking: identity is not a measurement

Norfair can associate detections and retain an ID, but `TrackedObject.estimate` is a
Kalman-filter position estimate. Carry the original matched observation in detection
data; populate canonical joint observations from that, not predicted tracker positions.
Require a match in the current frame: stale `last_detection` and `live_points` alone
do not prove a current observation. `update(period=...)` denotes a detector interval,
not a general elapsed-seconds parameter; adapt temporal sampling deliberately.
Source: [Tracker/TrackedObject](https://github.com/tryolabs/norfair/blob/master/norfair/tracker.py).

The proposed subject selector sits inside the pose stage, before canonical artifact
assembly. Existing `PoseFrame.subject_track_id` can hold the local identifier. Exclude
background tracks; reset association between videos; fail uncertain reacquisition rather
than joining different people. A single detection stream cannot distinguish people the
detector never emitted, so adding Norfair alone cannot fix every MediaPipe identity issue.
Start with baseline selection and add another tracker only when needed; avoid stacking
two trackers without a clear ownership rule.

**Acceptance:** second person enters/leaves; crossing; brief occlusion; total target loss;
mirrored person; fresh-video reset. No predicted position counts as a measured turnaround,
ROM endpoint or confidence gain. Long gaps remain invalid even while a track ID persists.

## 5. Reference construction and learned assessment

AIFit/Fit3D provides close prior work for the pipeline concept: 3D motion, rep segmentation,
trainer comparison and localized feedback. Study its comparison/evaluation approach;
do not claim the overall concept as new. Our implementation still needs compatible,
reviewed, versioned references and explicit uncertainty. [Project](https://fit3d.imar.ro/).

The paper uses autocorrelation initialization and constrained repetition refinement,
then distinguishes high-motion active angular features from low-motion passive features.
The compatible lesson is to separate intended elbow/upper-arm motion from trunk stability.
Do not add its optimizer before our simpler state machine has failed evaluation. Its
articulated-spine examples require joints our shoulder/hip midpoint torso axis does not
provide; torso lean is not lumbar curvature or spinal straightness.
[Author paper, sections 4.1–4.2](https://mihaifieraru.github.io/publication/fieraru_2021_cvpr/Fieraru_2021_CVPR.pdf).

The dataset/software terms restrict noncommercial use and redistribution. Do not bundle
clips, poses, model artifacts or derived training assets as though the project page
grants general product rights. No use-specific permission was obtained in this task.
[Terms](https://fit3d.imar.ro/legal).

For T06, proposed `packages/benchmarks/benchmarks/build_reference.py` should process
authorized footage through the same canonical pipeline, select approved complete reps
and record an actual representative trajectory. A deterministic medoid is a compatible
project choice: select an observed rep minimizing aggregate compatible-pair distance,
with a fixed tie rule. This is our proposed implementation, not a claim that AIFit uses
this exact estimator. Reviewed scalar ranges/tolerances remain separate from the medoid.

Wire `check_reference_compatibility` and `load_reference_profile` before scoring.
Current `ReferenceProfile` has approval/source IDs but no explicit authoritative flag,
immutable artifact hashes or typed alignment configuration. These are already delivery
obligations, not solved by choosing a dataset. Add them through a coordinated schema bump
with generated TS/JSON consumers. Returning only `bool` from compatibility also loses
useful refusal reasons; propose a typed internal check result without silently breaking
the existing exported interface.

ALEX's paired frontal/lateral loader is a mismatch for the current single-camera flow.
Learned assessment would require licensed compatible weights/data, labels for our view
and exercise, and a held-out validation design. Keep it out of P0 numerical scoring.
PoseRAC and rehabilitation counting remain optional evaluation baselines rather than
training prerequisites. Exact source findings are recorded below.

## 6. Contract and specification gaps to resolve during implementation

### Source findings behind deferred learned models

- **ALEX input:** `PreprocessedPoseVideoDataset.__getitem__` returns frontal/lateral
  images and frontal/lateral poses. `MultiModalModel.forward` consumes all four;
  `DualInputPose.forward` also expects two views. This is an assessment pipeline,
  not a raw-video pose provider or full-rep segmenter.
  [Loader](https://github.com/AhmedYasserrr/ALEX-GYM-1/blob/main/code/data/data_loader.py),
  [fusion model](https://github.com/AhmedYasserrr/ALEX-GYM-1/blob/main/code/models/merged_model.py),
  [pose model](https://github.com/AhmedYasserrr/ALEX-GYM-1/blob/main/code/models/pose_model.py).
- **ALEX geometry:** `compute_distances_and_angles_combined` expands 33 joints into
  pairwise distances/triplet cosines without our validity mask or body normalization.
  Epsilon handling is not a missing-measurement policy. `process_action_data` shuffles
  rows rather than enforcing subject-grouped splits in that function. Prefer named
  metrics and explicit subject/session separation.
  [Processing](https://github.com/AhmedYasserrr/ALEX-GYM-1/blob/main/code/utils/data_processing.py).
- **ALEX evaluation:** per-criterion confusion/F1 can inform future binary-label
  evaluation, not continuous similarity validation. `calculate_jaccard_index` is
  defined twice; the later signature conflicts with the call in
  `get_metrics_from_predictions`. That path would fail as written. Do not import it
  unchanged. Code/data/checkpoint permissions remain unresolved.
  [Evaluation module](https://github.com/AhmedYasserrr/ALEX-GYM-1/blob/main/code/utils/evaluation_metrics.py).
- **PoseRAC:** `Action_trigger.__call__` uses enter/exit thresholds, but acts on a
  learned score rather than our geometric signal. Its evaluation loops candidate
  action classes and keeps the count error closest to ground truth: this is oracle
  selection, not deployment-realistic evaluation. Any comparison must select the
  declared exercise before seeing the true count. Count MAE alone cannot validate
  boundaries. The reviewed evaluator explicitly uses CUDA.
  [Trigger](https://github.com/MiracleDance/PoseRAC/blob/main/model.py),
  [evaluator](https://github.com/MiracleDance/PoseRAC/blob/main/eval.py).
- **Rehabilitation segmentation:** method/availability documentation only was reviewed,
  not every source file. Its trained modified-TransRAC models and preprocessed sets
  are not included; terms remain unverified. No turnkey adoption recommended.
  [Author repository](https://github.com/abediai/repetition-segmentation).

### Other discovered candidates

Retain the earlier screen's deferred status for MotionBERT/GVHMR (different motion
reconstruction stacks), OpenCap (capture/biomechanics assumptions), RepNet (counting
without our metric outputs) and tslearn (alternative DTW toolkit). No additional deep
source audit or execution of those four pipelines was performed in T19. Selecting them
would need a specific failing baseline and separate bounded review; listing them here
does not imply validation. See the linked T18 report for source and terms pointers.

### Local implementation amendments

These were confirmed against current local files; no source or schema is changed here.

| Gap | Exact owner | Required amendment |
| --- | --- | --- |
| `PoseSequence` is a header, not the frame array | T04, proposed `packages/movement/movement/artifacts.py` shared reader boundary | Resolve `frames_artifact_key` through validated storage; supply immutable frames/timestamps/masks. Do not pass a header into numerical code and invent samples. |
| `smooth_series(series, window)` has no timestamps/quality or method | T05, existing `movement/core.py` | Introduce an internal timestamped signal/mask object and a versioned filtering config. Define gap/edge behaviour; preserve raw observations. Savitzky–Golay on irregular samples needs explicit handling. SciPy is not currently a movement dependency. |
| `compute_metrics(pose, reps)` has no exercise/view/config input | T05, existing `movement/core.py` | Add typed context or an exercise strategy before multiple exercises. Avoid hidden global exercise selection and implicit thresholds. |
| Normalized XY has different width/height scales | T04/T05, `VideoAsset` plus geometry helper | Recover aspect-correct image geometry before 2D angle computation. Separate preview normalization from Euclidean measurement. |
| Long-gap fills could erase absence | T04/T05, `JointObservation` plus artifact processing | Preserve raw validity, interpolation provenance and metric-specific masks. Existing optional `quality_method` alone must not become an undocumented interpretation. |
| Lat-pulldown `shoulder_drive` suggests muscle engagement | T05, `docs/EXERCISES.md` and exercise config | Define observable upper-arm/torso geometry; coarse joints cannot establish lat activation or scapular depression. Remove unsupported interpretation when formalising the metric. |
| Phase normalization expects a reference excursion before reviewed reference exists | T05/T06, segmentation config | Separate reviewed segmentation calibration from scoring-reference approval. If calibration is absent, expose raw angles/uncertain candidates; do not normalize each candidate to itself or synthesize bounds. |
| Alignment indices/provenance and score breakdown missing from public result | T06/T07/T11.2, `contracts/analysis.py`, `contracts/reference.py`, `contracts/scoring.py` | Design versioned artifact references/result fields; update generated consumers together. Arbitrary `Any` and unstructured provenance cannot be the long-term public alignment contract. |
| Architecture describes perception as fully deterministic | Documentation with T04 outcome | Scope hard reproducibility to identical pose artifacts/config through measurement/scoring. Record model/backend/runtime for perception separately; verify rather than promise identical inference across hardware. |

These amendments make upstream methods compatible with the intended product. Merely
installing a package would leave the gaps in place.

## 7. Dataset roles and evaluation boundaries

Use external skeleton data for isolated geometry/segmentation stress tests only after
verifying terms and mapping. Existing Kinect/mocap skeletons do not test whether our
phone-video pose extractor works. Rep-separated recordings also cannot directly validate
continuous-set segmentation without continuous annotations. Do not infer technique
standards for loaded lat pulldowns from unrelated rehabilitation labels.

The earlier [dataset screen](REUSE-SCREEN-2026-10-19.md#dataset-screen) records UI-PRMD,
IntelliRehabDS, KIMORE, FLEX and FLAG3D access/terms limits; no newly approved dataset or
reference was established here. Keep participant/session separation, independent manual
rep labels and distinct development/held-out clips. Evaluate pose coverage and identity,
count error, boundary timing, partial-rep handling, metric agreement and score sensitivity
separately. A good count must not conceal incorrect phase boundaries or invented depth.

## 8. Delivery order and promotion criteria

1. **T01/T04:** real MediaPipe artifact and synchronized diagnostics on the owned segment.
   Only if a concrete failure appears, compare the narrow Sports2D/rtmlib alternative.
2. **T05:** explicit geometry/masks/filtering/config plus the full-cycle state machine.
   Record raw and processed signals and deterministic regression fixtures.
3. **T03/T08.1 and T11.1:** make real measurements usable through upload/job/viewer flow;
   do not wait for scored references or optional ML assessors.
4. **T06/T07:** approved reference provenance, compatibility gate, DTAIDistance experiment,
   then phase-aware alignment and explainable scores. Missing reference keeps scores null.
5. **T13:** independent owned-video evaluation, optional legally usable external cases
   and optional learned-counter comparisons with deployment-realistic model selection.

Every adopted dependency needs a pinned release/revision, applicable terms, hashed lock
updates, correct container placement and relevant lint/type/contract/integration checks.
Every changed deterministic rule needs versioned configuration and regression fixtures.
Evaluate benefit before promotion; no numerical runtime/accuracy gain is asserted here.

## Review ledger

- Pose review: Sports2D processing/export/packaging; rtmlib Body, PoseTracker,
  RTMPose3d and BaseTool; mapped to D002, FR04 and current pose contracts.
- Counting review: Good-GYM, ALEX-GYM-1 and secondary counter methods; mapped to
  FR05, full-cycle Rep contract and single-camera scope.
- Alignment/reference review: DTAIDistance, Norfair and AIFit/Fit3D; mapped to
  FR07/08/11, null policy, provenance and measured-observation rules.
- Consolidator: checked current source/stubs/contracts and delivery sequence; separated
  recommendations, proposed files and runtime acceptance. Full-source audit of every
  repository from the discovery list was outside this bounded task.
