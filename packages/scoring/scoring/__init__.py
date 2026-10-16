from __future__ import annotations

"""Motion X Ray scoring — deterministic scoring against approved references.

Per-metric score: ``d = max(L - x, 0, x - U); s = 100 * max(0, 1 - d/T)``.
Scores are deterministic and never produced by an LLM (AGENTS.md rule 2); a
missing value lowers coverage rather than being fabricated (rule 3).
"""

from .core import (
    dtw_align,
    normalize_and_align,
    score_rep,
    score_set,
)

__all__ = [
    "normalize_and_align",
    "dtw_align",
    "score_rep",
    "score_set",
]
