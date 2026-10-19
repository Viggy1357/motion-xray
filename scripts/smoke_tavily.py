"""Motion X Ray — Tavily search connectivity smoke test.

Tavily populates the reviewed evidence library on an operator-triggered refresh
(skills/tavily-search). This script proves the search path can reach the API and
prints a ranked shortlist for a lat pulldown technique query.

Safety and credit rules (this project has limited credits):
  * The key is read from the environment ONLY (TAVILY_API_KEY). No key is ever
    hardcoded (AGENTS.md).
  * The DEFAULT path is a dry-run: it prints exactly what the call WOULD be and
    makes NO network call. CI relies on this.
  * ONLY with --live does it make exactly ONE bounded search call.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

_DEMO_QUERY = "cable lat pulldown proper form elbow path torso lean coaching cues"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tavily search smoke test — dry-run by default."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Make ONE real bounded search call (spends credits). "
        "Omit for a safe dry-run that touches no network.",
    )
    return parser.parse_args(argv)


def _dry_run() -> int:
    api_key_present = bool(os.environ.get("TAVILY_API_KEY"))
    print("[smoke_tavily] DRY-RUN — no network call made.")
    print(
        "[smoke_tavily]   TAVILY_API_KEY = "
        + ("<set>" if api_key_present else "<unset>")
    )
    print("[smoke_tavily] Would call (Python SDK):")
    print("[smoke_tavily]   client = TavilyClient(api_key=TAVILY_API_KEY)")
    print(f"[smoke_tavily]   client.search(query={_DEMO_QUERY!r}, max_results=5)")
    print("[smoke_tavily] Re-run with --live to make exactly ONE real call.")
    return 0


def _why_credible(tier: str) -> str:
    """Return a short operator-facing note derived from the source tier."""
    if tier == "professional":
        return "professional source (edu/gov/journal/manufacturer/coaching org)"
    if tier == "social":
        return "social/user-generated platform — review carefully before trusting"
    return "other source — needs operator review"


def _live() -> int:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        print(
            "[smoke_tavily] LIVE aborted — missing env: TAVILY_API_KEY",
            file=sys.stderr,
        )
        return 2

    # Lazy imports so the dry-run path never requires the SDK or packages.
    from benchmarks.evidence import rank_candidates, source_tier
    from providers.search.tavily_provider import TavilySearchProvider

    provider = TavilySearchProvider(max_results=5)
    candidates = asyncio.run(provider.search(_DEMO_QUERY))  # exactly one call.
    ranked = rank_candidates(candidates)

    print("[smoke_tavily] LIVE ok — one search made.")
    print(f"[smoke_tavily]   ranked shortlist ({len(ranked)}):")
    for candidate in ranked:
        tier = source_tier(candidate.url)
        title = candidate.title or "(untitled)"
        print(f"[smoke_tavily]   - {title}")
        print(f"[smoke_tavily]       {candidate.url}")
        print(f"[smoke_tavily]       why: {_why_credible(tier)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.live:
        return _live()
    return _dry_run()


if __name__ == "__main__":
    sys.exit(main())
