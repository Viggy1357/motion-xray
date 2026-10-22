# PRODUCT

Motion X Ray turns a short workout video into a rep-by-rep movement report. A user
records or uploads a set, the system reconstructs movement as a rotatable 3D skeleton,
compares it against a curated reference trajectory, and returns grounded coaching —
always with honest limitations. This document states the product scope and the P0
functional requirements. It is a statement of intent for the build, not a claim about a
validated biomechanics product: scores express *similarity to a selected reference*,
not correctness, safety, or effectiveness.

## Scope (P0)

### Active hackathon release profile (22 October2026)

The owner accepts an analysis-first gym companion and requests the execution plan in
`HACKATHON-EXECUTION-PLAN.md` before delegation. Target exercises are lat pulldown,
dumbbell curl, bodyweight squat and incline chest press (actual press variant checked
at intake); lateral raise is deferred for this release. This overrides the historical
exercise list below without claiming that all four are implemented.

Same-browser profile/workout log first; no cross-device sign-in. Free-first hosting,
with unavoidable cost flagged before activation. Current baseline comparison stays
provisional; deeper calibration is held. Report estimates, observation coverage and
missing components separately. Rep corrections, simple routines and the illustrative
muscle view support the main upload->analysis->coaching->log flow, with the optional
feature cut line in the execution plan. External camera hardware remains later scope.

### Original P0 specification (retained for traceability)

The P0 pipeline is: capture/upload → pose extraction → rep segmentation → exercise
metrics → reference comparison → deterministic similarity score → grounded coaching.
Results are shown as synchronized video + 2D overlay + rotatable 3D skeleton + a shared
rep timeline. Supported exercises are the simultaneous standing dumbbell curl, the
bilateral standing lateral raise, the bodyweight squat, and the cable lat pulldown
(added per `DECISIONS.md` D005; lat pulldown is the first exercise exercised end-to-end).

The product targets the **solo user** training without a personal trainer present. The
default comparison target is a **curated** reference that ships with the app — the user
never needs a second person. Trainer-provided and personal-best references are optional
P1 sources, not a requirement (see `DECISIONS.md` D006).

Out of scope for P0: medical or safety claims, exercises beyond the supported movements,
multi-person analysis, trainer/personal-best reference workflows (P1), and anything
requiring a GPU entitlement the project does not have (GEM-X 3D pose stays a documented
stretch goal — see `DECISIONS.md` D002).

## Processing and reuse requirements (20 October clarification)

- MediaPipe remains primary. Sports2D/Good-GYM supply methods to adapt; DTAIDistance is
  the preferred kernel candidate to verify. Norfair/rtmlib are conditional alternatives,
  not automatic additional services. D009 and the integration review define the gates.
- Count completed cycles from original video timestamps; retain partial/uncertain reps.
  A threshold crossing alone is not a completed repetition. Occluded arms are not averaged
  into valid measurements, and tracker predictions never count as observed joints.
- Complete existing profiles require estimated 3D; a 2D-only provider cannot silently
  satisfy them. Keep measured output where possible and explain unavailable quantities.
- Reference similarity needs a compatible, authorized and reviewed reference. Segmentation
  calibration is separate from reference approval; missing calibration does not justify
  invented excursion bounds. Raw angle inspection may precede valid rep/scoring output.
- Observable upper-arm/trunk geometry does not establish muscle activation, scapular
  depression, lumbar curvature, injury risk or safety. Coaching obeys these limits too.
- No general model training, paired-camera capture or external dataset dependency is
  added to P0. Skeleton datasets supplement isolated evaluation, not phone-video proof.

## Functional requirements

| ID | Name | One-line description |
| --- | --- | --- |
| FR01 | Capture | Record a short set in the browser within upload/duration limits. |
| FR02 | Upload | Accept an uploaded video asset and record verifiable metadata. |
| FR03 | Analysis lifecycle | Enqueue, track, cancel, and delete an analysis job. |
| FR04 | Pose extraction | Produce a canonical, timestamped pose sequence from the video. |
| FR05 | Rep segmentation | Detect repetitions and phase boundaries from the phase signal. |
| FR06 | Exercise catalogue | List supported exercises and variants. |
| FR07 | Reference comparison | Compare measured metrics against an approved reference profile. |
| FR08 | Deterministic scoring | Produce an explainable 0-100 similarity score (or honest null). |
| FR09 | Grounded coaching | Generate short coaching text from validated metrics only. |
| FR10 | X Ray viewer | Serve synchronized video, 2D overlay, 3D skeleton, and rep timeline. |
| FR11 | Evidence & references | Manage reference profiles and operator-triggered evidence refresh. |
| FR12 | Job status & honesty | Surface job state/stage and honest partial/failure results. |

See `docs/ARCHITECTURE.md` for how these requirements map onto the pipeline and
services, and `docs/EVALUATION.md` for the acceptance targets (labelled as targets, not
measured results).
