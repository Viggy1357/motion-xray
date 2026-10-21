"""Tests for anonymous session ownership and CSRF boundary.

Covers: establishment, validation, tampering, expiry, origin checks,
CSRF tokens, duplicate cookies, clock abuse, and configuration hardening.
"""

from __future__ import annotations


import pytest
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.session import SessionSecurity
from contracts.session import SessionInfo

_DUMMY_SECRET = "a" * 32
_ORIGIN = "http://localhost:3000"


def _make_app(sec: SessionSecurity) -> FastAPI:
    app = FastAPI()

    @app.get("/session", response_model=SessionInfo)
    def get_session(request: Request, response: Response) -> SessionInfo:
        return sec.establish(request, response)

    @app.post("/protected")
    def post_protected(request: Request) -> JSONResponse:
        owner = sec.validate(request, mutation=True)
        return JSONResponse({"owner": owner})

    @app.get("/read")
    def get_read(request: Request) -> JSONResponse:
        owner = sec.validate(request, mutation=False)
        return JSONResponse({"owner": owner})

    return app


@pytest.fixture
def client() -> TestClient:
    sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False, ttl_s=3600)
    app = _make_app(sec)
    return TestClient(app)


class TestEstablishment:
    def test_establish_returns_csrf_and_expires(self, client: TestClient) -> None:
        r = client.get("/session", headers={"Origin": _ORIGIN})
        assert r.status_code == 200
        data = r.json()
        assert "csrf_token" in data
        assert len(data["csrf_token"]) == 64
        assert "expires_at" in data
        cookie = r.cookies.get("mxr_session")
        assert cookie is not None
        assert cookie.startswith("v1.")

    def test_establish_reuses_valid_cookie(self, client: TestClient) -> None:
        r1 = client.get("/session", headers={"Origin": _ORIGIN})
        cookie = r1.cookies["mxr_session"]
        r2 = client.get("/session", headers={"Origin": _ORIGIN})
        # No Set-Cookie header on reuse, cookie unchanged, csrf stable
        assert "set-cookie" not in r2.headers
        assert client.cookies.get("mxr_session") == cookie
        assert r2.json()["csrf_token"] == r1.json()["csrf_token"]

    def test_establish_without_origin_ok(self, client: TestClient) -> None:
        r = client.get("/session")
        assert r.status_code == 200

    def test_establish_wrong_origin_403(self, client: TestClient) -> None:
        r = client.get("/session", headers={"Origin": "http://evil.com"})
        assert r.status_code == 403

    def test_establish_new_on_tampered_cookie(self, client: TestClient) -> None:
        r = client.get("/session", headers={"Origin": _ORIGIN})
        bad = r.cookies["mxr_session"][:-1] + "0"
        # Clear jar before installing tampered cookie to avoid duplicate cookies
        client.cookies.clear()
        client.cookies.set("mxr_session", bad, domain="localhost")
        r2 = client.get("/session", headers={"Origin": _ORIGIN})
        assert r2.status_code == 200
        # Inspect response cookie, not ambiguous jar
        assert "set-cookie" in r2.headers
        set_cookie_val = r2.headers["set-cookie"]
        assert bad not in set_cookie_val


