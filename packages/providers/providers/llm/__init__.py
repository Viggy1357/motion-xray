"""Coaching LLM providers.

The :class:`~providers.llm.protocol.LLMProvider` Protocol defines the
provider-agnostic coaching interface; :class:`~providers.llm.fake.FakeLLMProvider`
is a canned test double; the real Nebius Token Factory adapter lives in
``providers.llm.nebius_provider`` and imports the OpenAI SDK lazily.
"""

from __future__ import annotations
