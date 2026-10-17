from __future__ import annotations

"""Motion X Ray — Tavily search connectivity smoke test.

Tavily populates the reviewed evidence library on an operator-triggered refresh
(skills/tavily-search). This script proves the search path can reach the API.

Safety and credit rules (this project has limited credits):
  * The key is read from the environment ONLY (TAVILY_API_KEY). No key is ever
    hardcoded (AGENTS.md).
  * The DEFAULT path is a dry-run: it prints exactly what the call WOULD be and
    makes NO network call. CI relies on this.
  * ONLY with --live does it make exactly ONE bounded search call.
"""

import argparse
import os
import sys

_DEMO_QUERY = "standing dumbbell curl upper-arm position coaching cue"


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
    print(f"[smoke_tavily]   client.search(query={_DEMO_QUERY!r}, max_results=3)")
    print("[smoke_tavily] Re-run with --live to make exactly ONE real call.")
    return 0


def _live() -> int:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        print(
            "[smoke_tavily] LIVE aborted — missing env: TAVILY_API_KEY",
            file=sys.stderr,
        )
        return 2

    # Lazy import so the dry-run path never requires the SDK.
    from tavily import TavilyClient

    client = TavilyClient(api_key=api_key)
    res = client.search(query=_DEMO_QUERY, max_results=3)
    results = res.get("results", []) if isinstance(res, dict) else []
    print("[smoke_tavily] LIVE ok — one call made.")
    print(f"[smoke_tavily]   results returned = {len(results)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.live:
        return _live()
    return _dry_run()


if __name__ == "__main__":
    sys.exit(main())
