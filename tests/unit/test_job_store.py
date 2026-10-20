from __future__ import annotations

import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest
from contracts.enums import JobStage, JobState
from contracts.media import VideoAsset

from app.store import Conflict, LeaseLost, NotFound, Store


def _ts(dt: datetime) -> float:
    return dt.timestamp()


def _dt(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _video(
    asset_id: str = "a1",
    owner: str = "owner1",
    now: float = 1000.0,
    expires_at: float | None = None,
    storage_key: str = "media/v1.mp4",
    sha256: str = "a" * 64,
) -> VideoAsset:
    if expires_at is None:
        expires_at = now + 3600
    return VideoAsset(
        id=asset_id,
        owner_session_id=owner,
        storage_key=storage_key,
        sha256=sha256,
        mime="video/mp4",
        bytes=1024,
        duration_s=10.0,
        width=1920,
        height=1080,
        rotation=0,
        created_at=_dt(now),
        expires_at=_dt(expires_at),
    )


class TestStoreInit:
    def test_creates_parent_and_migrations(self, tmp_path: Path) -> None:
        db = tmp_path / "deep" / "store.db"
        s = Store(db)
        assert db.exists()
        with s._conn() as conn:
            assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            assert "assets" in tables
            assert "jobs" in tables

    def test_rejects_future_version(self, tmp_path: Path) -> None:
        db = tmp_path / "store.db"
        s = Store(db)
        with s._conn() as conn:
            conn.execute("PRAGMA user_version=2")
            conn.commit()
        with pytest.raises(RuntimeError, match="newer"):
            Store(db)

    def test_wal_and_foreign_keys(self, tmp_path: Path) -> None:
        db = tmp_path / "store.db"
        s = Store(db)
        with s._conn() as conn:
            assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
            assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


class TestRegisterAsset:
    def test_basic(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        out = s.register_asset(v, now=1000.0)
        assert out.id == v.id

    def test_requires_future_expires(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0, expires_at=999.0)
        with pytest.raises(ValueError):
            s.register_asset(v, now=1000.0)

    def test_requires_positive_bytes(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        v.bytes = 0
        with pytest.raises(ValueError):
            s.register_asset(v, now=1000.0)

    def test_requires_duration_in_range(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        v.duration_s = 31.0
        with pytest.raises(ValueError):
            s.register_asset(v, now=1000.0)
        v.duration_s = 0.0
        with pytest.raises(ValueError):
            s.register_asset(v, now=1000.0)

    def test_requires_positive_dims(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        v.width = 0
        with pytest.raises(ValueError):
            s.register_asset(v, now=1000.0)

    def test_requires_sha256_64_lower_hex(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0, sha256="A" * 64)
        with pytest.raises(ValueError):
            s.register_asset(v, now=1000.0)
        v.sha256 = "g" * 64
        with pytest.raises(ValueError):
            s.register_asset(v, now=1000.0)
        v.sha256 = "a" * 63
        with pytest.raises(ValueError):
            s.register_asset(v, now=1000.0)

    def test_rejects_traversal_storage_key(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        for bad in ["../x", "./x", "/x", "x/../y", "x\\y", "x//y", "x/", ".", "..", "x/./y"]:
            v = _video(now=1000.0, storage_key=bad)
            with pytest.raises(ValueError):
                s.register_asset(v, now=1000.0)

    def test_conflict_duplicate_id(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        with pytest.raises(Conflict):
            s.register_asset(v, now=1000.0)

    def test_persistence_across_reopen(self, tmp_path: Path) -> None:
        db = tmp_path / "s.db"
        s1 = Store(db)
        v = _video(now=1000.0)
        s1.register_asset(v, now=1000.0)
        s2 = Store(db)
        got = s2.get_asset("owner1", "a1", now=1000.0)
        assert got.id == "a1"


class TestGetAsset:
    def test_found(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        got = s.get_asset("owner1", "a1", now=1000.0)
        assert got.id == "a1"

    def test_not_found_wrong_owner(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        with pytest.raises(NotFound):
            s.get_asset("owner2", "a1", now=1000.0)

    def test_not_found_expired(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0, expires_at=2000.0)
        s.register_asset(v, now=1000.0)
        with pytest.raises(NotFound):
            s.get_asset("owner1", "a1", now=2001.0)

    def test_not_found_deleted(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.delete_asset("owner1", "a1", now=1000.0)
        with pytest.raises(NotFound):
            s.get_asset("owner1", "a1", now=1000.0)


class TestEnqueue:
    def test_basic(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        assert j.state == JobState.QUEUED
        assert j.stage == JobStage.VALIDATE
        assert j.attempt == 0
        assert j.lease_owner is None

    def test_requires_active_asset(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        with pytest.raises(NotFound):
            s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)

    def test_idempotency_same_payload(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j1 = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        j2 = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        assert j1.id == j2.id

    def test_idempotency_conflict_mismatched(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        with pytest.raises(Conflict):
            s.enqueue("owner1", "a1", "ex2", "var1", "rk1", "vh1", now=1000.0)

    def test_idempotency_tombstoned(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0, ttl_s=10)
        s.delete_job("owner1", j.id, now=1000.0)
        with pytest.raises(Conflict):
            s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)

    def test_input_hash_from_video(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0, sha256="b" * 64)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        assert j.input_hash == "b" * 64


class TestClaim:
    def test_claim_queued(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        j = s.claim("w1", now=1000.0, lease_s=60)
        assert j is not None
        assert j.state == JobState.RUNNING
        assert j.attempt == 1
        assert j.lease_owner is not None
        assert re.fullmatch(r"[0-9a-f]{32}", j.lease_owner)

    def test_claim_none_empty(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        assert s.claim("w1", now=1000.0) is None

    def test_claim_oldest(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk2", "vh1", now=1001.0)
        with s._conn() as conn:
            id1 = conn.execute("SELECT id FROM jobs WHERE request_key='rk1'").fetchone()[0]
            id2 = conn.execute("SELECT id FROM jobs WHERE request_key='rk2'").fetchone()[0]
        j1 = s.get_job("owner1", id1, now=1002.0)
        assert s.get_job("owner1", id2, now=1002.0).id == id2
        claimed = s.claim("w1", now=1002.0, lease_s=60)
        assert claimed is not None
        assert claimed.id == j1.id

    def test_reclaim_expired_lease(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        j1 = s.claim("w1", now=1000.0, lease_s=60)
        assert j1 is not None
        j2 = s.claim("w2", now=1061.0, lease_s=60)
        assert j2 is not None
        assert j2.id == j1.id
        assert j2.attempt == 2
        assert j2.lease_owner != j1.lease_owner
        assert j2.state == JobState.RUNNING

    def test_reclaim_same_worker_different_token(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        j1 = s.claim("w1", now=1000.0, lease_s=60)
        j2 = s.claim("w1", now=1061.0, lease_s=60)
        assert j2 is not None
        assert j2.lease_owner != j1.lease_owner

    def test_excludes_cancelled(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        s.cancel("owner1", j.id, now=1000.0)
        assert s.claim("w1", now=1000.0) is None

    def test_excludes_expired_job(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0, ttl_s=10)
        assert s.claim("w1", now=1011.0) is None

    def test_excludes_expired_asset(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0, expires_at=1050.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        assert s.claim("w1", now=1051.0) is None

    def test_excludes_deleted_asset(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        s.delete_asset("owner1", "a1", now=1000.0)
        assert s.claim("w1", now=1000.0) is None

    def test_concurrent_claim_exactly_one_winner(self, tmp_path: Path) -> None:
        db = tmp_path / "s.db"
        s0 = Store(db)
        v = _video(now=1000.0)
        s0.register_asset(v, now=1000.0)
        s0.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)

        results: list = []
        barrier = threading.Barrier(4)

        def worker() -> None:
            s = Store(db)
            barrier.wait()
            j = s.claim("w", now=1000.0, lease_s=60)
            results.append(j)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        winners = [r for r in results if r is not None]
        assert len(winners) == 1
        assert winners[0].attempt == 1


class TestHeartbeat:
    def test_extends_lease(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        j = s.claim("w1", now=1000.0, lease_s=60)
        assert j is not None
        j2 = s.heartbeat(j.id, j.lease_owner, now=1000.0, lease_s=120)
        assert j2.lease_until is not None
        assert j2.lease_until.timestamp() == 1120.0

    def test_preserves_token(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        j = s.claim("w1", now=1000.0, lease_s=60)
        assert j is not None
        j2 = s.heartbeat(j.id, j.lease_owner, now=1050.0, lease_s=60)
        assert j2.lease_owner == j.lease_owner

    def test_prevents_reclaim(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        j = s.claim("w1", now=1000.0, lease_s=60)
        assert j is not None
        s.heartbeat(j.id, j.lease_owner, now=1050.0, lease_s=60)
        j2 = s.claim("w2", now=1059.0, lease_s=60)
        assert j2 is None

    def test_lease_lost_wrong_token(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        j = s.claim("w1", now=1000.0, lease_s=60)
        assert j is not None
        with pytest.raises(LeaseLost):
            s.heartbeat(j.id, "badtoken", now=1000.0, lease_s=60)


class TestCheckpoint:
    def test_updates_stage(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        j = s.claim("w1", now=1000.0, lease_s=60)
        assert j is not None
        j2 = s.checkpoint(j.id, j.lease_owner, JobStage.POSE, now=1000.0)
        assert j2.stage == JobStage.POSE
        assert j2.state == JobState.RUNNING

    def test_stage_retained_on_reclaim(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        j1 = s.claim("w1", now=1000.0, lease_s=60)
        assert j1 is not None
        s.checkpoint(j1.id, j1.lease_owner, JobStage.SEGMENT, now=1000.0)
        j2 = s.claim("w2", now=1061.0, lease_s=60)
        assert j2 is not None
        assert j2.stage == JobStage.SEGMENT


class TestFinish:
    def test_success(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        j = s.claim("w1", now=1000.0, lease_s=60)
        assert j is not None
        j2 = s.finish(j.id, j.lease_owner, result_key="results/r1.json", now=1000.0)
        assert j2.state == JobState.SUCCEEDED
        assert j2.result_key == "results/r1.json"
        assert j2.lease_owner is None
        assert j2.lease_until is None

    def test_lease_lost_after_cancel(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        jc = s.claim("w1", now=1000.0, lease_s=60)
        assert jc is not None
        s.cancel("owner1", j.id, now=1000.0)
        with pytest.raises(LeaseLost):
            s.finish(j.id, jc.lease_owner, result_key="results/r1.json", now=1000.0)

    def test_rejects_bad_result_key(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        j = s.claim("w1", now=1000.0, lease_s=60)
        assert j is not None
        with pytest.raises(ValueError):
            s.finish(j.id, j.lease_owner, result_key="../x", now=1000.0)


class TestFail:
    def test_fail(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        j = s.claim("w1", now=1000.0, lease_s=60)
        assert j is not None
        j2 = s.fail(j.id, j.lease_owner, error="PIPELINE_ERROR", now=1000.0)
        assert j2.state == JobState.FAILED
        assert j2.error == "PIPELINE_ERROR"
        assert j2.lease_owner is None

    def test_rejects_bad_error(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        j = s.claim("w1", now=1000.0, lease_s=60)
        assert j is not None
        with pytest.raises(ValueError):
            s.fail(j.id, j.lease_owner, error="lowercase", now=1000.0)
        with pytest.raises(ValueError):
            s.fail(j.id, j.lease_owner, error="A" * 65, now=1000.0)


class TestCancel:
    def test_cancel_queued(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        j2 = s.cancel("owner1", j.id, now=1000.0)
        assert j2.state == JobState.CANCELLED
        assert j2.cancel_requested is True
        assert j2.lease_owner is None

    def test_cancel_running(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        jc = s.claim("w1", now=1000.0, lease_s=60)
        assert jc is not None
        j2 = s.cancel("owner1", j.id, now=1000.0)
        assert j2.state == JobState.CANCELLED
        assert j2.lease_owner is None

    def test_cancel_terminal_unchanged(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        jc = s.claim("w1", now=1000.0, lease_s=60)
        assert jc is not None
        assert s.finish(j.id, jc.lease_owner, result_key="r", now=1000.0).state == JobState.SUCCEEDED
        j2 = s.cancel("owner1", j.id, now=1000.0)
        assert j2.state == JobState.SUCCEEDED

    def test_cancel_before_claim_prevents_stale_finish(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        s.cancel("owner1", j.id, now=1000.0)
        with pytest.raises(LeaseLost):
            s.finish(j.id, "fake", result_key="r", now=1000.0)

    def test_repeated_cancel_idempotent(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        s.cancel("owner1", j.id, now=1000.0)
        j2 = s.cancel("owner1", j.id, now=1000.0)
        assert j2.state == JobState.CANCELLED

    def test_cross_owner_denied(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        with pytest.raises(NotFound):
            s.cancel("owner2", j.id, now=1000.0)


class TestDeleteJob:
    def test_delete_job(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        s.delete_job("owner1", j.id, now=1000.0)
        with pytest.raises(NotFound):
            s.get_job("owner1", j.id, now=1000.0)

    def test_delete_job_blocks_claim(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        s.delete_job("owner1", j.id, now=1000.0)
        assert s.claim("w1", now=1000.0) is None

    def test_delete_job_does_not_resurrect_request_key(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        s.delete_job("owner1", j.id, now=1000.0)
        with pytest.raises(Conflict):
            s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)

    def test_delete_job_cross_owner_denied(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        with pytest.raises(NotFound):
            s.delete_job("owner2", j.id, now=1000.0)

    def test_delete_job_idempotent(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        s.delete_job("owner1", j.id, now=1000.0)
        s.delete_job("owner1", j.id, now=1000.0)


class TestDeleteAsset:
    def test_delete_asset(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.delete_asset("owner1", "a1", now=1000.0)
        with pytest.raises(NotFound):
            s.get_asset("owner1", "a1", now=1000.0)

    def test_delete_asset_revokes_jobs(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        jc = s.claim("w1", now=1000.0, lease_s=60)
        assert jc is not None
        s.delete_asset("owner1", "a1", now=1000.0)
        with pytest.raises(NotFound):
            s.get_job("owner1", j.id, now=1000.0)
        with pytest.raises(LeaseLost):
            s.finish(j.id, jc.lease_owner, result_key="r", now=1000.0)

    def test_delete_asset_blocks_claim(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        s.delete_asset("owner1", "a1", now=1000.0)
        assert s.claim("w1", now=1000.0) is None

    def test_delete_asset_cross_owner_denied(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        with pytest.raises(NotFound):
            s.delete_asset("owner2", "a1", now=1000.0)

    def test_delete_asset_idempotent(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.delete_asset("owner1", "a1", now=1000.0)
        s.delete_asset("owner1", "a1", now=1000.0)


class TestGetJob:
    def test_found(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        got = s.get_job("owner1", j.id, now=1000.0)
        assert got.id == j.id

    def test_not_found_expired(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0, ttl_s=10)
        with pytest.raises(NotFound):
            s.get_job("owner1", j.id, now=1011.0)

    def test_not_found_deleted(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        s.delete_job("owner1", j.id, now=1000.0)
        with pytest.raises(NotFound):
            s.get_job("owner1", j.id, now=1000.0)

    def test_retains_unexpired_report_after_asset_expiry(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0, expires_at=1050.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0, ttl_s=100)
        jc = s.claim("w1", now=1000.0, lease_s=60)
        assert jc is not None
        s.finish(j.id, jc.lease_owner, result_key="results/r.json", now=1000.0)
        # Asset expired but job TTL still valid; get_job should succeed
        got = s.get_job("owner1", j.id, now=1055.0)
        assert got.state == JobState.SUCCEEDED
        assert got.result_key == "results/r.json"
        # get_input should fail because asset expired
        with pytest.raises(NotFound):
            s.get_input("owner1", j.id, now=1055.0)


class TestGetInput:
    def test_returns_asset_and_exercise_variant(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        asset, ex, var = s.get_input("owner1", j.id, now=1000.0)
        assert asset.id == "a1"
        assert ex == "ex1"
        assert var == "var1"

    def test_not_found_cross_owner(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        with pytest.raises(NotFound):
            s.get_input("owner2", j.id, now=1000.0)


class TestConnectionsClosed:
    def test_connections_closed_on_success(self, tmp_path: Path) -> None:
        db = tmp_path / "s.db"
        s = Store(db)
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        # Track connections by using a wrapper that counts open connections
        open_conns: list[sqlite3.Connection] = []
        orig_connect = sqlite3.connect
        def tracking_connect(*args, **kwargs):
            conn = orig_connect(*args, **kwargs)
            open_conns.append(conn)
            return conn
        import app.store
        app.store.sqlite3.connect = tracking_connect
        try:
            s2 = Store(db)
            s2.get_asset("owner1", "a1", now=1000.0)
            for conn in open_conns:
                # Try to use connection; closed connections raise ProgrammingError
                with pytest.raises(sqlite3.ProgrammingError):
                    conn.execute("SELECT 1")
        finally:
            app.store.sqlite3.connect = orig_connect

    def test_connections_closed_on_exception(self, tmp_path: Path) -> None:
        db = tmp_path / "s.db"
        s = Store(db)
        open_conns: list[sqlite3.Connection] = []
        orig_connect = sqlite3.connect
        def tracking_connect(*args, **kwargs):
            conn = orig_connect(*args, **kwargs)
            open_conns.append(conn)
            return conn
        import app.store
        app.store.sqlite3.connect = tracking_connect
        try:
            with pytest.raises(NotFound):
                s.get_asset("owner1", "nonexistent", now=1000.0)
            for conn in open_conns:
                with pytest.raises(sqlite3.ProgrammingError):
                    conn.execute("SELECT 1")
        finally:
            app.store.sqlite3.connect = orig_connect

    def test_no_leaked_connections(self, tmp_path: Path) -> None:
        db = tmp_path / "s.db"
        s = Store(db)
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        for i in range(5):
            s.get_asset("owner1", "a1", now=1000.0)


class TestJobTTL:
    def test_ttl_denies_read_and_claim(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0, ttl_s=10)
        with pytest.raises(NotFound):
            s.get_job("owner1", j.id, now=1011.0)
        assert s.claim("w1", now=1011.0) is None

    def test_ttl_overflow_rejected(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        with pytest.raises(ValueError):
            s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0, ttl_s=float("inf"))


@pytest.mark.parametrize("ttl", [1e308, 253402300800.0])
def test_invalid_deadline_does_not_persist_job(tmp_path: Path, ttl: float) -> None:
    store = Store(tmp_path / "store.db")
    store.register_asset(_video(), now=1000)
    with pytest.raises(ValueError):
        store.enqueue("owner1", "a1", "ex1", "var1", "key", "v1", now=1000, ttl_s=ttl)
    assert store.enqueue("owner1", "a1", "ex1", "var1", "key", "v1", now=1000).attempt == 0


def test_invalid_clock_does_not_revoke_job(tmp_path: Path) -> None:
    store = Store(tmp_path / "store.db")
    store.register_asset(_video(), now=1000)
    job = store.enqueue("owner1", "a1", "ex1", "var1", "key", "v1", now=1000)
    with pytest.raises(ValueError):
        store.delete_job("owner1", job.id, now=1e308)
    assert store.get_job("owner1", job.id, now=1000).state == JobState.QUEUED


@pytest.mark.parametrize("key", ["pose/a\x00.json", "../pose/a.json"])
def test_invalid_result_key_cannot_complete(tmp_path: Path, key: str) -> None:
    store = Store(tmp_path / "store.db")
    store.register_asset(_video(), now=1000)
    job = store.enqueue("owner1", "a1", "ex1", "var1", "key", "v1", now=1000)
    claimed = store.claim("worker", now=1000)
    assert claimed is not None and claimed.lease_owner is not None
    with pytest.raises(ValueError):
        store.finish(job.id, claimed.lease_owner, result_key=key, now=1001)
    with pytest.raises(ValueError):
        store.fail(job.id, claimed.lease_owner, error="ERROR\n", now=1001)
    assert store.get_job("owner1", job.id, now=1001).state == JobState.RUNNING


class TestAssetTTL:
    def test_asset_ttl_denies_claim_and_read(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0, expires_at=1050.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        with pytest.raises(NotFound):
            s.get_asset("owner1", "a1", now=1051.0)
        assert s.claim("w1", now=1051.0) is None
        assert s.get_job("owner1", j.id, now=1051.0).state == JobState.QUEUED
        with pytest.raises(NotFound):
            s.get_input("owner1", j.id, now=1051.0)


class TestTerminalSuccessFailure:
    def test_terminal_prevents_cancel(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        jc = s.claim("w1", now=1000.0, lease_s=60)
        assert jc is not None
        jf = s.finish(j.id, jc.lease_owner, result_key="r", now=1000.0)
        assert jf.state == JobState.SUCCEEDED
        j2 = s.cancel("owner1", j.id, now=1000.0)
        assert j2.state == JobState.SUCCEEDED

    def test_failed_terminal(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        j = s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        jc = s.claim("w1", now=1000.0, lease_s=60)
        assert jc is not None
        jf = s.fail(j.id, jc.lease_owner, error="ERR", now=1000.0)
        assert jf.state == JobState.FAILED
        j2 = s.cancel("owner1", j.id, now=1000.0)
        assert j2.state == JobState.FAILED


class TestSafePath:
    def test_rejects_all_bad_components(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        bad_paths = [
            "../x",
            "./x",
            ".",
            "..",
            "x//y",
            "x/",
            "x\\y",
            "/x",
            "x/./y",
            "x/../y",
            "x/y/",
        ]
        for bad in bad_paths:
            v = _video(now=1000.0, storage_key=bad)
            with pytest.raises(ValueError):
                s.register_asset(v, now=1000.0)


class TestSameWorkerReacquisition:
    def test_same_worker_reacquire_rejects_old_token(self, tmp_path: Path) -> None:
        s = Store(tmp_path / "s.db")
        v = _video(now=1000.0)
        s.register_asset(v, now=1000.0)
        s.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)
        j1 = s.claim("w1", now=1000.0, lease_s=60)
        assert j1 is not None
        # Reclaim by same worker after lease expiry
        j2 = s.claim("w1", now=1061.0, lease_s=60)
        assert j2 is not None
        # Old token should be rejected
        with pytest.raises(LeaseLost):
            s.heartbeat(j1.id, j1.lease_owner, now=1061.0, lease_s=60)
        # New token should work
        j3 = s.heartbeat(j2.id, j2.lease_owner, now=1061.0, lease_s=60)
        assert j3.lease_owner == j2.lease_owner


class TestConcurrencyTwoStores:
    def test_two_stores_exactly_one_claim(self, tmp_path: Path) -> None:
        db = tmp_path / "s.db"
        s0 = Store(db)
        v = _video(now=1000.0)
        s0.register_asset(v, now=1000.0)
        s0.enqueue("owner1", "a1", "ex1", "var1", "rk1", "vh1", now=1000.0)

        results: list = []
        barrier = threading.Barrier(2)

        def worker() -> None:
            s = Store(db)
            barrier.wait()
            j = s.claim("w", now=1000.0, lease_s=60)
            results.append(j)

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        winners = [r for r in results if r is not None]
        assert len(winners) == 1
