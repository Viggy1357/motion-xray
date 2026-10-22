from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from app import retention

from scoring.components import (
    ComparisonContext,
    ReferenceBand,
    compare_component,
)

from tests.unit.test_retention import NOW, _committed, _run, _sql


def _band(**kw) -> ReferenceBand:
    base = dict(
        metric_id="M1", unit="deg", lower=10.0, upper=20.0, tolerance=5.0,
        reviewer="rev1", review_status="qualified", source_id="src",
        version="v1", authoritative=True, view_id="refview", variant="var",
        provider="prov", mapping_version="map1",
    )
    base.update(kw)
    return ReferenceBand(**base)


def _ctx(**kw) -> ComparisonContext:
    base = dict(
        user_variant="var", reference_variant="var", user_provider="prov",
        reference_provider="prov", user_mapping_version="map1",
        reference_mapping_version="map1", user_view_id="userview",
        reference_view_id="refview", compatibility="confirmed",
        compatibility_reviewer="rev1", compatibility_version="c1",
    )
    base.update(kw)
    return ComparisonContext(**base)


def _receipt_path(f) -> Path:
    attempt = f["art_root"] / f["attempt_rel"]
    token = f["attempt_rel"].split("/")[-1]
    return attempt.parent / f".retention-{token}.json"


def _job_deleted(f) -> int:
    with f["store"]._conn() as con:
        return con.execute("SELECT deleted FROM jobs").fetchone()[0]


def test_malformed_frames_key_preserves_request_json(tmp_path: Path):
    f = _committed(tmp_path)
    mpath = f["art_root"] / f["attempt_rel"] / "manifest.json"
    art = json.loads(mpath.read_text())
    art["pose"]["frames_artifact_key"] = "pose/evil.jsonl"  # fails _POSE_KEY_RE
    mpath.write_text(json.dumps(art))
    _sql(f, "UPDATE assets SET expires_at=? WHERE id='asset1'", (NOW - 1,))
    _sql(f, "UPDATE jobs SET expires_at=?", (NOW - 1,))
    counts = _run(f)
    assert counts["attempts_removed"] == 0 and counts["payloads_removed"] == 0
    assert counts["deferred"] >= 1
    attempt = f["art_root"] / f["attempt_rel"]
    assert (attempt / "request.json").exists()
    assert (attempt / "proxy/proxy.mp4").exists()


def test_symlink_ancestor_raw_key_outside_untouched(tmp_path: Path):
    f = _committed(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "secret.mp4"
    target.write_bytes(b"keep me")
    (f["vid_root"] / "link").symlink_to(outside, target_is_directory=True)
    _sql(f, "UPDATE assets SET expires_at=?, payload=? WHERE id='asset1'",
         (NOW - 1, json.dumps({"storage_key": "link/secret.mp4"})))
    counts = _run(f)
    assert counts["raw_removed"] == 0
    assert counts["errors"] >= 1 or counts["deferred"] >= 1
    assert target.exists() and target.read_bytes() == b"keep me"


def test_symlink_ancestor_attempt_path_untouched(tmp_path: Path):
    f = _committed(tmp_path)
    outside = tmp_path / "outside_att"
    outside.mkdir()
    (outside / "keep.txt").write_text("x")
    attempt = f["art_root"] / f["attempt_rel"]
    real = attempt.parent / "real_payload"
    shutil.move(str(attempt / "proxy"), str(real))
    (attempt / "proxy").symlink_to(real, target_is_directory=True)
    _sql(f, "UPDATE jobs SET expires_at=?", (NOW - 1,))
    counts = _run(f)
    # rmtree on a dir containing a symlinked subdir must not follow it.
    assert (real / "proxy.mp4").exists() or counts["errors"] >= 1
    assert (outside / "keep.txt").exists()


def test_malformed_manifest_no_fd_leak_repeated(tmp_path: Path):
    f = _committed(tmp_path)
    (f["art_root"] / f["attempt_rel"] / "manifest.json").write_bytes(b"{bad")
    _sql(f, "UPDATE jobs SET expires_at=?", (NOW - 1,))
    _run(f)
    before = len(os.listdir("/proc/self/fd"))
    for _ in range(10):
        _run(f)
    after = len(os.listdir("/proc/self/fd"))
    assert abs(after - before) <= 2


def test_partial_rmtree_retry_with_receipt(tmp_path: Path, monkeypatch):
    """rmtree fails after manifest.json is removed; the durable receipt lets
    the next cleanup finish the committed attempt removal safely."""
    f = _committed(tmp_path)
    _sql(f, "UPDATE jobs SET expires_at=?", (NOW - 1,))
    attempt = f["art_root"] / f["attempt_rel"]
    sibling = attempt.parent / "unknown_sibling.txt"
    sibling.write_text("keep")
    real_rmtree = shutil.rmtree

    def flaky(name, dir_fd=None):
        dfd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dir_fd)
        try:
            os.unlink("manifest.json", dir_fd=dfd)
        finally:
            os.close(dfd)
        raise OSError("simulated partial failure")

    monkeypatch.setattr(retention.shutil, "rmtree", flaky)
    first = _run(f)
    assert first["errors"] >= 1 and first["attempts_removed"] == 0
    assert not (attempt / "manifest.json").exists()
    assert (attempt / "proxy/proxy.mp4").exists()
    receipt = _receipt_path(f)
    assert receipt.exists()  # proof of earlier manifest validation persists
    monkeypatch.setattr(retention.shutil, "rmtree", real_rmtree)
    second = _run(f)
    assert second["attempts_removed"] == 1
    assert not attempt.exists()
    assert sibling.exists()  # unrelated sibling preserved
    assert not receipt.exists()  # receipt removed after job marked deleted
    assert _job_deleted(f) == 1


