"""Offline doubles must return usable contract objects."""

import asyncio

from contracts.enums import CoachingStatus
from providers.llm.fake import FakeLLMProvider


def test_fake_coaching_is_explicitly_labelled():
    result = asyncio.run(FakeLLMProvider().coach({}))
    assert result.status == CoachingStatus.OK
    assert any("Fake" in text for text in result.limitations)
