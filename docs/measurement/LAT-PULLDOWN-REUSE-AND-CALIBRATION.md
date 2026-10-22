# Lat-Pulldown Reuse and Calibration Plan

Compiled 22 October 2026 from the dated 19–20 October reviews. Source assessment of candidate reuse and calibration plan for the posture-first lat-pulldown proof. This is a dated assessment of supplied documentation and prior code; it does not imply current upstream inspection or adoption of any listed project.

## 1. Candidate reuse decisions

| Candidate | Actual contribution to posture-first lat pulldown | Mismatch / risk | Decision | Primary source links from supplied docs | Must verify next |
| --- | --- | --- | --- | --- | --- |
| **Sports2D** | Confidence-gated angle/filter/diagnostic patterns; 2D comparison benchmark on same owned clip. | Assumes planar motion; rounds FPS; TLS side effects; static depth offsets must not become measured XYZ; OpenSim/IK adds assumptions. Full package drags Pose2Sim stack. | **Adapt methods only; isolated diagnostic comparison.** | [process.py](https://github.com/davidpagnon/Sports2D/blob/main/Sports2D/process.py), [common.py](https://github.com/davidpagnon/Sports2D/blob/main/Sports2D/Utilities/common.py) | Same-input 2D angle/filter trace vs MediaPipe; confirm no 3D truth leakage; pin revision and dependency terms before any code transplant. |
| **Good-GYM** | Hysteresis/threshold-state counter design for cycle segmentation. | Uses elapsed wall time, combines arm angles, no full-cycle `READY→OUTBOUND→TURNAROUND→RETURN→COMPLETE` record; pullup catalog is not a validated lat-pulldown profile. | **Adapt design, not implementation.** | [exercise_counters.py](https://github.com/yo-WASSUP/Good-GYM/blob/master/exercise_counters.py), [exercises.json](https://github.com/yo-WASSUP/Good-GYM/blob/master/data/exercises.json) | Map its angle logic to our versioned `lat_pulldown.yaml`; test state machine on owned clip for full-cycle completion, partial reps, dwell. |
| **DTAIDistance** | Multivariate DTW path kernel for tempo-robust alignment. | Window semantics must be translated to our phase-band setting; default cost is not our path-normalized trajectory error; compiled backend needs ARM/dependency check. | **First dependency candidate, behind internal adapter.** | [dtw_ndim.py](https://github.com/wannesm/dtaidistance/blob/master/src/dtaidistance/dtw_ndim.py), [dtw.py](https://github.com/wannesm/dtaidistance/blob/master/src/dtaidistance/dtw.py) | Fixture tests: identical series, tempo change, truncated rep, missing samples, anchor violations, excessive warping; pin backend/version. |
| **AIFit/Fit3D** | Reference-selection and deviation-evaluation methodology; separates active arm motion from trunk stability. | Terms restrict noncommercial research/art; no verified accessible lat-pulldown benchmark in this checkout; articulated-spine metrics exceed our joint set. | **Study and adapt design; no bundled data.** | [Project](https://fit3d.imar.ro/), [terms](https://fit3d.imar.ro/legal) | Confirm exercise inventory, skeleton mapping, labels and permissions before any data adoption; build our own approved reference via `build_reference.py`. |
| **ALEX-GYM-1** | Learned-assessment research example; per-criterion F1 could inform future binary-label evaluation. | Expects paired frontal/lateral images and poses; no compatible pretrained single-camera lat-pulldown engine; code has conflicting duplicate definitions. | **Defer runtime reuse to P1/T13 evaluation baseline.** | [data_loader.py](https://github.com/AhmedYasserrr/ALEX-GYM-1/blob/main/code/data/data_loader.py), [merged_model.py](https://github.com/AhmedYasserrr/ALEX-GYM-1/blob/main/code/models/merged_model.py) | Resolve code/data/checkpoint permissions; only revisit if our geometric scorer fails a specific, documented gap. |

**Norfair** and **rtmlib** are conditional: add only if the MediaPipe baseline shows a concrete identity or coverage failure. Norfair carries original detections, not predicted tracker positions; rtmlib 2D mode cannot satisfy current 3D-required profiles.

## 2. Calibration protocol for 2–3 public demos

Preferred demos: **QMotion corrected** (owner preference), **IMSA panel**, **Catalyst with view cuts**. Exclude deliberately incorrect examples and camera cuts.

### 2.1 Define observables per source

For each demo, record per-phase samples of:

1. **Elbow interior angle** (shoulder–elbow–wrist interior angle). This is not automatically anatomical flexion; if the convention is `180 − interior`, name and document it explicitly.
2. **Upper-arm/torso angle** (elbow–shoulder–hip interior angle), using a fixed shoulder-to-hip torso axis.
3. **Torso inclination / stability**: change in shoulder–hip axis angle relative to a fixed camera-plane reference, depending on view.
4. **Bar endpoint relative to chest** — currently **not implemented**; requires visible bar/chest localization from a manual or validated tracker. A calibrated reference alone cannot measure an unknown user's bar.
5. **Top/return extension** — elbow near-extension at the top, controlled return tempo.
6. **Cadence/tempo** — pull duration, return duration, pause at bottom; kept separate from posture score.

### 2.2 Fixed camera axis vs relative joint angles

- **Relative joint angles** (elbow, upper-arm/torso) are view-dependent but robust to camera roll if all three joints are visible. They must be compared only within the same view class (e.g., frontal, lateral, diagonal).
- **Fixed camera axis torso metrics** require a known stable direction in the frame (e.g., vertical door frame, floor line). If the camera is tilted or the athlete rotates, the fixed axis becomes a source-specific convention, not an absolute measure.
- For each demo, note the **camera plane** and whether the view is frontal, lateral, or diagonal. Diagonal class alone is insufficient for comparability; check yaw, plane and roll. Never fuse camera-plane angles from unmatched views into one distribution.
- Temporal angle excursion within a fixed camera plane does not require world-gravity alignment.

### 2.3 Phase and side compatibility

- Segment each demo into **outbound** (start → turnaround/bottom) and **return** (turnaround → complete) phases using manual timestamps.
- Record **side** (left/right) used for measurement. Side eligibility is fixed within a track; contralateral comparisons are not assumed equivalent and require validation before use.
- A rep is **compatible** for calibration only if the same side and same view class are present in both demo and user footage.

### 2.4 Uncertainty and manual check

- For each sampled frame, manually verify landmark identity (shoulder vs. elbow vs. wrist) and whether the joint is occluded.
- Record **measurement uncertainty** separately from **source range**: e.g., landmark placement ambiguity, frame sampling step, interpolation choice. Do not invent a fixed `3–5°` number where no actual measurement was made.
- Flag when a metric is **unobservable** from a given view (e.g., bar-chest contact depth in a frontal view; endpoint height may still be visible).

### 2.5 Source-per-demo ranges vs tolerances

- Record the **observed demo range** (min/max or phase-specific values) per source, per metric, per view.
- Derive **provisional scoring tolerance** only after reviewing all sources; a 2–3 video min/max is not a population norm.
- If a source gives only a qualitative cue, document the numeric operationalization and how it will be tested. Do not invent degrees.
- **Cadence** is recorded separately and does not enter the posture angle score. The existing trial cadence algorithm is known to fail; treat cadence as a separate, not unimplemented-blanket, concern.

## 3. Annotation schema

Every calibrated measurement or excluded observation must carry:

| Field | Meaning |
| --- | --- |
| `source_hash` | Immutable identifier of the source video/frame artifact: cryptographic SHA-256 of the immutable artifact plus transform/version annotation. Proposals are not a public schema. |
| `PTS` | Presentation timestamp in seconds from the original video. |
| `side` | `left` / `right` / `both` / `unspecified`. |
| `view` | `frontal` / `lateral_left` / `lateral_right` / `diagonal` / `other`. |
| `metric` | e.g., `elbow_interior_angle`, `upper_arm_torso_angle`, `torso_inclination_fixed_axis`. |
| `space` | `projected_2d` / `estimated_3d` / `manual_reference`. |
| `value_units` | Numeric value and unit (degrees, seconds, pixels, ratio, or `null`). |
| `landmarks` | Ordered list of joint names used. |
| `reference_axis` | For fixed-axis metrics, the axis definition in camera or world terms. |
| `uncertainty` | Estimated measurement uncertainty and any occlusion/interpolation flags. |
| `observation` | What was actually seen in the source. |
| `reason` | Machine-readable cause when value is `null` (e.g., `occluded`, `wrong_view`, `not_implemented`). The reason is a non-empty string; the measurement value is `null`. |
| `reviewer_provenance` | Human reviewer ID / automated module / version. |

A missing measurement must not be silently treated as a perfect score.

## 4. Not-implemented metrics

The following are explicitly **not implemented** in the current posture-first proof:

- **Bar endpoint / chest contact**: requires visible bar/chest localization from a manual or validated tracker. A calibrated reference alone cannot measure an unknown user's bar. No actual video angles should be invented.
- **Torso metrics beyond shoulder–hip axis**: lumbar curvature, spinal straightness, scapular depression, and lat activation cannot be measured with the current coarse joint set. The torso axis (starting lean and dynamic stability) is itself not yet implemented, although raw relative joint angles are available.

These remain candidates for future work with additional sensors, object tracking, or multi-angle reference reconstruction. Multi-camera reference reconstruction is not a reason to claim these metrics now.

## 5. Current 180-degree normalizer and torso omission

The existing `review_comparison.py` uses a **180-degree normalizer** for its experimental angle-pattern agreement score:

```
score = 100 * (1 - mean_mae / 180)
```

This is historical experimental arithmetic, not the new benchmark policy. It treats a 180° mean absolute error as zero agreement, which has no biomechanical justification for lat-pulldown technique. It also **omits torso stability** from the comparison because only elbow and upper-arm/torso angles are compared. The new calibration must replace or retire this normalizer with reviewed tolerances per metric, and must add an explicit torso-stability component where the view supports it.

## 6. Acceptance target

- At least **six usable user repetitions** are enough for the first proof. Exact recovery of all ten repetitions is not required.
- Sampling quality matters more than rep count; counts are secondary to measurement quality.
- A detected interval must correspond to the actual movement; do not merge cycles to hit the count.

## 7. Next bounded implementation chunk

The current T04 provider/raw-frame artifact has already been delivered. Do **not** reset the next task to pose baseline. The next bounded chunk is:

1. Sourced rubric-approved definitions.
2. Torso-axis / dynamic metrics using existing immutable artifacts.
3. Reference-manual calibration, extending extraction only as needed to reach at least six eligible user reps.
4. Review, not the whole pipeline.

**Acceptance:** Using existing immutable pose artifacts, deliver timestamped torso/arm observations for selected compatible reference repetitions, independently check sampled frames and define reference axes/uncertainty. Extend extraction only where needed for the subsequent six-rep user proof. Do not repeat the completed T04 baseline.

**What must precede a score:**

1. Sourced metric matrix and consolidated lat-pulldown rubric (§1 of workflow).
2. Reference metric profiles from 2–3 demos with manual checks and compatibility rules (§2).
3. Versioned provisional benchmark specification with frozen tolerances, weights, and scoring response.
4. Real user footage measurement on ≥6 usable reps with per-rep raw values, deviations, component scores, uncertainty, and excluded quantities.
5. Sensitivity checks showing the score responds to visible posture differences and correctly reports unavailability.

No production UI, multi-camera engine, data download, or host installs are in this chunk. No code generation bypasses the evidence matrix. Research methodology does not make video reuse legal; verify permissions separately. No new measurements, score weights, dataset downloads, or source-code changes are introduced by this plan. The system is ready for calibration, not approved ranges.
