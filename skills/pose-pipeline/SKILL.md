---
name: pose-pipeline
description: |
  How Motion X Ray extracts and canonicalizes pose from video using the MediaPipe Pose
  Landmarker (primary provider for this build), behind a provider-agnostic contract so
  GEM-X can be swapped in later. Use when implementing or debugging the pose adapter,
  the canonical skeleton mapping, coordinate transforms, or quality gating.
---

# Pose pipeline (MediaPipe primary)

## What this is for

Turn a decoded video into a canonical, timestamped pose artifact that downstream
movement analysis can trust. The adapter is provider-agnostic: MediaPipe today, GEM-X
possible later. Never leak provider-specific joint indices into downstream code —
map by anatomical name.

## Provider decision

- **Primary:** MediaPipe Pose Landmarker (CPU-friendly, exposes 2D landmarks and
  world landmarks). See DECISIONS.md D002.
- **Later/stretch:** NVIDIA GEM-X (GPU, 77-joint SOMA). Reserve: MMPose RTMW3D.
- Do NOT implement three stacks by default.
- Apply D009/D010 and the relevant T19 review. rtmlib is conditional on a measured
  baseline failure; a 2D-only model cannot satisfy current 3D-required profiles.
  Validate exact checkpoint coordinates/terms before enabling estimated 3D. Keep
  verified local checkpoints; no uncontrolled runtime downloads or TLS bypasses.

## Canonical skeleton (map by anatomical name, not index)

Required named joints: left/right shoulder, elbow, wrist, hip, knee, ankle.
Derive pelvis and shoulder-midpoint explicitly from paired joints; mark as derived.
Heel/toe optional. Keep native joints separately for diagnostics; document the mapping
by name.

## Coordinates and transforms

- Image coords: normalized to width/height, x right, y down.
- Canonical camera 3D: x image-right, y up, z toward viewer, via a DOCUMENTED adapter
  transform. Record handedness, units, native frame, scale status.
- Validate the transform against a known fixture BEFORE using the 3D viewer.
- Unknown world scale stays unknown — report body-length ratios, not centimeters.
- Restore image aspect ratio before Euclidean 2D angles; preview-normalized XY is
  not an isotropic measurement plane. Static export depth is not estimated anatomy.
- Client preview mirroring MUST NOT flip anatomical left/right in stored data.

## Quality gating (never fabricate)

- Keep native confidence/visibility and the method that produced them.
- Provisional valid mask: visibility >= 0.6, >= 80% required-joint coverage per rep;
  tune on labelled clips and FREEZE by adapter version.
- Interpolate only short internal gaps <= 0.1s; LABEL interpolated samples; do NOT use
  them to create rep turnaround events. Longer gaps break segments.
- If the person track changes, critical joints disappear, or depth is unstable: suppress
  affected metrics and explain why. Do not stitch two people into one set.
- Low quality may still allow video playback without allowing an overall score.
- If conditional Norfair association is needed, carry only current matched pose
  observations into joints. Predictions, stale last detections and live-point flags
  are not proof of a current measurement. Ambiguous reacquisition yields a gap.
- Resolve the PoseSequence manifest through a validated frame reader; preserve raw
  observations separately from timestamped filtered signals. Perception provenance
  does not imply bit-identical inference across hardware.

## Timing discipline

- Target 30 Hz analysis sampling; record the ACTUAL rate.
- Preserve a timestamp map from each sample to the proxy/source timeline.
- For variable-frame-rate clips, never use frame_index / nominal_fps as the sole time
  source. Derivatives use real seconds.

## Minimal call shape (MediaPipe Tasks, Python)

```python
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

base = mp_python.BaseOptions(model_asset_path=os.environ["POSE_CHECKPOINT_PATH"])
opts = vision.PoseLandmarkerOptions(
    base_options=base,
    running_mode=vision.RunningMode.VIDEO,  # per-frame with timestamps
    output_segmentation_masks=False,
)
with vision.PoseLandmarker.create_from_options(opts) as lm:
    # for each decoded frame at timestamp_ms:
    result = lm.detect_for_video(mp_image, timestamp_ms)
    # result.pose_landmarks (normalized 2D) and result.pose_world_landmarks (metric 3D)
```

Run inference in a worker, not the UI thread (synchronous inference can block).

## Gate A checklist (prove it works once)

20 October T04 local pose checkpoint is recorded in
`docs/audit/T04-resumed-pose-batch.md` and `T04-pose-results-2026-10-20.json` in the
same audit directory. Mapping/artifacts/adapter and diagnostic playback are delivered;
131 tests pass. Reuse that evidence instead of restarting the feasibility scaffold.
Identity remains unverified and depth is estimated; later measurements still need
quality/calibration gates. T01's separate runtime coaching proof remains open.

- [ ] Extract timestamped 2D + world landmarks from the authorized lat-pulldown
  segment first (D005); record its offset within the 55s source clip.
- [ ] Map to canonical named joints; verify correct anatomical left/right.
- [ ] Render a simple skeleton; confirm synchronized playback against the video clock.
- [ ] Record model revision, cold/warm runtime, peak memory, artifact size → DECISIONS.md.
- [ ] Validate the coordinate transform against a known-geometry fixture.
