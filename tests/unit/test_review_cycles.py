from __future__ import annotations

import math
from dataclasses import astuple

import pytest

from movement.review_cycles import ReviewConfig, CandidateResult, find_cycles


GOOD_CONFIG = ReviewConfig(version="v1", low_degrees=80.0, high_degrees=140.0, dwell_s=0.1, max_gap_s=0.15)


def test_config_requires_nonempty_version():
    with pytest.raises(ValueError):
        ReviewConfig(version="", low_degrees=80.0, high_degrees=140.0, dwell_s=0.1, max_gap_s=0.15)


def test_config_rejects_reversed_bounds():
    with pytest.raises(ValueError):
        ReviewConfig(version="v1", low_degrees=140.0, high_degrees=80.0, dwell_s=0.1, max_gap_s=0.15)


def test_config_rejects_equal_bounds():
    with pytest.raises(ValueError):
        ReviewConfig(version="v1", low_degrees=80.0, high_degrees=80.0, dwell_s=0.1, max_gap_s=0.15)


def test_config_rejects_nonfinite_and_out_of_range():
    bad = [
        (math.nan, 140.0),
        (math.inf, 140.0),
        (-math.inf, 140.0),
        (80.0, math.nan),
        (80.0, math.inf),
        (80.0, 181.0),
        (-0.1, 140.0),
    ]
    for low, high in bad:
        with pytest.raises(ValueError):
            ReviewConfig(version="v1", low_degrees=low, high_degrees=high, dwell_s=0.1, max_gap_s=0.15)


def test_config_rejects_nonpositive_dwell_or_gap():
    with pytest.raises(ValueError):
        ReviewConfig(version="v1", low_degrees=80.0, high_degrees=140.0, dwell_s=0.0, max_gap_s=0.15)
    with pytest.raises(ValueError):
        ReviewConfig(version="v1", low_degrees=80.0, high_degrees=140.0, dwell_s=0.1, max_gap_s=-0.1)
    with pytest.raises(ValueError):
        ReviewConfig(version="v1", low_degrees=80.0, high_degrees=140.0, dwell_s=math.inf, max_gap_s=0.15)


def test_static_high_angle_yields_zero_cycles():
    samples = [(0.0, 150.0), (0.1, 150.0), (0.2, 150.0), (0.3, 150.0)]
    result = find_cycles(samples, GOOD_CONFIG)
    assert result.status == "experimental"
    assert result.cycles == ()
    assert result.reason is None


def test_static_low_angle_yields_zero_cycles():
    samples = [(0.0, 50.0), (0.1, 50.0), (0.2, 50.0), (0.3, 50.0)]
    result = find_cycles(samples, GOOD_CONFIG)
    assert result.cycles == ()


def test_two_complete_cycles_exactly_two():
    cfg = ReviewConfig(version="v1", low_degrees=80.0, high_degrees=140.0, dwell_s=0.25, max_gap_s=0.5)
    # high 0.0-0.25, low 0.5-0.75, high 1.0-1.25 -> first cycle start=0.0 bottom=0.5 end=1.0
    # then high 1.0-1.25, low 1.5-1.75, high 2.0-2.25 -> second cycle start=1.0 bottom=1.5 end=2.0
    samples = [
        (0.00, 150.0), (0.25, 150.0),
        (0.50, 50.0), (0.75, 50.0),
        (1.00, 150.0), (1.25, 150.0),
        (1.50, 50.0), (1.75, 50.0),
        (2.00, 150.0), (2.25, 150.0),
    ]
    result = find_cycles(samples, cfg)
    assert len(result.cycles) == 2
    assert astuple(result.cycles[0]) == (0.0, 0.5, 1.0)
    assert astuple(result.cycles[1]) == (1.0, 1.5, 2.0)


