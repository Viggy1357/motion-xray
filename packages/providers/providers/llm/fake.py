from __future__ import annotations

"""Deterministic coaching LLM double for tests and offline development.

:class:`FakeLLMProvider` returns a fixed, valid
:class:`~contracts.analysis.CoachingResult` with ``status=ok`` — no network,
no SDK, no credit spend. CI uses this instead of a live Nebius call
(skills/nebius-token-factory: "CI never spends").
"""

from typing import Any

from contracts.analysis import CoachingResult
from contracts.enums import CoachingStatus


class FakeLLMProvider:
    """A canned :class:`LLMProvider` implementation for tests."""

    async def coach(self, evidence: Any) -> CoachingResult:
        """Return a fixed, valid coaching result independent of ``evidence``."""
        return CoachingResult(
            status=CoachingStatus.ok,
            summary="Fake coaching summary for deterministic tests.",
            observations=[
                "Fake observation: elbow path stayed consistent across reps.",
            ],
            next_set_cue="Keep upper arms still on the next set.",
            limitations=["Fake double — not generated from real measurements."],
        )
