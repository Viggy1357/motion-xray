from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path
from typing import Any

import pytest

from contracts.pose import JointObservation, PoseFrame
from movement.posture import ProjectionAxis, measure_torso_frame, summarize_window
from movement.observations import AngleObservation


def joint(
    xy: tuple[float, float] | None = None,
    xyz: tuple[float, float, float] | None = None,
    valid: bool = True,
    interpolated: bool = False,
    quality_method: str | None = None,
) -> JointObservation:
    return JointObservation(
        xy=xy,
        xyz=xyz,
        valid=valid,
        interpolated=interpolated,
        quality_method=quality_method,
    )


def pose_frame(
    frame_index: int = 0,
    timestamp_s: float = 0.0,
    **joints: JointObservation,
) -> PoseFrame:
    return PoseFrame(
        frame_index=frame_index,
        timestamp_s=timestamp_s,
        joints=joints,
    )


def axis_up(
    up_xy: tuple[float, float] = (0.0, -1.0),
    positive_cross_sign: int = 1,
    axis_id: str = "image_up",
) -> ProjectionAxis:
    return ProjectionAxis(
        version="posture-observation-v1",
        axis_id=axis_id,
        up_xy=up_xy,
        positive_cross_sign=positive_cross_sign,
    )


def test_projection_axis_happy_path() -> None:
    a = axis_up()
    assert a.version == "posture-observation-v1"
    assert a.axis_id == "image_up"
    assert a.up_xy == (0.0, -1.0)
    assert a.positive_cross_sign == 1


@pytest.mark.parametrize(
    "kwargs,expected_error",
    [
        ({"version": ""}, "version"),
        ({"axis_id": ""}, "axis_id"),
        ({"up_xy": (0.0, 0.0)}, "up_xy"),
        ({"up_xy": (1.0,)}, "up_xy"),
        ({"up_xy": (1.0, float("inf"))}, "finite"),
        ({"up_xy": (1.0, float("nan"))}, "finite"),
        ({"up_xy": (True, 1.0)}, "bool"),
        ({"positive_cross_sign": 0}, "sign"),
        ({"positive_cross_sign": 2}, "sign"),
        ({"positive_cross_sign": -2}, "sign"),
        ({"positive_cross_sign": 1.0}, "bool"),
        ({"positive_cross_sign": True}, "bool"),
        ({"up_xy": [0.0, -1.0]}, "accept"),
    ],
)
def test_projection_axis_rejects_invalid_fields(
    kwargs: dict[str, Any], expected_error: str
) -> None:
    base = {
        "version": "posture-observation-v1",
        "axis_id": "image_up",
        "up_xy": (0.0, -1.0),
        "positive_cross_sign": 1,
    }
    base.update(kwargs)
    if expected_error == "accept":
        a = ProjectionAxis(**base)
        assert a.up_xy == (0.0, -1.0)
    else:
        with pytest.raises(ValueError):
            ProjectionAxis(**base)


def test_projection_axis_is_frozen() -> None:
    a = axis_up()
    with pytest.raises(Exception):
        a.up_xy = (1.0, 0.0)


def test_measure_torso_frame_perpendicular_right_lean() -> None:
    f = pose_frame(
        left_hip=joint(xy=(0.5, 0.7)),
        left_shoulder=joint(xy=(0.7, 0.7)),
    )
    obs = measure_torso_frame(f, side="left", width=100, height=100, axis=axis_up())
    assert obs.metric == "torso_axis_angle"
    assert obs.space == "projected_2d"
    assert obs.value == pytest.approx(90.0, abs=1e-9)


def test_measure_torso_frame_perpendicular_left_lean() -> None:
    f = pose_frame(
        left_hip=joint(xy=(0.5, 0.7)),
        left_shoulder=joint(xy=(0.3, 0.7)),
    )
    obs = measure_torso_frame(f, side="left", width=100, height=100, axis=axis_up())
    assert obs.value == pytest.approx(-90.0, abs=1e-9)


