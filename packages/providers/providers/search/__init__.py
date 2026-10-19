"""Evidence search providers.

The :class:`~providers.search.protocol.SearchProvider` Protocol defines the
provider-agnostic interface; :class:`~providers.search.cached.CachedSearchProvider`
serves reviewed local records with zero network spend (the default); the live
Tavily adapter lives in ``providers.search.tavily_provider`` and imports its
SDK lazily. :class:`~providers.search.fake.FakeSearchProvider` is the
deterministic, network-free double used by tests.
"""

from __future__ import annotations

from providers.search.fake import FakeSearchProvider

__all__ = ["FakeSearchProvider"]
