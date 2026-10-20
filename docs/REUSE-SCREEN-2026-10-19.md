# Motion X-Ray: broader reuse screen

19 October 2026. T18; FR04, FR05, FR07, FR08, FR10.

## Decision

Use existing perception models and numerical libraries, integrate them through our
contracts, and build the exercise-specific measurement, reference governance and user
experience. Do not rebuild pose estimation or train a general exercise model for P0.
This screen recommends candidates, not new approved dependencies. MediaPipe remains
the primary provider under D002; lat pulldown remains the first vertical slice.

The most promising additions are Sports2D for comparison and processing patterns,
DTAIDistance for the DTW kernel, and conditional Norfair tracking. AIFit/Fit3D is close
prior work and should inform design and novelty claims.

## Evidence and limits

Reviewed primary project documentation, papers and selected licence pages. None of
these newly screened candidates was installed, executed or benchmarked in this task.
Download availability, compatible checkpoints and Linux/aarch64 support are not implied
by a README. Code, model weights, body models, dataset media and annotations can have
different terms. Pin an exact revision and record applicable terms before adoption.
No datasets, model weights or private media were downloaded; no paid calls were made.

## Repositories beyond gym apps

| Candidate | Potential saving | Fit and disposition |
| --- | --- | --- |
| [Sports2D](https://github.com/davidpagnon/Sports2D) | Video-to-pose/angles, filtering, person selection and trajectory exports | **First comparison candidate.** BSD-3-Clause code. Study angle/filtering/export behaviour; benchmark the same owned clip. Its 2D pipeline is not a drop-in source of reliable measured 3D. Optional OpenSim/IK adds assumptions and dependencies. |
| [rtmlib](https://github.com/Tau-J/rtmlib) | RTMPose-family inference without the full OpenMMLab stack | **Fallback provider candidate.** Apache-2.0 code; selected checkpoint terms and output layout need review. Useful if MediaPipe fails the pose gate. Do not assume every supported model supplies 3D. |
| [Norfair](https://github.com/tryolabs/norfair) | Associate detector/keypoint observations across frames | **Conditional.** BSD-3-Clause code. Evaluate if background people cause identity switching; tracking is separate from pose estimation and cannot recover invisible joints. Single-person analysis still applies. |
| [DTAIDistance](https://github.com/wannesm/dtaidistance) | Tested DTW distance/path kernels, Python and compiled implementations | **First numerical candidate.** Apache-2.0 code. Keep our normalization, phase constraints, missing-data gates and score policy; validate window/path semantics and ARM build before pinning. |
| [tslearn](https://github.com/tslearn-team/tslearn) | Alternative time-series distances and prototype methods | **Reserve.** Broader toolkit than P0 needs; dependency and licence review still owed. Avoid adopting two DTW libraries without a demonstrated need. |
| [MotionBERT](https://github.com/Walter0807/MotionBERT) | Temporal motion representation and 2D-to-3D lifting | **Later pose experiment.** Apache-2.0 code; checkpoint/training-data terms need separate review. Requires skeleton mapping and validation of gym/occlusion performance, not just a plausible skeleton. |
| [GVHMR](https://github.com/zju3dv/GVHMR) | Monocular global human-motion recovery | **Research reference.** Its licence restricts use to educational/research/nonprofit purposes; commercial use needs permission. Heavy model/body-model dependencies make this unsuitable as the default local P0 path. |
| [OpenCap core](https://github.com/opencap-org/opencap-core) | Adjacent biomechanics processing and validation methods | **Future methods review.** Do not assume its full capture/calibration pipeline fits one uploaded phone video. No adoption or complete dependency/licence audit performed. |
| [Google RepNet](https://github.com/google-research/google-research/tree/master/repnet) | General repetitive-video counting | **Secondary baseline.** Counting repeated visual motion does not provide joint metrics or technique labels. Exact model terms/runtime still need review. |
| [PoseRAC](https://github.com/MiracleDance/PoseRAC) | Pose-based repetition counting and salient-pose annotations | **Secondary baseline.** Could inform segmentation evaluation; exercise/view transfer and reuse terms remain unverified. A counter does not establish movement quality. |
| [Rehabilitation repetition segmentation](https://github.com/abediai/repetition-segmentation) | Methods/evaluation for irregular skeletal repetitions | **Method reference.** Useful for pauses and variable repetitions. The README excludes trained modified TransRAC models and preprocessed datasets/logs; not a complete pretrained replacement. Licence review remains open. |

Licence evidence for priority candidates: [Sports2D](https://raw.githubusercontent.com/davidpagnon/Sports2D/main/LICENSE),
[rtmlib](https://raw.githubusercontent.com/Tau-J/rtmlib/main/LICENSE),
[DTAIDistance](https://raw.githubusercontent.com/wannesm/dtaidistance/master/LICENSE),
[Norfair repository licence](https://github.com/tryolabs/norfair/blob/master/LICENSE),
[GVHMR](https://raw.githubusercontent.com/zju3dv/GVHMR/main/LICENSE).

## Dataset screen

| Dataset | Useful evidence | Access, mismatch and recommendation |
| --- | --- | --- |
| [AIFit / Fit3D](https://fit3d.imar.ro/) | Multi-view fitness data, 3D ground truth, repetitions and trainer/trainee comparison | **High research relevance.** This is close prior work for our intended flow. [Terms](https://fit3d.imar.ro/legal) restrict use to noncommercial research/education/art and restrict redistribution and commercial training. Study methods; do not bundle data or treat public access as product permission. |
| [UI-PRMD paper](https://doi.org/10.3390/data3010002) | Rehabilitation motion with correct/incorrect examples | **Evaluation candidate.** Paper describes a PDDL dedication. Official dataset page returned 403 during this screen, so current download access is unresolved. Captured skeletons differ from noisy phone-derived poses and loaded gym movements. |
| [IntelliRehabDS](https://zenodo.org/records/4610859) | Kinect 3D joints, correct/incorrect labels and a documented partial recording | **Evaluation candidate.** Skeleton archive is listed separately from much larger depth archives. Good for missing/partial-rep handling after schema mapping. [Author code](https://github.com/alina-miron/intellirehabds) has stated terms, but the fetched Zenodo licence field was blank: confirm dataset terms before using it. |
| [KIMORE publication](https://pubmed.ncbi.nlm.nih.gov/31217121/) | Rehabilitation RGB/depth/skeleton and clinical assessment | **Later evaluation.** Original access and data terms unresolved here. A permissive wrapper licence does not grant rights to the source dataset. Clinical labels do not become gym scoring rules. |
| [FLEX paper](https://arxiv.org/abs/2506.03198) | Loaded exercise, multi-view motion and error/feedback research | **Promising lead, not ready input.** Linked project URL returned 404 during this screen. Verify actual release, terms, exercise inventory and annotations before scheduling work around it. |
| [FLAG3D](https://andytang15.github.io/FLAG3D/) | Fitness motions with language instructions and multiple data modalities | **Research only for now.** Agreement-based access and scientific-research restrictions; not an immediately reusable product dataset. Activity/instruction labels do not necessarily label technique errors. |

No newly screened resource has yet been verified as an approved, directly usable
lat-pulldown reference for this product. Dataset relevance is not reference approval.
Do not derive arbitrary score tolerances from unrelated rehabilitation movements.

## Relationship to the earlier shortlist

Good-GYM remains useful for counter/state-machine patterns; ALEX-GYM-1 remains a
research example of exercise assessment. They are not replacements for our complete
pipeline. Earlier checks were documentation/selected-code screening, not execution.
This pass adds adjacent processing libraries, tracking, alignment and biomechanics
research; it does not imply those earlier projects were comprehensively audited.

GEM-X, MediaPipe, MMPose, RepCount/TransRAC, Fitness-AQA, CFRep and M3GYM retain their
previously recorded roles and limitations. Re-screen their exact artifacts if selected
for implementation. Do not reset the baseline or switch providers solely because a
new repository has an impressive demo or reported benchmark.

## Bounded implementation follow-up

1. **T01/T04:** Produce the real canonical MediaPipe artifact from the owned lat-pulldown
   segment. Record timestamps, selected-person identity, visibility, coordinate meanings,
   processing time and estimated-3D limitations. Manually label rep boundaries independently.
2. **Conditional pose comparison:** If that gate exposes a material failure, run one
   Sports2D/rtmlib comparison in an isolated container on the same input. Compare missing
   joints, identity switches, angle traces and runtime. Determine whether a 2D improvement
   sacrifices required 3D output. Record exact model/revision/terms before execution.
3. **T05:** Reuse suitable processing patterns while preserving video timestamps,
   per-side visibility gates, explicit pauses/partial reps and versioned exercise configs.
   Evaluate on held-out clips; do not tune and report accuracy on the same examples.
4. **T06/T07:** Evaluate DTAIDistance with known alignment fixtures: identity, tempo
   change, truncated repetition, missing samples and constrained warping. Pin the library
   only after numerical/path semantics match our requirements and container checks pass.
5. **T13:** Add a small legally usable external skeleton evaluation set if it contributes
   distinct failure cases. Keep subjects/sessions separated across development/evaluation.
   Report domain mismatch; separate pose error, segmentation error and similarity behaviour.

The owned clip remains the first integration input, not automatically an approved form
benchmark. External datasets supplement evaluation; they cannot replace real phone-video
testing or human review of the reference and metric rules. Nemotron still interprets
validated measurements and never computes movement scores.

## Stop rule

Stop discovery for now and deliver the first real pose-to-rep result. Reopen screening
for a specific observed blocker, missing exercise coverage or unresolved adoption terms.
No architecture, public contract, model provider or dependency changed in T18.