def test_invalid_receipt_fails_closed(tmp_path: Path):
    f = _committed(tmp_path)
    _sql(f, "UPDATE jobs SET expires_at=?", (NOW - 1,))
    attempt = f["art_root"] / f["attempt_rel"]
    _receipt_path(f).write_text(
        '{"format_version":"cleanup-receipt-v1","job_id":"evil"}')
    counts = _run(f)
    assert counts["attempts_removed"] == 0 and counts["deferred"] >= 1
    assert (attempt / "manifest.json").exists()
    assert (attempt / "proxy/proxy.mp4").exists()


def test_receipt_write_failure_no_delete(tmp_path: Path, monkeypatch):
    f = _committed(tmp_path)
    _sql(f, "UPDATE jobs SET expires_at=?", (NOW - 1,))
    attempt = f["art_root"] / f["attempt_rel"]
    real_open = os.open

    def bad_open(name, flags, mode=0o777, *, dir_fd=None):
        if isinstance(name, str) and name.startswith(".retention-") and flags & os.O_CREAT:
            raise OSError("receipt write blocked")
        return real_open(name, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(retention.os, "open", bad_open)
    counts = _run(f)
    assert counts["errors"] >= 1 and counts["attempts_removed"] == 0
    assert (attempt / "manifest.json").exists()
    assert (attempt / "proxy/proxy.mp4").exists()
    assert _job_deleted(f) == 0


def test_unknown_comparability_overflow_no_inf():
    band = _band(lower=-1e308, upper=-0.5e308)
    ctx = _ctx(compatibility="unknown", compatibility_reviewer=None)
    r = compare_component(1e308, None, "deg", band, ctx)
    assert r.score is None and r.score_kind is None
    assert r.score_reason == "non_finite_deviation"
    assert r.valid_technique_score is None
    for v in (r.delta_low, r.delta_high, r.signed_deviation, r.absolute_distance):
        assert v is None or v != float("inf")


def test_view_mismatch_descriptive_not_scored():
    band = _band(view_id="otherview")
    ctx = _ctx()  # reference_view_id="refview" != band.view_id
    r = compare_component(25.0, None, "deg", band, ctx)
    assert r.comparability == "incompatible"
    assert r.score is None and r.score_kind is None
    assert r.score_reason == "incompatible_metadata"
    assert r.valid_technique_score is None
    assert r.delta_high == 5.0 and r.absolute_distance == 5.0  # descriptive only


def test_owner_prototype_score_kind_and_no_technique_claim():
    band = _band(review_status="owner_prototype", authoritative=False)
    r = compare_component(15.0, None, "deg", band, _ctx())
    assert r.score == 100.0
    assert r.score_kind == "owner_reviewed_reference_similarity"
    assert r.score_reason == "owner_prototype_not_authoritative"
    assert r.valid_technique_score is None
