from __future__ import annotations

import asyncio
import hashlib
import json
import stat
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import ClientDisconnect

from app.ingest import MediaInfo, UploadRejected, ingest_video, probe_media
from app.store import Store


class FakeReceive:
    def __init__(self, chunks: list[bytes], *, disconnect: bool = False) -> None:
        self._chunks = chunks
        self._idx = 0
        self._disconnect = disconnect

    async def __call__(self) -> dict:
        if self._disconnect:
            return {"type": "http.disconnect"}
        if self._idx < len(self._chunks):
            chunk = self._chunks[self._idx]
            self._idx += 1
            return {"type": "http.request", "body": chunk, "more_body": self._idx < len(self._chunks)}
        return {"type": "http.request", "body": b"", "more_body": False}


class FakeRequest:
    def __init__(self, headers: dict[str, str], chunks: list[bytes], *, disconnect: bool = False) -> None:
        self.headers = headers
        self._receive = FakeReceive(chunks, disconnect=disconnect)

    async def stream(self):
        while True:
            msg = await self._receive()
            if msg.get("type") == "http.disconnect":
                raise ClientDisconnect()
            body = msg.get("body", b"")
            more = msg.get("more_body", False)
            yield body
            if not more:
                break

    async def body(self) -> bytes:
        parts = []
        async for chunk in self.stream():
            parts.append(chunk)
        return b"".join(parts)


def _make_probe_result(
    codec: str = "h264",
    width: int = 1280,
    height: int = 720,
    duration: str = "5.0",
    fps: str = "30/1",
    format_name: str = "mov,mp4,m4a,3gp,3g2,mj2",
    rotation: int | None = None,
    rotate_tag: str | None = None,
) -> bytes:
    stream: dict = {
        "codec_name": codec,
        "width": width,
        "height": height,
        "avg_frame_rate": fps,
    }
    if rotation is not None:
        stream["side_data_list"] = [{"rotation": rotation}]
    if rotate_tag is not None:
        stream["tags"] = {"rotate": rotate_tag}
    data = {
        "streams": [stream],
        "format": {
            "duration": duration,
            "format_name": format_name,
        },
    }
    return json.dumps(data).encode()


def test_probe_media_success():
    stdout = _make_probe_result()
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)) as mock:
        info = probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert info.duration_s == 5.0
    assert info.width == 1280
    assert info.height == 720
    assert info.rotation == 0
    assert info.mime == "video/mp4"
    args = mock.call_args[0][0]
    assert "ffprobe" in args
    assert "-protocol_whitelist" in args
    assert "file,pipe" in args
    assert "-format_whitelist" in args
    assert "mov,matroska,webm" in args
    assert "json" in args
    assert str(Path("/tmp/fake.mp4")) in args


def test_probe_media_rotation_side_data():
    stdout = _make_probe_result(rotation=90)
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        info = probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert info.rotation == 90


def test_probe_media_rotation_tag_fallback():
    stdout = _make_probe_result(rotate_tag="180")
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        info = probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert info.rotation == 180


def test_probe_media_rotation_side_data_preferred():
    stdout = _make_probe_result(rotation=-90, rotate_tag="180")
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        info = probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert info.rotation == -90


def test_probe_media_unsupported_codec():
    stdout = _make_probe_result(codec="mpeg4")
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422
    assert exc.value.code == "INVALID_MEDIA"


def test_probe_media_format_mismatch():
    stdout = _make_probe_result(format_name="hls")
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_duration_out_of_range():
    stdout = _make_probe_result(duration="61.0")
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4", max_duration_s=60)
    assert exc.value.status_code == 422


