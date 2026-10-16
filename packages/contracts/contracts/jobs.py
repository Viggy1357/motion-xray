from __future__ import annotations

"""Jobs-domain contract: the analysis job and its lease/retry bookkeeping."""

from typing import Optional

from .base import MXRModel, UTCDateTime
from .enums import JobStage, JobState


class AnalysisJob(MXRModel):
    """One unit of pipeline work with its state, stage, and lease.

    ``lease_owner``/``lease_until`` support at-most-one-worker processing;
    ``input_hash`` and ``version_hash`` make runs reproducible and cacheable;
    ``error`` is populated only on a failed state.
    """

    id: str
    owner: str
    state: JobState
    stage: JobStage
    attempt: int
    lease_owner: Optional[str] = None
    lease_until: Optional[UTCDateTime] = None
    cancel_requested: bool
    input_hash: str
    version_hash: str
    created_at: UTCDateTime
    updated_at: UTCDateTime
    error: Optional[str] = None
    result_key: Optional[str] = None
