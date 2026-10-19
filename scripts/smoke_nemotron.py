"""Motion X Ray — Nemotron (Nebius Token Factory) connectivity smoke test.

Token Factory is OpenAI-compatible; this script proves the coaching LLM path
can reach a real NVIDIA Nemotron model (skills/nebius-token-factory, D004).

Safety and credit rules (this project has limited credits):
  * Credentials are read from the environment ONLY (NEBIUS_BASE_URL /
    NEBIUS_MODEL_ID / NEBIUS_API_KEY). No key is ever hardcoded (AGENTS.md).
  * The DEFAULT path is a dry-run: it prints exactly what the call WOULD be and
    makes NO network call. CI relies on this.
  * ONLY with --live does it make exactly ONE bounded chat.completions call.
"""

from __future__ import annotations

import argparse
import os
import sys


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Nebius Token Factory (Nemotron) smoke test — dry-run by default."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Make ONE real bounded chat.completions call (spends credits). "
        "Omit for a safe dry-run that touches no network.",
    )
    return parser.parse_args(argv)


def _env() -> tuple[str | None, str | None, bool]:
    """Return (base_url, model_id, api_key_present) — never the key value."""
    base_url = os.environ.get("NEBIUS_BASE_URL")
    model_id = os.environ.get("NEBIUS_MODEL_ID")
    api_key_present = bool(os.environ.get("NEBIUS_API_KEY"))
    return base_url, model_id, api_key_present


def _dry_run() -> int:
    base_url, model_id, api_key_present = _env()
    print("[smoke_nemotron] DRY-RUN — no network call made.")
    print(f"[smoke_nemotron]   NEBIUS_BASE_URL = {base_url or '<unset>'}")
    print(f"[smoke_nemotron]   NEBIUS_MODEL_ID = {model_id or '<unset>'}")
    print(
        "[smoke_nemotron]   NEBIUS_API_KEY  = "
        + ("<set>" if api_key_present else "<unset>")
    )
    print("[smoke_nemotron] Would call (OpenAI-compatible):")
    print("[smoke_nemotron]   client = OpenAI(base_url=NEBIUS_BASE_URL, "
          "api_key=NEBIUS_API_KEY)")
    print("[smoke_nemotron]   client.chat.completions.create(")
    print("[smoke_nemotron]       model=NEBIUS_MODEL_ID, messages=[...],")
    print("[smoke_nemotron]       temperature=0.2, max_tokens=16, timeout=30)")
    print("[smoke_nemotron] Re-run with --live to make exactly ONE real call.")
    return 0


def _live() -> int:
    base_url, model_id, api_key_present = _env()
    api_key = os.environ.get("NEBIUS_API_KEY")
    missing = [
        name
        for name, value in (
            ("NEBIUS_BASE_URL", base_url),
            ("NEBIUS_MODEL_ID", model_id),
            ("NEBIUS_API_KEY", api_key),
        )
        if not value
    ]
    if missing:
        print(
            "[smoke_nemotron] LIVE aborted — missing env: " + ", ".join(missing),
            file=sys.stderr,
        )
        return 2

    # Lazy import so the dry-run path never requires the SDK.
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=api_key)
    resp = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": "Reply with the single word: ok"}],
        temperature=0.2,
        max_tokens=16,
        timeout=30,
    )
    print("[smoke_nemotron] LIVE ok — one call made.")
    print(f"[smoke_nemotron]   model   = {resp.model}")
    print(f"[smoke_nemotron]   content = {resp.choices[0].message.content!r}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.live:
        return _live()
    return _dry_run()


if __name__ == "__main__":
    sys.exit(main())
