from __future__ import annotations

"""Cached, offline evidence search double (the default provider).

:class:`CachedSearchProvider` reads reviewed local JSON records from
``data/references`` and returns them as
:class:`~providers.capabilities.SourceCandidate` objects. It makes NO network
call, so normal traffic spends zero Tavily credits (skills/tavily-search:
"Default to SEARCH_PROVIDER=cached"). This is a structure scaffold: the parse
logic is deferred.
"""

import os

from providers.capabilities import SourceCandidate

# Default location of reviewed local source records (relative to repo root).
_DEFAULT_REFERENCES_DIR = os.path.join("data", "references")


class CachedSearchProvider:
    """A :class:`SearchProvider` backed by reviewed local JSON records."""

    def __init__(self, references_dir: str | None = None) -> None:
        self._references_dir = references_dir or _DEFAULT_REFERENCES_DIR

    async def search(self, query: str) -> list[SourceCandidate]:
        """Return cached candidates matching ``query`` from local records.

        Reads reviewed JSON under ``references_dir`` and parses each into a
        :class:`SourceCandidate`; no network call is ever made.
        """
        # TODO(T10): load + filter the reviewed local JSON records (no network).
        raise NotImplementedError(
            "CachedSearchProvider.search is a scaffold stub — TODO(T10)."
        )

    async def extract(self, urls: list[str]) -> list[SourceCandidate]:
        """Return cached candidates for known ``urls`` from local records."""
        # TODO(T10): resolve each URL against the reviewed local records.
        raise NotImplementedError(
            "CachedSearchProvider.extract is a scaffold stub — TODO(T10)."
        )
