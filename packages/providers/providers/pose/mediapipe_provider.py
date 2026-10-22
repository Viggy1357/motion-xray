"""CPU pose inference with source PTS, explicit gaps and immutable artifacts."""

from __future__ import annotations

import contextlib
import hashlib
import importlib
import json
import math
import os
import select
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

from contracts.media import VideoAsset
from contracts.pose import PoseSequence
from providers.capabilities import PoseCapabilities
from providers.pose.artifacts import write_pose_frames
from providers.pose.canonical import JOINT_INDICES, map_pose_frame


_TIMESTAMP_PROBE_TIMEOUT_S = 90.0


@dataclass
class VideoProbe:
    timestamps: list[float]
    width: int
    height: int
    rotation: int
    duration_s: float


def _is_valid_number(val: Any, *, allow_bool: bool = False) -> bool:
    if isinstance(val, bool) and not allow_bool:
        return False
    if not isinstance(val, (int, float)):
        return False
    return math.isfinite(val)


def probe_video(path: Path) -> VideoProbe:
    if not path.is_file():
        raise ValueError(f"Video file not found: {path}")

    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries",
        "frame=best_effort_timestamp_time:stream=width,height:stream_side_data=side_data_type,rotation:stream_tags=rotate:format=duration",
        "-print_format", "json",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, check=True, timeout=_TIMESTAMP_PROBE_TIMEOUT_S)
    data = json.loads(result.stdout)

    frames = data.get("frames", [])
    streams = data.get("streams", [])
    fmt = data.get("format", {})

    if not frames or not streams:
        raise ValueError("No video frames or streams found")

    stream = streams[0]
    width = stream.get("width")
    height = stream.get("height")

    rotation = 0
    has_matrix = False
    if "side_data_list" in stream:
        for sd in stream["side_data_list"]:
            if sd.get("side_data_type") == "Display Matrix":
                rot = sd.get("rotation")
                if not _is_valid_number(rot) or rot not in (0, 90, -90, 180, -180):
                    raise ValueError("Invalid rotation metadata")
                rotation = int(rot)
                has_matrix = True
    if not has_matrix and "tags" in stream:
        rot_str = stream["tags"].get("rotate")
        if rot_str is not None:
            try:
                rotation = int(rot_str)
            except (ValueError, TypeError) as exc:
                raise ValueError("Invalid rotation metadata") from exc

    if not isinstance(width, int) or not (0 < width <= 1920):
        raise ValueError(f"Invalid width: {width}")
    if not isinstance(height, int) or not (0 < height <= 1920):
        raise ValueError(f"Invalid height: {height}")
    if rotation not in (0, 90, -90, 180, -180):
        raise ValueError(f"Invalid rotation: {rotation}")

    timestamps: list[float] = []
    for frame in frames:
        ts_str = frame.get("best_effort_timestamp_time")
        if ts_str is None:
            raise ValueError("Missing best_effort_timestamp_time")
        try:
            ts = float(ts_str)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid timestamp: {ts_str}")
        if not _is_valid_number(ts) or not (0 <= ts <= 120):
            raise ValueError(f"Timestamp out of range: {ts}")
        if timestamps and ts <= timestamps[-1]:
            raise ValueError(f"Non-increasing timestamp: {ts} after {timestamps[-1]}")
        timestamps.append(ts)

    if len(timestamps) < 2 or len(timestamps) > 7200:
        raise ValueError(f"Frame count out of range: {len(timestamps)}")

    dur_str = fmt.get("duration")
    if dur_str is None:
        raise ValueError("Missing duration")
    try:
        duration_s = float(dur_str)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid duration: {dur_str}")
    if not _is_valid_number(duration_s) or not (0 < duration_s <= 120):
        raise ValueError(f"Duration out of range: {duration_s}")

    if timestamps[-1] > duration_s + 1e-6:
        raise ValueError(f"Last timestamp {timestamps[-1]} exceeds duration {duration_s}")

    return VideoProbe(
        timestamps=timestamps,
        width=width,
        height=height,
        rotation=rotation,
        duration_s=duration_s,
    )