def test_measure_torso_frame_30_degrees_fixture() -> None:
    angle = math.radians(30.0)
    hip = (0.5, 0.7)
    shoulder = (0.5 + 0.2 * math.sin(angle), 0.7 - 0.2 * math.cos(angle))
    f = pose_frame(
        left_hip=joint(xy=hip),
        left_shoulder=joint(xy=shoulder),
    )
    obs = measure_torso_frame(f, side="left", width=100, height=100, axis=axis_up())
    assert obs.value == pytest.approx(30.0, abs=1e-9)


def test_measure_torso_frame_wrap_179_to_minus_179() -> None:
    a = math.radians(179.0)
    hip = (0.5, 0.7)
    shoulder_plus = (0.5 + 0.2 * math.sin(a), 0.7 - 0.2 * math.cos(a))
    obs_plus = measure_torso_frame(
        pose_frame(left_hip=joint(xy=hip), left_shoulder=joint(xy=shoulder_plus)),
        side="left",
        width=100,
        height=100,
        axis=axis_up(),
    )
    assert obs_plus.value == pytest.approx(179.0, abs=1e-9)

    a_minus = math.radians(-179.0)
    shoulder_minus = (0.5 + 0.2 * math.sin(a_minus), 0.7 - 0.2 * math.cos(a_minus))
    obs_minus = measure_torso_frame(
        pose_frame(timestamp_s=1.0, left_hip=joint(xy=hip), left_shoulder=joint(xy=shoulder_minus)),
        side="left",
        width=100,
        height=100,
        axis=axis_up(),
    )
    assert obs_minus.value == pytest.approx(-179.0, abs=1e-9)

    summary = summarize_window(
        [obs_plus, obs_minus],
        start_s=0.0,
        end_s=1.0,
        max_gap_s=1.0,
        circular=True,
    )
    assert summary.minimum == pytest.approx(179.0, abs=1e-9)
    assert summary.maximum == pytest.approx(181.0, abs=1e-9)
    assert summary.excursion == pytest.approx(2.0, abs=1e-9)
    assert summary.end_change == pytest.approx(2.0, abs=1e-9)


def test_measure_torso_frame_sign_mirroring() -> None:
    f = pose_frame(
        left_hip=joint(xy=(0.5, 0.7)),
        left_shoulder=joint(xy=(0.7, 0.7)),
    )
    obs_plus = measure_torso_frame(
        f, side="left", width=100, height=100, axis=axis_up(positive_cross_sign=1)
    )
    obs_minus = measure_torso_frame(
        f, side="left", width=100, height=100, axis=axis_up(positive_cross_sign=-1)
    )
    assert obs_plus.value == pytest.approx(-obs_minus.value, abs=1e-9)


def test_measure_torso_frame_tilted_axis() -> None:
    f = pose_frame(
        left_hip=joint(xy=(0.5, 0.7)),
        left_shoulder=joint(xy=(0.5 + 0.2 * math.cos(math.pi / 4), 0.7 + 0.2 * math.sin(math.pi / 4))),
    )
    axis = axis_up(up_xy=(math.cos(math.pi / 4), math.sin(math.pi / 4)), axis_id="tilted")
    obs = measure_torso_frame(f, side="left", width=100, height=100, axis=axis)
    assert obs.value == pytest.approx(0.0, abs=1e-9)


def test_measure_torso_frame_aspect_ratio_scaling() -> None:
    f = pose_frame(
        left_hip=joint(xy=(0.5, 0.7)),
        left_shoulder=joint(xy=(0.5, 0.5)),
    )
    obs = measure_torso_frame(f, side="left", width=200, height=100, axis=axis_up())
    assert obs.value == pytest.approx(0.0, abs=1e-9)


