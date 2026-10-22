import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from contracts.media import VideoAsset
from providers.pose.mediapipe_provider import (
    MediaPipePoseProvider,
    VideoProbe,
    _decode_frames,
    probe_video,
    select_samples,
)


class FakeArray:
    def __init__(self, buf, dtype):
        self.buf = buf
        self.dtype = dtype

    def reshape(self, shape):
        assert shape == (2, 3, 3), f"expected (2,3,3), got {shape}"
        return self


class FakeLandmarker:
    def __init__(self):
        self.closed = False
        self.ms_captured = []
        self.pose_count = 1
        self.error = False
        self.on_exit = None

    def _make_lm(self, x=0.5, y=0.4, z=0.1, vis=0.9, pres=0.95):
        return SimpleNamespace(x=x, y=y, z=z, visibility=vis, presence=pres)

    def detect_for_video(self, img, ms):
        self.ms_captured.append(ms)
        if self.error:
            raise RuntimeError("boom")
        if self.pose_count == 0:
            return SimpleNamespace(pose_landmarks=[], pose_world_landmarks=[])
        lms = [[self._make_lm() for _ in range(33)] for _ in range(self.pose_count)]
        return SimpleNamespace(pose_landmarks=lms, pose_world_landmarks=lms)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.closed = True
        if self.on_exit:
            self.on_exit()


@pytest.fixture
def make_video_asset(tmp_path):
    def _make(**overrides):
        defaults = dict(
            id="vid-1",
            owner_session_id="sess-1",
            storage_key="demo/video.mp4",
            sha256="",
            mime="video/mp4",
            bytes=0,
            duration_s=11.0,
            width=2,
            height=3,
            rotation=90,
            created_at=datetime.now(timezone.utc),
        )
        defaults.update(overrides)
        return VideoAsset(**defaults)
    return _make


@pytest.fixture
def real_source(tmp_path, make_video_asset):
    src_dir = tmp_path / "demo"
    src_dir.mkdir()
    src = src_dir / "video.mp4"
    src.write_bytes(b"fake-mp4-data")
    asset = make_video_asset(
        sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
        bytes=src.stat().st_size,
    )
    return src, asset


@pytest.fixture
def real_checkpoint(tmp_path):
    ckpt = tmp_path / "model.task"
    ckpt.write_bytes(b"fake-task-data")
    return ckpt


@pytest.fixture
def fake_probe():
    return VideoProbe(
        timestamps=[10.0, 10.02, 10.05, 10.11, 10.20],
        width=2,
        height=3,
        rotation=90,
        duration_s=11.0,
    )


@pytest.fixture
def fake_landmarker():
    return FakeLandmarker()


@pytest.fixture
def fake_mp_modules(fake_landmarker):
    np_mod = SimpleNamespace(
        uint8=object(),
        frombuffer=lambda b, dtype: FakeArray(b, dtype),
    )
    img = SimpleNamespace(
        ImageFormat=SimpleNamespace(SRGB=1),
        Image=lambda image_format, data: SimpleNamespace(fmt=image_format, data=data),
    )
    tasks = SimpleNamespace(
        BaseOptions=lambda model_asset_path: SimpleNamespace(path=model_asset_path),
    )
    vision = SimpleNamespace(
        RunningMode=SimpleNamespace(VIDEO="VIDEO"),
        PoseLandmarkerOptions=lambda base_options, running_mode, num_poses, output_segmentation_masks: SimpleNamespace(
            base=base_options, mode=running_mode, num_poses=num_poses, seg=output_segmentation_masks,
        ),
        PoseLandmarker=SimpleNamespace(
            create_from_options=lambda options: fake_landmarker,
        ),
    )
    mp = SimpleNamespace(Image=img.Image, ImageFormat=img.ImageFormat)
    return {"mediapipe": mp, "numpy": np_mod, "mediapipe.tasks.python": tasks, "mediapipe.tasks.python.vision": vision}


def _make_provider(tmp_path, ckpt, **kw):
    defaults = dict(
        checkpoint_path=str(ckpt),
        checkpoint_sha256=hashlib.sha256(ckpt.read_bytes()).hexdigest() if ckpt.is_file() else "a" * 64,
        source_root=tmp_path,
        artifact_root=tmp_path / "artifacts",
        start_s=10.0,
        duration_s=0.12,
        sample_rate_hz=20,
    )
    defaults.update(kw)
    return MediaPipePoseProvider(**defaults)


