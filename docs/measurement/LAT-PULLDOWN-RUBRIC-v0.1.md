# LAT-PULLDOWN-RUBRIC-v0.1

**Status:** `research_pending_calibration`
**Authoritative:** `false`
**Version:** 0.1 (QC-repaired)
**Date:** 22 October 2026
**Scope:** bilateral seated front cable lat pulldown, strict controlled baseline. Variants are noted where sources differ; variant-specific cues are not universal. This rubric is research-grade and ready for calibration, not approved for scoring.

---

## 1. Source inventory and paraphrases

| ID | Source | URL / locator | Paraphrase |
|----|--------|---------------|------------|
| S1 | ACE Fitness — Seated Lat Pulldown | https://www.acefitness.org/resources/everyone/exercise-library/158/seated-lat-pulldown/ (retrieved 2026-10-22) | Secure the seated setup, use a slight starting lean, avoid added backward movement during pulling, and return to extension. The chest endpoint and backward elbow movement guide the bottom position. |
| S2 | NASM — The Biomechanics of the Lat Pulldown | https://www.nasm.org/resource-center/blog/training/the-biomechanics-of-the-lat-pulldown-muscles-grip-and-form (retrieved 2026-10-22) | Maintain a stable torso, direct elbows toward the ribs, pull toward the upper chest and control both phases. Grip variants and common compensations need contextual interpretation. |
| S3 | Catalyst Athletics — Lat Pulldown | https://www.catalystathletics.com/exercise/725/Lat-Pulldown/ (retrieved 2026-10-22) | Use a braced trunk, a collarbone endpoint and a controlled return. The publisher also describes grip and backward-lean variations; those are not one universal technique. |
| S4 | QMotion — Lat Pulldown | https://www.qmsu.org/qmotion/guides/video/21286/Lat-Pulldown/ (retrieved 2026-10-22; published 2025-01-28 14:29) | Secure the legs, retain a slight backward torso inclination, pull toward the chest and return slowly to arm extension. |
| S5 | Jeff Nippard — auto-captions | https://www.youtube.com/watch?v=O94yEoGXtBY , selection 03:10–04:45 only (auto-captions, not manually audio-verified) | Discusses down-and-in elbow travel, upper-chest contact, extension on return and moderate starting lean. Momentum-assisted pulling is described separately as an advanced option. Captions need audio verification before numerical cue adoption. |

---

## 2. Consolidated technique narrative

The strict controlled front seated cable lat pulldown begins with thighs secured, torso braced, and a slight backward lean. The pull starts with scapular depression, followed by elbow drive downward and slightly inward, bringing the bar to the upper chest or collarbones. The return is controlled to full elbow extension. Torso stability, elbow path, bar endpoint, and controlled tempo are the primary observable criteria. Sources disagree on acceptable lean magnitude, exact endpoint zone, and whether momentum is ever acceptable. These are contextual disagreements between coaching sources, not errors to be resolved by vote or confidence scores.

---

## 3. Metric matrix

