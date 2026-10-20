"""Bounded, immutable JSONL pose artifacts; invalid input never becomes a gap fill."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

from contracts.pose import PoseFrame

MAX_FRAMES = 10000
MAX_LINE_BYTES = 128 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024


def write_pose_frames(root: Path, key: str, frames: Iterable[PoseFrame]) -> str:
    root = root.resolve()
    _validate_key(key)
    target = root / key
    _ensure_safe_path(root, target)

    temp_path: Path | None = None
    hash_obj = hashlib.sha256()
    total_size = 0
    frame_count = 0
    prev_index = -1
    prev_timestamp = -1.0

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            for frame in frames:
                frame_count += 1
                if frame_count > MAX_FRAMES:
                    raise ValueError(f"Too many frames: {MAX_FRAMES} max")

                validated = PoseFrame.model_validate(frame.model_dump(mode='json'))
                if not (validated.frame_index > prev_index):
                    raise ValueError("frame_index must be strictly increasing")
                if not (validated.timestamp_s > prev_timestamp):
                    raise ValueError("timestamp_s must be strictly increasing")
                prev_index = validated.frame_index
                prev_timestamp = validated.timestamp_s

                line = json.dumps(validated.model_dump(mode='json'),
                                sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8') + b'\n'
                if len(line) > MAX_LINE_BYTES:
                    raise ValueError(f"Line too long: {MAX_LINE_BYTES} bytes max")
                total_size += len(line)
                if total_size > MAX_TOTAL_BYTES:
                    raise ValueError(f"Total size too large: {MAX_TOTAL_BYTES} bytes max")

                temp_file.write(line)
                hash_obj.update(line)

            if frame_count == 0:
                raise ValueError("At least one frame required")

            temp_file.flush()
            os.fsync(temp_file.fileno())

        try:
            os.link(temp_path, target)
        except FileExistsError:
            _ensure_safe_path(root, target)
            if os.path.islink(target) or not target.is_file():
                raise FileExistsError(f"Target is not a regular file: {key}")
            if target.stat().st_size != temp_path.stat().st_size:
                raise FileExistsError(f"Target exists with different size: {key}")
            temp_data = temp_path.read_bytes()
            if target.read_bytes() != temp_data:
                raise FileExistsError(f"Target exists with different content: {key}")
        return hash_obj.hexdigest()
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def read_pose_frames(root: Path, key: str, *, expected_sha256: str | None = None) -> list[PoseFrame]:
    root = root.resolve()
    _validate_key(key)
    target = root / key
    _ensure_safe_path(root, target)

    if not target.is_file():
        raise FileNotFoundError(f"Not a regular file: {key}")

    stat_result = target.stat()
    if stat_result.st_size == 0:
        raise ValueError("Empty file")
    if stat_result.st_size > MAX_TOTAL_BYTES:
        raise ValueError("Total size too large")

    frames: list[PoseFrame] = []
    total_size = 0
    frame_count = 0
    prev_index = -1
    prev_timestamp = -1.0
    hash_obj = hashlib.sha256() if expected_sha256 else None

    with target.open('rb') as f:
        while True:
            line = f.readline(MAX_LINE_BYTES + 2)
            if not line:
                break
            if len(line) > MAX_LINE_BYTES or not line.endswith(b'\n'):
                raise ValueError("Line too long or missing newline")

            total_size += len(line)
            if total_size > MAX_TOTAL_BYTES:
                raise ValueError("Total size too large")

            if hash_obj:
                hash_obj.update(line)

            if line == b'\n':
                raise ValueError("Empty line")

            try:
                obj = json.loads(line.decode('utf-8'), object_pairs_hook=_reject_duplicate_keys)
            except json.JSONDecodeError as e:
                raise ValueError(f"Malformed JSON: {e}") from e

            frame = PoseFrame.model_validate(obj)
            if not (frame.frame_index > prev_index):
                raise ValueError("frame_index not strictly increasing")
            if not (frame.timestamp_s > prev_timestamp):
                raise ValueError("timestamp_s not strictly increasing")
            prev_index = frame.frame_index
            prev_timestamp = frame.timestamp_s

            frames.append(frame)
            frame_count += 1

            if frame_count > MAX_FRAMES:
                raise ValueError(f"Too many frames: {MAX_FRAMES} max")

    if frame_count == 0:
        raise ValueError("No frames")

    if expected_sha256:
        if hash_obj and hash_obj.hexdigest() != expected_sha256:
            raise ValueError("SHA256 mismatch")

    return frames


def _validate_key(key: str) -> None:
    if not key or key in ('.', '..') or chr(92) in key:
        raise ValueError(f"Invalid key: {key}")
    parts = key.split('/')
    if any(p in ('', '.', '..') for p in parts):
        raise ValueError(f"Invalid key component: {key}")


def _ensure_safe_path(root: Path, target: Path) -> None:
    if not root.is_absolute():
        raise ValueError("Root must be absolute")
    root = root.resolve()

    # Walk the lexical path without resolving symlinks
    parts = target.parts[len(root.parts):]
    current = root
    for part in parts:
        if part in ('', '.', '..'):
            raise ValueError(f"Invalid path component: {part}")
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Symlink in path: {current}")

    # Final target must resolve within root
    if not current.resolve().is_relative_to(root):
        raise ValueError("Key escapes root")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate key: {key}")
        result[key] = value
    return result