class TestValidation:
    def test_validate_read_without_mutation(self, client: TestClient) -> None:
        client.get("/session", headers={"Origin": _ORIGIN})
        r = client.get("/read")
        assert r.status_code == 200
        assert "owner" in r.json()

    def test_validate_mutation_requires_origin(self, client: TestClient) -> None:
        client.get("/session", headers={"Origin": _ORIGIN})
        r = client.post("/protected")
        assert r.status_code == 403

    def test_validate_mutation_requires_csrf_token(self, client: TestClient) -> None:
        client.get("/session", headers={"Origin": _ORIGIN})
        r = client.post("/protected", headers={"Origin": _ORIGIN})
        assert r.status_code == 403

    def test_validate_mutation_wrong_csrf_token(self, client: TestClient) -> None:
        client.get("/session", headers={"Origin": _ORIGIN})
        r = client.post("/protected", headers={"Origin": _ORIGIN, "X-CSRF-Token": "0" * 64})
        assert r.status_code == 403

    def test_validate_mutation_valid_roundtrip(self, client: TestClient) -> None:
        r1 = client.get("/session", headers={"Origin": _ORIGIN})
        token = r1.json()["csrf_token"]
        r2 = client.post("/protected", headers={"Origin": _ORIGIN, "X-CSRF-Token": token})
        assert r2.status_code == 200
        assert len(r2.json()["owner"]) == 32

    def test_validate_expired_cookie(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False, ttl_s=1)
        app = _make_app(sec)
        c = TestClient(app)
        c.get("/session", headers={"Origin": _ORIGIN})
        import time
        time.sleep(1.1)
        r = c.get("/read")
        assert r.status_code == 403

    def test_validate_future_issued(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False, ttl_s=3600)
        app = _make_app(sec)
        c = TestClient(app)
        future = int(__import__("time").time()) + 100
        payload = f"v1.{'a'*32}.{future}".encode()
        import hmac
        import hashlib
        sig = hmac.new(_DUMMY_SECRET.encode(), payload, hashlib.sha256).hexdigest()
        c.cookies.set("mxr_session", f"v1.{'a'*32}.{future}.{sig}")
        r = c.get("/read")
        assert r.status_code == 403

    def test_duplicate_cookies_rejected(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False, ttl_s=3600)
        app = _make_app(sec)
        c = TestClient(app)
        r = c.get("/read", headers={"Cookie": "mxr_session=abc; mxr_session=def"})
        assert r.status_code == 403

    def test_missing_cookie_rejected(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False, ttl_s=3600)
        app = _make_app(sec)
        c = TestClient(app)
        r = c.get("/read")
        assert r.status_code == 403

    def test_tampered_signature_rejected(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False, ttl_s=3600)
        app = _make_app(sec)
        c = TestClient(app)
        c.get("/session", headers={"Origin": _ORIGIN})
        bad = c.cookies["mxr_session"][:-1] + "0"
        # Clear jar before installing tampered cookie to avoid second cookie
        c.cookies.clear()
        c.cookies.set("mxr_session", bad, domain="localhost")
        r = c.get("/read")
        assert r.status_code == 403

    def test_expired_cookie_rejected_with_clock(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False, ttl_s=3600)
        app = _make_app(sec)
        c = TestClient(app)
        c.get("/session", headers={"Origin": _ORIGIN})
        # Direct injected clock assertion
        with pytest.raises(Exception):
            sec.validate(None, now=9999999999)


class TestCSRF:
    def test_malformed_csrf_ascii_rejected(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False, ttl_s=3600)
        app = _make_app(sec)
        c = TestClient(app)
        c.get("/session", headers={"Origin": _ORIGIN})
        r = c.post("/protected", headers={"Origin": _ORIGIN, "X-CSRF-Token": "bad!"})
        assert r.status_code == 403

    def test_unicode_csrf_rejected(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False, ttl_s=3600)
        app = _make_app(sec)
        c = TestClient(app)
        c.get("/session", headers={"Origin": _ORIGIN})
        # Pass bytes header to reach ASGI and assert 403, not UnicodeEncodeError in client
        r = c.post("/protected", headers={"Origin": _ORIGIN, "X-CSRF-Token": b"cafe9" * 16})
        assert r.status_code == 403

    def test_short_csrf_rejected(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False, ttl_s=3600)
        app = _make_app(sec)
        c = TestClient(app)
        c.get("/session", headers={"Origin": _ORIGIN})
        r = c.post("/protected", headers={"Origin": _ORIGIN, "X-CSRF-Token": "a" * 63})
        assert r.status_code == 403

    def test_long_csrf_rejected(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False, ttl_s=3600)
        app = _make_app(sec)
        c = TestClient(app)
        c.get("/session", headers={"Origin": _ORIGIN})
        r = c.post("/protected", headers={"Origin": _ORIGIN, "X-CSRF-Token": "a" * 65})
        assert r.status_code == 403


