"""Reference-domain contracts: approved reference profiles and their sources.

A :class:`ReferenceProfile` is the versioned, human-approved target a user's
movement is compared against; :class:`SourceRecord` captures the vetted,
reviewable provenance behind it (AGENTS.md rules 5 and 6).
"""

from __future__ import annotations

from typing import List, Optional

from .base import MXRModel, UTCDateTime
from .enums import ReferenceType


class ReferenceProfile(MXRModel):
    """A versioned, approved reference for one exercise/variant/view."""

    id: str
    version: str
    type: ReferenceType
    scope: str
    exercise: str
    variant: Optional[str] = None
    view: Optional[str] = None
    provider_compatibility: List[str] = []
    approved_by: Optional[str] = None
    approved_date: Optional[UTCDateTime] = None
    source_ids: List[str] = []
    pose_key: Optional[str] = None
    metric_rules: dict[str, dict] = {}
    approval_status: str


class SourceRecord(MXRModel):
    """A single reviewable source backing one or more reference profiles."""

    id: str
    canonical_url: str
    title: str
    publisher: Optional[str] = None
    retrieved_at: UTCDateTime
    source_tier: str
    relevant_claims: List[str] = []
    review_status: str
    reviewer: Optional[str] = None
    reviewed_date: Optional[UTCDateTime] = None
    reuse_terms: Optional[str] = None
