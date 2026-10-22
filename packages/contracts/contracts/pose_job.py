"""Private artifact contract for a pose-only analysis job.

This module defines the input and artifact models for the pose pipeline.
It intentionally does not construct reports or process bytes; parent
consumers validate identity/hash/path relationships against actual bytes.
"""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .analysis import AnalysisResult
from .pose import PoseSequence
from .base import MXRModel
from .enums import CoachingStatus, JobState
from .jobs import AnalysisJob
from .media import VideoAsset
from .proxy import ProxyTimestampMap


class PoseJobInput(MXRModel):
    """Validated input bundle for a pose-only job."""

    job: AnalysisJob
    video: VideoAsset
    exercise_id: str
    variant: str

    @model_validator(mode="after")
    def valid_pose_job_input(self) -> Self:
        if self.job.state != JobState.RUNNING:
            raise ValueError("job.state must be RUNNING")
        if self.job.lease_owner is None:
            raise ValueError("job.lease_owner must be set")
        if self.job.owner != self.video.owner_session_id:
            raise ValueError("job.owner must match video.owner_session_id")
        if self.job.input_hash != self.video.sha256:
            raise ValueError("job.input_hash must match video.sha256")
        if not (0 < self.video.duration_s <= 60):
            raise ValueError("video.duration_s must be in (0, 60]")
        return self


class PoseJobArtifacts(MXRModel):
    """Artifacts produced by a pose-only job.

    ``pose`` and ``proxy`` are the actual typed headers; ``report`` is a
    pose-only partial report whose deterministic fields are empty and whose coaching
    status is explicitly unavailable.
    """

    format_version: Literal["pose-job-v1"] = "pose-job-v1"
    request_sha256: Annotated[str, Field(pattern="^[0-9a-f]{64}$")]
    pose: PoseSequence
    proxy: ProxyTimestampMap
    report: AnalysisResult

    @model_validator(mode="after")
    def pose_only_report(self) -> Self:
        r = self.report
        if r.reps or r.metrics or r.source_ids:
            raise ValueError("pose-only report must have empty reps/metrics/source_ids")
        if r.score is not None or r.best_rep_id is not None or r.worst_rep_id is not None:
            raise ValueError("pose-only report must have null score/best_rep_id/worst_rep_id")
        if "POSE_ONLY" not in r.warnings:
            raise ValueError("pose-only report must include 'POSE_ONLY' in warnings")
        if r.coaching is None:
            raise ValueError("pose-only report coaching must be present")
        if r.coaching.status != CoachingStatus.UNAVAILABLE:
            raise ValueError("pose-only report coaching.status must be UNAVAILABLE")
        if r.coaching.summary is not None or r.coaching.next_set_cue is not None:
            raise ValueError("pose-only report coaching summary/next_set_cue must be None")
        if r.coaching.observations:
            raise ValueError("pose-only report coaching.observations must be empty")
        return self
