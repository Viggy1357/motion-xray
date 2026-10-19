"""Real pose provider backed by the MediaPipe Pose Landmarker (STUB).

Primary provider for this build (DECISIONS.md D002). The MediaPipe import is
LAZY — kept inside the methods — so that importing this module (or the pose
Protocol) does NOT require the ``mediapipe`` ML dependency. Only the worker
image installs the ``providers[pose]`` extra; the api image never pulls it.

Call shape to implement (skills/pose-pipeline/SKILL.md)::

    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    base = mp_python.BaseOptions(model_asset_path=os.environ["POSE_CHECKPOINT_PATH"])
    opts = vision.PoseLandmarkerOptions(
        base_options=base,
        running_mode=vision.RunningMode.VIDEO,
        output_segmentation_masks=False,
    )
    with vision.PoseLandmarker.create_from_options(opts) as lm:
        result = lm.detect_for_video(mp_image, timestamp_ms)
        # result.pose_landmarks (normalized 2D) + result.pose_world_landmarks (3D)

Map landmarks to canonical named joints (never leak provider indices), label
interpolated samples, and keep unknown world scale unknown.
"""

from __future__ import annotations

import os

from contracts.media import VideoAsset
from contracts.pose import PoseSequence

from providers.capabilities import PoseCapabilities


class MediaPipePoseProvider:
    """Pose provider using MediaPipe Pose Landmarker (not yet implemented)."""

    def __init__(self, checkpoint_path: str | None = None) -> None:
        # Credentials/paths come from env only; no hardcoded paths or keys.
        self._checkpoint_path = checkpoint_path or os.environ.get(
            "POSE_CHECKPOINT_PATH"
        )

    def capabilities(self) -> PoseCapabilities:
        """Return MediaPipe's capabilities (2D + estimated 3D, no true scale)."""
        # TODO(T04): populate from the loaded model revision and skills notes.
        raise NotImplementedError(
            "MediaPipePoseProvider.capabilities is a scaffold stub — TODO(T04)."
        )

    def infer(self, video: VideoAsset) -> PoseSequence:
        """Run MediaPipe inference over ``video`` (lazy ML import inside)."""
        # TODO(T04): lazy-import mediapipe here so module import stays ML-free:
        #   from mediapipe.tasks import python as mp_python
        #   from mediapipe.tasks.python import vision
        raise NotImplementedError(
            "MediaPipePoseProvider.infer is a scaffold stub — TODO(T04)."
        )
