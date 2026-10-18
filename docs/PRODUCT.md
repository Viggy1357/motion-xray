# PRODUCT

Motion X Ray turns a short workout video into a rep-by-rep movement report. A user
records or uploads a set, the system reconstructs movement as a rotatable 3D skeleton,
compares it against a curated reference trajectory, and returns grounded coaching —
always with honest limitations. This document states the product scope and the P0
functional requirements. It is a statement of intent for the build, not a claim about a
validated biomechanics product: scores express *similarity to a selected reference*,
not correctness, safety, or effectiveness.

## Scope (P0)

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
