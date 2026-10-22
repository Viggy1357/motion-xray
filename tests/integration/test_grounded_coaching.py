from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.coaching as coaching
from contracts.analysis import CoachingResult
from contracts.enums import CoachingStatus

from tests.integration import test_movement_reports as movement_fixtures
from tests.integration.test_movement_reports import _headers, _session

# Fixture assignments via module alias (avoids Ruff F811 redefinition).
client = movement_fixtures.client
env_setup = movement_fixtures.env_setup
lat_succeeded = movement_fixtures.lat_succeeded


class FakeProvider:
    """Deterministic async provider; no network, no paid CI dependency."""

    calls = 0
    behavior = "ok"
    on_call = None

    def __init__(self) -> None:
        self.last_usage = {"model": "nvidia/fake", "usage": {"total_tokens": 12}, "status": "validated"}

    async def coach(self, evidence):
        type(self).calls += 1
        if type(self).on_call is not None:
            type(self).on_call()
        if type(self).behavior == "raise":
            raise RuntimeError("boom")
        if type(self).behavior == "unavailable":
            return CoachingResult(status=CoachingStatus.UNAVAILABLE, limitations=list(evidence.limitations))
        obs = [c for c in evidence.candidates if c.kind == "observation"]
        cue = [c for c in evidence.candidates if c.kind == "cue"]
        return CoachingResult(
            status=CoachingStatus.OK,
            summary=obs[0].text,
            observations=[c.text for c in obs[:2]],
            next_set_cue=cue[0].text if cue else None,
            limitations=list(evidence.limitations),
        )


@pytest.fixture(autouse=True)
def fake_provider(monkeypatch):
    FakeProvider.calls = 0
    FakeProvider.behavior = "ok"
    FakeProvider.on_call = None
    monkeypatch.setattr(coaching, "_provider_factory", lambda: FakeProvider())
    yield


def _post(client: TestClient, f):
    return client.post(f"/v1/analyses/{f.job.id}/coaching", headers=_headers(f.csrf))


def _rows(f):
    with f.store._conn() as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='grounded_coaching'").fetchone():
            return []
        return conn.execute(
            "SELECT owner, job_id, key, state, result_json FROM grounded_coaching"
        ).fetchall()


class _Report:
    def __init__(self, dump):
        self._dump = dump

    def model_dump(self, mode="json"):
        return self._dump


def _live_report(client: TestClient, f) -> dict:
    r = client.get(
        f"/v1/analyses/{f.job.id}/movement-report", headers=_headers(f.csrf)
    )
    assert r.status_code == 200
    return r.json()


def _synthetic_report() -> dict:
    """Two completed cycles plus hostile rows that must be rejected."""
    reps = [
        {"id": "rep-a", "ordinal": 1, "side": "left", "start_s": 1.5, "end_s": 3.5,
         "completion_status": "completed", "scorable": True},
        {"id": "rep-b", "ordinal": 2, "side": "left", "start_s": 5.0, "end_s": 7.25,
         "completion_status": "completed", "scorable": True},
        {"id": "rep-partial", "ordinal": 3, "side": "left", "start_s": 9.0, "end_s": 10.5,
         "completion_status": "partial", "scorable": False},
    ]
    metrics = [
        {"id": "elbow_flexion/1", "rep_id": "rep-a", "side": "left", "value": 140.0,
         "unit": "degrees", "dimensionality": "angle", "reference_interval": [120.0, 150.0],
         "deviation": 0.0, "coverage": 0.95, "status": "observed"},
        {"id": "elbow_flexion/2", "rep_id": "rep-b", "side": "left", "value": 110.0,
         "unit": "degrees", "dimensionality": "angle", "reference_interval": [120.0, 150.0],
         "deviation": 10.0, "coverage": 0.9, "status": "observed"},
        # Rejections below:
        {"id": "partial-seg", "rep_id": "rep-partial", "side": "left", "value": 130.0,
         "unit": "degrees", "dimensionality": "angle", "coverage": 0.99, "status": "observed"},
        {"id": "wrong-side", "rep_id": "rep-a", "side": "right", "value": 130.0,
         "unit": "degrees", "dimensionality": "angle", "coverage": 0.99, "status": "observed"},
        {"id": "none-value", "rep_id": "rep-a", "side": "left", "value": None,
         "unit": "degrees", "dimensionality": "angle", "coverage": 0.99,
         "status": "observed", "reason": "gap"},
        {"id": "zero-coverage", "rep_id": "rep-a", "side": "left", "value": 130.0,
         "unit": "degrees", "dimensionality": "angle", "coverage": 0.0, "status": "observed"},
        {"id": "low-coverage", "rep_id": "rep-b", "side": "left", "value": 130.0,
         "unit": "degrees", "dimensionality": "angle", "coverage": 0.79, "status": "observed"},
        {"id": "temporal", "rep_id": "rep-a", "side": "left", "value": 2.5,
         "unit": "seconds", "dimensionality": "time", "coverage": 0.99, "status": "observed"},
        {"id": "ghost-rep", "rep_id": "rep-missing", "side": "left", "value": 130.0,
         "unit": "degrees", "dimensionality": "angle", "coverage": 0.99, "status": "observed"},
        {"id": "dup-1", "rep_id": "rep-a", "side": "left", "value": 145.0,
         "unit": "degrees", "dimensionality": "angle", "reference_interval": [120.0, 150.0],
         "deviation": 0.0, "coverage": 0.9, "status": "observed"},
    ]
    return {
        "schema_version": "0.3.0", "analysis_id": "x", "exercise": "lat_pulldown",
        "variant": "wide", "recipe_version": "r1", "reps": reps, "metrics": metrics,
    }


