"""Anonymous session ownership and CSRF boundary for FastAPI/Starlette.

Stateless signed identity using HMAC-SHA256. No server-side session storage.
"""

from __future__ import annotations

import hashlib
import hmac
import math
import os
import re
import secrets
import time
from datetime import datetime, timezone
from typing import Final
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, Response
from starlette.status import HTTP_403_FORBIDDEN, HTTP_503_SERVICE_UNAVAILABLE

from contracts.session import SessionInfo

_COOKIE_NAME: Final = "mxr_session"
_VERSION: Final = "v1"
_MAX_TOTAL_LEN: Final = 256


class SessionSecurity:
    """Configuration and validator for session security policy.

    All validation happens at construction; callers may assume the instance
    is well-formed and safe to use.
    """

    def __init__(
        self,
        *,
        secret: str,
        origin: str,
        secure: bool,
        ttl_s: int = 86400,
    ) -> None:
        if not isinstance(secure, bool):
            raise ValueError("secure must be boolean")
        if not isinstance(secret, str) or len(secret.encode("utf-8")) < 32:
            raise ValueError("secret must be >= 32 UTF-8 bytes")
        self._secret: Final = secret.encode("utf-8")

        scheme, host, port = self._parse_origin(origin)
        if secure and scheme != "https":
            raise ValueError("secure production requires HTTPS origin")
        self.origin: Final = f"{scheme}://{host}" + (f":{port}" if (port != 443 and scheme == "https") or (port != 80 and scheme == "http") else "")
        self._secure: Final = bool(secure)

        if isinstance(ttl_s, bool) or not isinstance(ttl_s, int) or ttl_s <= 0 or ttl_s > 604800:
            raise ValueError("ttl must be positive and <= 604800")
        self.ttl_s: Final = ttl_s

    @staticmethod
    def _parse_origin(value: str) -> tuple[str, str, int]:
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("origin scheme must be http or https")
        if not parsed.hostname:
            raise ValueError("origin must have a valid hostname")
        host = parsed.hostname
        # Reject spaces and control characters in hostname
        if any(ord(c) < 0x21 or c == ' ' for c in host):
            raise ValueError("origin hostname contains invalid characters")
        # Validate hostname is valid (IPv6 or regular hostname, no path/query/userinfo)
        if '/' in host or '?' in host or '#' in host or '@' in host:
            raise ValueError("origin hostname contains invalid characters")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("origin must not contain credentials")
        if parsed.path not in ("", "/"):
            raise ValueError("origin path must be empty or /")
        if parsed.query or parsed.fragment:
            raise ValueError("origin must not contain query or fragment")
        # Reject multiple trailing slashes - only exactly one configured slash allowed
        # urlsplit normalizes path, but we need to check raw for multiple slashes
        if '//' in value.rsplit('?', 1)[0].rsplit('#', 1)[0]:
            # Check if it's in the path portion (after host)
            netloc_end = value.find('://') + 3
            path_start = value.find('/', netloc_end)
            if path_start != -1 and '//' in value[path_start:]:
                raise ValueError("origin must not contain multiple slashes")
        port = parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
        if not (1 <= port <= 65535):
            raise ValueError("origin port must be 1..65535")
        # Preserve IPv6 brackets when reconstructing origin
        if ':' in host and not host.startswith('['):
            # IPv6 without brackets - urlsplit strips them, need to re-add
            pass
        netloc = parsed.netloc
        # Extract host with brackets for IPv6
        if ']' in netloc:
            bracket_end = netloc.find(']') + 1
            host_with_brackets = netloc[:bracket_end]
        else:
            host_with_brackets = host
        return parsed.scheme, host_with_brackets, port

    @classmethod
    def from_environment(cls) -> "SessionSecurity":
        """Load configuration from environment variables.

        Raises HTTPException(503) on missing or invalid config so the
        application fails closed rather than booting with a weak secret.
        """
        secret = os.environ.get("SESSION_SECRET")
        origin = os.environ.get("APP_ORIGIN", "http://localhost:3000")
        env = os.environ.get("APP_ENV", "development")
        secure = env not in ("development", "test")

        errors: list[str] = []
        if not secret:
            errors.append("SESSION_SECRET missing")

        try:
            return cls(secret=secret or "", origin=origin, secure=secure)
        except ValueError as exc:
            errors.append(str(exc))
            raise HTTPException(
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "SESSION_CONFIG_INVALID", "errors": errors},
            ) from None

    def _sign(self, payload: bytes) -> str:
        return hmac.new(self._secret, payload, hashlib.sha256).hexdigest()

    def _make_cookie_value(self, owner: str, issued: int) -> str:
        payload = f"{_VERSION}.{owner}.{issued}".encode("utf-8")
        sig = self._sign(payload)
        return f"{_VERSION}.{owner}.{issued}.{sig}"

    def _parse_cookie(self, value: str) -> tuple[str, int, str] | None:
        if len(value) > _MAX_TOTAL_LEN:
            return None
        parts = value.split(".")
        if len(parts) != 4:
            return None
        ver, owner, issued_s, sig = parts
        if ver != _VERSION:
            return None
        if not re.fullmatch(r"[0-9a-f]{32}", owner):
            return None
        if not re.fullmatch(r"[0-9a-f]{64}", sig):
            return None
        if not re.fullmatch(r"[0-9]{1,12}", issued_s):
            return None
        issued = int(issued_s)
        if str(issued) != issued_s or issued < 0:
            return None
        return owner, issued, sig

    def _verify_signature(self, owner: str, issued: int, sig: str) -> bool:
        payload = f"{_VERSION}.{owner}.{issued}".encode("utf-8")
        expected = self._sign(payload)
        return hmac.compare_digest(expected, sig)

    def _csrf_token(self, owner: str, issued: int) -> str:
        payload = f"csrf.{_VERSION}.{owner}.{issued}".encode("utf-8")
        return hmac.new(self._secret, payload, hashlib.sha256).hexdigest()

    def _now(self, now: float | None) -> float:
        if now is None:
            now = time.time()
        if isinstance(now, bool) or not isinstance(now, (int, float)):
            raise ValueError("invalid clock type")
        now_f = float(now)
        if math.isnan(now_f) or math.isinf(now_f) or now_f < 0:
            raise ValueError("invalid clock value")
        # Validate time.time() result is also valid
        try:
            dt = datetime.fromtimestamp(now_f, tz=timezone.utc)
            _ = dt.timestamp()
        except (OSError, OverflowError, ValueError):
            raise ValueError("invalid clock value")
        # Check representability of now + ttl instead of hard 2038 cap
        try:
            dt_future = datetime.fromtimestamp(now_f + self.ttl_s, tz=timezone.utc)
            _ = dt_future.timestamp()
        except (OSError, OverflowError, ValueError):
            raise ValueError("invalid clock value")
        return now_f

    def _set_cookie(self, response: Response, value: str, issued: int) -> None:
        response.set_cookie(
            key=_COOKIE_NAME,
            value=value,
            httponly=True,
            samesite="strict",
            path="/",
            secure=self._secure,
            max_age=self.ttl_s,
            expires=datetime.fromtimestamp(issued + self.ttl_s, tz=timezone.utc),
        )

    def _clear_cookie(self, response: Response) -> None:
        response.delete_cookie(key=_COOKIE_NAME, path="/")

    def _reject(self, *, clear_cookie: bool = False, response: Response | None = None) -> HTTPException:
        if clear_cookie and response is not None:
            self._clear_cookie(response)
        return HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail={"code": "SESSION_INVALID"},
        )

    def _check_origin(self, request: Request) -> None:
        origins = request.headers.getlist("origin")
        if len(origins) != 1:
            raise self._reject()
        origin = origins[0]
        if origin != self.origin:
            raise self._reject()

    def _get_cookie(self, request: Request) -> str | None:
        raw_list = request.headers.getlist("cookie")
        found: list[str] = []
        for raw in raw_list:
            for part in raw.split(";"):
                part = part.strip()
                if part.startswith(_COOKIE_NAME + "="):
                    found.append(part[len(_COOKIE_NAME) + 1 :])
        if len(found) > 1:
            raise self._reject()
        return found[0] if found else None

    def establish(
        self,
        request: Request,
        response: Response,
        *,
        now: float | None = None,
    ) -> SessionInfo:
        """Return a valid session, reusing an existing cookie when possible.

        GET requests with an Origin header must exactly match the configured
        origin. On mismatch we reject rather than normalising an untrusted
        value into a URL.
        """
        ts = self._now(now)

        if request.method == "GET":
            origins = request.headers.getlist("origin")
            if origins:
                if len(origins) != 1:
                    raise self._reject()
                self._check_origin(request)

        existing = self._get_cookie(request)
        if existing is not None:
            parsed = self._parse_cookie(existing)
            if parsed is not None:
                owner, issued, sig = parsed
                if self._verify_signature(owner, issued, sig):
                    if issued <= ts + 30 and ts < issued + self.ttl_s:
                        expires = datetime.fromtimestamp(issued + self.ttl_s, tz=timezone.utc)
                        return SessionInfo(
                            csrf_token=self._csrf_token(owner, issued),
                            expires_at=expires,
                        )

        # Create new session
        owner = secrets.token_hex(16)
        issued = int(ts)
        value = self._make_cookie_value(owner, issued)
        self._set_cookie(response, value, issued)
        expires = datetime.fromtimestamp(issued + self.ttl_s, tz=timezone.utc)
        return SessionInfo(
            csrf_token=self._csrf_token(owner, issued),
            expires_at=expires,
        )

    def validate(
        self,
        request: Request,
        *,
        mutation: bool = False,
        now: float | None = None,
    ) -> str:
        """Return authenticated owner string, or raise 403.

        For mutation requests, exact Origin match and X-CSRF-Token are required.
        """
        ts = self._now(now)

        if mutation:
            self._check_origin(request)
            tokens = request.headers.getlist("x-csrf-token")
            if len(tokens) != 1:
                raise self._reject()
            token = tokens[0]
            if not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{64}", token):
                raise self._reject()

        raw = self._get_cookie(request)
        if raw is None:
            raise self._reject()

        parsed = self._parse_cookie(raw)
        if parsed is None:
            raise self._reject()
        owner, issued, sig = parsed

        if not self._verify_signature(owner, issued, sig):
            raise self._reject()

        if issued > ts + 30:
            raise self._reject()
        if ts >= issued + self.ttl_s:
            raise self._reject()

        if mutation:
            expected = self._csrf_token(owner, issued)
            if not hmac.compare_digest(expected, token):
                raise self._reject()

        return owner
