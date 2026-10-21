from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.main import app
from app.session import SessionSecurity
from app.store import Store
from contracts.media import VideoAsset


@pytest.fixture
def env_setup(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "jobs.db"
    media_path = tmp_path / "media"
    media_path.mkdir(parents=True, exist_ok=True)
    artifacts_path = tmp_path / "artifacts"
    artifacts_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("VIDEO_ROOT", str(media_path))
    monkeypatch.setenv("ARTIFACT_ROOT", str(artifacts_path))
    monkeypatch.setenv("SESSION_SECRET", "x" * 64)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_ORIGIN", "http://testserver")
    monkeypatch.setenv("MAX_UPLOAD_MB", "100")
    monkeypatch.setenv("MAX_VIDEO_SECONDS", "30")
    monkeypatch.setenv("RAW_MEDIA_TTL_HOURS", "24")
    monkeypatch.setenv("POSE_CHECKPOINT_SHA256", "b" * 64)
    monkeypatch.setenv("REPORT_TTL_DAYS", "7")
    yield tmp_path, str(db_path), str(media_path), str(artifacts_path)


@pytest.fixture
def client(env_setup):
    with TestClient(app, base_url="http://testserver") as c:
        yield c


def _session(client: TestClient) -> tuple[str, str]:
    r = client.get("/v1/session")
    assert r.status_code == 200
    data = r.json()
    return data["csrf_token"], client.cookies["mxr_session"]


def _owner_from_cookie(client: TestClient) -> str:
    cookie = client.cookies["mxr_session"]
    req = Request({"type": "http", "headers": [(b"cookie", f"mxr_session={cookie}".encode())]})
    return SessionSecurity.from_environment().validate(req)


def _headers(csrf: str) -> dict[str, str]:
    return {"Origin": "http://testserver", "X-CSRF-Token": csrf}


def _register_asset(store: Store, owner: str, asset_id: str = "a" * 32) -> None:
    now = datetime.now(timezone.utc)
    asset = VideoAsset(
        id=asset_id,
        owner_session_id=owner,
        storage_key="uploads/video.mp4",
        sha256="a" * 64,
        mime="video/mp4",
        bytes=1024,
        duration_s=5.0,
        width=640,
        height=480,
        rotation=0,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )
    store.register_asset(asset)


def test_create_and_get_status(client: TestClient, env_setup):
    tmp_path, db_path, *_ = env_setup
    store = Store(Path(db_path))
    csrf, _ = _session(client)
    owner = _owner_from_cookie(client)
    _register_asset(store, owner)
    headers = _headers(csrf)
    body = {"video_id": "a" * 32, "exercise_id": "squat", "request_key": "req1"}
    r = client.post("/v1/analyses", json=body, headers=headers)
    assert r.status_code == 202
    data = r.json()
    assert data["analysis_scope"] == "pose_only"
    assert data["lease_owner"] is None
    assert data["result_key"] is None
    job_id = data["id"]
    r2 = client.post("/v1/analyses", json=body, headers=headers)
    assert r2.status_code == 202
    assert r2.json()["id"] == job_id
    r3 = client.get(f"/v1/analyses/{job_id}", headers=headers)
    assert r3.status_code == 200
    assert r3.json()["id"] == job_id


def test_invalid_csrf(client: TestClient):
    _session(client)
    r = client.post("/v1/analyses", json={"video_id": "a" * 32, "exercise_id": "squat", "request_key": "req1"}, headers={"Origin": "http://testserver", "X-CSRF-Token": "bad"})
    assert r.status_code == 403


def test_claim_then_status_still_public(client: TestClient, env_setup):
    tmp_path, db_path, *_ = env_setup
    store = Store(Path(db_path))
    csrf, _ = _session(client)
    owner = _owner_from_cookie(client)
    _register_asset(store, owner)
    headers = _headers(csrf)
    r = client.post("/v1/analyses", json={"video_id": "a" * 32, "exercise_id": "squat", "request_key": "req1"}, headers=headers)
    job_id = r.json()["id"]
    token = store.claim("probe")
    assert token is not None and token.lease_owner is not None
    r2 = client.get(f"/v1/analyses/{job_id}", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["lease_owner"] is None
    assert r2.json()["result_key"] is None


def test_cross_owner_404(client: TestClient, env_setup):
    tmp_path, db_path, *_ = env_setup
    store = Store(Path(db_path))
    csrf1, _ = _session(client)
    owner1 = _owner_from_cookie(client)
    _register_asset(store, owner1)
    r = client.post("/v1/analyses", json={"video_id": "a" * 32, "exercise_id": "squat", "request_key": "req1"}, headers=_headers(csrf1))
    job_id = r.json()["id"]
    client.cookies.clear()
    csrf2, _ = _session(client)
    owner2 = _owner_from_cookie(client)
    _register_asset(store, owner2, asset_id="b" * 32)
    foreign = client.post("/v1/analyses", json={"video_id": "b" * 32, "exercise_id": "squat", "request_key": "req1"}, headers=_headers(csrf2))
    assert foreign.status_code == 202
    r2 = client.get(f"/v1/analyses/{job_id}", headers=_headers(csrf2))
    assert r2.status_code == 404
    r3 = client.get(f"/v1/analyses/{job_id}/result", headers=_headers(csrf2))
    assert r3.status_code == 404


def test_pending_result_409(client: TestClient, env_setup):
    tmp_path, db_path, *_ = env_setup
    store = Store(Path(db_path))
    csrf, _ = _session(client)
    owner = _owner_from_cookie(client)
    _register_asset(store, owner)
    headers = _headers(csrf)
    r = client.post("/v1/analyses", json={"video_id": "a" * 32, "exercise_id": "squat", "request_key": "req1"}, headers=headers)
    job_id = r.json()["id"]
    r2 = client.get(f"/v1/analyses/{job_id}/result", headers=headers)
    assert r2.status_code == 409
    assert r2.json()["code"] == "RESULT_NOT_READY"


def test_cancel_and_delete(client: TestClient, env_setup):
    tmp_path, db_path, *_ = env_setup
    store = Store(Path(db_path))
    csrf, _ = _session(client)
    owner = _owner_from_cookie(client)
    _register_asset(store, owner)
    headers = _headers(csrf)
    r = client.post("/v1/analyses", json={"video_id": "a" * 32, "exercise_id": "squat", "request_key": "req1"}, headers=headers)
    job_id = r.json()["id"]
    r2 = client.post(f"/v1/analyses/{job_id}/cancel", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["state"] == "cancelled"
    r3 = client.delete(f"/v1/analyses/{job_id}", headers=headers)
    assert r3.status_code == 204
    r4 = client.get(f"/v1/analyses/{job_id}", headers=headers)
    assert r4.status_code == 404


def test_invalid_variant_422(client: TestClient, env_setup):
    tmp_path, db_path, *_ = env_setup
    store = Store(Path(db_path))
    csrf, _ = _session(client)
    owner = _owner_from_cookie(client)
    _register_asset(store, owner)
    r = client.post("/v1/analyses", json={"video_id": "a" * 32, "exercise_id": "squat", "request_key": "req1", "variant": "x" * 65}, headers=_headers(csrf))
    assert r.status_code == 422


def test_invalid_request_field_422(client: TestClient, env_setup):
    tmp_path, db_path, *_ = env_setup
    store = Store(Path(db_path))
    csrf, _ = _session(client)
    owner = _owner_from_cookie(client)
    _register_asset(store, owner)
    r = client.post("/v1/analyses", json={"video_id": "a" * 32, "exercise_id": "squat", "request_key": "req1", "owner": "evil"}, headers=_headers(csrf))
    assert r.status_code == 422


def test_missing_session_secret_503(client: TestClient, monkeypatch):
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    r = client.get("/v1/session")
    assert r.status_code == 503
    assert r.json()["code"] == "SESSION_CONFIG_INVALID"


def test_short_session_secret_503(client: TestClient, monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "short")
    r = client.get("/v1/session")
    assert r.status_code == 503
    body = r.json()
    assert body["code"] == "SESSION_CONFIG_INVALID"
    assert "short" not in str(body)


def test_corrupt_result_503_no_leak(client: TestClient, env_setup):
    tmp_path, db_path, media_root, artifacts_root = env_setup
    store = Store(Path(db_path))
    csrf, _ = _session(client)
    owner = _owner_from_cookie(client)
    _register_asset(store, owner)
    headers = _headers(csrf)
    r = client.post("/v1/analyses", json={"video_id": "a" * 32, "exercise_id": "squat", "request_key": "req1"}, headers=headers)
    job_id = r.json()["id"]
    token = store.claim("probe")
    assert token is not None and token.lease_owner is not None
    key = f"attempts/{job_id}/{token.lease_owner}/manifest.json"
    (Path(artifacts_root) / key).parent.mkdir(parents=True, exist_ok=True)
    (Path(artifacts_root) / key).write_bytes(b"PRIVATE_CORRUPT")
    store.finish(job_id, token.lease_owner, result_key=key)
    r2 = client.get(f"/v1/analyses/{job_id}/result", headers=headers)
    assert r2.status_code == 503
    text = r2.text
    assert "PRIVATE_CORRUPT" not in text
    assert str(tmp_path) not in text
    assert r2.headers.get("cache-control") == "no-store"


def test_canonical_id_too_long_404(client: TestClient):
    _session(client)
    r = client.get("/v1/analyses/" + "a" * 33, headers={"Origin": "http://testserver"})
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"
