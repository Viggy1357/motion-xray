"""Cached, offline evidence search double (the default provider).

:class:`CachedSearchProvider` reads reviewed local JSON records from
``data/references`` and returns them as
:class:`~providers.capabilities.SourceCandidate` objects. It makes NO network
call, so normal traffic spends zero Tavily credits (skills/tavily-search:
"Default to SEARCH_PROVIDER=cached"). When no reviewed records exist yet it
returns an empty shortlist — an honest "nothing cached" rather than an error.
"""

from __future__ import annotations

import json
import os

from providers.capabilities import SourceCandidate

# Default location of reviewed local source records (relative to repo root).
_DEFAULT_REFERENCES_DIR = os.path.join("data", "references")


class CachedSearchProvider:
    """A :class:`SearchProvider` backed by reviewed local JSON records."""

    def __init__(self, references_dir: str | None = None) -> None:
        self._references_dir = references_dir or _DEFAULT_REFERENCES_DIR

    def _load_candidates(self) -> list[SourceCandidate]:
        """Parse every reviewed JSON source record into a candidate (no network).

        A missing directory simply yields no candidates; malformed files are
        skipped rather than fabricated into leads (AGENTS.md rule 3).
        """
        candidates: list[SourceCandidate] = []
        if not os.path.isdir(self._references_dir):
            return candidates
        for name in sorted(os.listdir(self._references_dir)):
            if not name.endswith(".json"):
                continue
            path = os.path.join(self._references_dir, name)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except (OSError, ValueError):
                continue
            if not isinstance(data, dict):
                continue
            url = data.get("canonical_url") or data.get("url")
            if not url:
                continue
            candidates.append(
                SourceCandidate(
                    url=url,
                    title=data.get("title"),
                    publisher=data.get("publisher"),
                    snippet=data.get("snippet"),
                    retrieved_at=data.get("retrieved_at"),
                )
            )
        return candidates

    async def search(self, query: str) -> list[SourceCandidate]:
        """Return cached candidates from local records; never calls the network."""
        return self._load_candidates()

    async def extract(self, urls: list[str]) -> list[SourceCandidate]:
        """Return cached candidates whose URL is in ``urls`` (no network)."""
        wanted = set(urls)
        return [c for c in self._load_candidates() if c.url in wanted]
