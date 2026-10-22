import math

import pytest

from scoring.review_comparison import compare_review_cycles


def _constant_samples(times, elbow=90.0, upper=100.0):
    return [(t, elbow, upper) for t in times]


def test_identical_constant_curves_score_100():
    times = [0.0, 1.0, 2.0, 3.0, 4.0]
    user = _constant_samples(times)
    ref = _constant_samples(times)
    result = compare_review_cycles(
        user, (0.0, 2.0, 4.0),
        ref, (0.0, 2.0, 4.0),
        max_gap_s=2.0,
        points_per_phase=5,
    )
    assert result["status"] == "experimental"
    assert result["experimental_agreement_score"] == 100.0
    assert result["mean_mae_degrees"] == 0.0
    assert result["grid_point_count"] == 9
    # time_pairs length = 2*points_per_phase - 1
    assert len(result["user_time_pairs"]) == 9


def test_different_angles_expected_mae_and_score():
    # elbow diff 20, upper diff 40 => MAE 30 => score 100*(1-30/180)=83.333...
    user = _constant_samples([0.0, 1.0, 2.0, 3.0, 4.0], elbow=90.0, upper=100.0)
    ref = _constant_samples([0.0, 1.0, 2.0, 3.0, 4.0], elbow=110.0, upper=140.0)
    result = compare_review_cycles(
        user, (0.0, 2.0, 4.0),
        ref, (0.0, 2.0, 4.0),
        max_gap_s=1.0,
        points_per_phase=5,
    )
    assert result["elbow_mae_degrees"] == 20.0
    assert result["upper_arm_torso_mae_degrees"] == 40.0
    assert result["mean_mae_degrees"] == 30.0
    assert math.isclose(result["experimental_agreement_score"], 83.33333333333333, rel_tol=1e-12)


def test_different_phase_durations_same_angles_score_100():
    user_times = [0.0, 0.5, 1.0, 1.5, 2.0]
    ref_times = [0.0, 2.0, 4.0]
    user = _constant_samples(user_times)
    ref = _constant_samples(ref_times)
    result = compare_review_cycles(
        user, (0.0, 1.0, 2.0),
        ref, (0.0, 2.0, 4.0),
        max_gap_s=2.0,
        points_per_phase=5,
    )
    assert result["status"] == "experimental"
    assert result["experimental_agreement_score"] == 100.0
    assert result["user_pull_duration_s"] == 1.0
    assert result["user_return_duration_s"] == 1.0
    assert result["reference_pull_duration_s"] == 2.0
    assert result["reference_return_duration_s"] == 2.0


def test_exact_source_endpoint_no_interpolation():
    user = [(0.0, 80.0, 70.0), (2.0, 80.0, 70.0), (4.0, 80.0, 70.0)]
    ref = [(0.0, 80.0, 70.0), (2.0, 80.0, 70.0), (4.0, 80.0, 70.0)]
    result = compare_review_cycles(
        user, (0.0, 2.0, 4.0),
        ref, (0.0, 2.0, 4.0),
        max_gap_s=2.0,
        points_per_phase=2,
    )
    assert result["status"] == "experimental"
    assert result["experimental_agreement_score"] == 100.0
    assert result["grid_point_count"] == 3


def test_none_hole_causes_unavailable():
    user = [(0.0, 80.0, 70.0), (1.0, None, 70.0), (2.0, 80.0, 70.0), (3.0, 80.0, 70.0), (4.0, 80.0, 70.0)]
    ref = _constant_samples([0.0, 1.0, 2.0, 3.0, 4.0])
    result = compare_review_cycles(
        user, (0.0, 2.0, 4.0),
        ref, (0.0, 2.0, 4.0),
        max_gap_s=1.0,
        points_per_phase=5,
    )
    assert result["status"] == "unavailable"
    assert result["experimental_agreement_score"] is None
    assert result["authoritative"] is False
    assert result["valid_technique_score"] is None
    assert result["reason"] == "insufficient_observations"


def test_long_gap_unavailable():
    user = [(0.0, 80.0, 70.0), (2.0, 80.0, 70.0), (4.0, 80.0, 70.0)]
    ref = _constant_samples([0.0, 1.0, 2.0, 3.0, 4.0])
    result = compare_review_cycles(
        user, (0.0, 2.0, 4.0),
        ref, (0.0, 2.0, 4.0),
        max_gap_s=0.5,
        points_per_phase=5,
    )
    assert result["status"] == "unavailable"
    assert result["reason"] == "insufficient_observations"


def test_out_of_range_cycle_raises():
    user = _constant_samples([0.0, 1.0, 2.0])
    ref = _constant_samples([0.0, 1.0, 2.0])
    with pytest.raises(ValueError):
        compare_review_cycles(
            user, (2.0, 1.0, 0.0),
            ref, (0.0, 1.0, 2.0),
            max_gap_s=1.0,
        )


def test_non_finite_timestamp_raises():
    user = [(float("nan"), 80.0, 70.0), (1.0, 80.0, 70.0), (2.0, 80.0, 70.0)]
    ref = _constant_samples([0.0, 1.0, 2.0])
    with pytest.raises(ValueError):
        compare_review_cycles(
            user, (0.0, 1.0, 2.0),
            ref, (0.0, 1.0, 2.0),
            max_gap_s=1.0,
        )


def test_angle_out_of_range_raises():
    user = [(0.0, 80.0, 70.0), (1.0, 181.0, 70.0), (2.0, 80.0, 70.0)]
    ref = _constant_samples([0.0, 1.0, 2.0])
    with pytest.raises(ValueError):
        compare_review_cycles(
            user, (0.0, 1.0, 2.0),
            ref, (0.0, 1.0, 2.0),
            max_gap_s=1.0,
        )


