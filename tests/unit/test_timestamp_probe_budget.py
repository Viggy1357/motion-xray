"""Timestamp-probe wall budget tests (offline; ffprobe subprocess mocked).

Root cause: probe_video used timeout=30 and a real 39.92s 1080p HEVC clip
exceeded it (TimeoutExpired at 30.03s). The budget is now a named 90s
constant: finite, ~2.25x the observed worst-case clip, not unbounded.
Decoder budget rollback (240 -> 120 baseline) is covered elsewhere.
"""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from providers.pose.mediapipe_provider import (
    _TIMESTAMP_PROBE_TIMEOUT_S,
    probe_video,
)


def _fake_ffprobe_json(timestamps=("0.0", "0.033333"), duration="1.0") -> bytes:
    return json.dumps({
        "frames": [{"best_effort_timestamp_time": t} for t in timestamps],
        "streams": [{"width": 1920, "height": 1080}],
        "format": {"duration": duration},
    }).encode()


def test_probe_uses_named_90s_timeout(tmp_path):
    vid = tmp_path / "clip.mp4"
    vid.write_bytes(b"fake")
    assert _TIMESTAMP_PROBE_TIMEOUT_S == 90.0
    with patch.object(
        subprocess, "run",
        return_value=SimpleNamespace(stdout=_fake_ffprobe_json(), returncode=0),
    ) as mock_run:
        probe = probe_video(vid)
    mock_run.assert_called_once()
    assert mock_run.call_args.kwargs["timeout"] == 90.0
    assert probe.width == 1920
    assert probe.timestamps == [0.0, 0.033333]
    assert probe.duration_s == 1.0


def test_probe_timeout_expired_propagates(tmp_path):
    vid = tmp_path / "clip.mp4"
    vid.write_bytes(b"fake")

    def boom(*a, **kw):
        assert kw["timeout"] == 90.0
        raise subprocess.TimeoutExpired(cmd=kw.get("cmd", a[0]), timeout=90.0)

    with patch.object(subprocess, "run", side_effect=boom) as mock_run:
        with pytest.raises(subprocess.TimeoutExpired):
            probe_video(vid)
    assert mock_run.call_count == 1  # not retried, not swallowed


def test_probe_invalid_timestamp_still_rejected(tmp_path):
    vid = tmp_path / "clip.mp4"
    vid.write_bytes(b"fake")
    bad = _fake_ffprobe_json(timestamps=("0.1", "0.05"))
    with patch.object(
        subprocess, "run",
        return_value=SimpleNamespace(stdout=bad, returncode=0),
    ) as mock_run:
        with pytest.raises(ValueError, match="Non-increasing timestamp"):
            probe_video(vid)
    assert mock_run.call_args.kwargs["timeout"] == 90.0


def test_probe_other_limits_unchanged(tmp_path):
    vid = tmp_path / "clip.mp4"
    vid.write_bytes(b"fake")
    over_duration = _fake_ffprobe_json(duration="121.0")
    with patch.object(
        subprocess, "run",
        return_value=SimpleNamespace(stdout=over_duration, returncode=0),
    ):
        with pytest.raises(ValueError, match="Duration out of range"):
            probe_video(vid)
    too_wide = json.dumps({
        "frames": [{"best_effort_timestamp_time": "0.0"},
                   {"best_effort_timestamp_time": "0.1"}],
        "streams": [{"width": 1921, "height": 1080}],
        "format": {"duration": "1.0"},
    }).encode()
    with patch.object(
        subprocess, "run",
        return_value=SimpleNamespace(stdout=too_wide, returncode=0),
    ):
        with pytest.raises(ValueError, match="Invalid width"):
            probe_video(vid)