def test_happy_path_grounded_ok(client: TestClient, lat_succeeded):
    r = _post(client, lat_succeeded)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["observations"]
    assert all("measured" in o and "degrees" in o for o in body["observations"])
    assert all(len(o) <= 350 for o in body["observations"])
    assert body["next_set_cue"]
    assert any("unreviewed" in lim or "estimated" in lim for lim in body["limitations"])
    assert any(lim.startswith("Cue source: https://") for lim in body["limitations"])
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert FakeProvider.calls == 1
    rows = _rows(lat_succeeded)
    assert len(rows) == 1 and rows[0]["state"] == "done"


def test_csrf_required(client: TestClient, lat_succeeded):
    r = client.post(f"/v1/analyses/{lat_succeeded.job.id}/coaching")
    assert r.status_code == 403
    assert r.headers["cache-control"] == "no-store"
    assert FakeProvider.calls == 0


def test_foreign_owner_404(client: TestClient, lat_succeeded):
    client.cookies.clear()
    csrf2 = _session(client)
    r = client.post(
        f"/v1/analyses/{lat_succeeded.job.id}/coaching", headers=_headers(csrf2)
    )
    assert r.status_code == 404
    assert FakeProvider.calls == 0


def test_no_observations_no_provider_call(client: TestClient, lat_succeeded, monkeypatch):
    monkeypatch.setattr(coaching, "_build_evidence", lambda report: None)
    r = _post(client, lat_succeeded)
    assert r.status_code == 200
    assert r.json()["status"] == "unavailable"
    assert FakeProvider.calls == 0
    assert _rows(lat_succeeded) == []


def test_revocation_during_provider_404(client: TestClient, lat_succeeded):
    def delete_job():
        lat_succeeded.store.delete_job(lat_succeeded.owner, lat_succeeded.job.id)

    FakeProvider.on_call = delete_job
    r = _post(client, lat_succeeded)
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"
    # Reservation marked failed without any private payload.
    rows = _rows(lat_succeeded)
    assert len(rows) == 1 and rows[0]["state"] == "failed"
    cached = json.loads(rows[0]["result_json"])
    assert cached["status"] == "unavailable" and cached["limitations"] == []


def test_cache_hit_across_provider_instances(client: TestClient, lat_succeeded):
    r1 = _post(client, lat_succeeded)
    r2 = _post(client, lat_succeeded)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json() == r2.json()
    assert FakeProvider.calls == 1  # second request served from durable SQLite cache


def test_global_quota_exhausted_429(client: TestClient, lat_succeeded):
    now = time.time()
    with lat_succeeded.store._conn() as conn:
        coaching._ensure_table(conn)
        conn.execute("BEGIN IMMEDIATE")
        for i in range(coaching.GLOBAL_DAILY_LIMIT):
            conn.execute(
                "INSERT INTO grounded_coaching VALUES (?,?,?,NULL,'failed',?,?,NULL)",
                (f"other-{i}", lat_succeeded.job.id, f"k{i}", now, now + 3600),
            )
        conn.execute("COMMIT")
    r = _post(client, lat_succeeded)
    assert r.status_code == 429
    assert r.json()["code"] == "COACHING_QUOTA_EXCEEDED"
    assert FakeProvider.calls == 0


def test_owner_quota_exhausted_429(client: TestClient, lat_succeeded):
    now = time.time()
    with lat_succeeded.store._conn() as conn:
        coaching._ensure_table(conn)
        conn.execute("BEGIN IMMEDIATE")
        for i in range(coaching.OWNER_DAILY_LIMIT):
            conn.execute(
                "INSERT INTO grounded_coaching VALUES (?,?,?,NULL,'done',?,?,NULL)",
                (lat_succeeded.owner, f"job-{i}", f"k{i}", now, now + 3600),
            )
        conn.execute("COMMIT")
    r = _post(client, lat_succeeded)
    assert r.status_code == 429
    assert FakeProvider.calls == 0


