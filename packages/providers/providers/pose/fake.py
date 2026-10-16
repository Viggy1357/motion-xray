from __future__ import annotations

"""Deterministic pose double for tests and offline development.

:class:`FakePoseProvider` returns a small, fixed :class:`PoseSequence` built
from the real contract models — no randomness, no network, no ML dependency.
It never fabricates a skeleton it would pass off as real perception: the
sequence is explicitly labelled with provider ``"fake"`` so no downstream
code mistakes it for genuine MediaPipe output (AGENTS.md rule 3).
"""

from contracts.pose import PoseSequence

from providers.capabilities import PoseCapabilities

# Canonical named joints the pose pipeline requires (skills/pose-pipeline).
_REQUIRED_JOINTS = (
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)


class FakePoseProvider:
    """A deterministic :class:`PoseProvider` implementation for tests."""

    def capabilities(self) -> PoseCapabilities:
        """Return fixed capabilities mirroring a 2D+estimated-3D provider."""
        return PoseCapabilities(
            supports_2d=True,
            supports_estimated_3d=True,
            world_translation=False,
            calibration="none",
            joint_availability={name: True for name in _REQUIRED_JOINTS},
            confidence_semantics="fake-fixed",
        )

    def infer(self, video) -> PoseSequence:
        """Return a deterministic sequence header for ``video``.

        The frames artifact is a stable fake key; the header is honest about
        being a fake provider so no scoring path treats it as real data.
        """
        video_id = getattr(video, "id", "fake-video")
        return PoseSequence(
            schema_version="1",
            video_id=video_id,
            provider="fake",
            model_revision="fake-0",
            native_skeleton="fake-canonical",
            joint_mapping_version="1",
            sample_rate_hz=30.0,
            units="normalized",
            coordinate_system="image",
            capabilities={
                "supports_2d": True,
                "supports_estimated_3d": True,
                "world_translation": False,
            },
            quality_method="fake-fixed",
            frames_artifact_key=f"fake/pose/{video_id}.frames",
        )
