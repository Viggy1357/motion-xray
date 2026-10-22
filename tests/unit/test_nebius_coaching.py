"""Offline tests for the Nebius coaching adapter: no network, no SDK needed."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from contracts.enums import CoachingStatus
from providers.llm.nebius_provider import (
    CoachingCandidate,
    CoachingEvidence,
    NebiusLLMProvider,
)

OBS = dict(id="o1", text="Knee valgus observed in rep 1.", rep_ids=["r1"], metric_ids=["m1"], kind="observation")
CUE = dict(id="u1", text="Push knees out on the next set.", claim_ids=["c1"], kind="cue")
GOOD_OUT = json.dumps({"observation_ids": ["o1"], "cue_id": "u1"})


def ev(**kw):
    base = dict(exercise="squat", rep_ids=["r1"], metric_ids=["m1"], approved_claim_ids=["c1"],
                candidates=[CoachingCandidate(**OBS), CoachingCandidate(**CUE)],
                limitations=["side view only"], profile_version="p1")
    base.update(kw)
    return CoachingEvidence(**base)


class FakeCompletions:
    def __init__(self, content=GOOD_OUT, finish="stop", exc=None, delay=0.0):
        self.calls, self.content, self.finish, self.exc, self.delay = 0, content, finish, exc, delay

    async def create(self, **kw):
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.exc:
            raise self.exc
        msg = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason=self.finish)],
                               usage=SimpleNamespace(total_tokens=10))


class FakeClient:
    def __init__(self, comp):
        self.chat = SimpleNamespace(completions=comp)
        self.closed = False

    async def close(self):
        self.closed = True


def provider(monkeypatch, comp=None, max_calls=3, **env):
    monkeypatch.setenv("NEBIUS_API_KEY", "sk-secret-test-key")
    monkeypatch.setenv("NEBIUS_MODEL_ID", "nvidia/nemotron-nano")
    monkeypatch.setenv("NEBIUS_BASE_URL", "https://api.studio.nebius.ai/v1")
    monkeypatch.setenv("ALLOW_LIVE_COACHING", "true")
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    comp = comp or FakeCompletions()
    return NebiusLLMProvider(max_calls=max_calls, client_factory=lambda: FakeClient(comp)), comp


def test_happy_path_renders_and_sanitizes(monkeypatch):
    p, comp = provider(monkeypatch)
    r = asyncio.run(p.coach(ev()))
    assert r.status == CoachingStatus.OK and r.observations == [OBS["text"]]
    assert r.next_set_cue == CUE["text"] and r.limitations == ["side view only"]
    assert comp.calls == 1 and p.last_usage["model"].startswith("nvidia/")
    assert "sk-secret" not in str(r.model_dump()) and "sk-secret" not in str(p.last_usage)


def test_gating_blocks_without_flag(monkeypatch):
    p, comp = provider(monkeypatch)
    monkeypatch.delenv("ALLOW_LIVE_COACHING")
    assert asyncio.run(p.coach(ev())).status == CoachingStatus.UNAVAILABLE and comp.calls == 0


@pytest.mark.parametrize("env", [
    {"NEBIUS_MODEL_ID": "openai/gpt"}, {"NEBIUS_API_KEY": ""},
    {"NEBIUS_BASE_URL": "http://api.studio.nebius.ai/v1"},
    {"NEBIUS_BASE_URL": "https://evil.example.com/v1"},
])
def test_gating_blocks_bad_env(monkeypatch, env):
    p, comp = provider(monkeypatch, **env)
    assert asyncio.run(p.coach(ev())).status == CoachingStatus.UNAVAILABLE and comp.calls == 0


def test_no_candidates_no_call(monkeypatch):
    p, comp = provider(monkeypatch)
    assert asyncio.run(p.coach(ev(candidates=[]))).status == CoachingStatus.UNAVAILABLE
    assert comp.calls == 0


def test_oversize_payload_rejected(monkeypatch):
    p, comp = provider(monkeypatch)
    assert asyncio.run(p.coach(ev(exercise="x" * 20000))).status == CoachingStatus.UNAVAILABLE
    assert comp.calls == 0


def test_cache_dedup(monkeypatch):
    p, comp = provider(monkeypatch)
    e = ev()
    asyncio.run(p.coach(e))
    asyncio.run(p.coach(e))
    assert comp.calls == 1


def test_concurrent_dedup(monkeypatch):
    p, comp = provider(monkeypatch, comp=FakeCompletions(delay=0.05))
    async def concurrent_calls():
        return await asyncio.gather(*[p.coach(ev()) for _ in range(5)])
    results = asyncio.run(concurrent_calls())
    assert comp.calls == 1 and all(r.status == CoachingStatus.OK for r in results)


def test_call_quota(monkeypatch):
    p, comp = provider(monkeypatch, max_calls=1)
    assert asyncio.run(p.coach(ev())).status == CoachingStatus.OK
    other = ev(rep_ids=["r2"], candidates=[CoachingCandidate(**{**OBS, "rep_ids": ["r2"]})])
    assert asyncio.run(p.coach(other)).status == CoachingStatus.UNAVAILABLE and comp.calls == 1


def test_sdk_failure_cached_no_retry(monkeypatch):
    p, comp = provider(monkeypatch, comp=FakeCompletions(exc=RuntimeError("boom")))
    e = ev()
    r1, r2 = asyncio.run(p.coach(e)), asyncio.run(p.coach(e))
    assert r1.status == r2.status == CoachingStatus.UNAVAILABLE and comp.calls == 1


def test_timeout_unavailable(monkeypatch):
    p, comp = provider(monkeypatch, comp=FakeCompletions(exc=asyncio.TimeoutError()))
    assert asyncio.run(p.coach(ev())).status == CoachingStatus.UNAVAILABLE and comp.calls == 1


@pytest.mark.parametrize("out", [
    json.dumps({"observation_ids": ["nope"], "cue_id": None}),          # unknown ID
    json.dumps({"observation_ids": ["o1"], "cue_id": "u1", "x": 1}),    # extra field
    json.dumps({"observation_ids": ["o1"], "cue_id": "o1"}),            # cue must be cue kind
    json.dumps({"observation_ids": ["o1", "o1"], "cue_id": None}),      # duplicate IDs
    json.dumps({"observation_ids": ["o1", "o1", "o2", "o3"], "cue_id": None}),
    json.dumps({"observation_ids": [], "cue_id": None}),                # empty selection
    json.dumps({"cue_id": "u1"}),                                       # missing key
])
def test_hallucinated_or_malformed_output_rejected(monkeypatch, out):
    p, _ = provider(monkeypatch, comp=FakeCompletions(content=out))
    assert asyncio.run(p.coach(ev())).status == CoachingStatus.UNAVAILABLE


def test_finish_length_and_null_content(monkeypatch):
    p, _ = provider(monkeypatch, comp=FakeCompletions(finish="length"))
    assert asyncio.run(p.coach(ev())).status == CoachingStatus.UNAVAILABLE
    p2, _ = provider(monkeypatch, comp=FakeCompletions(content=None))
    assert asyncio.run(p2.coach(ev())).status == CoachingStatus.UNAVAILABLE


def test_evidence_validation():
    with pytest.raises(ValidationError):  # observation unknown metric
        ev(candidates=[CoachingCandidate(**{**OBS, "metric_ids": ["zz"]})])
    with pytest.raises(ValidationError):  # cue without approved claim
        ev(candidates=[CoachingCandidate(**{**CUE, "claim_ids": []})])
    with pytest.raises(ValidationError):  # extra field forbidden
        CoachingCandidate(**{**OBS, "image": "x"})
    with pytest.raises(ValidationError):  # empty ID rejected
        ev(rep_ids=[""])
    with pytest.raises(ValidationError):  # text bound
        CoachingCandidate(**{**OBS, "text": "y" * 351})


def test_lazy_sdk_import_not_required(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "openai", None)  # would explode if imported
    p, comp = provider(monkeypatch)
    assert asyncio.run(p.coach(ev())).status == CoachingStatus.OK and comp.calls == 1


def test_max_calls_bounds():
    with pytest.raises(ValueError):
        NebiusLLMProvider(max_calls=0)
    with pytest.raises(ValueError):
        NebiusLLMProvider(max_calls=21)