def test_measure_torso_frame_aspect_ratio_changes_angle() -> None:
    f = pose_frame(
        left_hip=joint(xy=(0.5, 0.7)),
        left_shoulder=joint(xy=(0.6, 0.6)),
    )
    obs_square = measure_torso_frame(
        f, side="left", width=100, height=100, axis=axis_up()
    )
    obs_wide = measure_torso_frame(
        f, side="left", width=200, height=100, axis=axis_up()
    )
    assert obs_square.value != pytest.approx(obs_wide.value, abs=1e-9)
    expected_square = math.degrees(math.atan2(1.0, 1.0))
    assert obs_square.value == pytest.approx(expected_square, abs=1e-9)
    expected_wide = math.degrees(math.atan2(2.0, 1.0))
    assert obs_wide.value == pytest.approx(expected_wide, abs=1e-9)


def test_measure_torso_frame_huge_coordinates() -> None:
    f = pose_frame(
        left_hip=joint(xy=(1e150, 1e150)),
        left_shoulder=joint(xy=(1e150 + 1e149, 1e150)),
    )
    obs = measure_torso_frame(f, side="left", width=100, height=100, axis=axis_up())
    assert obs.value == pytest.approx(90.0, abs=1e-9)


def test_measure_torso_frame_tiny_coordinates() -> None:
    f = pose_frame(
        left_hip=joint(xy=(1e-150, 1e-150)),
        left_shoulder=joint(xy=(1e-150 + 1e-151, 1e-150)),
    )
    obs = measure_torso_frame(f, side="left", width=100, height=100, axis=axis_up())
    assert obs.value == pytest.approx(90.0, abs=1e-9)


def test_measure_torso_frame_huge_width_height() -> None:
    f = pose_frame(
        left_hip=joint(xy=(0.5, 0.7)),
        left_shoulder=joint(xy=(0.7, 0.7)),
    )
    obs = measure_torso_frame(
        f, side="left", width=10_000, height=10_000, axis=axis_up()
    )
    assert obs.value == pytest.approx(90.0, abs=1e-9)


def test_measure_torso_frame_tiny_width_height() -> None:
    f = pose_frame(
        left_hip=joint(xy=(0.5, 0.7)),
        left_shoulder=joint(xy=(0.7, 0.7)),
    )
    obs = measure_torso_frame(f, side="left", width=1, height=1, axis=axis_up())
    assert obs.value == pytest.approx(90.0, abs=1e-9)


def test_measure_torso_frame_rejects_invalid_side() -> None:
    f = pose_frame(left_hip=joint(xy=(0.5, 0.7)), left_shoulder=joint(xy=(0.5, 0.5)))
    with pytest.raises(ValueError):
        measure_torso_frame(f, side="center", width=100, height=100, axis=axis_up())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "width,height",
    [
        (0, 100),
        (100, 0),
        (-1, 100),
        (100, -1),
        (100.5, 100),
        (100, True),
        (True, 100),
    ],
)
def test_measure_torso_frame_rejects_bad_dimensions(width: Any, height: Any) -> None:
    f = pose_frame(left_hip=joint(xy=(0.5, 0.7)), left_shoulder=joint(xy=(0.5, 0.5)))
    with pytest.raises(ValueError):
        measure_torso_frame(f, side="left", width=width, height=height, axis=axis_up())


def test_measure_torso_frame_missing_joint() -> None:
    f = pose_frame(left_hip=joint(xy=(0.5, 0.7)))
    obs = measure_torso_frame(f, side="left", width=100, height=100, axis=axis_up())
    assert obs.value is None
    assert obs.reason == "missing_joint"


def test_measure_torso_frame_invalid_joint() -> None:
    f = pose_frame(
        left_hip=joint(xy=(0.5, 0.7), valid=False),
        left_shoulder=joint(xy=(0.5, 0.5)),
    )
    obs = measure_torso_frame(f, side="left", width=100, height=100, axis=axis_up())
    assert obs.value is None
    assert obs.reason == "invalid_joint"


def test_measure_torso_frame_interpolated_joint() -> None:
    f = pose_frame(
        left_hip=joint(xy=(0.5, 0.7), interpolated=True, quality_method="linear"),
        left_shoulder=joint(xy=(0.5, 0.5)),
    )
    obs = measure_torso_frame(f, side="left", width=100, height=100, axis=axis_up())
    assert obs.value is None
    assert obs.reason == "interpolated_joint"


