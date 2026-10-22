from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from app import retention
from app.retention import cleanup_once
from providers.pose.artifacts import write_pose_frames

from tests.unit.test_pose_job_artifacts import _build_fixture

TOKEN = "b" * 32
NOW = 1_700_000_000.0


def _committed(tmp_path: Path):
    f = _build_fixture(tmp_path)
    write_pose_frames(f["attempt_dir"], f["frames_key"], f["frames"])
    art_root = tmp_path / "artifacts"
    dest = art_root / "attempts" / f["job"].id / TOKEN
    dest.mkdir(parents=True)
    for item in f["attempt_dir"].iterdir():
        if item.is_dir():
            shutil.copytree(item, dest / item.name)
        else:
            shutil.copy2(item, dest / item.name)
    vid_root = tmp_path / "videos"
    raw = vid_root / "uploads"
    raw.mkdir(parents=True)
    (raw / "asset1.mp4").write_bytes(b"raw video")
    result_key = f"attempts/{f['job'].id}/{TOKEN}/manifest.json"
    claimed = f["request"].job
    f["store"].finish(claimed.id, claimed.lease_owner, result_key=result_key)
    f["art_root"], f["vid_root"], f["result_key"] = art_root, vid_root, result_key
    f["attempt_rel"] = result_key.rsplit("/", 1)[0]
    return f


def _run(f, now=NOW):
    return cleanup_once(f["store"], f["vid_root"], f["art_root"], now=now)


def _sql(f, stmt, args=()):
    with f["store"]._conn() as c:
        c.execute(stmt, args)


def test_before_expiration_nothing_deleted(tmp_path: Path):
    f = _committed(tmp_path)
    counts = _run(f)
    assert counts["raw_removed"] == counts["payloads_removed"] == 0
    assert counts["attempts_removed"] == counts["reports_deleted"] == 0
    assert (f["vid_root"] / "uploads/asset1.mp4").exists()
    assert (f["art_root"] / f["attempt_rel"] / "proxy/proxy.mp4").exists()


def test_raw_ttl_expire_strips_payloads_keeps_report(tmp_path: Path):
    f = _committed(tmp_path)
    _sql(f, "UPDATE assets SET expires_at=? WHERE id='asset1'", (NOW - 1,))
    counts = _run(f)
    assert counts["raw_removed"] == 1
    assert counts["payloads_removed"] == 3  # proxy.mp4, timestamp_map, frames
    assert counts["reports_deleted"] == 0
    attempt = f["art_root"] / f["attempt_rel"]
    assert not (attempt / "proxy/proxy.mp4").exists()
    assert not (attempt / f["frames_key"]).exists()
    assert (attempt / "manifest.json").exists()
    assert (attempt / "request.json").exists()


def test_report_ttl_removes_attempt_keeps_sibling(tmp_path: Path):
    f = _committed(tmp_path)
    sibling = f["art_root"] / "attempts" / "other"
    sibling.mkdir(parents=True)
    (sibling / "keep.txt").write_text("x")
    _sql(f, "UPDATE jobs SET expires_at=?", (NOW - 1,))
    counts = _run(f)
    assert counts["attempts_removed"] == 1 and counts["reports_deleted"] == 1
    assert not (f["art_root"] / f["attempt_rel"]).exists()
    assert (sibling / "keep.txt").exists()
    with f["store"]._conn() as c:
        row = c.execute("SELECT deleted, state, result_key FROM jobs").fetchone()
    assert row["deleted"] == 1 and row["state"] == "succeeded"
    assert row["result_key"] == f["result_key"]
    # Retry: manifest already gone, known-not-present -> silent skip.
    again = _run(f)
    assert again["errors"] == 0 and again["attempts_removed"] == 0


def test_unsafe_storage_key_rejected_outside_preserved(tmp_path: Path):
    f = _committed(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("keep")
    _sql(f, "UPDATE assets SET expires_at=?, payload=? WHERE id='asset1'",
         (NOW - 1, json.dumps({"storage_key": "../outside.txt"})))
    counts = _run(f)
    assert counts["raw_removed"] == 0 and counts["deferred"] >= 1
    assert outside.exists()


def test_active_job_defers_raw(tmp_path: Path):
    f = _committed(tmp_path)
    f["store"].enqueue("owner", "asset1", "lat_pulldown", "v1", "request2", "vhash")
    _sql(f, "UPDATE assets SET expires_at=? WHERE id='asset1'", (NOW - 1,))
    counts = _run(f)
    assert counts["raw_removed"] == 0 and counts["deferred"] >= 1
    assert (f["vid_root"] / "uploads/asset1.mp4").exists()


def test_malformed_manifest_defers_and_preserves(tmp_path: Path):
    f = _committed(tmp_path)
    (f["art_root"] / f["attempt_rel"] / "manifest.json").write_bytes(b"{not json")
    _sql(f, "UPDATE assets SET expires_at=? WHERE id='asset1'", (NOW - 1,))
    _sql(f, "UPDATE jobs SET expires_at=?", (NOW - 1,))
    counts = _run(f)
    assert counts["attempts_removed"] == 0 and counts["payloads_removed"] == 0
    assert counts["deferred"] >= 1
    assert (f["art_root"] / f["attempt_rel"] / "proxy/proxy.mp4").exists()


def test_unlink_error_leaves_metadata(tmp_path: Path, monkeypatch):
    f = _committed(tmp_path)
    _sql(f, "UPDATE jobs SET expires_at=?", (NOW - 1,))
    real = os.unlink
    state = {"raised": False}

    def flaky(*a, **k):
        if not state["raised"]:
            state["raised"] = True
            raise OSError("simulated EACCES")
        return real(*a, **k)

    monkeypatch.setattr(retention.os, "unlink", flaky)
    counts = _run(f)
    assert counts["errors"] >= 1
    with f["store"]._conn() as c:
        row = c.execute("SELECT deleted, result_key FROM jobs").fetchone()
    assert row["deleted"] == 0 and row["result_key"] == f["result_key"]


def test_fd_count_bounded(tmp_path: Path):
    f = _committed(tmp_path)
    _sql(f, "UPDATE assets SET expires_at=? WHERE id='asset1'", (NOW - 1,))
    _sql(f, "UPDATE jobs SET expires_at=?", (NOW - 1,))
    _run(f)
    before = len(os.listdir("/proc/self/fd"))
    _run(f)
    after = len(os.listdir("/proc/self/fd"))
    assert abs(after - before) <= 2


def test_unsafe_roots_rejected(tmp_path: Path):
    f = _committed(tmp_path)
    with pytest.raises(ValueError):
        cleanup_once(f["store"], Path("relative"), f["art_root"], now=NOW)
    with pytest.raises(ValueError):
        cleanup_once(f["store"], f["vid_root"], f["vid_root"] / "sub", now=NOW)
    with pytest.raises(ValueError):
        cleanup_once(f["store"], f["vid_root"], f["art_root"], now=float("nan"))
    assert (f["vid_root"] / "uploads/asset1.mp4").exists()
