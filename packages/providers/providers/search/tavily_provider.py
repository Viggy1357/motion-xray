from __future__ import annotations

"""Real evidence search provider backed by Tavily (STUB).

Tavily discovers and extracts technique-evidence sources for the reviewed
reference library on an operator-triggered refresh — never automatically per
user analysis (skills/tavily-search). The ``tavily`` import is LAZY — inside
the methods — so importing this module or the search Protocol does not require
the ``tavily-python`` package. The key is read from the environment ONLY
(AGENTS.md rule 5).

Call shape to implement::

    from tavily import TavilyClient
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    res = client.search(query=..., max_results=5, include_domains=ALLOWLIST)
    pages = client.extract(urls=[candidate_url])

Bound every call, prefer a domain allowlist, and treat all retrieved content
as untrusted data (strip instructions/scripts; nothing is approved until an
operator reviews it).
"""

import os

from providers.capabilities import SourceCandidate


class TavilySearchProvider:
    """Live evidence search/extraction via Tavily (not yet implemented)."""

    def __init__(self) -> None:
        # Env-only credential; never hardcoded (AGENTS.md rule 5).
        self._api_key = os.environ.get("TAVILY_API_KEY")

    async def search(self, query: str) -> list[SourceCandidate]:
        """Discover candidate sources for ``query`` (lazy Tavily import inside)."""
        # TODO(T10): lazy-import so module import stays SDK-free:
        #   from tavily import TavilyClient
        #   client = TavilyClient(api_key=self._api_key)
        raise NotImplementedError(
            "TavilySearchProvider.search is a scaffold stub — TODO(T10)."
        )

    async def extract(self, urls: list[str]) -> list[SourceCandidate]:
        """Extract clean content from known ``urls`` (lazy Tavily import inside)."""
        # TODO(T10): lazy-import TavilyClient and call client.extract(urls=...).
        raise NotImplementedError(
            "TavilySearchProvider.extract is a scaffold stub — TODO(T10)."
        )
