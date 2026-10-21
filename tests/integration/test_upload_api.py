from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import uploads
from app.ingest import UploadRejected
from app.store import Store


@pytest.fixture
def env_setup(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "test.db"
    media_path = tmp_path / "media"
    media_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("VIDEO_ROOT", str(media_path))
    monkeypatch.setenv("SESSION_SECRET", "x" * 64)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_ORIGIN", "http://testserver")
    monkeypatch.setenv("MAX_UPLOAD_MB", "100")
    monkeypatch.setenv("MAX_VIDEO_SECONDS", "30")
    monkeypatch.setenv("RAW_MEDIA_TTL_HOURS", "24")
    store = Store(Path(db_path))
    monkeypatch.setattr(uploads, "get_store", lambda: store)
    yield tmp_path, str(db_path), str(media_path), store


@pytest.fixture
def app(env_setup):
    test_app = FastAPI()
    test_app.include_router(uploads.router)
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app, base_url="http://testserver")


def _session(client: TestClient) -> tuple[str, str]:
    r = client.get("/v1/session")
    assert r.status_code == 200
    data = r.json()
    csrf = data["csrf_token"]
    cookie = r.cookies["mxr_session"]
    return csrf, cookie


def test_session_no_store(client: TestClient):
    r = client.get("/v1/session")
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    assert "mxr_session" in r.cookies


def test_session_second_get_404(client: TestClient):
    r = client.get("/v1/session")
    assert r.status_code == 200
    cookie = r.cookies["mxr_session"]
    r2 = client.get("/v1/session", headers={"Cookie": f"mxr_session={cookie}"})
    assert r2.status_code == 200
    r3 = client.get("/v1/session", headers={"Cookie": f"mxr_session={cookie}; mxr_session={cookie}"})
    assert r3.status_code == 403
    assert r3.headers["cache-control"] == "no-store"


def test_upload_no_csrf(client: TestClient, monkeypatch):
    csrf, cookie = _session(client)
    called = False
    async def fake_ingest(*args, **kwargs):
        nonlocal called
        called = True
        return None
    monkeypatch.setattr(uploads, "ingest_video", fake_ingest)
    r = client.post(
        "/v1/videos",
        headers={"Cookie": f"mxr_session={cookie}", "Origin": "http://testserver", "Content-Type": "video/mp4"},
        content=b"x",
    )
    assert r.status_code == 403
    assert r.headers["cache-control"] == "no-store"
    assert not called


def test_upload_wrong_origin(client: TestClient, monkeypatch):
    csrf, cookie = _session(client)
    called = False
    async def fake_ingest(*args, **kwargs):
        nonlocal called
        called = True
        return None
    monkeypatch.setattr(uploads, "ingest_video", fake_ingest)
    r = client.post(
        "/v1/videos",
        headers={"Cookie": f"mxr_session={cookie}", "X-CSRF-Token": csrf, "Origin": "http://evil", "Content-Type": "video/mp4"},
        content=b"x",
    )
    assert r.status_code == 403
    assert not called


def test_upload_no_cookie(client: TestClient, monkeypatch):
    csrf, _ = _session(client)
    client.cookies.clear()
    called = False
    async def fake_ingest(*args, **kwargs):
        nonlocal called
        called = True
        return None
    monkeypatch.setattr(uploads, "ingest_video", fake_ingest)
    r = client.post(
        "/v1/videos",
        headers={"X-CSRF-Token": csrf, "Origin": "http://testserver", "Content-Type": "video/mp4"},
        content=b"x",
    )
    assert r.status_code == 403
    assert not called


def test_upload_missing_consent(client: TestClient):
    csrf, cookie = _session(client)
    r = client.post(
        "/v1/videos",
        headers={"Cookie": f"mxr_session={cookie}", "X-CSRF-Token": csrf, "Origin": "http://testserver", "Content-Type": "video/mp4"},
        content=b"x",
    )
    assert r.status_code == 400
    assert r.headers["cache-control"] == "no-store"
    assert r.json()["code"] == "CONSENT_REQUIRED"


def test_upload_wrong_mime(client: TestClient):
    csrf, cookie = _session(client)
    r = client.post(
        "/v1/videos",
        headers={"Cookie": f"mxr_session={cookie}", "X-CSRF-Token": csrf, "Origin": "http://testserver", "X-Upload-Consent": "true", "Content-Type": "video/avi"},
        content=b"x",
    )
    assert r.status_code == 415
    assert r.json()["code"] == "INVALID_MEDIA"


