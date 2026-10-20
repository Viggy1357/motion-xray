from __future__ import annotations

import json
from typing import Generator

import pytest
from contracts.pose import JointObservation, PoseFrame
from providers.pose.artifacts import read_pose_frames, write_pose_frames


def sample_frames() -> list[PoseFrame]:
    return [
        PoseFrame(
            frame_index=0,
            timestamp_s=0.0,
            joints={
                'left_shoulder': JointObservation(xy=(0.1, 0.2), valid=True, interpolated=False)
            }
        ),
        PoseFrame(
            frame_index=1,
            timestamp_s=0.1,
            joints={
                'left_shoulder': JointObservation(xy=(0.3, 0.4), valid=True, interpolated=False)
            }
        )
    ]


def test_roundtrip(tmp_path) -> None:
    key = "test/frames.jsonl"
    frames = sample_frames()
    root = tmp_path / "root"
    root.mkdir()

    sha = write_pose_frames(root, key, frames)
    loaded = read_pose_frames(root, key, expected_sha256=sha)
    assert len(loaded) == 2
    assert loaded[0].frame_index == 0
    assert loaded[1].frame_index == 1

    # Idempotent write
    assert write_pose_frames(root, key, frames) == sha


def test_conflicting_write(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    key = "conflict.jsonl"

    frame1 = PoseFrame(frame_index=0, timestamp_s=0.0, joints={})
    frame2 = PoseFrame(frame_index=0, timestamp_s=0.1, joints={})  # different

    write_pose_frames(root, key, [frame1])
    with pytest.raises(FileExistsError):
        write_pose_frames(root, key, [frame2])
    # Original preserved
    assert len(read_pose_frames(root, key)) == 1


def test_invalid_key(tmp_path) -> None:
    root = tmp_path / "root"
    with pytest.raises(ValueError, match="Invalid key"):
        write_pose_frames(root, "../escape", [])
    with pytest.raises(ValueError, match="Invalid key"):
        write_pose_frames(root, "has\\backslash", [])
    with pytest.raises(ValueError, match="Invalid key component"):
        write_pose_frames(root, "bad/..", [])
    with pytest.raises(ValueError, match="Invalid key component"):
        write_pose_frames(root, "bad/./part", [])


def test_symlink_rejection(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "link").symlink_to("target")
    with pytest.raises(ValueError, match="Symlink in path"):
        write_pose_frames(root, "link/file", [])

    # Dangling symlink
    (root / "dangling").symlink_to("nonexistent")
    with pytest.raises(ValueError, match="Symlink in path"):
        write_pose_frames(root, "dangling/file", [])

    # Internal symlink
    (root / "dir").mkdir()
    (root / "dir" / "link").symlink_to("target")
    with pytest.raises(ValueError, match="Symlink in path"):
        write_pose_frames(root, "dir/link/file", [])


def test_nonincreasing_frames(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    frames = [PoseFrame(frame_index=1, timestamp_s=0.1, joints={}),
              PoseFrame(frame_index=1, timestamp_s=0.2, joints={})]  # same index
    with pytest.raises(ValueError, match="strictly increasing"):
        write_pose_frames(root, "bad.jsonl", frames)


def test_empty_input(tmp_path) -> None:
    root = tmp_path / "root"
    with pytest.raises(ValueError, match="At least one frame"):
        write_pose_frames(root, "empty.jsonl", [])


def test_malformed_json(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    path = root / "bad.jsonl"
    path.write_text("{\n\n}")  # missing newline, then blank line
    with pytest.raises(ValueError, match="Malformed JSON"):
        read_pose_frames(root, "bad.jsonl")


def test_generator_failure_cleanup(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    def bad_gen() -> Generator[PoseFrame, None, None]:
        yield sample_frames()[0]
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError):
        write_pose_frames(root, "fail.jsonl", bad_gen())
    assert not (root / "fail.jsonl").exists()
    # No temp files left
    assert len(list(root.iterdir())) == 0


def test_digest_tamper(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    key = "tamper.jsonl"
    frames = sample_frames()
    sha = write_pose_frames(root, key, frames)

    # Modify file
    path = root / key
    data = path.read_bytes()
    path.write_bytes(data.replace(b'0.1', b'0.11'))  # still valid, ordered JSON

    with pytest.raises(ValueError, match="SHA256 mismatch"):
        read_pose_frames(root, key, expected_sha256=sha)


def test_duplicate_keys(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    path = root / "dup.jsonl"
    # Duplicate key in JSON
    line = '{"frame_index":0,"timestamp_s":0.0,"joints":{},"frame_index":1}\n'
    path.write_text(line)
    with pytest.raises(ValueError, match="Duplicate key"):
        read_pose_frames(root, "dup.jsonl")


def test_equal_timestamps(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    frames = [PoseFrame(frame_index=0, timestamp_s=0.1, joints={}),
              PoseFrame(frame_index=1, timestamp_s=0.1, joints={})]  # equal timestamp
    with pytest.raises(ValueError, match="strictly increasing"):
        write_pose_frames(root, "bad.jsonl", frames)


def test_blank_lines(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    path = root / "blank.jsonl"
    path.write_text("{\"frame_index\":0,\"timestamp_s\":0.0,\"joints\":{}}\n\n")
    with pytest.raises(ValueError, match="Empty line"):
        read_pose_frames(root, "blank.jsonl")


@pytest.mark.parametrize("limit,value", [
    ("MAX_FRAMES", 1), ("MAX_LINE_BYTES", 10), ("MAX_TOTAL_BYTES", 10),
])
def test_bounds_enforcement(tmp_path, monkeypatch, limit, value) -> None:
    frames = sample_frames()
    write_pose_frames(tmp_path, "valid.jsonl", frames)
    monkeypatch.setattr(f"providers.pose.artifacts.{limit}", value)
    with pytest.raises(ValueError):
        write_pose_frames(tmp_path, "refused.jsonl", frames)
    with pytest.raises(ValueError):
        read_pose_frames(tmp_path, "valid.jsonl")
    assert not (tmp_path / "refused.jsonl").exists()


def test_target_symlink_and_exact_bytes(tmp_path):
    frames = sample_frames()
    digest = write_pose_frames(tmp_path, "original.jsonl", frames)
    data = (tmp_path / "original.jsonl").read_bytes()
    assert data == b"".join(json.dumps(f.model_dump(mode="json"), sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode() + b"\n" for f in frames)
    assert read_pose_frames(tmp_path, "original.jsonl", expected_sha256=digest) == frames
    (tmp_path / "link.jsonl").symlink_to("original.jsonl")
    for operation in [lambda: write_pose_frames(tmp_path, "link.jsonl", frames),
                      lambda: read_pose_frames(tmp_path, "link.jsonl")]:
        with pytest.raises(ValueError, match="Symlink"):
            operation()
