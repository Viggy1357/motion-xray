"""Manual endpoint geometry helper (internal).

Pure-stdlib geometry over MANUAL same-frame image annotations produced by a
manual annotator (e.g. Codex-assisted clicking), NOT professional or human
ground truth, and NOT automated perception. No automatic bar tracking, no
video/image access, no third-party deps, no model calls.

Measurements are explicit manual observations (bar point, chest target,
shoulder, hip), NOT wrist proxies. A zero 2D bar-to-chest distance does NOT
establish contact: depth is unobserved, so contact is ALWAYS unavailable.

Normalized distances use the manually observed shoulder-hip segment and are
comparable only between view-compatible setups. This module computes geometry
only; it never scores and never validates any aggregate milestone (e.g. M5).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import TypeGuard

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _finite(x: object) -> TypeGuard[float]:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


@dataclass(frozen=True, slots=True)
class Point:
    """One manually annotated image point with provenance."""

    x: float
    y: float
    frame_pts_s: float
    source_hash: str

    def __post_init__(self) -> None:
        if not _finite(self.x) or not _finite(self.y):
            raise ValueError("point coordinates must be finite non-bool numbers")
        if not _finite(self.frame_pts_s) or self.frame_pts_s < 0.0:
            raise ValueError("frame_pts_s must be a finite non-negative non-bool number")
        if not isinstance(self.source_hash, str) or _HASH_RE.fullmatch(self.source_hash) is None:
            raise ValueError("source_hash must be a 64-char lowercase hex sha256")


@dataclass(frozen=True, slots=True)
class Measurement:
    """value is None iff reason is a non-empty string. No magical defaults."""

    value: float | None
    reason: str | None
    unit: str

    def __post_init__(self) -> None:
        if (self.value is None) != (self.reason is not None):
            raise ValueError("value is None iff reason is not None")
        if self.reason is not None and (not isinstance(self.reason, str) or not self.reason):
            raise ValueError("reason must be a non-empty string when present")
        if self.value is not None and not _finite(self.value):
            raise ValueError("value must be finite and non-bool when present")


def _missing(reason: str, unit: str) -> Measurement:
    return Measurement(value=None, reason=reason, unit=unit)


def _check_frame(
    points: tuple[Point, ...],
    *,
    width: int,
    height: int,
    expected_source_sha256: str,
    expected_frame_pts_s: float,
    max_pts_delta_s: float,
) -> str | None:
    """Validate bounds, provenance binding, and same-frame PTS allowance."""
    for p in points:
        if not (0.0 <= p.x < width and 0.0 <= p.y < height):
            return "point_out_of_image_bounds"
    if any(p.source_hash != expected_source_sha256 for p in points):
        return "source_hash_mismatch"
    if any(abs(p.frame_pts_s - expected_frame_pts_s) > max_pts_delta_s for p in points):
        return "frame_pts_delta_exceeds_allowance"
    return None


def _validate_common(
    width: object,
    height: object,
    expected_source_sha256: object,
    expected_frame_pts_s: object,
    allowance: object,
) -> tuple[int, int, str, float, float]:
    if not isinstance(width, int) or isinstance(width, bool) or width <= 0:
        raise ValueError("width must be a positive int")
    if not isinstance(height, int) or isinstance(height, bool) or height <= 0:
        raise ValueError("height must be a positive int")
    if not isinstance(expected_source_sha256, str) or _HASH_RE.fullmatch(expected_source_sha256) is None:
        raise ValueError("expected_source_sha256 must be a 64-char lowercase hex sha256")
    if not _finite(expected_frame_pts_s) or expected_frame_pts_s < 0.0:
        raise ValueError("expected_frame_pts_s must be a finite non-negative non-bool number")
    if not _finite(allowance) or allowance < 0.0:
        raise ValueError("max_pts_delta_s must be a finite non-negative non-bool number")
    return int(width), int(height), expected_source_sha256, float(expected_frame_pts_s), float(allowance)


def measure_endpoint(
    *,
    bar: Point | None,
    chest: Point | None,
    shoulder: Point | None,
    hip: Point | None,
    width: int,
    height: int,
    expected_source_sha256: str,
    expected_frame_pts_s: float,
    max_pts_delta_s: float,
) -> dict[str, Measurement]:
    """Manual bar-to-chest endpoint geometry at one annotated frame.

    All points must bind to the caller-known asset (expected_source_sha256)
    and to expected_frame_pts_s within max_pts_delta_s. A zero allowance is
    valid and requires the exact same frame PTS. A positive allowance makes
    the result provisional; the caller preserves provenance metadata.

    Returns normalized vertical and euclidean bar-to-chest distances,
    normalized by the manually observed shoulder-hip segment length
    (comparable only between view-compatible setups). Contact is ALWAYS
    unavailable (depth unobserved), even at zero 2D distance.
    """
    width, height, sha, pts, allowance = _validate_common(
        width, height, expected_source_sha256, expected_frame_pts_s, max_pts_delta_s
    )
    out: dict[str, Measurement] = {
        "bar_chest_contact": _missing("contact_unavailable_depth_unobserved", "flag"),
    }
    if bar is None or chest is None or shoulder is None or hip is None:
        reason = "missing_coordinates"
        out["bar_chest_vertical_norm"] = _missing(reason, "ratio")
        out["bar_chest_euclidean_norm"] = _missing(reason, "ratio")
        return out
    err = _check_frame(
        (bar, chest, shoulder, hip),
        width=width,
        height=height,
        expected_source_sha256=sha,
        expected_frame_pts_s=pts,
        max_pts_delta_s=allowance,
    )
    if err is not None:
        out["bar_chest_vertical_norm"] = _missing(err, "ratio")
        out["bar_chest_euclidean_norm"] = _missing(err, "ratio")
        return out
    seg = math.hypot(shoulder.x - hip.x, shoulder.y - hip.y)
    if seg == 0.0 or not math.isfinite(seg):
        out["bar_chest_vertical_norm"] = _missing("degenerate_body_segment", "ratio")
        out["bar_chest_euclidean_norm"] = _missing("degenerate_body_segment", "ratio")
        return out
    out["bar_chest_vertical_norm"] = Measurement((bar.y - chest.y) / seg, None, "ratio")
    out["bar_chest_euclidean_norm"] = Measurement(
        math.hypot(bar.x - chest.x, bar.y - chest.y) / seg, None, "ratio"
    )
    return out


def annotation_interval(values: object) -> Measurement:
    """Spread (max-min) of repeated manual annotations, in pixels.

    This is a measurement uncertainty interval, NOT a valid scoring tolerance.
    """
    if not isinstance(values, (list, tuple)) or len(values) < 2:
        raise ValueError("values must be a list/tuple of at least two numbers")
    if not all(_finite(v) for v in values):
        raise ValueError("values must be finite non-bool numbers")
    vals = [float(v) for v in values]
    return Measurement(max(vals) - min(vals), None, "pixels")