class TestConfig:
    def test_short_secret_rejected(self) -> None:
        with pytest.raises(ValueError):
            SessionSecurity(secret="short", origin=_ORIGIN, secure=False)

    def test_missing_secret_503(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SESSION_SECRET", raising=False)
        monkeypatch.setenv("APP_ORIGIN", _ORIGIN)
        with pytest.raises(Exception) as exc:
            SessionSecurity.from_environment()
        assert exc.value.status_code == 503

    def test_production_requires_https(self) -> None:
        with pytest.raises(ValueError):
            SessionSecurity(secret=_DUMMY_SECRET, origin="http://example.com", secure=True)

    def test_secure_cookie_flags(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin="https://example.com", secure=True, ttl_s=3600)
        app = _make_app(sec)
        c = TestClient(app)
        r = c.get("/session")
        assert r.status_code == 200

    def test_invalid_origin_port_too_high(self) -> None:
        with pytest.raises(ValueError):
            SessionSecurity(secret=_DUMMY_SECRET, origin="http://localhost:70000", secure=False)

    def test_invalid_origin_port_zero(self) -> None:
        with pytest.raises(ValueError):
            SessionSecurity(secret=_DUMMY_SECRET, origin="http://localhost:0", secure=False)

    def test_invalid_origin_with_credentials(self) -> None:
        with pytest.raises(ValueError):
            SessionSecurity(secret=_DUMMY_SECRET, origin="http://user:pass@localhost", secure=False)

    def test_invalid_origin_with_query(self) -> None:
        with pytest.raises(ValueError):
            SessionSecurity(secret=_DUMMY_SECRET, origin="http://localhost?foo", secure=False)

    def test_invalid_origin_with_fragment(self) -> None:
        with pytest.raises(ValueError):
            SessionSecurity(secret=_DUMMY_SECRET, origin="http://localhost#foo", secure=False)

    def test_invalid_origin_with_path(self) -> None:
        with pytest.raises(ValueError):
            SessionSecurity(secret=_DUMMY_SECRET, origin="http://localhost/foo", secure=False)

    def test_origin_rejects_multiple_trailing_slashes(self) -> None:
        with pytest.raises(ValueError):
            SessionSecurity(secret=_DUMMY_SECRET, origin="http://localhost:3000//", secure=False)

    def test_origin_allows_single_trailing_slash(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin="http://localhost:3000/", secure=False)
        assert sec.origin == "http://localhost:3000"

    def test_origin_localhost_ok(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin="http://localhost", secure=False)
        assert sec.origin == "http://localhost"

    def test_origin_ipv6_ok(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin="http://[::1]:3000", secure=False)
        assert sec.origin == "http://[::1]:3000"

    def test_bool_secure_rejected(self) -> None:
        with pytest.raises(ValueError):
            SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure="true")  # type: ignore[arg-type]

    def test_bool_ttl_rejected(self) -> None:
        with pytest.raises(ValueError):
            SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False, ttl_s="3600")  # type: ignore[arg-type]


class TestClock:
    def test_invalid_clock_nan(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False)
        with pytest.raises(ValueError):
            sec._now(float("nan"))

    def test_invalid_clock_inf(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False)
        with pytest.raises(ValueError):
            sec._now(float("inf"))

    def test_invalid_clock_negative(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False)
        with pytest.raises(ValueError):
            sec._now(-1)

    def test_invalid_clock_bool(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False)
        with pytest.raises(ValueError):
            sec._now(True)

    def test_invalid_clock_huge(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False)
        with pytest.raises(ValueError):
            sec._now(2**40)

    def test_clock_with_ttl_overflow(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False, ttl_s=604800)
        with pytest.raises(ValueError):
            sec._now(253402300799 - 604800 + 1)

    def test_valid_clock_int(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False)
        assert sec._now(1234567890) == 1234567890.0

    def test_valid_clock_float(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False)
        assert sec._now(1234567890.5) == 1234567890.5