class TestConstructorValidation:
    @pytest.mark.parametrize("field,bad", [
        ("start_s", -1),
        ("start_s", float("inf")),
        ("duration_s", 0),
        ("duration_s", 61),
        ("duration_s", float("nan")),
        ("sample_rate_hz", 0),
        ("sample_rate_hz", 31),
        ("sample_rate_hz", float("inf")),
        ("visibility_threshold", -0.1),
        ("visibility_threshold", 1.1),
        ("visibility_threshold", float("nan")),
    ])
    def test_rejects_invalid(self, tmp_path, real_checkpoint, field, bad):
        kwargs = {field: bad}
        with pytest.raises(ValueError):
            _make_provider(tmp_path, real_checkpoint, **kwargs)

    def test_accepts_inclusive_bounds(self, tmp_path, real_checkpoint):
        _make_provider(tmp_path, real_checkpoint, duration_s=30, sample_rate_hz=30, visibility_threshold=0)
        _make_provider(tmp_path, real_checkpoint, visibility_threshold=1)

    def test_rejects_bool_start(self, tmp_path, real_checkpoint):
        with pytest.raises(ValueError):
            _make_provider(tmp_path, real_checkpoint, start_s=True)


class TestStorageValidation:
    @pytest.fixture(autouse=True)
    def patch_probe(self, monkeypatch, fake_probe):
        def fake_probe_fn(path):
            return fake_probe
        monkeypatch.setattr("providers.pose.mediapipe_provider.probe_video", fake_probe_fn)

    def test_symlink_escape_refused(self, tmp_path, real_checkpoint, make_video_asset):
        outside = tmp_path.parent / f"outside_{tmp_path.name}.txt"
        outside.write_text("x")
        link = tmp_path / "demo" / "video.mp4"
        link.parent.mkdir(parents=True)
        link.symlink_to(outside)
        asset = make_video_asset(sha256=hashlib.sha256(b"x").hexdigest(), bytes=1)
        prov = _make_provider(tmp_path, real_checkpoint)
        with pytest.raises(ValueError, match="escapes"):
            prov.infer(asset)

    def test_traversal_escape_refused(self, tmp_path, real_checkpoint, make_video_asset):
        asset = make_video_asset(storage_key="../escape", sha256=hashlib.sha256(b"x").hexdigest(), bytes=1)
        prov = _make_provider(tmp_path, real_checkpoint)
        with pytest.raises(ValueError, match="storage_key"):
            prov.infer(asset)

    def test_size_mismatch(self, tmp_path, real_checkpoint, real_source):
        src, asset = real_source
        asset = asset.model_copy(update={"bytes": src.stat().st_size + 1})
        prov = _make_provider(tmp_path, real_checkpoint)
        with pytest.raises(ValueError, match="size mismatch"):
            prov.infer(asset)

    def test_hash_mismatch(self, tmp_path, real_checkpoint, real_source, make_video_asset):
        _, asset = real_source
        asset = asset.model_copy(update={"sha256": "0" * 64})
        prov = _make_provider(tmp_path, real_checkpoint)
        with pytest.raises(ValueError, match="SHA256 mismatch"):
            prov.infer(asset)

    def test_missing_checkpoint(self, tmp_path, real_source, make_video_asset):
        src, asset = real_source
        prov = _make_provider(tmp_path, tmp_path / "no.task")
        with pytest.raises(RuntimeError, match="Checkpoint not found"):
            prov.infer(asset)

    def test_checkpoint_hash_mismatch(self, tmp_path, real_source, real_checkpoint, make_video_asset):
        _, asset = real_source
        prov = _make_provider(tmp_path, real_checkpoint, checkpoint_sha256="0" * 64)
        with pytest.raises(ValueError, match="Checkpoint SHA256 mismatch"):
            prov.infer(asset)


