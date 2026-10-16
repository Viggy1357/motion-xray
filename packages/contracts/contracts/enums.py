from __future__ import annotations

"""Enumerations shared across Motion X Ray contracts.

All enums are ``(str, Enum)`` so they serialise to their string value in JSON
and read naturally in logs and API payloads.
"""

from enum import Enum


class CompletionStatus(str, Enum):
    """Whether a detected repetition was carried to completion."""

    COMPLETED = "completed"
    PARTIAL = "partial"
    UNCERTAIN = "uncertain"


class ReferenceType(str, Enum):
    """Provenance class of a reference profile."""

    EVIDENCE = "evidence"
    TRAINER = "trainer"
    PERSONAL = "personal"


class JobState(str, Enum):
    """Lifecycle state of an analysis job."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStage(str, Enum):
    """Pipeline stage an analysis job is currently executing."""

    VALIDATE = "validate"
    POSE = "pose"
    SEGMENT = "segment"
    METRICS = "metrics"
    COMPARE = "compare"
    COACH = "coach"


class CoachingStatus(str, Enum):
    """Whether coaching output is available for a result."""

    OK = "ok"
    UNAVAILABLE = "unavailable"