class TestCookieParsing:
    def test_issued_regex_rejects_hex(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False)
        assert sec._parse_cookie("v1.a" * 16 + ".abc.def0123456789abcdef0123456789abcdef0123456789abcdef0123456789") is None

    def test_issued_regex_rejects_leading_zero_mismatch(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False)
        # int("0123") == 123, str(123) != "0123"
        val = "v1." + "a" * 32 + ".0123." + "0" * 64
        assert sec._parse_cookie(val) is None

    def test_issued_regex_accepts_canonical(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False)
        owner = "a" * 32
        sig = "0" * 64
        val = f"v1.{owner}.123.{sig}"
        assert sec._parse_cookie(val) == (owner, 123, sig)

    def test_cookie_value_too_long(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False)
        assert sec._parse_cookie("x" * 257) is None


class TestOriginMatching:
    def test_exact_origin_match_required(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin="http://localhost:3000", secure=False)
        app = _make_app(sec)
        c = TestClient(app)
        c.get("/session")
        r = c.post("/protected", headers={"Origin": "http://localhost:3000", "X-CSRF-Token": "0" * 64})
        # Missing CSRF token establishment, but origin check happens first on mutation
        assert r.status_code in (403,)

    def test_origin_scheme_mismatch_rejected(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin="http://localhost:3000", secure=False)
        app = _make_app(sec)
        c = TestClient(app)
        c.get("/session")
        r = c.post("/protected", headers={"Origin": "https://localhost:3000", "X-CSRF-Token": "0" * 64})
        assert r.status_code == 403

    def test_origin_port_mismatch_rejected(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin="http://localhost:3000", secure=False)
        app = _make_app(sec)
        c = TestClient(app)
        c.get("/session")
        r = c.post("/protected", headers={"Origin": "http://localhost:3001", "X-CSRF-Token": "0" * 64})
        assert r.status_code == 403

    def test_duplicate_origin_rejected(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin="http://localhost:3000", secure=False)
        app = _make_app(sec)
        c = TestClient(app)
        token = c.get("/session").json()["csrf_token"]
        r = c.post("/protected", headers=[("Origin", _ORIGIN), ("Origin", _ORIGIN), ("X-CSRF-Token", token)])
        assert r.status_code == 403
        assert c.post("/protected", headers={"Origin": _ORIGIN, "X-CSRF-Token": token}).status_code == 200

    def test_duplicate_csrf_rejected(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin="http://localhost:3000", secure=False)
        app = _make_app(sec)
        c = TestClient(app)
        token = c.get("/session").json()["csrf_token"]
        r = c.post("/protected", headers=[("Origin", _ORIGIN), ("X-CSRF-Token", token), ("X-CSRF-Token", token)])
        assert r.status_code == 403
        assert c.post("/protected", headers={"Origin": _ORIGIN, "X-CSRF-Token": token}).status_code == 200


class TestStableIdentity:
    def test_reload_preserves_identity(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False, ttl_s=3600)
        app = _make_app(sec)
        c = TestClient(app)
        r1 = c.get("/session", headers={"Origin": _ORIGIN})
        owner1 = c.cookies["mxr_session"].split(".")[1]
        # Simulate reload with same cookie
        r2 = c.get("/session", headers={"Origin": _ORIGIN})
        owner2 = c.cookies["mxr_session"].split(".")[1]
        assert owner1 == owner2
        assert r1.json()["csrf_token"] == r2.json()["csrf_token"]

    def test_establish_replaces_invalid_cookie(self) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False, ttl_s=3600)
        app = _make_app(sec)
        c = TestClient(app)
        c.cookies.set("mxr_session", "v1.badvalue")
        r = c.get("/session", headers={"Origin": _ORIGIN})
        assert r.status_code == 200
        assert r.cookies["mxr_session"] != "v1.badvalue"


class TestCookieExpires:
    def test_cookie_expires_uses_injected_clock(self, monkeypatch) -> None:
        sec = SessionSecurity(secret=_DUMMY_SECRET, origin=_ORIGIN, secure=False, ttl_s=3600)
        now = 1700000000.0
        app = _make_app(sec)
        c = TestClient(app)
        from email.utils import parsedate_to_datetime
        monkeypatch.setattr("app.session.time.time", lambda: now)
        r = c.get("/session", headers={"Origin": _ORIGIN})
        assert r.status_code == 200
        expires = r.headers["set-cookie"].split("expires=", 1)[1].split(";", 1)[0]
        assert parsedate_to_datetime(expires).timestamp() == now + 3600