def select_samples(
    timestamps: list[float],
    start_s: float,
    duration_s: float,
    rate: float,
) -> list[tuple[int, float]]:
    # ffprobe formats source PTS to microseconds. Avoid dropping every other
    # near-30Hz sample because 0.033333 rounds below 1/30 by 0.33 microseconds.
    eps = 1e-6
    end_s = start_s + duration_s
    samples: list[tuple[int, float]] = []
    next_time = start_s
    for idx, ts in enumerate(timestamps):
        if ts < start_s - eps:
            continue
        if ts >= end_s - eps:
            break
        if ts >= next_time - eps:
            samples.append((idx, ts))
            next_time = ts + 1.0 / rate
    return samples


def _load_runtime() -> tuple[Any, Any, Any, Any]:
    """Keep the API import ML-free and permit offline decoder/runtime fixtures."""
    return (
        importlib.import_module("mediapipe"), importlib.import_module("numpy"),
        importlib.import_module("mediapipe.tasks.python"),
        importlib.import_module("mediapipe.tasks.python.vision"),
    )


class MediaPipePoseProvider:
    def __init__(
        self,
        checkpoint_path: str | None = None,
        *,
        checkpoint_sha256: str | None = None,
        source_root: Path | None = None,
        artifact_root: Path | None = None,
        start_s: float = 0,
        duration_s: float = 10,
        sample_rate_hz: float = 30,
        visibility_threshold: float = 0.6,
    ):
        configured_checkpoint = checkpoint_path or os.environ.get("POSE_CHECKPOINT_PATH")
        self._checkpoint_path = Path(configured_checkpoint or "/app/models/pose_landmarker.task")
        self._checkpoint_sha256 = checkpoint_sha256 or os.environ.get("POSE_CHECKPOINT_SHA256")
        self._source_root = (source_root or Path(os.environ.get("VIDEO_ROOT", "/app/data"))).resolve()
        self._artifact_root = (artifact_root or Path(os.environ.get("ARTIFACT_ROOT", "/state/artifacts"))).resolve()

        if not _is_valid_number(start_s):
            raise ValueError("start_s must be a finite number")
        if start_s < 0:
            raise ValueError("start_s must be >= 0")

        if not _is_valid_number(duration_s):
            raise ValueError("duration_s must be a finite number")
        if not (0 < duration_s <= 60):
            raise ValueError("duration_s must be in (0, 60]")

        if not _is_valid_number(sample_rate_hz):
            raise ValueError("sample_rate_hz must be a finite number")
        if not (0 < sample_rate_hz <= 30):
            raise ValueError("sample_rate_hz must be in (0, 30]")

        if not _is_valid_number(visibility_threshold):
            raise ValueError("visibility_threshold must be a finite number")
        if not (0 <= visibility_threshold <= 1):
            raise ValueError("visibility_threshold must be in [0, 1]")

        self._start_s = float(start_s)
        self._duration_s = float(duration_s)
        self._sample_rate_hz = float(sample_rate_hz)
        self._visibility_threshold = float(visibility_threshold)

    def capabilities(self) -> PoseCapabilities:
        return PoseCapabilities(
            supports_2d=True,
            supports_estimated_3d=True,
            world_translation=False,
            calibration=None,
            joint_availability={name: True for name in (*JOINT_INDICES, "pelvis", "shoulder_midpoint")},
            confidence_semantics="visibility_presence_proxy_not_3d_confidence",
        )

    def infer(self, video: VideoAsset) -> PoseSequence:
        storage_path = self._validate_storage_key(video.storage_key)
        source_file = (self._source_root / storage_path).resolve()
        if not source_file.is_relative_to(self._source_root):
            raise ValueError("Source file escapes source_root")
        if not source_file.is_file():
            raise ValueError("Source file not found")
        if source_file.stat().st_size > 100 * 1024 * 1024:
            raise ValueError("Source file exceeds 100MB")
        if source_file.stat().st_size != video.bytes:
            raise ValueError("Source file size mismatch")

        sha = hashlib.sha256()
        with source_file.open("rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                sha.update(chunk)
        if sha.hexdigest() != video.sha256:
            raise ValueError("Source file SHA256 mismatch")

        probe = probe_video(source_file)
        if abs(probe.duration_s - video.duration_s) > 0.1:
            raise ValueError("Duration mismatch between probe and video")
        if probe.width != video.width or probe.height != video.height or probe.rotation != video.rotation:
            raise ValueError("Video metadata mismatch")

        end_s = self._start_s + self._duration_s
        if end_s > probe.duration_s + 1e-6:
            raise ValueError("Requested time range exceeds video duration")

        if not self._checkpoint_path.is_file():
            raise RuntimeError(f"Checkpoint not found: {self._checkpoint_path}")
        if self._checkpoint_sha256 is None:
            raise RuntimeError("checkpoint_sha256 is required")
        if len(self._checkpoint_sha256) != 64:
            raise ValueError("checkpoint_sha256 must be 64 hex characters")
        try:
            int(self._checkpoint_sha256, 16)
        except ValueError:
            raise ValueError("checkpoint_sha256 must be hex")
        actual_ckpt_sha = hashlib.sha256(self._checkpoint_path.read_bytes()).hexdigest()
        if actual_ckpt_sha != self._checkpoint_sha256:
            raise ValueError(f"Checkpoint SHA256 mismatch: expected {self._checkpoint_sha256}, got {actual_ckpt_sha}")

        mp, np, tasks, vision = _load_runtime()

        base_options = tasks.BaseOptions(model_asset_path=str(self._checkpoint_path))
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=2,
            output_segmentation_masks=False,
        )

        samples = select_samples(probe.timestamps, self._start_s, self._duration_s, self._sample_rate_hz)
        if len(samples) < 2:
            raise ValueError("Not enough frames to sample")

        sample_set = set(idx for idx, _ in samples)
        last_selected_idx = samples[-1][0]

        frames = []
        last_timestamp_ms = -1

        with contextlib.closing(_decode_frames(source_file, probe)) as decoder:
            with vision.PoseLandmarker.create_from_options(options) as landmarker:
                for raw_frame, source_index, ts in decoder:
                    if source_index not in sample_set:
                        continue

                    h, w = probe.height, probe.width
                    if abs(probe.rotation) == 90:
                        h, w = w, h
                    frame_size = h * w * 3
                    if len(raw_frame) != frame_size:
                        raise ValueError(f"Frame size mismatch: expected {frame_size}, got {len(raw_frame)}")

                    img_data = np.frombuffer(raw_frame, dtype=np.uint8).reshape((h, w, 3))
                    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_data)

                    timestamp_ms = int(round(ts * 1000))
                    if timestamp_ms <= last_timestamp_ms:
                        raise ValueError("Non-increasing timestamp_ms")
                    last_timestamp_ms = timestamp_ms

                    result = landmarker.detect_for_video(mp_img, timestamp_ms)

                    image_landmarks: list[Any] = []
                    world_landmarks: list[Any] = []
                    subject_id: str | None = None
                    if (
                        result.pose_landmarks is not None
                        and result.pose_world_landmarks is not None
                        and len(result.pose_landmarks) == 1
                        and len(result.pose_world_landmarks) == 1
                    ):
                        image_landmarks = result.pose_landmarks[0]
                        world_landmarks = result.pose_world_landmarks[0]
                        subject_id = "single-detection-identity-unverified"

                    frame = map_pose_frame(
                        image_landmarks,
                        world_landmarks,
                        frame_index=source_index,
                        timestamp_s=ts,
                        subject_track_id=subject_id,
                        visibility_threshold=self._visibility_threshold,
                    )
                    frames.append(frame)

                    if source_index >= last_selected_idx:
                        break

        if len(frames) < 2:
            raise ValueError("Not enough frames processed")

        selected_indices = {f.frame_index for f in frames}
        if selected_indices != sample_set:
            missing = sample_set - selected_indices
            raise ValueError(f"Missing selected frames: {missing}")

        content_hash = self._compute_content_hash(frames)
        artifact_key = f"pose/{content_hash}.jsonl"
        write_pose_frames(self._artifact_root, artifact_key, frames)

        first_ts = frames[0].timestamp_s
        last_ts = frames[-1].timestamp_s
        actual_rate = (len(frames) - 1) / (last_ts - first_ts) if last_ts > first_ts else self._sample_rate_hz

        return PoseSequence(
            video_id=video.id,
            provider="mediapipe",
            model_revision=f"sha256:{self._checkpoint_sha256}",
            native_skeleton="mediapipe-33",
            joint_mapping_version="mp33-camera-v1",
            sample_rate_hz=actual_rate,
            units="model_estimated_meters_uncalibrated",
            coordinate_system="hip_relative_camera_x_right_y_up_z_toward_viewer",
            capabilities={
                "supports_2d": True,
                "supports_estimated_3d": True,
                "world_translation": False,
                "physical_scale": False,
                "identity_verified": False,
            },
            quality_method="mp33-camera-v1;visibility_presence_proxy_not_3d_confidence;identity_unverified;source_pts_sampling_v1_tolerance_1us",
            frames_artifact_key=artifact_key,
        )

    def _validate_storage_key(self, key: str) -> Path:
        if not key or key in (".", ".."):
            raise ValueError("Invalid storage_key")
        if chr(92) in key:
            raise ValueError("Invalid storage_key: backslash not allowed")
        parts = key.split("/")
        if any(p in ("", ".", "..") for p in parts):
            raise ValueError("Invalid storage_key component")
        path = Path(key)
        if path.is_absolute():
            raise ValueError("storage_key must be relative")
        return path

    def _compute_content_hash(self, frames: list[Any]) -> str:
        import json
        lines = []
        for frame in frames:
            dump = frame.model_dump(mode="json")
            line = json.dumps(dump, sort_keys=True, separators=(",", ":"), allow_nan=False)
            lines.append(line + "\n")
        content = "".join(lines).encode("utf-8")
        return hashlib.sha256(content).hexdigest()