def test_probe_media_zero_duration():
    stdout = _make_probe_result(duration="0.0")
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_invalid_dimensions():
    stdout = _make_probe_result(width=0, height=720)
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_dimensions_too_large():
    stdout = _make_probe_result(width=1921, height=1080)
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_invalid_fps():
    stdout = _make_probe_result(fps="0/0")
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_fps_too_high():
    stdout = _make_probe_result(fps="300/1")
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_invalid_rotation():
    stdout = _make_probe_result(rotation=45)
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_malformed_rotation_fractional_string():
    stream = {
        "codec_name": "h264",
        "width": 1280,
        "height": 720,
        "avg_frame_rate": "30/1",
        "side_data_list": [{"rotation": "90.5"}],
    }
    stdout = json.dumps({"streams": [stream], "format": {"duration": "5.0", "format_name": "mov,mp4"}}).encode()
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_malformed_rotation_bool():
    stream = {
        "codec_name": "h264",
        "width": 1280,
        "height": 720,
        "avg_frame_rate": "30/1",
        "side_data_list": [{"rotation": True}],
    }
    stdout = json.dumps({"streams": [stream], "format": {"duration": "5.0", "format_name": "mov,mp4"}}).encode()
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_malformed_rotation_nan():
    stream = {
        "codec_name": "h264",
        "width": 1280,
        "height": 720,
        "avg_frame_rate": "30/1",
        "side_data_list": [{"rotation": float("nan")}],
    }
    stdout = json.dumps({"streams": [stream], "format": {"duration": "5.0", "format_name": "mov,mp4"}}).encode()
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_matrix_zero_wins_tag_ninety():
    stream = {
        "codec_name": "h264",
        "width": 1280,
        "height": 720,
        "avg_frame_rate": "30/1",
        "side_data_list": [{"rotation": 0}],
        "tags": {"rotate": "90"},
    }
    stdout = json.dumps({"streams": [stream], "format": {"duration": "5.0", "format_name": "mov,mp4"}}).encode()
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        info = probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert info.rotation == 0


def test_probe_media_nonlist_side_data():
    stream = {
        "codec_name": "h264",
        "width": 1280,
        "height": 720,
        "avg_frame_rate": "30/1",
        "side_data_list": {"rotation": 90},
    }
    stdout = json.dumps({"streams": [stream], "format": {"duration": "5.0", "format_name": "mov,mp4"}}).encode()
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_list_nonobject_side_data():
    stream = {
        "codec_name": "h264",
        "width": 1280,
        "height": 720,
        "avg_frame_rate": "30/1",
        "side_data_list": [90],
    }
    stdout = json.dumps({"streams": [stream], "format": {"duration": "5.0", "format_name": "mov,mp4"}}).encode()
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_malformed_tags_list():
    stream = {
        "codec_name": "h264",
        "width": 1280,
        "height": 720,
        "avg_frame_rate": "30/1",
        "tags": ["rotate", "90"],
    }
    stdout = json.dumps({"streams": [stream], "format": {"duration": "5.0", "format_name": "mov,mp4"}}).encode()
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_invalid_nested_json_type():
    stdout = json.dumps({"streams": "bad", "format": {"duration": "5.0", "format_name": "mov"}}).encode()
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_timeout():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ffprobe", 30)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422
    assert exc.value.code == "INVALID_MEDIA"


def test_probe_media_missing_ffprobe():
    with patch("subprocess.run", side_effect=FileNotFoundError("ffprobe")):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 503
    assert exc.value.code == "MEDIA_VALIDATOR_UNAVAILABLE"


def test_probe_media_nonzero_return():
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "ffprobe", stderr=b"bad file")):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422
    assert "bad file" not in exc.value.message
    assert "probe failed" in exc.value.message


