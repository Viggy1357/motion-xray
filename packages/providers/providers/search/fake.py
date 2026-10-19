"""Deterministic search double for tests and offline development.

:class:`FakeSearchProvider` mirrors :class:`~providers.pose.fake.FakePoseProvider`:
it returns a small, fixed list of :class:`~providers.capabilities.SourceCandidate`
objects with no randomness, no network, and no SDK import. The fixed shortlist
deliberately spans a professional-domain source and a social-domain source so
ranking/mapping tests can assert tier ordering without ever spending credits.
"""

from __future__ import annotations

from datetime import datetime, timezone

from providers.capabilities import SourceCandidate

# A fixed retrieval instant so candidates are byte-for-byte deterministic.
_FIXED_RETRIEVED_AT = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

# Canonical shortlist: one professional (manufacturer/.edu) and one social
# (youtube) URL, plus an 'other' domain, so tier ordering is observable.
_FIXED_CANDIDATES = (
    SourceCandidate(
        url="https://www.lifefitness.com/en-us/cable-lat-pulldown-guide",
        title="Cable Lat Pulldown — Setup and Form",
        publisher="lifefitness.com",
        snippet="Keep the torso near-upright and drive the elbows down.",
        retrieved_at=_FIXED_RETRIEVED_AT,
    ),
    SourceCandidate(
        url="https://kinesiology.university.edu/lat-pulldown-mechanics",
        title="Lat Pulldown Mechanics",
        publisher="university.edu",
        snippet="Scapular depression precedes elbow flexion through the pull.",
        retrieved_at=_FIXED_RETRIEVED_AT,
    ),
    SourceCandidate(
        url="https://www.youtube.com/watch?v=latpulldownform",
        title="Lat Pulldown Form Tips",
        publisher="youtube.com",
        snippet="A short cue video on lat pulldown elbow path.",
        retrieved_at=_FIXED_RETRIEVED_AT,
    ),
)


class FakeSearchProvider:
    """A deterministic :class:`SearchProvider` implementation for tests."""

    async def search(self, query: str) -> list[SourceCandidate]:
        """Return the fixed deterministic candidate shortlist (no network)."""
        return list(_FIXED_CANDIDATES)

    async def extract(self, urls: list[str]) -> list[SourceCandidate]:
        """Return deterministic candidates for the requested ``urls``."""
        return [
            SourceCandidate(
                url=url,
                title="Extracted page",
                publisher=None,
                snippet="Deterministic fake extracted content.",
                retrieved_at=_FIXED_RETRIEVED_AT,
            )
            for url in urls
        ]
