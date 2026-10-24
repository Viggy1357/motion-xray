#!/usr/bin/env python3
"""Bounded local onboarding helper for Motion X Ray.

This script is intentionally stdlib-only and runs inside the pinned Python
3.12 base image extracted from ``infra/api.Dockerfile``. It performs three
bounded jobs:

1. ``prepare_env`` — create ``.env`` from ``.env.example`` if missing, fill
   only the empty ``SESSION_SECRET`` (or a known placeholder) with a fresh
   ``secrets.token_hex(32)`` value, and preserve every other line.
2. ``verify_model_manifest`` — load ``data/pose_models/mediapipe-full-v1.json``
   and validate the pinned download URL, SHA-256, and size against a strict
   allow-list (HTTPS, ``storage.googleapis.com`` host, whitelisted path prefix,
   no traversal/symlink targets).
3. ``download_model`` — bounded HTTPS download with a 30 s socket timeout and a 90 s read-loop deadline and a
   manifest-sized byte cap. The file is streamed to a sibling ``.part`` path,
   hashed as it arrives, and only atomically published when the SHA-256 and
   byte count match. Partial files are cleaned on any failure.
Docker orchestration is performed by the host Bash wrapper.

The module exposes the helper functions so they can be unit-tested without
touching the host environment.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import stat
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Callable, Iterable

# --- Pinned model manifest constants -----------------------------------------
# These are duplicated from data/pose_models/mediapipe-full-v1.json so the
# bootstrap can refuse to download from any URL that is not the exact pinned
# artifact. The JSON file is the source of truth at runtime; these constants
# are the safety net.
EXPECTED_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/1/pose_landmarker_full.task"
)
EXPECTED_MODEL_SHA256 = "5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1"
EXPECTED_MODEL_BYTES = 9398198

# Bounded network budgets.
DOWNLOAD_TIMEOUT_SECONDS = 30
DOWNLOAD_MAX_BYTES = EXPECTED_MODEL_BYTES  # never accept more than the manifest size
# .env handling.
SESSION_SECRET_KEY = "SESSION_SECRET"
SESSION_SECRET_PLACEHOLDERS = {
    "",
    "changeme",
    "change-me",
    "please-change-me",
    "replace-me",
    "set-me",
}


# ---------------------------------------------------------------------------
# .env preparation
# ---------------------------------------------------------------------------

def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _atomic_write(path: Path, data: str) -> None:
    """Write ``data`` to ``path`` atomically with mode 0600."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(data)
        os.chmod(tmp_name, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def _generate_session_secret() -> str:
    # 32 bytes -> 64 hex chars; well above any reasonable minimum.
    return secrets.token_hex(32)


def _is_placeholder(value: str) -> bool:
    return value.strip().lower() in SESSION_SECRET_PLACEHOLDERS


def prepare_env(repo_root: Path, env_path: Path | None = None,
                example_path: Path | None = None,
                secret_generator: Callable[[], str] | None = None) -> dict:
    """Prepare ``.env`` from ``.env.example``.

    Returns a dict describing what changed so callers can log without leaking
    secret values. The dict never contains the secret itself.
    """
    repo_root = Path(repo_root)
    env_path = Path(env_path) if env_path else repo_root / ".env"
    example_path = Path(example_path) if example_path else repo_root / ".env.example"
    secret_generator = secret_generator or _generate_session_secret

    if example_path.is_symlink():
        raise ValueError(f"refusing to use symlink example env: {example_path}")
    if not example_path.is_file():
        raise FileNotFoundError(f"missing example env: {example_path}")

    if env_path.is_symlink():
        raise ValueError(f"refusing to use symlink env: {env_path}")

    created = False
    if not env_path.is_file():
        # Copy with a restrictive umask so the new file is owner-only.
        umask = os.umask(0o077)
        try:
            shutil.copyfile(example_path, env_path)
        finally:
            os.umask(umask)
        os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)
        created = True

    original = _read_text(env_path)
    lines = original.splitlines(keepends=True)

    # Preserve the file's existing newline style. splitlines(keepends=True)
    # keeps trailing newlines; if the file did not end with one we add none.
    trailing_newline = original.endswith("\n")

    secret_filled = False
    secret_already_set = False
    malformed = False
    seen_secret = False

    new_lines: list[str] = []
    for raw in lines:
        line = raw.rstrip("\n").rstrip("\r")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(raw)
            continue
        if "=" not in line:
            new_lines.append(raw)
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key != SESSION_SECRET_KEY:
            new_lines.append(raw)
            continue
        if seen_secret:
            malformed = True
            new_lines.append(raw)
            continue
        seen_secret = True
        if _is_placeholder(value):
            new_value = f"{key}={secret_generator()}\n"
            new_lines.append(new_value)
            secret_filled = True
        else:
            # Non-empty configured value: preserve as-is.
            new_lines.append(raw)
            secret_already_set = True

    # If the example defines SESSION_SECRET but the existing .env does not
    # mention it at all, append a freshly generated one.
    if not seen_secret:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] = new_lines[-1] + "\n"
        new_lines.append(f"{SESSION_SECRET_KEY}={secret_generator()}\n")
        secret_filled = True

    if malformed:
        raise ValueError(
            f"malformed .env: duplicate or invalid {SESSION_SECRET_KEY} entries; "
            "fix .env manually before re-running."
        )

    new_contents = "".join(new_lines)
    if not trailing_newline and new_contents.endswith("\n"):
        new_contents = new_contents.rstrip("\n")

    if new_contents == original:
        # Preserve existing config exactly; do not rewrite the file.
        return {
            "created": created,
            "secret_filled": False,
            "secret_already_set": secret_already_set,
            "changed": False,
        }

    _atomic_write(env_path, new_contents)
    # Existing env files keep their original permissions; chmod 0600
    # only applies to newly created files (handled above).
    return {
        "created": created,
        "secret_filled": secret_filled,
        "secret_already_set": secret_already_set,
        "changed": True,
    }


