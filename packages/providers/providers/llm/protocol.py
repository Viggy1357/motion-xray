"""The provider-agnostic coaching LLM interface.

The ONLY runtime LLM job in Motion X Ray is coaching: turning validated,
deterministic measurements into a few grounded observations. The model never
sees raw video, never produces scores, and never invents numbers
(skills/nebius-token-factory; AGENTS.md rule 2).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from contracts.analysis import CoachingResult


@runtime_checkable
class LLMProvider(Protocol):
    """A grounded coaching provider over structured deterministic evidence."""

    async def coach(self, evidence: Any) -> CoachingResult:
        """Produce grounded coaching for ``evidence`` (structured metrics).

        ``evidence`` is the small, pre-validated bundle of selected
        exercise/reference, metrics, deviations, rep intervals and approved
        claims — never raw video or full pose arrays. On any failure the
        implementation returns a :class:`~contracts.analysis.CoachingResult`
        with ``status=unavailable`` rather than fabricating observations.
        """
        ...