def test_measure_torso_frame_missing_coordinates() -> None:
    f = pose_frame(
        left_hip=joint(xy=None, xyz=(0.0, 0.0, 0.0)),
        left_shoulder=joint(xy=(0.5, 0.5)),
    )
    obs = measure_torso_frame(f, side="left", width=100, height=100, axis=axis_up())
    assert obs.value is None
    assert obs.reason == "missing_coordinates"


def test_measure_torso_frame_degenerate_geometry() -> None:
    f = pose_frame(
        left_hip=joint(xy=(0.5, 0.7)),
        left_shoulder=joint(xy=(0.5, 0.7)),
    )
    obs = measure_torso_frame(f, side="left", width=100, height=100, axis=axis_up())
    assert obs.value is None
    assert obs.reason == "degenerate_geometry"


def test_measure_torso_frame_reason_precedence() -> None:
    f = pose_frame(
        left_shoulder=joint(xy=(0.5, 0.5), valid=False),
    )
    obs = measure_torso_frame(f, side="left", width=100, height=100, axis=axis_up())
    assert obs.reason == "missing_joint"


def test_measure_torso_frame_only_same_side() -> None:
    f = pose_frame(
        right_hip=joint(xy=(0.5, 0.7)),
        right_shoulder=joint(xy=(0.5, 0.5)),
    )
    obs = measure_torso_frame(f, side="left", width=100, height=100, axis=axis_up())
    assert obs.value is None
    assert obs.reason == "missing_joint"


def test_measure_torso_frame_preserves_frame_index_and_timestamp() -> None:
    f = pose_frame(
        frame_index=42,
        timestamp_s=3.5,
        left_hip=joint(xy=(0.5, 0.7)),
        left_shoulder=joint(xy=(0.5, 0.5)),
    )
    obs = measure_torso_frame(f, side="left", width=100, height=100, axis=axis_up())
    assert obs.frame_index == 42
    assert obs.timestamp_s == pytest.approx(3.5)


def test_measure_torso_frame_negative_angle_allowed() -> None:
    f = pose_frame(
        left_hip=joint(xy=(0.5, 0.7)),
        left_shoulder=joint(xy=(0.3, 0.7)),
    )
    obs = measure_torso_frame(f, side="left", width=100, height=100, axis=axis_up())
    assert obs.value == pytest.approx(-90.0, abs=1e-9)


def _torso_obs(value: float | None, timestamp_s: float, reason: str | None = None) -> AngleObservation:
    return AngleObservation(
        frame_index=0,
        timestamp_s=timestamp_s,
        metric="torso_axis_angle",
        space="projected_2d",
        side="left",
        value=value,
        reason=reason,
    )


def test_summarize_window_happy_path_linear() -> None:
    samples = [_torso_obs(10.0, 0.0), _torso_obs(20.0, 1.0), _torso_obs(30.0, 2.0)]
    summary = summarize_window(
        samples, start_s=0.0, end_s=2.0, max_gap_s=1.0, circular=False
    )
    assert summary.requested_start_s == 0.0
    assert summary.requested_end_s == 2.0
    assert summary.first_pts_s == 0.0
    assert summary.last_pts_s == 2.0
    assert summary.total_samples == 3
    assert summary.valid_samples == 3
    assert summary.minimum == pytest.approx(10.0, abs=1e-9)
    assert summary.maximum == pytest.approx(30.0, abs=1e-9)
    assert summary.excursion == pytest.approx(20.0, abs=1e-9)
    assert summary.start_value == pytest.approx(10.0, abs=1e-9)
    assert summary.end_value == pytest.approx(30.0, abs=1e-9)
    assert summary.end_change == pytest.approx(20.0, abs=1e-9)
    assert summary.reason is None