class TestProbe:
    def test_ffprobe_command_and_parsing(self, tmp_path):
        vid = tmp_path / "v.mp4"
        vid.write_bytes(b"x")
        fake_out = json.dumps({
            "frames": [
                {"best_effort_timestamp_time": "0.0"},
                {"best_effort_timestamp_time": "0.1"},
            ],
            "streams": [{
                "width": 640, "height": 480,
                "side_data_list": [{"side_data_type": "Display Matrix", "rotation": -90}],
            }],
            "format": {"duration": "1.0"},
        })
        with patch.object(subprocess, "run", return_value=SimpleNamespace(stdout=fake_out.encode(), returncode=0)) as mock_run:
            probe = probe_video(vid)
        cmd = mock_run.call_args[0][0]
        assert "ffprobe" in cmd[0]
        assert str(vid) in cmd
        show_entries = [a for a in cmd if a.startswith("frame=") or a.startswith("stream=") or a.startswith("format=")]
        assert len(show_entries) == 1
        assert ":" in show_entries[0]
        assert probe.rotation == -90
        assert probe.timestamps == [0.0, 0.1]

    @pytest.mark.parametrize("bad_ts", [
        [0.0],
        [0.0, 0.0],
        [0.1, 0.0],
        [0.0, float("nan")],
    ])
    def test_rejects_bad_timestamps(self, tmp_path, bad_ts):
        vid = tmp_path / "v.mp4"
        vid.write_bytes(b"x")
        frames = [{"best_effort_timestamp_time": str(t)} for t in bad_ts]
        fake_out = json.dumps({
            "frames": frames,
            "streams": [{"width": 640, "height": 480}],
            "format": {"duration": "10.0"},
        })
        with patch.object(subprocess, "run", return_value=SimpleNamespace(stdout=fake_out.encode(), returncode=0)):
            with pytest.raises(ValueError):
                probe_video(vid)

    def test_rejects_invalid_rotation(self, tmp_path):
        vid = tmp_path / "v.mp4"
        vid.write_bytes(b"x")
        fake_out = json.dumps({
            "frames": [{"best_effort_timestamp_time": "0.0"}, {"best_effort_timestamp_time": "0.1"}],
            "streams": [{"width": 640, "height": 480, "side_data_list": [{"side_data_type": "Display Matrix", "rotation": 45}]}],
            "format": {"duration": "1.0"},
        })
        with patch.object(subprocess, "run", return_value=SimpleNamespace(stdout=fake_out.encode(), returncode=0)):
            with pytest.raises(ValueError, match="Invalid rotation"):
                probe_video(vid)


class TestSelectSamples:
    def test_basic(self):
        ts = [0, 0.01, 0.02, 0.5, 0.51, 1.0]
        assert select_samples(ts, 0, 1.1, 2) == [(0, 0.0), (3, 0.5), (5, 1.0)]

    def test_endpoint_excluded(self):
        ts = [0, 0.4, 0.5, 0.9, 1.0]
        assert select_samples(ts, 0, 1.0, 2) == [(0, 0.0), (2, 0.5)]

    def test_microsecond_quantization(self):
        ts = [10.005, 10.021667, 10.038333, 10.055, 10.071667, 10.088333]
        assert select_samples(ts, 10.0, 0.1, 30) == [(0, 10.005), (2, 10.038333), (4, 10.071667)]

    def test_strict_end_exclusion(self):
        ts = [0.0, 0.033, 0.066, 0.1]
        assert select_samples(ts, 0, 0.1, 30) == [(0, 0.0), (2, 0.066)]


