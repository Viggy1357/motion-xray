"""Unit tests for the deterministic source-tier ranker (no network, no SDK).

``rank_candidates`` must deterministically place a professional/manufacturer
domain above a social-platform domain so an operator reviews the most credible
leads first. These tests use inline SourceCandidate objects and never touch the
network or import the tavily SDK.
"""

from __future__ import annotations

from datetime import datetime, timezone

from benchmarks.evidence import TIER_PROFESSIONAL, TIER_SOCIAL, rank_candidates, source_tier

from providers.capabilities import SourceCandidate

_WHEN = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _candidate(url: str) -> SourceCandidate:
    return SourceCandidate(url=url, title="t", publisher=None, snippet=None, retrieved_at=_WHEN)


def test_professional_sorts_before_social() -> None:
    """A manufacturer/.edu source ranks ahead of a social-platform source."""
    social = _candidate("https://www.tiktok.com/@user/video/123")
    professional = _candidate("https://kinesiology.university.edu/lat-pulldown")

    ranked = rank_candidates([social, professional])

    assert ranked[0].url == professional.url
    assert ranked[-1].url == social.url


def test_source_tier_classification() -> None:
    """Hosts map to the expected tier labels."""
    assert source_tier("https://www.lifefitness.com/guide") == TIER_PROFESSIONAL
    assert source_tier("https://example.edu/paper") == TIER_PROFESSIONAL
    assert source_tier("https://www.instagram.com/p/abc") == TIER_SOCIAL
    assert source_tier("https://youtu.be/abc") == TIER_SOCIAL


def test_ranking_is_deterministic() -> None:
    """Ranking the same candidates twice yields identical order."""
    candidates = [
        _candidate("https://www.youtube.com/watch?v=b"),
        _candidate("https://acsm.org/pulldown"),
        _candidate("https://randomblog.example/post"),
    ]
    first = [c.url for c in rank_candidates(candidates)]
    second = [c.url for c in rank_candidates(candidates)]
    assert first == second
    # professional first, other in the middle, social last.
    assert first[0] == "https://acsm.org/pulldown"
    assert first[-1] == "https://www.youtube.com/watch?v=b"