def _db_path(store):
    for attr in ("_db_path", "db_path", "_path", "path", "_db"):
        p = getattr(store, attr, None)
        if isinstance(p, (str, Path)) and str(p) != ":memory:":
            return str(p)
    return None


def test_concurrent_reservation_two_connections_only_one_accepted(client: TestClient, lat_succeeded):
    report = _live_report(client, lat_succeeded)
    ev = coaching._build_evidence(_Report(report))
    assert ev is not None
    key = coaching._cache_key(_Report(report), ev)
    now = time.time()
    path = _db_path(lat_succeeded.store)
    if path:
        c1 = sqlite3.connect(path)
        c2 = sqlite3.connect(path)
        c1.row_factory = sqlite3.Row
        c2.row_factory = sqlite3.Row
        conns = (c1, c2)
    else:
        c1 = lat_succeeded.store._conn().__enter__()
        c2 = lat_succeeded.store._conn().__enter__()
        conns = (c1, c2)
    try:
        d1, _ = coaching._reserve(c1, lat_succeeded.owner, lat_succeeded.job.id, key, now)
        d2, _ = coaching._reserve(c2, lat_succeeded.owner, lat_succeeded.job.id, key, now)
    finally:
        for c in conns:
            try:
                c.close()
            except Exception:
                pass
    assert d1 == "reserved"
    assert d2 == "busy"  # exactly one reservation accepted


def test_expired_row_fails_closed_no_quota_bypass(client: TestClient, lat_succeeded):
    report = _live_report(client, lat_succeeded)
    ev = coaching._build_evidence(_Report(report))
    key = coaching._cache_key(_Report(report), ev)
    now = time.time()
    with lat_succeeded.store._conn() as conn:
        coaching._ensure_table(conn)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO grounded_coaching VALUES (?,?,?,NULL,'reserved',?,?,NULL)",
            (lat_succeeded.owner, lat_succeeded.job.id, key, now - 2 * coaching.CACHE_TTL_S,
             now - coaching.CACHE_TTL_S),
        )
        conn.execute("COMMIT")
    r = _post(client, lat_succeeded)
    assert r.status_code == 503
    assert r.json()["code"] == "COACHING_UNAVAILABLE"
    assert FakeProvider.calls == 0  # expired rows never grant a new call
    rows = _rows(lat_succeeded)
    assert len(rows) == 1 and rows[0]["state"] == "reserved"  # history preserved


def test_in_progress_409_no_autoretry(client: TestClient, lat_succeeded):
    orig = coaching._reserve
    coaching._reserve = lambda *a, **k: ("busy", None)
    try:
        r = _post(client, lat_succeeded)
    finally:
        coaching._reserve = orig
    assert r.status_code == 409
    assert r.json()["code"] == "COACHING_IN_PROGRESS"
    assert r.json()["retryable"] is False
    assert FakeProvider.calls == 0


def test_failure_cached_no_retry(client: TestClient, lat_succeeded):
    FakeProvider.behavior = "unavailable"
    r1 = _post(client, lat_succeeded)
    assert r1.status_code == 200
    assert r1.json()["status"] == "unavailable"
    rows = _rows(lat_succeeded)
    assert len(rows) == 1 and rows[0]["state"] == "failed"
    FakeProvider.behavior = "ok"
    r2 = _post(client, lat_succeeded)
    assert r2.status_code == 200
    assert r2.json()["status"] == "unavailable"  # durable failure: never retried
    assert FakeProvider.calls == 1


def test_provider_exception_cached_failure(client: TestClient, lat_succeeded):
    FakeProvider.behavior = "raise"
    r = _post(client, lat_succeeded)
    assert r.status_code == 200
    assert r.json()["status"] == "unavailable"
    rows = _rows(lat_succeeded)
    assert rows[0]["state"] == "failed"


def test_single_model_call_and_usage_recorded(client: TestClient, lat_succeeded):
    r = _post(client, lat_succeeded)
    assert r.status_code == 200
    assert FakeProvider.calls == 1
    with lat_succeeded.store._conn() as conn:
        row = conn.execute("SELECT usage_json FROM grounded_coaching").fetchone()
    usage = json.loads(row["usage_json"])
    assert usage["model"] == "nvidia/fake"