class TestInfer:
    @pytest.fixture
    def patched_infer(self, tmp_path, real_source, real_checkpoint, fake_probe, fake_mp_modules, fake_landmarker):
        src, asset = real_source
        prov = _make_provider(tmp_path, real_checkpoint)
        cleanup_flag = {"decoder": False, "landmarker": False}
        fake_landmarker.on_exit = lambda: cleanup_flag.__setitem__("landmarker", True)

        def fake_decode(sf, pr):
            try:
                for i, ts in enumerate(pr.timestamps):
                    yield bytes(range(18)), i, ts
            finally:
                cleanup_flag["decoder"] = True

        def fake_load_runtime():
            return (fake_mp_modules["mediapipe"], fake_mp_modules["numpy"],
                    fake_mp_modules["mediapipe.tasks.python"], fake_mp_modules["mediapipe.tasks.python.vision"])

        with patch("providers.pose.mediapipe_provider.probe_video", return_value=fake_probe), \
             patch("providers.pose.mediapipe_provider._decode_frames", side_effect=fake_decode), \
             patch("providers.pose.mediapipe_provider._load_runtime", side_effect=fake_load_runtime):
            yield prov, asset, cleanup_flag

    def test_successful_infer(self, patched_infer, tmp_path, real_checkpoint, fake_landmarker):
        prov, asset, cleanup_flag = patched_infer
        result = prov.infer(asset)

        assert cleanup_flag["decoder"]
        assert cleanup_flag["landmarker"]
        assert result.provider == "mediapipe"
        assert result.frames_artifact_key.startswith("pose/")
        assert result.frames_artifact_key.endswith(".jsonl")

        from providers.pose.artifacts import read_pose_frames
        frames = list(read_pose_frames(tmp_path / "artifacts", result.frames_artifact_key))
        assert len(frames) == 3
        assert [f.frame_index for f in frames] == [0, 2, 3]
        assert [f.timestamp_s for f in frames] == [10.0, 10.05, 10.11]
        assert result.model_revision == f"sha256:{hashlib.sha256(real_checkpoint.read_bytes()).hexdigest()}"
        assert result.sample_rate_hz == pytest.approx(2 / 0.11)
        assert fake_landmarker.ms_captured == [10000, 10050, 10110]

        for f in frames:
            assert f.subject_track_id == "single-detection-identity-unverified"
            for j in f.joints.values():
                assert j.valid
                assert j.xy is not None
                assert j.xyz is not None
                assert not j.interpolated

        artifact_path = tmp_path / "artifacts" / result.frames_artifact_key
        assert hashlib.sha256(artifact_path.read_bytes()).hexdigest() == Path(result.frames_artifact_key).stem

    @pytest.mark.parametrize("pose_count,expect_id", [
        (0, None),
        (1, "single-detection-identity-unverified"),
        (2, None),
    ])
    def test_pose_counts(self, patched_infer, fake_landmarker, pose_count, expect_id):
        prov, asset, _ = patched_infer
        fake_landmarker.pose_count = pose_count
        result = prov.infer(asset)

        from providers.pose.artifacts import read_pose_frames
        frames = list(read_pose_frames(prov._artifact_root, result.frames_artifact_key))
        for f in frames:
            assert f.subject_track_id == expect_id
            for j in f.joints.values():
                if expect_id is None:
                    assert not j.valid
                    assert j.xy is None
                    assert j.xyz is None
                else:
                    assert j.valid
                    assert j.xy is not None

    def test_infer_failure_cleanup(self, patched_infer, fake_landmarker):
        prov, asset, cleanup_flag = patched_infer
        fake_landmarker.error = True
        with pytest.raises(RuntimeError, match="boom"):
            prov.infer(asset)
        assert cleanup_flag["decoder"]
        assert cleanup_flag["landmarker"]
        assert not any(prov._artifact_root.rglob("*.jsonl"))


class TestDecodeFramesMock:
    def test_short_read_cleanup(self, tmp_path):
        probe = VideoProbe(timestamps=[0.0], width=1, height=1, rotation=0, duration_s=1.0)
        vid = tmp_path / "v.mp4"
        vid.write_bytes(b"x")

        flags = {"terminate": False, "kill": False, "wait": False, "close": False}

        class FakeStdout:
            def fileno(self):
                return 3
            def close(self):
                flags["close"] = True

        fake_proc = SimpleNamespace(
            stdout=FakeStdout(),
            poll=lambda: None,
            terminate=lambda: flags.__setitem__("terminate", True),
            wait=lambda timeout=None: flags.__setitem__("wait", True),
            kill=lambda: flags.__setitem__("kill", True),
        )

        with patch("subprocess.Popen", return_value=fake_proc) as mock_popen, \
             patch("select.select", return_value=([fake_proc.stdout], [], [])), \
             patch("os.read", return_value=b""):
            with pytest.raises(ValueError, match="Short read"):
                list(_decode_frames(vid, probe))
        mock_popen.assert_called_once()
        assert flags["terminate"]
        assert flags["wait"]
        assert flags["close"]


class TestCapabilities:
    def test_lazy_import_not_called(self, tmp_path, real_checkpoint):
        prov = _make_provider(tmp_path, real_checkpoint)
        with patch("providers.pose.mediapipe_provider._load_runtime", side_effect=AssertionError("import called")):
            caps = prov.capabilities()
        assert caps.supports_2d
        assert caps.supports_estimated_3d
        assert caps.world_translation is False
        assert "pelvis" in caps.joint_availability

    def test_default_values(self, tmp_path, real_checkpoint):
        prov = _make_provider(tmp_path, real_checkpoint)
        caps = prov.capabilities()
        assert caps.supports_2d
        assert caps.supports_estimated_3d
        assert caps.world_translation is False
        assert "pelvis" in caps.joint_availability