# ---------------------------------------------------------------------------
# Model manifest verification
# ---------------------------------------------------------------------------

def verify_model_manifest(manifest_path: Path) -> dict:
    """Load and validate the pinned model manifest.

    Raises ``ValueError`` for any deviation from the pinned constants. The
    returned dict is the parsed manifest.
    """
    manifest_path = Path(manifest_path)
    try:
        data = json.loads(_read_text(manifest_path))
    except json.JSONDecodeError as exc:
        raise ValueError(f"manifest is not valid JSON: {manifest_path}: {exc}") from exc

    url = data.get("download_url")
    sha = data.get("sha256")
    size = data.get("bytes")
    local_path = data.get("local_path")

    if not isinstance(url, str) or not url:
        raise ValueError("manifest missing download_url")
    if url != EXPECTED_MODEL_URL:
        raise ValueError(
            f"manifest download_url does not match the pinned URL; "
            f"expected {EXPECTED_MODEL_URL}"
        )

    if sha != EXPECTED_MODEL_SHA256:
        raise ValueError("manifest sha256 does not match the pinned value")
    if size != EXPECTED_MODEL_BYTES:
        raise ValueError("manifest bytes does not match the pinned value")

    if not isinstance(local_path, str) or not local_path:
        raise ValueError("manifest missing local_path")
    if local_path != "models/pose_landmarker_full.task":
        raise ValueError(
            "manifest local_path must be models/pose_landmarker_full.task"
        )
    if ".." in Path(local_path).parts or Path(local_path).is_absolute():
        raise ValueError("manifest local_path must be a relative path with no traversal")

    return data


# ---------------------------------------------------------------------------
# Bounded model download
# ---------------------------------------------------------------------------

def _validate_local_target(repo_root: Path, local_path: str) -> Path:
    """Resolve ``local_path`` under ``repo_root`` and reject traversal/symlinks."""
    repo_root_resolved = repo_root.resolve()
    # Reject each raw component before resolve so we never touch a symlinked
    # parent or a dangling target.
    raw = Path(local_path)
    for part in raw.parts:
        if part in ("..", "."):
            raise ValueError(f"model local_path has traversal segment: {local_path}")
    if raw.is_absolute():
        raise ValueError(f"model local_path must be relative: {local_path}")
    candidate = repo_root_resolved
    for part in raw.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError(f"refusing to use symlink path: {candidate}")
    candidate = candidate.resolve()
    candidate.relative_to(repo_root_resolved)
    return candidate


