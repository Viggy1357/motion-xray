from __future__ import annotations

"""Shared provider capability and candidate models.

:class:`PoseCapabilities` lets downstream code reason about what a pose
provider can and cannot deliver (e.g. MediaPipe exposes estimated 3D world
landmarks but no true metric scale), so benchmarks can refuse incompatible
comparisons instead of fabricating them (AGENTS.md rule 3).

:class:`SourceCandidate` is the lightweight record a search provider returns
before an operator reviews and promotes it to an approved
``contracts.reference.SourceRecord``.
"""

from typing import Optional

from contracts.base import MXRModel, UTCDateTime


class PoseCapabilities(MXRModel):
    """What a pose provider can deliver, so consumers never assume more.

    Fields are intentionally descriptive rather than prescriptive: a provider
    declares its honest capabilities and downstream scoring/benchmarks decide
    whether a given comparison is supportable.
    """

    supports_2d: bool
    supports_estimated_3d: bool
    world_translation: bool
    calibration: Optional[str] = None
    joint_availability: dict[str, bool] = {}
    confidence_semantics: Optional[str] = None


class SourceCandidate(MXRModel):
    """An unreviewed evidence candidate discovered or extracted by search.

    This is a research lead, not an approved source — all retrieved content is
    untrusted data until an operator reviews it (see skills/tavily-search).
    """

    url: str
    title: Optional[str] = None
    publisher: Optional[str] = None
    snippet: Optional[str] = None
    retrieved_at: Optional[UTCDateTime] = None