| Metric ID | Cue / evidence IDs | Source agreement / conflict | Operational geometry or proxy | Phase / units | Camera eligibility | Required landmarks | Implementation status | Importance rationale | Tolerance known / absent |
|-----------|--------------------|-----------------------------|-------------------------------|---------------|--------------------|--------------------|-----------------------|----------------------|--------------------------|
| M1 | `torso_start_lean` | S1 slight lean, ≤30° cue; S2 slight lean fine; S3 neutral trunk, lean listed as variation; S4 slight backwards lean; S5 moderate lean acceptable. **Conflict** on magnitude. | Signed angle between torso segment (shoulder–hip) and a declared reference: camera-vertical/world baseline established from the scene, or the seat-back normal (which is not gravity-aligned and must be labeled as such). Positive = backward lean. Baseline convention must be recorded per video. | Start of rep / degrees | Side view preferred; diagonal side only if baseline calibrated; frontal not eligible. View eligibility must be validated before reporting. | Visible-side shoulder and hip (both sides not required if visible side is validated), plus a calibrated vertical reference or seat-back line. | Pending: baseline convention and calibration. | Establishes setup consistency; distinguishes strict from excessive-lean variants. | **Absent.** ACE 30° is a source-specific coaching cue, not a validated projected-measurement tolerance. |
| M2 | `torso_dynamic_excursion` | S1 avoid additional backward lean during pull; S2 torso stable; S3 trunk braced; S4 maintain slight lean (implies stable); S5 cable stays pretty straight in side view. **Consensus** for strict baseline. | Change in torso lean angle from pull start to turnaround, or max-minus-min lean within the rep. Computable within a stable camera without a physical gravity reference, provided the signed projection plane is valid; absolute lean (M1) still needs the calibrated baseline. | Pull phase / degrees | Side view preferred; camera must be stable. | Same as M1. | Pending: depends on M1 angle definition; excursion itself does not require world calibration. | Quantifies projected torso movement; does not measure momentum, force or its cause. | **Absent.** No validated excursion limit. |
| M3 | `elbow_interior_rom` | S1 pull until elbows stop moving down; S2 elbows down toward ribs; S3 pull to collarbones; S4 bar into chest; S5 full elbow extension at top. **Consensus:** elbow flexes on pull, extends on return. | Interior angle at elbow: `shoulder → elbow → wrist`. | Full rep / degrees | Side or diagonal side. | Shoulder, elbow, wrist on visible side. | Raw per-frame angle implemented (T05.1 `elbow_angle`). Per-rep ROM, min/max extraction, and endpoint events are **not implemented**. | Describes elbow excursion; adequacy requires a compatible reference, not a universal flexion target. | **Absent.** No validated min/max degrees. |
| M4 | `upper_arm_torso_angle` | S1 elbows down toward sides; S2 elbows down and toward ribs; S5 elbows down and in at ~10–15° from top view. **Consensus:** upper arm moves downward relative to torso. | Interior angle at shoulder: `elbow → shoulder → hip`, same side. Smaller = upper arm closer to torso. **Observable limit:** this scalar side-projection angle cannot distinguish out-of-plane arm motion and cannot by itself prove a lat-driven path, lat activation, or distinguish pulldown from row; it is a proxy for the "elbows down" cue only. | Pull phase / degrees | Side or diagonal side; side-projection limitations apply. | Elbow, shoulder, hip on visible side. | Raw per-frame angle implemented (T05.1 `upper_arm_torso_angle`); per-rep events not implemented. | Proxy for elbow-drive cue. | **Absent.** Jeff's 10–15° is a top-view cue, not a side-view angle, and is not a calibrated tolerance. |
| M5 | `chest_bar_endpoint` | S1 top or mid-chest; S2 upper chest; S3 collarbones; S4 chest; S5 top of sternum/upper chest. **Conflict** on exact zone. | Proxy: vertical position of wrist relative to shoulder/hip at turnaround. **Limit:** a wrist proxy cannot establish bar–chest contact or an acceptable bar landing; without validated bar/chest localization the bar endpoint is unavailable. A wrist proxy remains unscored until separately validated and cannot satisfy the required bar-endpoint component. | Turnaround / pixels or normalized units | Side view; wrist and shoulder visible; true bar endpoint requires object detection. | Wrist, shoulder, hip; bar detection pending. | Pending: no bar detector; turnaround event not implemented. | Ensures the pull finishes at an appropriate height. | **Absent.** No validated vertical tolerance. |
| M6 | `return_extension` | S1 return to full elbow extension; S2 control both directions; S3 return under control; S4 arms into full extension; S5 full elbow extension at top. **Consensus.** | `elbow_angle` at a `return_end` event, compared to a compatible reference extension target. Do not normalize an incomplete user return into full extension. | Return phase / degrees | Side or diagonal side. | Shoulder, elbow, wrist on visible side. | Raw per-frame angle implemented; `return_end` event and per-rep endpoint are **not implemented**. | Incomplete extension shortens ROM and may inflate rep count. | **Absent.** No validated extension threshold. |
| M7 | `tempo_control` | S1 pause momentarily, slowly return (concentric cue is "slowly exhale", not an explicit slow-pull prescription); S2 control both directions, slower tempo limits momentum; S3 return under control; S4 slowly allow arms into extension; S5 advanced momentum allowed only if negative controlled. **Conflict:** strict sources emphasize control; Jeff permits advanced cheating. Not all sources demand a slow concentric. | Durations of pull phase, return phase, and pause at turnaround, from rep segmentation. | Full rep / seconds | Any eligible view. | Rep segmentation events (`pull_start`, `turnaround`, `return_end`). | An experimental trial exists with a known defect: it misses/merges cycles, and its bottom anchor is low-threshold entry rather than the true extremum. Segmentation is not validated. | Separates controlled reps from momentum-driven reps. Reported separately; **not required for the posture score**. | **Absent.** No validated tempo bounds. |
| M8 | `head_shoulder_setup` | S1 head aligned with spine, scapulae depressed/retracted; S2 tall posture, shoulders away from ears, avoid forward head/shrug; S5 chest up, thoracic extension, scapulae depressed. **Consensus** on qualitative setup. | Conditional, unscored proxy: shoulder–ear vertical distance (shrug flag) where landmarks exist. The PoseFrame contract uses an arbitrary joint-name dictionary and does not forbid head joints, but the current workflow has no implemented, validated head metric. | Setup and pull / pixels or qualitative flags | Frontal or side depending on cue. | Ears, shoulders, hips if provided by the detector. | Pending: no implemented validated head metric. | Supports posture cues; cannot claim activation or spinal-curve measurement. | **Absent.** No validated thresholds. |

---

## 4. Consensus, single-source, and engineering-hypothesis classification

