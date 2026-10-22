# Posture benchmark workflow — current owner direction

22 October 2026. T05/T06/T07; FR05/FR07/FR08/FR11/FR12.
Supersedes the ten-rep acceptance target and segmentation-first ordering in earlier
feedback notes. This is the active workflow for the lat-pulldown proof.

## Goal and acceptance

Demonstrate exercise-specific posture measurement and explainable reference-based
scoring. **More than five usable user repetitions (at least six) suffice for the
first proof.** Exact recovery of all ten is not a gate. Repetition boundaries support
measurement; rep counting is not the product's main feature. A detected interval must
still correspond to the movement being measured: do not accept merged cycles merely
to meet the sample count. Show exclusions and analysed coverage; do not imply the
unanalysed repetitions were assessed or select only the best-looking repetitions.

Detailed timestamped guidance, highlights of deviations and missed observations are
the next feature after measurement/scoring proof. Measurement availability/reasons
remain necessary now so missing information cannot create a misleading score.

## 0. Existing resources first

Inspect the existing reuse screen, integration review, local code and available
upstream artifacts for the specific gap before expanding web discovery. Assess fit,
limitations, evidence and reuse terms explicitly; listing a repo is not adopting it.
Prior reviews are dated source assessments, not current runtime benchmarks.

| Existing lead | Useful for this workflow | What it does not establish | Current action |
| --- | --- | --- | --- |
| Sports2D | Joint-angle definitions, filtering and diagnostic comparison methods | Reliable cross-view3D or correct lat-pulldown tolerances | Consult reviewed methods before new geometry work; test any adoption |
| Good-GYM | Segmenting usable movement cycles | A validated lat-pulldown posture rubric | Secondary helper; avoid counter-first work |
| DTAIDistance | Aligning reference/user movement with tempo differences | Technique criteria, component weights or score calibration | Reuse only if alignment needs it and kernel checks pass |
| AIFit/Fit3D | Reference selection, deviation evaluation, possible labelled evaluation data | A verified accessible/licensed lat-pulldown benchmark in this checkout | Check exercise inventory, labels, skeleton mapping and terms before data adoption |
| ALEX/other screened learned assessors | Assessment/evaluation research | A compatible pretrained assessor for our footage | Defer unless a specific documented gap warrants a narrow check |

Evidence: `../REUSE-SCREEN-2026-10-19.md` and
`../INTEGRATION-REVIEW-2026-10-20.md`. No new dependency or dataset approved here.

## 1. Consolidate roughly five credible technique sources

Build a source-to-criterion matrix, then one exercise rubric. Existing leads to
verify/consolidate first: ACE, NASM, Jeff Nippard, QMotion and Catalyst. They are a
shortlist, not five completed or equally weighted evidence reviews. NSCA is a reserve
lead; its earlier snippet-only evidence needs full-content verification before use.
Use full text or original video with time references; do not treat repeated versions
of the same source as independent agreement. Use existing retrieved evidence first,
then targeted official-source searches for missing or conflicting guidance.

For every criterion record: source/location, exercise/grip/variant, agreement and
disagreement, cue, proposed observable, importance rationale, camera requirements,
implementation status and unresolved assumptions. Preserve disagreements and variant
differences rather than averaging conflicting cues into one universal rule.

Candidate inventory to confirm through that review: starting torso inclination;
torso excursion/stability during pulling; elbow and upper-arm/torso motion and range;
bar endpoint relative to chest; top/return extension; and tempo/control as a separate
component. These are candidates, not an exhaustive validated rubric. Map each agreed
criterion to measurable, conditional/proxy, or presently unobservable. A shoulder/hip
axis does not measure spinal curvature; wrist position is not confirmed bar contact.

Deliverable: a single sourced metric matrix and consolidated lat-pulldown rubric.
Each metric has a definition, units, direction, phase and uncertainty/visibility rule.

## 2. Calibrate against two or three reference demonstrations

Start with the existing QMotion corrected section, IMSA and Catalyst; preserve owner
preference for QMotion and exclude deliberately incorrect examples and camera cuts.
Identify variant/view differences and review selected movement phases. Measure the
rubric's observables, manually check landmarks/angles and retain source timestamps.
Record source-wise values before consolidation; never fuse unmatched camera-plane
angles into one distribution or use pose-model confidence as accuracy evidence.

Per metric, distinguish **observed demo range**, measurement uncertainty and
**provisional scoring tolerance**. A two/three-video min/max is not a population-wide
acceptable range. If a source supplies only a qualitative cue, record how a proposed
numeric operationalization will be tested; do not attribute invented degrees to it.
Some metrics may remain unavailable pending camera or object-tracking support.

Deliverable: reference metric profiles, checked sample frames, compatibility rules
and a versioned provisional benchmark specification. Freeze selection, tolerances,
weights and scoring response before evaluating the user result. Keep historical
experimental configurations unchanged; a new policy requires a new version/fixtures.

## 3. Apply to user footage and prove the score

Select at least six usable real repetitions using declared quality/coverage rules,
not agreement with the reference. Enough footage must be extracted to find them;
processing the entire set or recovering all ten is optional for this first proof.
Respect bounded diagnostic processing and reconcile chunk overlaps if used.

Measure the same compatible components; retain torso movement when normalizing
position/scale. Report per-rep raw values, deviations, component scores, uncertainty
and excluded quantities. Keep tempo separate from posture. The180-degree agreement
formula is historical experimental arithmetic, not the new benchmark policy.

Define each score response from reviewed tolerances and component importance, with
sensitivity checks. An aggregate needs explicit required components and sufficient
coverage; unavailable measurements are not zero or automatically good. If coverage
cannot support an overall result, show the available components and an unavailable
aggregate. Do not label a high arm-angle agreement as overall good technique when a
required torso/bar criterion was not observed. This is reference-based assessment,
not a claim of universal correctness or safety.

Deliverable: reviewable posture/scoring proof on at least six reps, including examples
where the score responds to visible posture differences and cases it cannot assess.
Validate on separate footage before claiming generalization beyond the pilot.

## 4. Guidance afterwards; reference3D later

Once the measurement/scoring proof works, turn deterministic deviations into specific
timestamped highlights and helpful improvement guidance. LLMs explain measured evidence;
they do not determine joint angles or invent scores. Other UI/infrastructure/hosting
and exercise expansion remain held behind the core proof.

The owner's multi-angle idea concerns **reference videos**, not user multi-camera
capture. A reference-derived3D benchmark is a distant future feature. No synchronized
user capture, triangulation implementation or new recording request belongs in this
pass. Preserve current view compatibility limits rather than silently solving this
through an unvalidated reconstruction.