def test_partial_head_before_first_high_retained():
    cfg = ReviewConfig(version="v1", low_degrees=80.0, high_degrees=140.0, dwell_s=0.25, max_gap_s=0.5)
    samples = [
        (0.0, 50.0), (0.25, 50.0),
        (0.5, 150.0), (0.75, 150.0),
        (1.0, 50.0), (1.25, 50.0),
    ]
    result = find_cycles(samples, cfg)
    assert result.cycles == ()
    assert result.partial_spans
    # partial span should cover the open high attempt that never completed
    for a, b in result.partial_spans:
        assert 0.0 <= a < b <= 1.25


def test_trailing_open_high_retained_as_partial():
    cfg = ReviewConfig(version="v1", low_degrees=80.0, high_degrees=140.0, dwell_s=0.25, max_gap_s=0.5)
    samples = [
        (0.0, 150.0), (0.25, 150.0),
        (0.5, 50.0), (0.75, 50.0),
        (1.0, 150.0),
    ]
    result = find_cycles(samples, cfg)
    assert result.cycles == ()
    assert result.partial_spans
    for a, b in result.partial_spans:
        assert 0.0 <= a < b <= 1.0


def test_timestamp_gap_resets_active_cycle():
    cfg = ReviewConfig(version="v1", low_degrees=80.0, high_degrees=140.0, dwell_s=0.25, max_gap_s=0.5)
    # high plateau, gap > max_gap, then low-high cannot bridge
    samples = [
        (0.0, 150.0), (0.25, 150.0),
        (1.0, 50.0), (1.25, 50.0),
        (1.5, 150.0), (1.75, 150.0),
    ]
    result = find_cycles(samples, cfg)
    assert result.cycles == ()
    assert result.partial_spans


def test_none_angle_gap_resets_active_cycle():
    cfg = ReviewConfig(version="v1", low_degrees=80.0, high_degrees=140.0, dwell_s=0.25, max_gap_s=0.5)
    samples = [
        (0.0, 150.0), (0.25, 150.0),
        (0.5, None), (0.75, 50.0), (1.0, 50.0),
        (1.25, 150.0), (1.5, 150.0),
    ]
    result = find_cycles(samples, cfg)
    assert result.cycles == ()
    assert result.partial_spans


def test_non_qualifying_intermediate_resets_dwell_not_phase():
    cfg = ReviewConfig(version="v1", low_degrees=80.0, high_degrees=140.0, dwell_s=0.25, max_gap_s=0.5)
    # high 0.0-0.25, brief dip at 0.5 (not low), back high 0.75-1.0 -> high dwell should reset
    samples = [
        (0.0, 150.0), (0.25, 150.0),
        (0.5, 100.0),
        (0.75, 150.0), (1.0, 150.0),
        (1.25, 50.0), (1.5, 50.0),
        (1.75, 150.0), (2.0, 150.0),
    ]
    result = find_cycles(samples, cfg)
    # Confirmed initial high remains anchored at0.0 across intermediate angles.
    assert len(result.cycles) == 1
    assert astuple(result.cycles[0]) == (0.0, 1.25, 1.75)


def test_dwell_measured_by_timestamp_duration_not_index():
    cfg = ReviewConfig(version="v1", low_degrees=80.0, high_degrees=140.0, dwell_s=0.25, max_gap_s=0.5)
    # same number of samples as two_complete_cycles but stretched -> only one cycle completes
    samples = [
        (0.0, 150.0), (0.1, 150.0),
        (0.2, 50.0), (0.3, 50.0),
        (0.4, 150.0), (0.5, 150.0),
        (0.6, 50.0), (0.7, 50.0),
        (0.8, 150.0),
    ]
    result = find_cycles(samples, cfg)
    assert result.cycles == ()


def test_jitter_around_threshold_does_not_inflate_counts():
    cfg = ReviewConfig(version="v1", low_degrees=80.0, high_degrees=140.0, dwell_s=0.25, max_gap_s=0.5)
    # alternate just above/below high threshold rapidly
    samples = [
        (0.0, 141.0), (0.1, 139.0), (0.2, 141.0), (0.3, 139.0),
        (0.4, 141.0), (0.5, 139.0), (0.6, 141.0), (0.7, 139.0),
    ]
    result = find_cycles(samples, cfg)
    assert result.cycles == ()