def _hash_stream(stream, hasher: "hashlib._Hash", max_bytes: int,
                  total_deadline: float | None = None) -> tuple[bytes, int]:
    """Read ``stream`` in chunks, hashing and enforcing ``max_bytes``.

    If ``total_deadline`` is provided (monotonic seconds), the read loop
    aborts with a generic CLI error when the deadline is exceeded.
    """
    buf = bytearray()
    total = 0
    while True:
        if total_deadline is not None and time.monotonic() >= total_deadline:
            raise RuntimeError("download exceeded 90s total deadline")
        chunk = stream.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValueError(
                f"download exceeded manifest size of {max_bytes} bytes"
            )
        hasher.update(chunk)
        buf.extend(chunk)
    return bytes(buf), total


def download_model(repo_root: Path, manifest: dict,
                   url_opener: Callable[[str, float], object] | None = None) -> Path:
    """Download and verify the pinned model.

    ``url_opener`` is injectable for tests; it must return a file-like object
    with a ``read`` method. The default uses ``urllib.request.urlopen`` with a
    30 s timeout.
    """
    repo_root = Path(repo_root)
    local_path = manifest["local_path"]
    expected_sha = manifest["sha256"]
    expected_bytes = int(manifest["bytes"])
    url = manifest["download_url"]

    target = _validate_local_target(repo_root, local_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        # Verify the existing file before deciding to skip or fail.
        hasher = hashlib.sha256()
        size = 0
        with target.open("rb") as fh:
            while True:
                chunk = fh.read(64 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                hasher.update(chunk)
        if hasher.hexdigest() == expected_sha and size == expected_bytes:
            return target
        raise ValueError(
            f"existing model file at {target} does not match the pinned "
            f"sha256/size; remove it manually before re-running: rm {target}"
        )

    opener = url_opener or _default_url_open
    part_path = target.with_suffix(target.suffix + ".part")
    if part_path.is_symlink():
        raise ValueError(f"refusing to overwrite symlink at {part_path}")

    deadline = time.monotonic() + 90
    try:
        response = opener(url, DOWNLOAD_TIMEOUT_SECONDS)
        try:
            # Verify the final URL after redirects matches the expected URL.
            final_url = getattr(response, "url", url)
            if final_url != EXPECTED_MODEL_URL:
                raise ValueError(
                    f"download redirected to unexpected URL: {final_url}"
                )
            hasher = hashlib.sha256()
            with part_path.open("wb") as out:
                buf, total = _hash_stream(
                    response, hasher, expected_bytes, total_deadline=deadline
                )
                if total != expected_bytes:
                    raise ValueError(
                        f"downloaded {total} bytes but manifest declares "
                        f"{expected_bytes}; refusing to publish"
                    )
                out.write(buf)
            digest = hasher.hexdigest()
            if digest != expected_sha:
                raise ValueError(
                    f"downloaded sha256 {digest} does not match pinned "
                    f"{expected_sha}; refusing to publish"
                )
            os.replace(part_path, target)
            os.chmod(target, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            return target
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()
    except Exception:
        # Clean up any partial file on failure.
        try:
            part_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _default_url_open(url: str, timeout: float):
    request = urllib.request.Request(url, headers={"User-Agent": "motion-xray-bootstrap/1.0"})
    return urllib.request.urlopen(request, timeout=timeout)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Iterable[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    prepare_only = os.environ.get("QUICKSTART_PREPARE_ONLY", "0") == "1"

    env_file = repo_root / ".env"
    example_file = repo_root / ".env.example"
    manifest_path = repo_root / "data" / "pose_models" / "mediapipe-full-v1.json"

    env_summary = prepare_env(repo_root, env_file, example_file)
    print(f"bootstrap: env created={env_summary['created']} "
          f"secret_filled={env_summary['secret_filled']} "
          f"secret_already_set={env_summary['secret_already_set']}")

    manifest = verify_model_manifest(manifest_path)
    model_path = download_model(repo_root, manifest)
    print(f"bootstrap: model verified at {model_path}")

    if prepare_only:
        print("bootstrap: --prepare-only set; skipping build/up.")
        return 0

    # The host Bash wrapper handles docker compose orchestration.
    # This script only prepares the environment and downloads the model.
    print("bootstrap: environment and model ready; host will orchestrate compose.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        # Generic CLI error: print type + message, no traceback.
        print(f"bootstrap: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
