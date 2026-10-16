from __future__ import annotations

"""Real coaching provider: NVIDIA Nemotron via Nebius Token Factory (STUB).

Token Factory is OpenAI-compatible; this is the required runtime NVIDIA-model
path for the hackathon (skills/nebius-token-factory, DECISIONS.md D004). The
``openai`` import is LAZY — inside the method — so importing this module or
the LLM Protocol does not require the ``openai`` package. Credentials are read
from the environment ONLY; no key is ever hardcoded (AGENTS.md rule 5).

Call shape to implement::

    from openai import OpenAI
    client = OpenAI(
        base_url=os.environ["NEBIUS_BASE_URL"],   # .../v1
        api_key=os.environ["NEBIUS_API_KEY"],
    )
    resp = client.chat.completions.create(
        model=os.environ["NEBIUS_MODEL_ID"],      # discovered from catalog
        messages=[...],
        temperature=0.2,
        max_tokens=400,
    )

Cache by a hash of the structured input, bound the budget, and on exhaustion
return ``CoachingResult(status=unavailable)`` rather than retrying.
"""

import os
from typing import Any

from contracts.analysis import CoachingResult


class NebiusLLMProvider:
    """Coaching via Nebius Token Factory (OpenAI-compatible; not implemented)."""

    def __init__(self) -> None:
        # Env-only configuration; never a hardcoded key (AGENTS.md rule 5).
        self._base_url = os.environ.get("NEBIUS_BASE_URL")
        self._model_id = os.environ.get("NEBIUS_MODEL_ID")
        self._api_key = os.environ.get("NEBIUS_API_KEY")

    async def coach(self, evidence: Any) -> CoachingResult:
        """Call Nemotron for grounded coaching (lazy OpenAI import inside)."""
        # TODO(T09): lazy-import the client so module import stays SDK-free:
        #   from openai import OpenAI
        #   client = OpenAI(base_url=self._base_url, api_key=self._api_key)
        raise NotImplementedError(
            "NebiusLLMProvider.coach is a scaffold stub — TODO(T09)."
        )
