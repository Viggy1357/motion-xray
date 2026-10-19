"""Motion X Ray providers — provider-agnostic interfaces and adapters.

This package defines the ``typing.Protocol`` interfaces for the three external
capabilities Motion X Ray depends on (pose estimation, coaching LLM, and
evidence search), plus deterministic ``Fake*`` doubles and real-provider
stubs. Real provider modules import their third-party SDKs lazily inside
methods so that importing an interface never requires the heavy ML/LLM/search
dependencies (AGENTS.md rules 4 and 6; DECISIONS.md D002).

Submodules:
    ``providers.capabilities`` — shared capability/candidate models.
    ``providers.pose``         — pose estimation interface + MediaPipe stub.
    ``providers.llm``          — coaching LLM interface + Nebius stub.
    ``providers.search``       — evidence search interface + Tavily stub.
"""

from __future__ import annotations

from .capabilities import PoseCapabilities, SourceCandidate

__all__ = [
    "PoseCapabilities",
    "SourceCandidate",
]
