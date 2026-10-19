"""Pose-domain contracts: per-joint observations, frames, and sequences.

Per AGENTS.md rule 3, a joint that could not be observed is marked
``valid=False`` (optionally interpolated with a stated method) rather than
being given a fabricated coordinate.
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Self, Tuple

from pydantic import Field, model_validator

from .base import FiniteFloat, MXRModel, SCHEMA_VERSION


class JointObservation(MXRModel):
    """One joint at one frame.

    ``xy`` and ``xyz`` are both optional: a provider may deliver 2D, 3D, or
    neither (when the joint is occluded). ``valid`` records whether this is a
    usable observation; ``interpolated`` and ``quality_method`` document how a
    filled value was produced so downstream determinism is auditable.
    """

    xy: Optional[Tuple[FiniteFloat, FiniteFloat]] = None
    xyz: Optional[Tuple[FiniteFloat, FiniteFloat, FiniteFloat]] = None
    native_quality: Optional[FiniteFloat] = None
    valid: bool
    interpolated: bool
    quality_method: Optional[str] = None

    @model_validator(mode="after")
    def observed_coordinates(self) -> Self:
        if self.valid and self.xy is None and self.xyz is None:
            raise ValueError("valid joint requires observed coordinates")
        if self.interpolated and not self.quality_method:
            raise ValueError("interpolated joint requires a quality method")
        return self


class PoseFrame(MXRModel):
    """All observed joints at a single video frame."""

    frame_index: Annotated[int, Field(ge=0)]
    timestamp_s: Annotated[FiniteFloat, Field(ge=0)]
    subject_track_id: Optional[str] = None
    joints: dict[str, JointObservation]


class PoseSequence(MXRModel):
    """Header/manifest for a pose capture over a whole video.

    The per-frame data is large and is stored out of band under
    ``frames_artifact_key``; this model is the versioned descriptor that makes
    the artifact interpretable and reproducible.
    """

    schema_version: Literal["0.2.0"] = SCHEMA_VERSION
    video_id: str
    provider: str
    model_revision: str
    native_skeleton: str
    joint_mapping_version: str
    sample_rate_hz: Annotated[FiniteFloat, Field(gt=0)]
    units: str
    coordinate_system: str
    capabilities: dict[str, bool]
    quality_method: str
    frames_artifact_key: str