def test_evidence_uses_actual_rep_ids_and_timestamps(client: TestClient, lat_succeeded):
    ev = coaching._build_evidence(_Report(_synthetic_report()))
    assert ev is not None
    obs = [c for c in ev.candidates if c.kind == "observation"]
    assert obs, "expected grounded observations"
    # Actual rep IDs only; never synthesized rep-{index}.
    assert set(ev.rep_ids) == {"rep-a", "rep-b"}
    assert all(not rid.startswith("rep-") or rid in ("rep-a", "rep-b") for rid in ev.rep_ids)
    assert "rep-partial" not in ev.rep_ids and "rep-missing" not in ev.rep_ids
    # Actual timestamps from each rep across both cycles; never 0.0 defaults.
    texts = {c.id: c.text for c in obs}
    assert any("(1.50\u20133.50s)" in t for t in texts.values())
    assert any("(5.00\u20137.25s)" in t for t in texts.values())
    assert all("0.00\u20130.00s" not in t for t in texts.values())
    # Rejected: partial segments, wrong side, None values, zero/low coverage,
    # temporal (non-degree) metrics, ghost reps.
    rejected = {"partial-seg", "wrong-side", "none-value", "zero-coverage",
                "low-coverage", "temporal", "ghost-rep"}
    assert rejected.isdisjoint(set(ev.metric_ids))
    assert set(ev.metric_ids) == {"elbow_flexion/1", "elbow_flexion/2", "dup-1"}
    # IDs are obs-{ordinal}-{metricindex} and unique.
    ids = [c.id for c in ev.candidates]
    assert len(set(ids)) == len(ids)
    for c in obs:
        assert c.id.startswith("obs-")
        assert set(c.rep_ids) <= set(ev.rep_ids)
        assert set(c.metric_ids) <= set(ev.metric_ids)
    # Sorting: largest absolute deviation first (rep-b deviates by 10).
    assert obs[0].rep_ids == ["rep-b"]
    assert "below the band by 10.0 degrees" in obs[0].text
    # Same feature across cycles is allowed: metric IDs deduped, unique list.
    assert len(ev.metric_ids) == len(set(ev.metric_ids))
    assert len(ev.rep_ids) == len(set(ev.rep_ids))


def test_evidence_bounds_and_ids(client: TestClient, lat_succeeded):
    ev = coaching._build_evidence(_Report(_live_report(client, lat_succeeded)))
    assert ev is not None
    assert len(ev.candidates) <= 12
    obs = [c for c in ev.candidates if c.kind == "observation"]
    cues = [c for c in ev.candidates if c.kind == "cue"]
    assert 1 <= len(obs) <= 8
    assert len(cues) <= 1
    ids = [c.id for c in ev.candidates]
    assert len(set(ids)) == len(ids)
    for c in obs:
        assert set(c.rep_ids) <= set(ev.rep_ids)
        assert set(c.metric_ids) <= set(ev.metric_ids)
        assert len(c.text) <= 350
    for c in cues:
        assert set(c.claim_ids) <= set(ev.approved_claim_ids)
        low = c.text.lower()
        assert "injury" not in low and "lumbar" not in low and "activation" not in low
    payload = json.dumps(ev.model_dump())
    assert len(payload.encode()) <= 10_000


def test_cache_key_includes_model_and_recipe(client: TestClient, lat_succeeded, monkeypatch):
    report = _Report(_live_report(client, lat_succeeded))
    ev = coaching._build_evidence(report)
    monkeypatch.setenv("NEBIUS_MODEL_ID", "nvidia/model-a")
    k1 = coaching._cache_key(report, ev)
    monkeypatch.setenv("NEBIUS_MODEL_ID", "nvidia/model-b")
    k2 = coaching._cache_key(report, ev)
    assert k1 != k2  # no cross-model cache reuse


def test_day_start_uses_argument():
    ts = 1_700_000_000.0  # fixed instant
    from datetime import datetime, timezone
    want = datetime.fromtimestamp(ts, timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    assert coaching._day_start(ts) == want
    assert coaching._day_start(want + 3600) == want
    assert coaching.OWNER_DAILY_LIMIT >= 4  # four-exercise personal demo


def test_lifetime_quota_does_not_reset_with_the_day(lat_succeeded):
    now = time.time()
    with lat_succeeded.store._conn() as conn:
        coaching._ensure_table(conn)
        conn.executemany(
            "INSERT INTO grounded_coaching (owner,job_id,key,state,reserved_at,expires_at) VALUES (?,?,?,'failed',?,?)",
            [("old-owner", f"old-job-{i}", f"old-key-{i}", now - 172800, now - 86400)
             for i in range(coaching.GLOBAL_LIFETIME_LIMIT)],
        )
        decision, _ = coaching._reserve(conn, lat_succeeded.owner, lat_succeeded.job.id, "new-key", now)
    assert decision == "quota"
    assert FakeProvider.calls == 0
