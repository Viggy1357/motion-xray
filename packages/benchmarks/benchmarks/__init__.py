"""Motion X Ray benchmarks — reference profiles and compatibility gating.

Loads approved reference profiles and checks whether a pose provider's
capabilities are sufficient to score against them, so no unsupportable
comparison is ever run (AGENTS.md rule 3).
"""

from __future__ import annotations

from .core import check_reference_compatibility, load_reference_profile

__all__ = [
    "check_reference_compatibility",
    "load_reference_profile",
]
