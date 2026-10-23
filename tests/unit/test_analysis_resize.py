"""Focused tests for ffmpeg-side analysis resize: dimensions, command shape,
byte framing, source PTS preservation, config gating and child wiring."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.processing_config import (
    DEFAULT_CHECKPOINT_SHA256,
    analysis_resize_enabled,
    analysis_resize_enabled_for,
    processing_version,
)
from providers.pose.mediapipe_provider import (
    MediaPipePoseProvider,
    VideoProbe,
    _analysis_dimensions,
    _decode_frames,
)


def _probe(w: int, h: int, rot: int = 0, ts=(0.0, 0.033333)) -> VideoProbe:
    return VideoProbe(timestamps=list(ts), width=w, height=h, rotation=rot, duration_s=1.0)


class TestAnalysisDimensions:
    @pytest.mark.parametrize("w,h,rot,expected", [
        (1920, 1080, 0, (720, 1280)),      # landscape
        (1920, 1080, 180, (720, 1280)),    # 180 keeps orientation
        (1920, 1080, -180, (720, 1280)),
        (1920, 1080, 90, (1280, 720)),     # portrait via +90
        (1920, 1080, -90, (1280, 720)),    # portrait via -90
        (1080, 1920, 0, (1280, 720)),      # native portrait
        (1081, 1919, 0, (1278, 720)),      # odd dims, nearest int, no even req
        (640, 480, 0, (480, 640)),         # small: never upscale
        (720, 1280, 0, (1280, 720)),       # exactly at bounds
        (1, 2000, 0, (1280, 1)),           # clamp to min 1
    ])
    def test_scaling(self, w, h, rot, expected):
        assert _analysis_dimensions(_probe(w, h, rot), True) == expected

    def test_disabled_returns_display_dims(self):
        assert _analysis_dimensions(_probe(1920, 1080, 90), False) == (1920, 1080)
        assert _analysis_dimensions(_probe(1920, 1080, 0), False) == (1080, 1920)

    def test_aspect_preserved_within_one_pixel(self):
        h, w = _analysis_dimensions(_probe(2560, 1440, 0), True)
        assert (h, w) == (720, 1280)
        assert abs((w / h) - (2560 / 1440)) < 0.01


class TestStrictBool:
    @pytest.mark.parametrize("bad", [1, 0, "1", "true", None, 1.0])
    def test_rejects_non_bool(self, bad):
        with pytest.raises(ValueError, match="resize_for_analysis"):
            MediaPipePoseProvider(resize_for_analysis=bad)

    def test_accepts_bool(self):
        assert MediaPipePoseProvider(resize_for_analysis=True)._resize_for_analysis is True
        assert MediaPipePoseProvider()._resize_for_analysis is False


class _FakeStdout:
    def __init__(self):
        self.closed = False

    def fileno(self):
        return 3

    def close(self):
        self.closed = True


def _run_decoder(probe: VideoProbe, resize: bool):
    captured = {}
    stdout = _FakeStdout()
    proc = SimpleNamespace(
        stdout=stdout,
        poll=lambda: None,
        returncode=0,
        terminate=lambda: None,
        kill=lambda: None,
        wait=lambda timeout=None: None,
    )

    def fake_popen(cmd, **kw):
        captured["cmd"] = cmd
        return proc

    with patch("subprocess.Popen", side_effect=fake_popen), \
         patch("select.select", return_value=([stdout], [], [])), \
         patch("os.read", side_effect=lambda fd, n: bytes(n)):
        frames = list(_decode_frames(Path("/tmp/v.mp4"), probe, resize_for_analysis=resize))
    return captured["cmd"], frames, stdout


class TestDecodeCommand:
    def test_scaled_command_shape_and_pts(self):
        probe = _probe(1281, 721, 0)
        cmd, frames, stdout = _run_decoder(probe, True)
        assert "-vf" in cmd
        assert cmd[cmd.index("-vf") + 1] == "scale=1279:720"
        assert cmd.index("-vf") < cmd.index("-f")
        assert not any("setpts" in a for a in cmd)
        assert not any(a.startswith("fps") for a in cmd)
        assert "-fps_mode" in cmd and cmd[cmd.index("-fps_mode") + 1] == "passthrough"
        assert [len(raw) for raw, _, _ in frames] == [720 * 1279 * 3] * 2
        assert [i for _, i, _ in frames] == [0, 1]
        assert [ts for _, _, ts in frames] == probe.timestamps
        assert stdout.closed

    def test_no_scale_when_within_bounds(self):
        cmd, frames, _ = _run_decoder(_probe(640, 480, 0), True)
        assert "-vf" not in cmd
        assert [len(raw) for raw, _, _ in frames] == [480 * 640 * 3] * 2

    def test_disabled_legacy_shape(self):
        probe = _probe(1281, 721, 90)
        cmd, frames, _ = _run_decoder(probe, False)
        assert "-vf" not in cmd
        assert [len(raw) for raw, _, _ in frames] == [1281 * 721 * 3] * 2

    def test_rotation_aware_scale(self):
        cmd, frames, _ = _run_decoder(_probe(1920, 1080, -90), True)
        assert cmd[cmd.index("-vf") + 1] == "scale=720:1280"
        assert len(frames[0][0]) == 1280 * 720 * 3


class TestConfig:
    def test_default_off(self, monkeypatch):
        monkeypatch.delenv("POSE_ANALYSIS_RESIZE", raising=False)
        assert analysis_resize_enabled() is False

    def test_on(self, monkeypatch):
        monkeypatch.setenv("POSE_ANALYSIS_RESIZE", "1")
        assert analysis_resize_enabled() is True

    @pytest.mark.parametrize("bad", ["2", "true", "01", "", "yes", " "])
    def test_invalid_raises(self, monkeypatch, bad):
        monkeypatch.setenv("POSE_ANALYSIS_RESIZE", bad)
        with pytest.raises(ValueError, match="POSE_ANALYSIS_RESIZE"):
            analysis_resize_enabled()

    def test_version_hash_changes_with_flag(self, monkeypatch):
        monkeypatch.delenv("POSE_ANALYSIS_RESIZE", raising=False)
        base = processing_version(DEFAULT_CHECKPOINT_SHA256)
        monkeypatch.setenv("POSE_ANALYSIS_RESIZE", "1")
        enabled = processing_version(DEFAULT_CHECKPOINT_SHA256)
        assert base != enabled
        assert enabled == processing_version(DEFAULT_CHECKPOINT_SHA256)


def _load_child():
    path = Path(__file__).resolve().parents[2] / "services" / "pose" / "child.py"
    spec = importlib.util.spec_from_file_location("pose_child_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_child_capture(monkeypatch, tmp_path, exercise="dumbbell_curl"):
    child = _load_child()
    captured = {}

    class FakeProvider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def infer(self, video):
            raise RuntimeError("sentinel-stop")

    monkeypatch.setattr(child, "MediaPipePoseProvider", FakeProvider)
    monkeypatch.setattr(child, "build_proxy", lambda *a, **k: {})
    monkeypatch.setattr(child, "_validate_request_path", lambda *a: b"{}")
    request = SimpleNamespace(
        video=SimpleNamespace(duration_s=1.0),
        job=SimpleNamespace(id="j", version_hash="0" * 64),
        exercise_id=exercise,
        variant="v",
    )
    monkeypatch.setattr(
        child.PoseJobInput, "model_validate_json", classmethod(lambda cls, b: request)
    )
    with pytest.raises(RuntimeError, match="sentinel-stop"):
        child.run_child(
            tmp_path / "request.json", tmp_path, tmp_path, tmp_path / "c.task", "0" * 64
        )
    return captured


class TestChildWiring:
    def test_flag_on_curl_true(self, monkeypatch, tmp_path):
        monkeypatch.setenv("POSE_ANALYSIS_RESIZE", "1")
        assert _run_child_capture(monkeypatch, tmp_path)["resize_for_analysis"] is True

    @pytest.mark.parametrize("exercise", ["lat_pulldown", "squat", "incline_chest_press", "unknown"])
    def test_flag_on_others_false(self, monkeypatch, tmp_path, exercise):
        monkeypatch.setenv("POSE_ANALYSIS_RESIZE", "1")
        assert _run_child_capture(monkeypatch, tmp_path, exercise)["resize_for_analysis"] is False

    def test_flag_off_all_false(self, monkeypatch, tmp_path):
        monkeypatch.delenv("POSE_ANALYSIS_RESIZE", raising=False)
        for exercise in ("dumbbell_curl", "lat_pulldown", "squat", "incline_chest_press", "unknown"):
            assert _run_child_capture(monkeypatch, tmp_path, exercise)["resize_for_analysis"] is False


class TestScopedResizeConfig:
    def test_invalid_env_raises(self, monkeypatch):
        monkeypatch.setenv("POSE_ANALYSIS_RESIZE", "yes")
        with pytest.raises(ValueError, match="POSE_ANALYSIS_RESIZE"):
            analysis_resize_enabled_for("dumbbell_curl")

    def test_hash_changes_when_scope_monkeypatched(self, monkeypatch):
        monkeypatch.setenv("POSE_ANALYSIS_RESIZE", "1")
        base = processing_version(DEFAULT_CHECKPOINT_SHA256)
        monkeypatch.setattr(
            "app.processing_config.ANALYSIS_RESIZE_EXERCISES",
            ("dumbbell_curl", "squat"),
        )
        widened = processing_version(DEFAULT_CHECKPOINT_SHA256)
        assert widened != base
        assert widened == processing_version(DEFAULT_CHECKPOINT_SHA256)

    def test_returns_strict_bool(self, monkeypatch):
        monkeypatch.setenv("POSE_ANALYSIS_RESIZE", "1")
        assert analysis_resize_enabled_for("dumbbell_curl") is True
        assert analysis_resize_enabled_for("squat") is False
        monkeypatch.setenv("POSE_ANALYSIS_RESIZE", "0")
        assert analysis_resize_enabled_for("dumbbell_curl") is False