def test_summarize_window_circular_shortest_arc() -> None:
    samples = [_torso_obs(170.0, 0.0), _torso_obs(-170.0, 1.0)]
    summary = summarize_window(
        samples, start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=True
    )
    assert summary.minimum == pytest.approx(170.0, abs=1e-9)
    assert summary.maximum == pytest.approx(190.0, abs=1e-9)
    assert summary.excursion == pytest.approx(20.0, abs=1e-9)
    assert summary.end_change == pytest.approx(20.0, abs=1e-9)


def test_summarize_window_circular_ambiguous_180() -> None:
    samples = [_torso_obs(0.0, 0.0), _torso_obs(180.0, 1.0)]
    summary = summarize_window(
        samples, start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=True
    )
    assert summary.reason == "ambiguous_rotation"
    assert summary.minimum is None
    assert summary.maximum is None
    assert summary.excursion is None


def test_summarize_window_insufficient_samples() -> None:
    samples = [_torso_obs(10.0, 0.0)]
    summary = summarize_window(
        samples, start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=False
    )
    assert summary.reason == "insufficient_samples"
    assert summary.minimum is None
    assert summary.maximum is None


def test_summarize_window_missing_observation() -> None:
    samples = [
        _torso_obs(10.0, 0.0),
        _torso_obs(None, 1.0, reason="missing_joint"),
        _torso_obs(20.0, 2.0),
    ]
    summary = summarize_window(
        samples, start_s=0.0, end_s=2.0, max_gap_s=1.0, circular=False
    )
    assert summary.reason == "missing_observation"
    assert summary.minimum is None


def test_summarize_window_timestamp_gap() -> None:
    samples = [_torso_obs(10.0, 0.0), _torso_obs(20.0, 2.0)]
    summary = summarize_window(
        samples, start_s=0.0, end_s=2.0, max_gap_s=1.0, circular=False
    )
    assert summary.reason == "timestamp_gap"


def test_summarize_window_partial_window_start_gap() -> None:
    samples = [_torso_obs(10.0, 0.6), _torso_obs(20.0, 1.0)]
    summary = summarize_window(
        samples, start_s=0.0, end_s=1.0, max_gap_s=0.5, circular=False
    )
    assert summary.reason == "partial_window"


def test_summarize_window_partial_window_end_gap() -> None:
    samples = [_torso_obs(10.0, 0.0), _torso_obs(20.0, 0.4)]
    summary = summarize_window(
        samples, start_s=0.0, end_s=1.0, max_gap_s=0.5, circular=False
    )
    assert summary.reason == "partial_window"


def test_summarize_window_no_padding_or_interpolation() -> None:
    samples = [_torso_obs(10.0, 0.0), _torso_obs(20.0, 2.0)]
    summary = summarize_window(
        samples, start_s=0.0, end_s=2.0, max_gap_s=0.5, circular=False
    )
    assert summary.reason == "timestamp_gap"


def test_summarize_window_mixed_side_rejected() -> None:
    a = _torso_obs(10.0, 0.0)
    b = AngleObservation(
        frame_index=0,
        timestamp_s=1.0,
        metric="torso_axis_angle",
        space="projected_2d",
        side="right",
        value=20.0,
        reason=None,
    )
    with pytest.raises(ValueError):
        summarize_window([a, b], start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=False)


def test_summarize_window_mixed_metric_rejected() -> None:
    a = _torso_obs(10.0, 0.0)
    b = AngleObservation(
        frame_index=0,
        timestamp_s=1.0,
        metric="elbow_angle",
        space="projected_2d",
        side="left",
        value=20.0,
        reason=None,
    )
    with pytest.raises(ValueError):
        summarize_window([a, b], start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=False)


def test_summarize_window_timestamps_not_strictly_increasing() -> None:
    samples = [_torso_obs(10.0, 0.0), _torso_obs(20.0, 0.0)]
    with pytest.raises(ValueError):
        summarize_window(
            samples, start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=False
        )


def test_summarize_window_timestamps_not_finite() -> None:
    samples = [_torso_obs(10.0, float("inf"))]
    with pytest.raises(ValueError):
        summarize_window(
            samples, start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=False
        )