def test_probe_media_invalid_json():
    with patch("subprocess.run", return_value=MagicMock(stdout=b"not json", returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_invalid_unicode():
    with patch("subprocess.run", return_value=MagicMock(stdout=b"\xff\xfe", returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_not_dict():
    with patch("subprocess.run", return_value=MagicMock(stdout=b"[]", returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_no_streams():
    stdout = json.dumps({"streams": [], "format": {"duration": "5.0", "format_name": "mov"}}).encode()
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_output_too_large():
    with patch("subprocess.run", return_value=MagicMock(stdout=b"x" * 65537, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def test_probe_media_unsupported_mime():
    with pytest.raises(UploadRejected) as exc:
        probe_media(Path("/tmp/fake.avi"), "video/avi")
    assert exc.value.status_code == 415


def test_probe_media_fraction_overflow():
    stream = {
        "codec_name": "h264",
        "width": 1280,
        "height": 720,
        "avg_frame_rate": "999999999999999999999/1",
    }
    stdout = json.dumps({"streams": [stream], "format": {"duration": "5.0", "format_name": "mov,mp4"}}).encode()
    with patch("subprocess.run", return_value=MagicMock(stdout=stdout, returncode=0)):
        with pytest.raises(UploadRejected) as exc:
            probe_media(Path("/tmp/fake.mp4"), "video/mp4")
    assert exc.value.status_code == 422


def _run(coro):
    return asyncio.run(coro)


def test_ingest_success(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    root = tmp_path / "uploads"
    data = b"\x00\x00\x00\x18ftypmp42" + b"x" * 1024
    sha = hashlib.sha256(data).hexdigest()
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4", "content-length": str(len(data))},
        chunks=[data[:512], data[512:]],
    )

    with patch("app.ingest.probe_media", return_value=MediaInfo(duration_s=5.0, width=1280, height=720, rotation=0, mime="video/mp4")):
        asset = _run(ingest_video(req, store, root, "a" * 32, now=1000.0))

    assert asset.owner_session_id == "a" * 32
    assert asset.sha256 == sha
    assert asset.bytes == len(data)
    assert asset.duration_s == 5.0
    assert asset.width == 1280
    assert asset.height == 720
    assert asset.rotation == 0
    assert asset.mime == "video/mp4"
    assert asset.timestamp_map_key is None
    assert asset.storage_key.startswith("uploads/" + "a" * 32 + "/")
    assert asset.storage_key.endswith("/source.bin")

    final_path = root / asset.storage_key
    assert final_path.exists()
    assert stat.S_IMODE(final_path.stat().st_mode) == 0o600
    assert final_path.read_bytes() == data

    loaded = store.get_asset("a" * 32, asset.id, now=1000.0)
    assert loaded.id == asset.id
    assert loaded.sha256 == sha


def test_ingest_wrong_consent(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    req = FakeRequest(
        headers={"x-upload-consent": "false", "content-type": "video/mp4"},
        chunks=[b"x"],
    )
    with pytest.raises(UploadRejected) as exc:
        _run(ingest_video(req, store, tmp_path / "root", "a" * 32))
    assert exc.value.status_code == 400
    assert exc.value.code == "CONSENT_REQUIRED"


def test_ingest_missing_consent(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    req = FakeRequest(
        headers={"content-type": "video/mp4"},
        chunks=[b"x"],
    )
    with pytest.raises(UploadRejected) as exc:
        _run(ingest_video(req, store, tmp_path / "root", "a" * 32))
    assert exc.value.status_code == 400


def test_ingest_bad_mime(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/avi"},
        chunks=[b"x"],
    )
    with pytest.raises(UploadRejected) as exc:
        _run(ingest_video(req, store, tmp_path / "root", "a" * 32))
    assert exc.value.status_code == 415


def test_ingest_mime_with_params(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    root = tmp_path / "uploads"
    data = b"\x00\x00\x00\x18ftypmp42" + b"x" * 100
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4; charset=utf-8", "content-length": str(len(data))},
        chunks=[data],
    )
    with patch("app.ingest.probe_media", return_value=MediaInfo(duration_s=1.0, width=640, height=480, rotation=0, mime="video/mp4")):
        asset = _run(ingest_video(req, store, root, "a" * 32, now=1000.0))
    assert asset.mime == "video/mp4"


def test_ingest_oversize_content_length(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4", "content-length": "104857601"},
        chunks=[b"x"],
    )
    with pytest.raises(UploadRejected) as exc:
        _run(ingest_video(req, store, tmp_path / "root", "a" * 32))
    assert exc.value.status_code == 413


def test_ingest_negative_content_length(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4", "content-length": "-1"},
        chunks=[b"x"],
    )
    with pytest.raises(UploadRejected) as exc:
        _run(ingest_video(req, store, tmp_path / "root", "a" * 32))
    assert exc.value.status_code == 400


def test_ingest_malformed_content_length(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4", "content-length": "abc"},
        chunks=[b"x"],
    )
    with pytest.raises(UploadRejected) as exc:
        _run(ingest_video(req, store, tmp_path / "root", "a" * 32))
    assert exc.value.status_code == 400


def test_ingest_empty_body(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4"},
        chunks=[b""],
    )
    with pytest.raises(UploadRejected) as exc:
        _run(ingest_video(req, store, tmp_path / "root", "a" * 32))
    assert exc.value.status_code == 422


def test_ingest_size_mismatch(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4", "content-length": "100"},
        chunks=[b"x" * 50],
    )
    with pytest.raises(UploadRejected) as exc:
        _run(ingest_video(req, store, tmp_path / "root", "a" * 32))
    assert exc.value.status_code == 400


def test_ingest_stream_oversize(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4"},
        chunks=[b"x" * 104857601],
    )
    with pytest.raises(UploadRejected) as exc:
        _run(ingest_video(req, store, tmp_path / "root", "a" * 32))
    assert exc.value.status_code == 413


def test_ingest_client_disconnect_cleanup(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    root = tmp_path / "uploads"
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4"},
        chunks=[b"x" * 100],
        disconnect=True,
    )
    with pytest.raises(UploadRejected) as exc:
        _run(ingest_video(req, store, root, "a" * 32))
    assert exc.value.status_code == 400
    assert exc.value.code == "INVALID_MEDIA"
    assert not any(p.name.startswith(".upload-") for p in root.rglob("*") if p.is_dir())


def test_ingest_probe_failure_cleanup(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    root = tmp_path / "uploads"
    data = b"\x00\x00\x00\x18ftypmp42" + b"x" * 100
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4", "content-length": str(len(data))},
        chunks=[data],
    )
    with patch("app.ingest.probe_media", side_effect=UploadRejected(422, "INVALID_MEDIA", "bad probe")):
        with pytest.raises(UploadRejected):
            _run(ingest_video(req, store, root, "a" * 32))
    assert not any(p.name.startswith(".upload-") for p in root.rglob("*") if p.is_dir())
    assert not (root / "uploads").exists() or len(list((root / "uploads").rglob("source.bin"))) == 0


def test_ingest_db_failure_cleanup(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    root = tmp_path / "uploads"
    data = b"\x00\x00\x00\x18ftypmp42" + b"x" * 100
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4", "content-length": str(len(data))},
        chunks=[data],
    )

    def bad_register(*args, **kwargs):
        raise RuntimeError("db down")

    with patch("app.ingest.probe_media", return_value=MediaInfo(duration_s=1.0, width=640, height=480, rotation=0, mime="video/mp4")):
        with patch.object(store, "register_asset", side_effect=bad_register):
            with pytest.raises(RuntimeError):
                _run(ingest_video(req, store, root, "a" * 32))

    assert not any(p.name.startswith(".upload-") for p in root.rglob("*") if p.is_dir())
    assert not (root / "uploads").exists() or len(list((root / "uploads").rglob("source.bin"))) == 0


def test_ingest_collision_no_delete_existing(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    root = tmp_path / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    owner_dir = root / "uploads" / ("a" * 32)
    owner_dir.mkdir(parents=True)
    existing = owner_dir / b"existing".hex()
    existing.mkdir()
    (existing / "source.bin").write_text("existing")

    data = b"\x00\x00\x00\x18ftypmp42" + b"x" * 100
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4", "content-length": str(len(data))},
        chunks=[data],
    )

    with patch("app.ingest.probe_media", return_value=MediaInfo(duration_s=1.0, width=640, height=480, rotation=0, mime="video/mp4")):
        with patch("app.ingest.os.urandom", return_value=b"existing"):
            with pytest.raises(UploadRejected) as exc:
                _run(ingest_video(req, store, root, "a" * 32, now=1000.0))
    assert exc.value.status_code == 409
    assert (existing / "source.bin").read_text() == "existing"


def test_ingest_symlink_inside_root_denied(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    root = tmp_path / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    uploads_dir = root / "uploads"
    uploads_dir.mkdir()
    real_owner = uploads_dir / ("b" * 32)
    real_owner.mkdir()
    owner_link = uploads_dir / ("a" * 32)
    owner_link.symlink_to(real_owner)

    data = b"\x00\x00\x00\x18ftypmp42" + b"x" * 100
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4", "content-length": str(len(data))},
        chunks=[data],
    )
    with patch("app.ingest.probe_media", return_value=MediaInfo(duration_s=1.0, width=640, height=480, rotation=0, mime="video/mp4")):
        with pytest.raises(UploadRejected) as exc:
            _run(ingest_video(req, store, root, "a" * 32, now=1000.0))
    assert exc.value.status_code == 503


def test_ingest_symlink_outside_root_denied(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    root = tmp_path / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    uploads_dir = root / "uploads"
    uploads_dir.mkdir()
    evil_target = tmp_path / "evil"
    evil_target.mkdir()
    owner_link = uploads_dir / ("a" * 32)
    owner_link.symlink_to(evil_target)

    data = b"\x00\x00\x00\x18ftypmp42" + b"x" * 100
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4", "content-length": str(len(data))},
        chunks=[data],
    )
    with patch("app.ingest.probe_media", return_value=MediaInfo(duration_s=1.0, width=640, height=480, rotation=0, mime="video/mp4")):
        with pytest.raises(UploadRejected) as exc:
            _run(ingest_video(req, store, root, "a" * 32, now=1000.0))
    assert exc.value.status_code == 503


def test_ingest_invalid_owner():
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4"},
        chunks=[b"x"],
    )
    with pytest.raises(ValueError):
        _run(ingest_video(req, MagicMock(), Path("/tmp/root"), "badowner"))


def test_ingest_invalid_config_max_bytes():
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4"},
        chunks=[b"x"],
    )
    with pytest.raises(UploadRejected) as exc:
        _run(ingest_video(req, MagicMock(), Path("/tmp/root"), "a" * 32, max_bytes=0))
    assert exc.value.status_code == 503
    assert exc.value.code == "CONFIG_INVALID"


def test_ingest_invalid_config_max_duration():
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4"},
        chunks=[b"x"],
    )
    with pytest.raises(UploadRejected) as exc:
        _run(ingest_video(req, MagicMock(), Path("/tmp/root"), "a" * 32, max_duration_s=61))
    assert exc.value.status_code == 503


def test_ingest_invalid_config_ttl():
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4"},
        chunks=[b"x"],
    )
    with pytest.raises(UploadRejected) as exc:
        _run(ingest_video(req, MagicMock(), Path("/tmp/root"), "a" * 32, ttl_s=86401))
    assert exc.value.status_code == 503


def test_ingest_invalid_config_now():
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4"},
        chunks=[b"x"],
    )
    with pytest.raises(UploadRejected) as exc:
        _run(ingest_video(req, MagicMock(), Path("/tmp/root"), "a" * 32, now=float("inf")))
    assert exc.value.status_code == 503


def test_ingest_default_now_post2020(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    root = tmp_path / "uploads"
    data = b"\x00\x00\x00\x18ftypmp42" + b"x" * 100
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4", "content-length": str(len(data))},
        chunks=[data],
    )
    with patch("app.ingest.probe_media", return_value=MediaInfo(duration_s=1.0, width=640, height=480, rotation=0, mime="video/mp4")) as mock_probe:
        with patch("app.ingest.time.time", return_value=1609459200.0) as mock_time:
            asset = _run(ingest_video(req, store, root, "a" * 32))
    assert asset.created_at.year >= 2021
    mock_probe.assert_called_once()
    mock_time.assert_called_once()


def test_ingest_webm_accepted(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    root = tmp_path / "uploads"
    data = b"\x1a\x45\xdf\xa3" + b"x" * 100
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/webm", "content-length": str(len(data))},
        chunks=[data],
    )
    with patch("app.ingest.probe_media", return_value=MediaInfo(duration_s=1.0, width=640, height=480, rotation=0, mime="video/webm")):
        asset = _run(ingest_video(req, store, root, "a" * 32, now=1000.0))
    assert asset.mime == "video/webm"


def test_ingest_quicktime_accepted(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    root = tmp_path / "uploads"
    data = b"\x00\x00\x00\x18ftypqt" + b"x" * 100
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/quicktime", "content-length": str(len(data))},
        chunks=[data],
    )
    with patch("app.ingest.probe_media", return_value=MediaInfo(duration_s=1.0, width=640, height=480, rotation=0, mime="video/quicktime")):
        asset = _run(ingest_video(req, store, root, "a" * 32, now=1000.0))
    assert asset.mime == "video/quicktime"


def test_ingest_duplicate_header_content_length(tmp_path: Path):
    class DupHeaders:
        def __init__(self, d: dict):
            self._d = d
        def get(self, k, default=None):
            return self._d.get(k, default)
        def getlist(self, k):
            if k == "content-length":
                return ["100", "200"]
            return [self._d.get(k)] if k in self._d else []

    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4", "content-length": "100"},
        chunks=[b"x"],
    )
    req.headers = DupHeaders(req.headers)
    with pytest.raises(UploadRejected) as exc:
        _run(ingest_video(req, MagicMock(), tmp_path / "root", "a" * 32))
    assert exc.value.status_code == 400


def test_ingest_cancellation_during_probe(tmp_path: Path):
    store_path = tmp_path / "store.db"
    store = Store(store_path)
    root = tmp_path / "uploads"
    data = b"\x00\x00\x00\x18ftypmp42" + b"x" * 100
    req = FakeRequest(
        headers={"x-upload-consent": "true", "content-type": "video/mp4", "content-length": str(len(data))},
        chunks=[data],
    )

    def cancelled_probe(*args, **kwargs):
        raise asyncio.CancelledError()

    with patch("app.ingest.probe_media", side_effect=cancelled_probe):
        with pytest.raises(asyncio.CancelledError):
            _run(ingest_video(req, store, root, "a" * 32))

    assert not any(p.name.startswith(".upload-") for p in root.rglob("*") if p.is_dir())
    assert not (root / "uploads").exists() or len(list((root / "uploads").rglob("source.bin"))) == 0
