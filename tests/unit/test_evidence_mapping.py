"""Unit tests for discover_evidence candidate->draft mapping (no network).

Discovery must return only DRAFT source records (review_status='pending') with
a source_tier set; nothing is auto-approved. The async function is driven with
the deterministic FakeSearchProvider via dependency injection — no network, no
tavily SDK import.
"""

from __future__ import annotations

import asyncio

from benchmarks.evidence import discover_evidence

from providers.search.fake import FakeSearchProvider


def test_discover_returns_only_pending_drafts() -> None:
    """Every returned record is a pending draft with a tier and no reviewer."""
    drafts = asyncio.run(
        discover_evidence(
            "lat_pulldown",
            "elbow path and torso lean coaching cues",
            provider=FakeSearchProvider(),
        )
    )

    assert drafts, "expected at least one draft from the fake provider"
    for record in drafts:
        assert record.review_status == "pending"
        assert record.source_tier
        assert record.reviewer is None
        assert record.reviewed_date is None


def test_discover_ranks_professional_before_social() -> None:
    """The fake shortlist's professional source maps ahead of the social one."""
    drafts = asyncio.run(
        discover_evidence(
            "lat_pulldown",
            "technique",
            provider=FakeSearchProvider(),
        )
    )
    tiers = [record.source_tier for record in drafts]
    # professional entries precede the social entry in the ranked output.
    assert tiers.index("professional") < tiers.index("social")


def test_draft_ids_are_deterministic() -> None:
    """Running discovery twice yields identical draft ids (determinism)."""
    first = asyncio.run(
        discover_evidence("lat_pulldown", "q", provider=FakeSearchProvider())
    )
    second = asyncio.run(
        discover_evidence("lat_pulldown", "q", provider=FakeSearchProvider())
    )
    assert [r.id for r in first] == [r.id for r in second]