def test_rejects_non_strictly_increasing_timestamps():
    samples = [(0.0, 150.0), (0.0, 150.0), (0.1, 50.0)]
    with pytest.raises(ValueError):
        find_cycles(samples, GOOD_CONFIG)


def test_rejects_negative_timestamp():
    samples = [(-0.1, 150.0), (0.0, 50.0)]
    with pytest.raises(ValueError):
        find_cycles(samples, GOOD_CONFIG)


def test_rejects_invalid_angle_values():
    bad_samples = [
        [(0.0, 150.0), (0.1, math.nan)],
        [(0.0, 150.0), (0.1, math.inf)],
        [(0.0, 150.0), (0.1, -1.0)],
        [(0.0, 150.0), (0.1, 181.0)],
        [(0.0, 150.0), (0.1, True)],  # bool is rejected explicitly
    ]
    for samples in bad_samples:
        with pytest.raises(ValueError):
            find_cycles(samples, GOOD_CONFIG)


def test_cycles_are_ordered_in_time():
    cfg = ReviewConfig(version="v1", low_degrees=80.0, high_degrees=140.0, dwell_s=0.25, max_gap_s=0.5)
    samples = [
        (0.0, 150.0), (0.25, 150.0),
        (0.5, 50.0), (0.75, 50.0),
        (1.0, 150.0), (1.25, 150.0),
        (1.5, 50.0), (1.75, 50.0),
        (2.0, 150.0), (2.25, 150.0),
    ]
    result = find_cycles(samples, cfg)
    starts = [c.start_s for c in result.cycles]
    assert starts == sorted(starts)
    assert all(c.start_s < c.bottom_s < c.end_s for c in result.cycles)


def test_candidate_result_defaults():
    result = CandidateResult(cycles=(), partial_spans=())
    assert result.status == "experimental"
    assert result.reason is None


def test_ramp_with_intermediates_and_brief_unconfirmed_return():
    """Regression for real ramp 145->130->100->70 with intermediate angles.

    Config: low=80, high=140, dwell=0.25, gap=0.5, tstep=0.25.
    Sequence:
      0.00 high 150
      0.25 high 150   -> initial high confirmed (0.25 - 0.00 >= 0.25)
      0.50 mid  120   -> intermediate, low dwell resets but first high survives
      0.75 mid  100   -> still intermediate
      1.00 low  70    -> low anchor
      1.25 low  70    -> low confirmed (1.25 - 1.00 >= 0.25)
      1.50 mid  100   -> intermediate, return dwell resets but cycle survives
      1.75 mid  120   -> still intermediate
      2.00 high 150   -> return anchor
      2.25 mid  120   -> return dwell not confirmed, resets
    => 0 cycles.
    Adding 2.50 high 150, 2.75 high 150 confirms the return and yields exactly
    1 cycle without losing the already-confirmed first high/low pair.
    """
    cfg = ReviewConfig(version="v1", low_degrees=80.0, high_degrees=140.0, dwell_s=0.25, max_gap_s=0.5)
    base = [
        (0.00, 150.0), (0.25, 150.0),
        (0.50, 120.0), (0.75, 100.0),
        (1.00, 70.0), (1.25, 70.0),
        (1.50, 100.0), (1.75, 120.0),
        (2.00, 150.0), (2.25, 120.0),
    ]
    result = find_cycles(base, cfg)
    assert result.cycles == ()
    # The confirmed first high/low pair should survive, so adding a confirmed
    # return high produces one cycle anchored at the original first high.
    extended = base + [(2.50, 150.0), (2.75, 150.0)]
    result2 = find_cycles(extended, cfg)
    assert len(result2.cycles) == 1
    assert astuple(result2.cycles[0]) == (0.0, 1.0, 2.5)
