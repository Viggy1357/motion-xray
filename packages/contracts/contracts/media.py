"""Media-domain contracts: the uploaded video asset and its metadata."""

from __future__ import annotations

from typing import Optional

from .base import FiniteFloat, MXRModel, UTCDateTime


class VideoAsset(MXRModel):
    """A single uploaded workout video and the facts we record about it.

    The bytes themselves live in object storage under ``storage_key``; this
    model carries only verifiable metadata (hash, dimensions, duration) so the
    pipeline can reason about the asset without touching the media.
    """

    id: str
    owner_session_id: str
    storage_key: str
    sha256: str
    mime: str
    bytes: int
    duration_s: FiniteFloat
    width: int
    height: int
    rotation: int
    timestamp_map_key: Optional[str] = None
    created_at: UTCDateTime
    expires_at: Optional[UTCDateTime] = None