| Criterion | Classification |
|-----------|----------------|
| Thighs secured / feet planted | Consensus (S1, S2, S4, S5) |
| Some backward lean acceptable at start | Consensus on "some lean"; conflict on magnitude (S1 ≤30° cue, S5 moderate, S3 variation) |
| Avoid additional backward lean during pull | Consensus for strict baseline (S1–S4); S5 permits advanced momentum variant |
| Depress scapulae before/initiating pull | Consensus (S1, S2, S5) — pose cannot measure scapular control |
| Drive elbows down / down-and-in | Consensus (S1, S2, S5) |
| Bar to upper chest / collarbones / top of sternum | Consensus on high-chest endpoint; conflict on exact zone |
| Controlled return to full elbow extension | Consensus (S1–S5) |
| Controlled tempo / negative | Consensus for strict baseline (S1–S4); S5 advanced-momentum variant is a single-source exception; sources differ on concentric-speed wording |
| Elbows ~10–15° from top view | Single-source (S5); top-view specific, not a side-view angle or scoring threshold |
| Cable travels in a pretty straight line in side view | Single-source (S5) engineering hypothesis for lean validation |
| Bar contact with top of sternum | Single-source (S5) |
| Behind-the-neck pulldown avoided | Single-source (S2); out of scope for front pulldown |
| Grip-width effects on muscle emphasis | Single-source / descriptive (S2); not a posture metric |

Neither the ACE 30° cue nor Jeff's top-view 10–15° cue is adopted as an automatic scoring threshold. The 2–3 demonstration clips in §7 are a calibration range, not validated tolerances, and do not establish population rules.

---

## 5. What this rubric does NOT claim

- It does **not** claim pose detection can measure scapular control, spinal curvature, muscle activation, forces, load, safety, or bar contact without a bar detector; these are excluded from all score claims.
- It does **not** treat source cues as validated numerical tolerances.
- It does **not** claim cues prove causal diagnoses (e.g., a wrist proxy does not prove lat-driven motion).
- It does **not** claim to have watched footage or measured new angles.
- It does **not** approve any reference video, trajectory, tolerance, or scoring weight.

---

## 6. Minimum required component coverage for aggregate scoring

Core components required before any aggregate score is reported for a rep:

1. **Torso:** both `torso_start_lean` (M1) **and** `torso_dynamic_excursion` (M2) must be available; they are distinct observables, not either/or.
2. **Arm ROM:** `elbow_interior_rom` (M3) and `return_extension` (M6) must both be available. These are reported as one ROM component family; elbow ROM and return extent must not be double-counted as independent weighted features.
3. **Shoulder drive:** `upper_arm_torso_angle` (M4) must be available.
4. **Endpoint:** `chest_bar_endpoint` (M5) must be available as a wrist proxy, labeled as proxy.

If any required core metric is missing, the aggregate is **unavailable**. Merely marking a reason for a missing metric does not permit an aggregate. If all core components cannot yet be measured, report components only. `head_shoulder_setup` (M8) is conditional and unscored. `tempo_control` (M7) is reported separately and is not required for the posture score.

---

## 7. Repetition and calibration acceptance

- **Success target:** at least **6 usable user repetitions** for the first proof. Exact recovery of 10 reps is not required and remains a later feature, not a gate.
- **Calibration order:**
  1. Confirm criteria from this rubric.
  2. Acquire and review **2–3 reference demonstration clips** (existing preference: QMotion corrected section, IMSA, Catalyst; exclude deliberately incorrect examples and camera cuts).
  3. Measure rubric observables manually, record source timestamps, and derive provisional tolerances.
  4. Only then apply to user footage and produce scores.

This is a narrow ordered calibration handoff, not a full MVP.

---

## 8. Scoring tolerances and weights

All scoring tolerances and component weights are **UNKNOWN / null** pending reference measurements and independent review. No new ranges, tolerances, or weights are introduced by this rubric. Implementations must use `null` or explicit "pending" placeholders until calibration is complete.

---

## 9. References

- S1 ACE Fitness. *Seated Lat Pulldown*. https://www.acefitness.org/resources/everyone/exercise-library/158/seated-lat-pulldown/ (retrieved 2026-10-22).
- S2 NASM. *The Biomechanics of the Lat Pulldown: Muscles, Grips, and Form*. https://www.nasm.org/resource-center/blog/training/the-biomechanics-of-the-lat-pulldown-muscles-grip-and-form (retrieved 2026-10-22).
- S3 Catalyst Athletics. *Lat Pulldown*. https://www.catalystathletics.com/exercise/725/Lat-Pulldown/ (retrieved 2026-10-22).
- S4 QMotion. *Lat Pulldown* (video). https://www.qmsu.org/qmotion/guides/video/21286/Lat-Pulldown/ (retrieved 2026-10-22; published 2025-01-28 14:29).
- S5 Jeff Nippard. *Lat Pulldown* (original auto-captions, not manually verified). https://www.youtube.com/watch?v=O94yEoGXtBY , selection 03:10–04:45.