def test_summarize_window_value_none_requires_reason() -> None:
    a = AngleObservation(
        frame_index=0,
        timestamp_s=0.0,
        metric="torso_axis_angle",
        space="projected_2d",
        side="left",
        value=None,
        reason=None,
    )
    with pytest.raises(ValueError):
        summarize_window([a, a], start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=False)


def test_summarize_window_reason_requires_none_value() -> None:
    a = AngleObservation(
        frame_index=0,
        timestamp_s=0.0,
        metric="torso_axis_angle",
        space="projected_2d",
        side="left",
        value=10.0,
        reason="missing_joint",
    )
    with pytest.raises(ValueError):
        summarize_window([a, a], start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=False)


def test_summarize_window_rejects_non_finite_value() -> None:
    a = AngleObservation(
        frame_index=0,
        timestamp_s=0.0,
        metric="torso_axis_angle",
        space="projected_2d",
        side="left",
        value=float("inf"),
        reason=None,
    )
    with pytest.raises(ValueError):
        summarize_window([a, a], start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=False)


def test_summarize_window_rejects_bool_value() -> None:
    a = AngleObservation(
        frame_index=0,
        timestamp_s=0.0,
        metric="torso_axis_angle",
        space="projected_2d",
        side="left",
        value=True,  # type: ignore[arg-type]
        reason=None,
    )
    with pytest.raises(ValueError):
        summarize_window([a, a], start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=False)


def test_summarize_window_boundary_inclusive() -> None:
    samples = [_torso_obs(10.0, 0.0), _torso_obs(20.0, 1.0)]
    summary = summarize_window(
        samples, start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=False
    )
    assert summary.valid_samples == 2


def test_summarize_window_empty_selection() -> None:
    samples = [_torso_obs(10.0, 5.0)]
    summary = summarize_window(
        samples, start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=False
    )
    assert summary.reason == "insufficient_samples"
    assert summary.first_pts_s is None
    assert summary.last_pts_s is None


def test_summarize_window_no_source_mutation() -> None:
    samples = [_torso_obs(10.0, 0.0), _torso_obs(20.0, 1.0)]
    original = [dataclasses.replace(s) for s in samples]
    summarize_window(samples, start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=False)
    assert samples == original


def test_summarize_window_preserves_first_actual_pts_single_selection() -> None:
    samples = [_torso_obs(10.0, 0.0)]
    summary = summarize_window(
        samples, start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=False
    )
    assert summary.first_pts_s == 0.0
    assert summary.last_pts_s == 0.0
    assert summary.total_samples == 1
    assert summary.valid_samples == 1
    assert summary.reason == "insufficient_samples"


def test_summarize_window_missing_observation_priority_over_gap() -> None:
    samples = [
        _torso_obs(10.0, 0.0),
        _torso_obs(None, 0.5, reason="missing_joint"),
        _torso_obs(20.0, 2.0),
    ]
    summary = summarize_window(
        samples, start_s=0.0, end_s=2.0, max_gap_s=1.0, circular=False
    )
    assert summary.reason == "missing_observation"


def test_summarize_window_circular_zero_norm_valid() -> None:
    samples = [_torso_obs(0.0, 0.0), _torso_obs(0.0, 1.0)]
    summary = summarize_window(
        samples, start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=True
    )
    assert summary.reason is None
    assert summary.minimum == pytest.approx(0.0, abs=1e-9)
    assert summary.maximum == pytest.approx(0.0, abs=1e-9)
    assert summary.excursion == pytest.approx(0.0, abs=1e-9)


def test_summarize_window_circular_values_null_consistency() -> None:
    samples = [_torso_obs(0.0, 0.0), _torso_obs(180.0, 1.0)]
    summary = summarize_window(
        samples, start_s=0.0, end_s=1.0, max_gap_s=1.0, circular=True
    )
    assert summary.start_value is None
    assert summary.end_value is None
    assert summary.end_change is None


