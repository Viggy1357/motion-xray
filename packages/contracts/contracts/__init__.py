from __future__ import annotations

"""Motion X Ray contracts — the Pydantic v2 schema source of truth.

Import public models and enums from this package root, e.g.::

    from contracts import AnalysisResult, JobState
"""

from .analysis import (
    AnalysisResult,
    CoachingResult,
    Metric,
    Rep,
)
from .base import MXRModel, ensure_finite_float, ensure_utc
from .enums import (
    CoachingStatus,
    CompletionStatus,
    JobStage,
    JobState,
    ReferenceType,
)
from .jobs import AnalysisJob
from .media import VideoAsset
from .pose import JointObservation, PoseFrame, PoseSequence
from .reference import ReferenceProfile, SourceRecord
from .scoring import ScoreBreakdown

__all__ = [
    # base
    "MXRModel",
    "ensure_utc",
    "ensure_finite_float",
    # enums
    "CompletionStatus",
    "ReferenceType",
    "JobState",
    "JobStage",
    "CoachingStatus",
    # media
    "VideoAsset",
    # pose
    "JointObservation",
    "PoseFrame",
    "PoseSequence",
    # analysis
    "Rep",
    "Metric",
    "CoachingResult",
    "AnalysisResult",
    # reference
    "ReferenceProfile",
    "SourceRecord",
    # scoring
    "ScoreBreakdown",
    # jobs
    "AnalysisJob",
]