def _decode_frames(
    source_file: Path,
    probe: VideoProbe,
) -> Generator[tuple[bytes, int, float], None, None]:
    cmd = [
        "ffmpeg",
        "-v", "error",
        "-i", str(source_file),
        "-map", "0:v:0",
        "-an", "-sn",
        "-fps_mode", "passthrough",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "pipe:1",
    ]
    proc = None
    deadline = 120.0
    start_time = time.monotonic()
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if proc.stdout is None:
            raise RuntimeError("Failed to open decoder stdout")

        h, w = probe.height, probe.width
        if abs(probe.rotation) == 90:
            h, w = w, h
        frame_size = h * w * 3

        for source_index, ts in enumerate(probe.timestamps):
            raw = bytearray()
            while len(raw) < frame_size:
                if time.monotonic() - start_time > deadline:
                    raise RuntimeError("Decoder deadline exceeded")
                ready, _, _ = select.select([proc.stdout], [], [], 5.0)
                if not ready:
                    if proc.poll() is not None:
                        raise RuntimeError("Decoder exited unexpectedly")
                    continue
                to_read = frame_size - len(raw)
                chunk = os.read(proc.stdout.fileno(), to_read)
                if not chunk:
                    break
                raw.extend(chunk)
            if len(raw) != frame_size:
                raise ValueError(f"Short read: expected {frame_size}, got {len(raw)}")
            yield bytes(raw), source_index, ts

        proc.stdout.close()
        proc.wait(timeout=5)
        if proc.returncode != 0:
            raise RuntimeError(f"Decoder failed: {proc.returncode}")
    finally:
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            finally:
                if proc.stdout is not None:
                    proc.stdout.close()
