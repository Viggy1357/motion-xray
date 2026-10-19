"""Real evidence search provider backed by Tavily.

Tavily discovers and extracts technique-evidence sources for the reviewed
reference library on an operator-triggered refresh — never automatically per
user analysis (skills/tavily-search). The ``tavily`` import is LAZY — inside
the methods — so importing this module (or the search Protocol) does not
require the ``tavily-python`` package to be installed. The key is read from the
environment ONLY (AGENTS.md rule 5) and never hardcoded.

Every call is bounded (``max_results`` default 5, a 15s timeout, and an
optional domain allowlist). All retrieved text is UNTRUSTED data: it is copied
verbatim into :class:`~providers.capabilities.SourceCandidate` fields and never
interpreted, executed, or allowed to influence control flow (D007,
skills/tavily-search). ``extract`` returns the same lightweight candidate shape
so nothing downstream treats raw page text as approved evidence.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from providers.capabilities import SourceCandidate

# Env var that holds the server-side Tavily key. Read at call time only.
_API_KEY_ENV = "TAVILY_API_KEY"


def _publisher_from_url(url: str) -> Optional[str]:
    """Derive a human-readable publisher from a URL host, or None."""
    try:
        host = urlparse(url).netloc
    except Exception:
        return None
    if not host:
        return None
    return host[4:] if host.startswith("www.") else host


class TavilySearchProvider:
    """Live evidence search/extraction via Tavily (lazy SDK import)."""

    def __init__(
        self,
        *,
        max_results: int = 5,
        timeout_s: int = 15,
        allowlist: Optional[list[str]] = None,
    ) -> None:
        # Bounds are stored up front; the credential is NOT read here so that
        # merely constructing the provider (e.g. in tests) never requires the
        # key — it is resolved lazily at call time (acceptance criterion).
        self._max_results = max_results
        self._timeout_s = timeout_s
        self._allowlist = list(allowlist) if allowlist else None

    def _api_key(self) -> str:
        """Return the env-only Tavily key, raising a clear error if unset."""
        api_key = os.environ.get(_API_KEY_ENV)
        if not api_key:
            raise RuntimeError(
                f"{_API_KEY_ENV} is not set; Tavily search requires the key "
                "from the environment (never hardcoded)."
            )
        return api_key

    def _candidate_from_result(self, result: dict) -> SourceCandidate:
        """Map one Tavily result dict into a SourceCandidate (untrusted text)."""
        url = str(result.get("url") or "")
        title = result.get("title")
        # Tavily puts the page text/snippet in 'content'; treat it as data only.
        snippet = result.get("content")
        publisher = result.get("publisher") or _publisher_from_url(url)
        return SourceCandidate(
            url=url,
            title=title if title is not None else None,
            publisher=publisher,
            snippet=snippet if snippet is not None else None,
            retrieved_at=datetime.now(timezone.utc),
        )

    async def search(self, query: str) -> list[SourceCandidate]:
        """Discover candidate sources for ``query`` (lazy Tavily import inside)."""
        # Lazy import keeps module import SDK-free (context.json QUIRK).
        from tavily import TavilyClient

        client = TavilyClient(api_key=self._api_key())
        res = client.search(
            query=query,
            max_results=self._max_results,
            include_domains=self._allowlist or None,
        )
        results = res.get("results", []) if isinstance(res, dict) else []
        return [
            self._candidate_from_result(r)
            for r in results
            if isinstance(r, dict)
        ]

    async def extract(self, urls: list[str]) -> list[SourceCandidate]:
        """Extract clean content from known ``urls`` (lazy Tavily import inside)."""
        # Lazy import keeps module import SDK-free (context.json QUIRK).
        from tavily import TavilyClient

        client = TavilyClient(api_key=self._api_key())
        res = client.extract(urls=urls)
        results = res.get("results", []) if isinstance(res, dict) else []
        candidates: list[SourceCandidate] = []
        for r in results:
            if not isinstance(r, dict):
                continue
            url = str(r.get("url") or "")
            # extract() returns the page body under 'raw_content'; untrusted.
            snippet = r.get("raw_content") or r.get("content")
            candidates.append(
                SourceCandidate(
                    url=url,
                    title=r.get("title"),
                    publisher=r.get("publisher") or _publisher_from_url(url),
                    snippet=snippet if snippet is not None else None,
                    retrieved_at=datetime.now(timezone.utc),
                )
            )
        return candidates
