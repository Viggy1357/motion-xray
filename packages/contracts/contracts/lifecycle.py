"""Lifecycle-domain contract: public analysis request and status.

These models are intentionally separate from the internal job model in
:mod:`contracts.jobs`.  Callers can request an analysis and poll for status
without ever seeing worker-fencing fields such as ``lease_owner`` or
``result_key``.
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional

from pydantic import StringConstraints

from .base import MXRModel
from .jobs import AnalysisJob

VideoId = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{32}$")]
ExerciseId = Literal["lat_pulldown", "squat", "dumbbell_curl", "lateral_raise"]
RequestKey = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9._:-]+$", min_length=1, max_length=128)]
Variant = Annotated[str, StringConstraints(min_length=1, max_length=64)]


class AnalysisCreateRequest(MXRModel):
    """Public request to create a new analysis job."""

    video_id: VideoId
    exercise_id: ExerciseId
    variant: Optional[Variant] = None
    request_key: RequestKey


class AnalysisStatus(AnalysisJob):
    """Public view of an analysis job.

    This is an additive subclass of :class:`AnalysisJob`.  Worker-only fencing
    and storage fields are always nulled so they are never exposed through the
    public API, while every other field is inherited unchanged.
    """

    analysis_scope: Literal["pose_only"] = "pose_only"
    lease_owner: None = None
    result_key: None = None

    @classmethod
    def from_job(cls, job: AnalysisJob) -> "AnalysisStatus":
        """Build a public status view from an internal ``AnalysisJob``."""
        data = job.model_dump()
        data["lease_owner"] = None
        data["result_key"] = None
        return cls.model_validate(data)
