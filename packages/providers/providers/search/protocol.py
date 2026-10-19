"""The provider-agnostic evidence search interface.

Search populates the reviewed evidence library that grounds coaching and
reference tolerances. The default provider is ``cached`` (reviewed local
records, zero spend); the live Tavily provider is used only for
operator-triggered refresh (skills/tavily-search).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from providers.capabilities import SourceCandidate


@runtime_checkable
class SearchProvider(Protocol):
    """A source of evidence candidates for the reference library."""

    async def search(self, query: str) -> list[SourceCandidate]:
        """Discover candidate sources matching ``query``.

        Returns unreviewed :class:`~providers.capabilities.SourceCandidate`
        leads; nothing is "approved" until an operator reviews it.
        """
        ...

    async def extract(self, urls: list[str]) -> list[SourceCandidate]:
        """Extract clean content from already-known ``urls``.

        Retrieved content is untrusted data — callers strip instructions and
        scripts before storing (skills/tavily-search).
        """
        ...
