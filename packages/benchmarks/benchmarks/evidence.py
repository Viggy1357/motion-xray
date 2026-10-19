"""Evidence discovery orchestration for the reviewed reference library.

This module turns a search provider's raw leads into DRAFT
:class:`~contracts.reference.SourceRecord` objects for the reference library.
It is deliberately conservative about spend and trust:

* :func:`discover_evidence` calls ``provider.search`` exactly once and maps the
  ranked candidates into drafts. It NEVER calls ``extract`` — per
  skills/tavily-search the escalation order is search -> extract -> map ->
  crawl -> research, and extract/crawl spend more credits, so discovery stops
  at search and an operator escalates deliberately.
* Every returned record is a DRAFT: ``review_status='pending'`` with no
  reviewer and no reviewed date. An operator reviews and approves a draft
  before it is ever used to ground coaching or tolerances. Nothing here is
  auto-approved (AGENTS.md rule 3; D007).
* All retrieved text is UNTRUSTED data — it is copied into record fields only
  and never interpreted, executed, or allowed to influence control flow.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlparse

from contracts.reference import SourceRecord

from providers.capabilities import SourceCandidate

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids import cycle at runtime
    from providers.search.protocol import SearchProvider

# Tier labels. 'professional' sources are credible technique guidance
# (education, government, peer-reviewed journals, manufacturers, known coaching
# orgs); 'social' sources are user-generated platforms; everything else is
# 'other'. A lower rank sorts first: professional < other < social.
TIER_PROFESSIONAL = "professional"
TIER_SOCIAL = "social"
TIER_OTHER = "other"

_TIER_RANK = {
    TIER_PROFESSIONAL: 0,
    TIER_OTHER: 1,
    TIER_SOCIAL: 2,
}

# Host suffixes / fragments that mark a professional source.
_PROFESSIONAL_SUFFIXES = (".edu", ".gov", ".ac.uk")
_PROFESSIONAL_FRAGMENTS = (
    "journal",
    "pubmed",
    "ncbi.nlm.nih.gov",
    "nih.gov",
    "nsca.com",
    "acsm.org",
    "strengthandconditioning",
    "lifefitness.com",
    "roguefitness.com",
    "concept2.com",
)

# Social / user-generated platform hosts.
_SOCIAL_FRAGMENTS = (
    "tiktok.com",
    "instagram.com",
    "youtube.com",
    "youtu.be",
    "facebook.com",
    "reddit.com",
    "x.com",
    "twitter.com",
)


def _host(url: str) -> str:
    """Return the lowercased netloc of ``url`` (without a leading www.)."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return ""
    return host[4:] if host.startswith("www.") else host


def source_tier(url: str) -> str:
    """Classify ``url`` into a source tier label.

    Returns ``'professional'`` for education/government/journal/manufacturer or
    known coaching-org hosts, ``'social'`` for user-generated platforms, and
    ``'other'`` otherwise.
    """
    host = _host(url)
    if not host:
        return TIER_OTHER
    if any(fragment in host for fragment in _SOCIAL_FRAGMENTS):
        return TIER_SOCIAL
    if host.endswith(_PROFESSIONAL_SUFFIXES) or any(
        fragment in host for fragment in _PROFESSIONAL_FRAGMENTS
    ):
        return TIER_PROFESSIONAL
    return TIER_OTHER


def _tier_rank(url: str) -> int:
    """Return the sort rank for ``url``'s tier (professional sorts first)."""
    return _TIER_RANK[source_tier(url)]


def rank_candidates(candidates: list[SourceCandidate]) -> list[SourceCandidate]:
    """Return ``candidates`` ordered deterministically by (tier rank, url).

    Professional sources rank above 'other', which rank above social; ties
    break on the URL string so the ordering is stable and reproducible.
    """
    return sorted(candidates, key=lambda c: (_tier_rank(c.url), c.url))


def _draft_id(exercise_id: str, url: str) -> str:
    """Return a deterministic draft id derived from exercise + url."""
    digest = hashlib.sha256(f"{exercise_id}|{url}".encode("utf-8")).hexdigest()
    return f"src-{digest[:16]}"


def _candidate_to_draft(exercise_id: str, candidate: SourceCandidate) -> SourceRecord:
    """Map one ranked candidate into a DRAFT SourceRecord (pending review)."""
    retrieved_at = candidate.retrieved_at or datetime.now(timezone.utc)
    return SourceRecord(
        id=_draft_id(exercise_id, candidate.url),
        canonical_url=candidate.url,
        # Title is required on the record; fall back to the URL if the lead had
        # none. Retrieved text is untrusted and copied verbatim only.
        title=candidate.title or candidate.url,
        publisher=candidate.publisher,
        retrieved_at=retrieved_at,
        source_tier=source_tier(candidate.url),
        relevant_claims=[],
        review_status="pending",
        reviewer=None,
        reviewed_date=None,
        reuse_terms=None,
    )


async def discover_evidence(
    exercise_id: str,
    technique_question: str,
    *,
    provider: "SearchProvider",
    max_results: int = 5,
    allowlist: Optional[list[str]] = None,
) -> list[SourceRecord]:
    """Discover DRAFT evidence sources for an exercise technique question.

    Builds a query from ``exercise_id`` + ``technique_question``, runs exactly
    one ``provider.search`` call, ranks the returned candidates by source tier,
    and maps each into a DRAFT :class:`~contracts.reference.SourceRecord`
    (``review_status='pending'``). An operator reviews and approves a draft
    before it is used — nothing returned here is approved.

    ``extract()`` is intentionally NOT called in this path to conserve credits
    (see skills/tavily-search escalation order); an operator escalates to
    extract/crawl deliberately. ``max_results`` and ``allowlist`` describe the
    intended bounds; a real provider enforces them on its own calls.
    """
    query = f"{exercise_id} {technique_question}".strip()
    candidates = await provider.search(query)
    ranked = rank_candidates(candidates)
    return [_candidate_to_draft(exercise_id, candidate) for candidate in ranked]