def test_measure_torso_frame_stability_translation_rescale() -> None:
    axis = axis_up()
    f1 = pose_frame(
        left_hip=joint(xy=(0.5, 0.7)),
        left_shoulder=joint(xy=(0.7, 0.7)),
    )
    f2 = pose_frame(
        left_hip=joint(xy=(0.6, 0.8)),
        left_shoulder=joint(xy=(0.8, 0.8)),
    )
    o1 = measure_torso_frame(f1, side="left", width=100, height=100, axis=axis)
    o2 = measure_torso_frame(f2, side="left", width=100, height=100, axis=axis)
    assert o1.value == pytest.approx(o2.value, abs=1e-9)


def test_measure_torso_frame_repeat_identical() -> None:
    f = pose_frame(
        left_hip=joint(xy=(0.5, 0.7)),
        left_shoulder=joint(xy=(0.5, 0.5)),
    )
    o1 = measure_torso_frame(f, side="left", width=100, height=100, axis=axis_up())
    o2 = measure_torso_frame(f, side="left", width=100, height=100, axis=axis_up())
    assert o1 == o2


def test_measure_torso_frame_up_xy_pixel_vector_not_normalized() -> None:
    f = pose_frame(
        left_hip=joint(xy=(0.5, 0.7)),
        left_shoulder=joint(xy=(0.7, 0.7)),
    )
    axis = axis_up(up_xy=(0.0, -100.0))
    obs = measure_torso_frame(f, side="left", width=100, height=100, axis=axis)
    assert obs.value == pytest.approx(90.0, abs=1e-9)


def test_measure_torso_frame_tuple_coercion_for_frozen_immutability() -> None:
    a = ProjectionAxis(
        version="v1",
        axis_id="test",
        up_xy=[0.0, -1.0],
        positive_cross_sign=1,
    )
    assert isinstance(a.up_xy, tuple)
    assert a.up_xy == (0.0, -1.0)


def test_measure_torso_frame_rejects_bool_coercion() -> None:
    with pytest.raises(ValueError):
        ProjectionAxis(
            version="v1",
            axis_id="test",
            up_xy=(True, -1.0),
            positive_cross_sign=1,
        )


def test_fixture_loads_and_matches_expected_values() -> None:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "movement" / "posture-v1.json"
    data = json.loads(fixture_path.read_text())
    assert data["version"] == "posture-observation-v1"
    cases = {c["name"]: c for c in data["cases"]}

    c = cases["perpendicular_right"]
    f = pose_frame(
        left_hip=joint(xy=tuple(c["hip"])),
        left_shoulder=joint(xy=tuple(c["shoulder"])),
    )
    obs = measure_torso_frame(
        f,
        side="left",
        width=c["width"],
        height=c["height"],
        axis=ProjectionAxis(**c["axis"]),
    )
    assert obs.value == pytest.approx(c["expected_degrees"], abs=1e-9)

    c = cases["tilted_30_degrees"]
    f = pose_frame(
        left_hip=joint(xy=tuple(c["hip"])),
        left_shoulder=joint(xy=tuple(c["shoulder"])),
    )
    obs = measure_torso_frame(
        f,
        side="left",
        width=c["width"],
        height=c["height"],
        axis=ProjectionAxis(**c["axis"]),
    )
    assert obs.value == pytest.approx(c["expected_degrees"], abs=1e-9)

    c = cases["wrap_179_to_minus_179"]
    obs_plus = _torso_obs(c["plus_degrees"], 0.0)
    obs_minus = _torso_obs(c["minus_degrees"], 1.0)
    summary = summarize_window(
        [obs_plus, obs_minus],
        start_s=c["window_start_s"],
        end_s=c["window_end_s"],
        max_gap_s=c["max_gap_s"],
        circular=c["circular"],
    )
    assert summary.minimum == pytest.approx(c["expected_minimum"], abs=1e-9)
    assert summary.maximum == pytest.approx(c["expected_maximum"], abs=1e-9)
    assert summary.excursion == pytest.approx(c["expected_excursion"], abs=1e-9)
    assert summary.end_change == pytest.approx(c["expected_end_change"], abs=1e-9)