def test_invalid_points_per_phase_raises():
    user = _constant_samples([0.0, 1.0, 2.0])
    ref = _constant_samples([0.0, 1.0, 2.0])
    with pytest.raises(ValueError):
        compare_review_cycles(
            user, (0.0, 1.0, 2.0),
            ref, (0.0, 1.0, 2.0),
            max_gap_s=1.0,
            points_per_phase=1,
        )


def test_invalid_max_gap_raises():
    user = _constant_samples([0.0, 1.0, 2.0])
    ref = _constant_samples([0.0, 1.0, 2.0])
    with pytest.raises(ValueError):
        compare_review_cycles(
            user, (0.0, 1.0, 2.0),
            ref, (0.0, 1.0, 2.0),
            max_gap_s=0.0,
        )


def test_linear_interpolation_used_when_bounding_values_present():
    user = [(0.0, 0.0, 0.0), (2.0, 20.0, 40.0), (4.0, 40.0, 80.0)]
    ref = [(0.0, 0.0, 0.0), (2.0, 20.0, 40.0), (4.0, 40.0, 80.0)]
    result = compare_review_cycles(
        user, (0.0, 2.0, 4.0),
        ref, (0.0, 2.0, 4.0),
        max_gap_s=3.0,
        points_per_phase=3,
    )
    assert result["status"] == "experimental"
    assert result["elbow_mae_degrees"] == 0.0
    assert result["upper_arm_torso_mae_degrees"] == 0.0
    assert result["experimental_agreement_score"] == 100.0


def test_metadata_fields_present():
    user = _constant_samples([0.0, 1.0, 2.0, 3.0, 4.0])
    ref = _constant_samples([0.0, 1.0, 2.0, 3.0, 4.0])
    result = compare_review_cycles(
        user, (0.0, 2.0, 4.0),
        ref, (0.0, 2.0, 4.0),
        max_gap_s=1.0,
        points_per_phase=5,
    )
    assert result["algorithm_version"] == "lat-review-angle-agreement-v1"
    assert result["authoritative"] is False
    assert result["valid_technique_score"] is None
    assert result["score_label"] == "Unvalidated angle-pattern agreement; not technique correctness"
    assert result["normalization_degrees"] == 180
    assert result["per_feature_weights"] == {"elbow": 0.5, "upper_arm_torso": 0.5}


def test_none_at_non_grid_time_still_unavailable():
    # A hole at a time that is not exactly on the grid still makes the
    # resampled grid point unavailable because interpolation hits a None.
    user = [
        (0.0, 80.0, 70.0),
        (0.9, 80.0, None),
        (2.0, 80.0, 70.0),
        (3.0, 80.0, 70.0),
        (4.0, 80.0, 70.0),
    ]
    ref = _constant_samples([0.0, 1.0, 2.0, 3.0, 4.0])
    result = compare_review_cycles(
        user, (0.0, 2.0, 4.0),
        ref, (0.0, 2.0, 4.0),
        max_gap_s=1.0,
        points_per_phase=5,
    )
    assert result["status"] == "unavailable"
    assert result["reason"] == "insufficient_observations"


def test_long_gap_between_observations_makes_grid_unavailable():
    # max_gap_s is small; even if a grid point lands inside the gap, the
    # bracketing sample interval exceeds max_gap_s.
    user = [(0.0, 80.0, 70.0), (3.0, 80.0, 70.0), (4.0, 80.0, 70.0)]
    ref = _constant_samples([0.0, 1.0, 2.0, 3.0, 4.0])
    result = compare_review_cycles(
        user, (0.0, 2.0, 4.0),
        ref, (0.0, 2.0, 4.0),
        max_gap_s=0.5,
        points_per_phase=5,
    )
    assert result["status"] == "unavailable"
    assert result["reason"] == "insufficient_observations"


def test_time_pairs_correspond_to_matched_normalized_phase_points():
    # Different absolute durations but same normalized phase grids should
    # produce paired (user_time, reference_time) points.
    user = _constant_samples([0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5])
    ref = _constant_samples([0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0])
    result = compare_review_cycles(
        user, (0.0, 0.75, 1.5),
        ref, (0.0, 6.0, 12.0),
        max_gap_s=2.0,
        points_per_phase=5,
    )
    assert result["status"] == "experimental"
    pairs = result["user_time_pairs"]
    assert len(pairs) == 9
    # first pair: start of phase 1
    assert pairs[0] == (0.0, 0.0)
    # last pair: end of phase 2
    assert pairs[-1] == (1.5, 12.0)
    # bottom appears once
    assert (0.75, 6.0) in pairs
    # the previous wrong zip(user_phase1, user_phase2) would have paired starts
    # of the two phases; ensure we never see (0.0, 0.75) or (0.0, 6.0).
    assert (0.0, 0.75) not in pairs
    assert (0.0, 6.0) not in pairs


def test_exact_boundaries_used_despite_floating_point_grid():
    # Use an irrational-looking duration so the grid step is not exact.
    user = [(0.0, 80.0, 70.0), (1.0, 80.0, 70.0), (2.0, 80.0, 70.0)]
    ref = [(0.0, 80.0, 70.0), (1.0, 80.0, 70.0), (2.0, 80.0, 70.0)]
    result = compare_review_cycles(
        user, (0.0, 1.0, 2.0),
        ref, (0.0, 1.0, 2.0),
        max_gap_s=1.0,
        points_per_phase=3,
    )
    assert result["status"] == "experimental"
    assert result["grid_point_count"] == 5
    # With exact boundary enforcement, the middle grid point of phase 1 is
    # exactly 0.5 and should interpolate successfully.
    assert result["experimental_agreement_score"] == 100.0