def test_upload_too_large(client: TestClient, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    csrf, cookie = _session(client)
    async def fake_ingest(*args, **kwargs):
        raise UploadRejected(413, "TOO_LARGE", "too large")
    monkeypatch.setattr(uploads, "ingest_video", fake_ingest)
    r = client.post(
        "/v1/videos",
        headers={"Cookie": f"mxr_session={cookie}", "X-CSRF-Token": csrf, "Origin": "http://testserver", "X-Upload-Consent": "true", "Content-Type": "video/mp4"},
        content=b"x" * (2 * 1024 * 1024),
    )
    assert r.status_code == 413
    assert r.json()["code"] == "TOO_LARGE"


def test_upload_invalid_probe(client: TestClient, monkeypatch):
    csrf, cookie = _session(client)
    async def fake_ingest(*args, **kwargs):
        raise UploadRejected(422, "INVALID_PROBE", "probe failed")
    monkeypatch.setattr(uploads, "ingest_video", fake_ingest)
    r = client.post(
        "/v1/videos",
        headers={"Cookie": f"mxr_session={cookie}", "X-CSRF-Token": csrf, "Origin": "http://testserver", "X-Upload-Consent": "true", "Content-Type": "video/mp4"},
        content=b"x",
    )
    assert r.status_code == 422
    assert r.json()["code"] == "INVALID_PROBE"


def test_upload_integrated(client: TestClient, env_setup, monkeypatch):
    from app import ingest as ingest_mod
    from app.ingest import MediaInfo
    monkeypatch.setattr(ingest_mod, "probe_media", lambda path, declared_mime, *, max_duration_s=30: MediaInfo(duration_s=1.0, width=100, height=100, rotation=0, mime=declared_mime))
    csrf, cookie = _session(client)
    data = b"\x00\x00\x00\x20ftypisom" + b"\x00" * 1000
    r = client.post(
        "/v1/videos",
        headers={"Cookie": f"mxr_session={cookie}", "X-CSRF-Token": csrf, "Origin": "http://testserver", "X-Upload-Consent": "true", "Content-Type": "video/mp4"},
        content=data,
    )
    assert r.status_code == 201
    assert r.headers["cache-control"] == "no-store"
    body = r.json()
    assert body["mime"] == "video/mp4"
    assert body["owner_session_id"] == cookie.split(".")[1]
    assert body["bytes"] == len(data)
    assert body["sha256"] == hashlib.sha256(data).hexdigest()
    assert body["duration_s"] == 1.0
    assert body["width"] == 100
    assert body["height"] == 100

    # GET metadata
    vid = body["id"]
    r2 = client.get(
        f"/v1/videos/{vid}",
        headers={"Cookie": f"mxr_session={cookie}", "Origin": "http://testserver"},
    )
    assert r2.status_code == 200
    assert r2.headers["cache-control"] == "no-store"
    meta = r2.json()
    assert meta["id"] == vid
    assert meta["sha256"] == body["sha256"]

    # cross-owner 404
    client.cookies.clear()
    csrf2, cookie2 = _session(client)
    r3 = client.get(
        f"/v1/videos/{vid}",
        headers={"Cookie": f"mxr_session={cookie2}", "Origin": "http://testserver"},
    )
    assert r3.status_code == 404
    assert r3.json()["code"] == "NOT_FOUND"
    assert r3.headers["cache-control"] == "no-store"


def test_no_session_secret(client: TestClient, monkeypatch):
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    r = client.get("/v1/session")
    assert r.status_code == 503
    assert r.json()["code"] == "SESSION_CONFIG_INVALID"
    assert r.headers["cache-control"] == "no-store"


def test_oversized_asset_identifier_is_private_not_server_error(client: TestClient):
    _session(client)
    response = client.get("/v1/videos/" + "a" * 257)
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
    assert response.headers["cache-control"] == "no-store"


def test_bad_db_url(client: TestClient, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://bad")
    r = client.get("/v1/session")
    assert r.status_code == 503
    body = r.json()
    assert body["code"] == "CONFIG_INVALID"
    assert r.headers["cache-control"] == "no-store"


def test_bad_budget(client: TestClient, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "200")
    r = client.get("/v1/session")
    assert r.status_code == 503
    body = r.json()
    assert body["code"] == "CONFIG_INVALID"
    assert r.headers["cache-control"] == "no-store"


def test_openapi_binary_declared(client: TestClient):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    post = spec["paths"]["/v1/videos"]["post"]
    body = post["requestBody"]["content"]
    for mime in ("video/mp4", "video/quicktime", "video/webm"):
        assert mime in body
        assert body[mime]["schema"]["format"] == "binary"
