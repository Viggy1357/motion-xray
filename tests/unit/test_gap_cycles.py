from __future__ import annotations

import pytest

from movement.review_cycles import ReviewConfig, find_cycles

# Binary-exact fixtures: step 0.125, dwell 0.125, so dwell comparisons like
# 0.125 - 0.0 >= 0.125 are exact in IEEE754 (no 0.3 - 0.2 < 0.1 artifacts).
H = 0.125
BASE = dict(version="v2", low_degrees=80.0, high_degrees=140.0, dwell_s=0.125, max_gap_s=0.375)
CFG = ReviewConfig(missing_gap_s=0.25, **BASE)


def _head():
    # confirmed high at 0.0, confirmed low at 0.25, return high starts 0.5
    return [(0.0, 150.0), (0.125, 150.0), (0.25, 50.0), (0.375, 50.0), (0.5, 150.0)]


def test_default_missing_gap_zero_is_old_behavior():
    cfg = ReviewConfig(**BASE)
    assert cfg.missing_gap_s == 0.0
    samples = _head() + [(0.625, None), (0.75, 150.0), (0.875, 150.0)]
    result = find_cycles(samples, cfg)
    assert result.cycles == ()
    assert result.partial_spans


def test_completed_cycle_defaults_empty_spans():
    samples = _head() + [(0.625, 150.0)]
    result = find_cycles(samples, CFG)
    assert len(result.cycles) == 1
    assert result.cycle_missing_spans == ((),)


def test_strict_path_has_aligned_empty_metadata_per_cycle():
    cfg = ReviewConfig(**BASE)  # missing_gap_s = 0.0, strict old behavior
    samples = (_head() + [(0.625, 150.0)]
               + [(0.75, 50.0), (0.875, 50.0), (1.0, 150.0), (1.125, 150.0)])
    result = find_cycles(samples, cfg)
    assert len(result.cycles) == 2
    assert result.cycle_missing_spans == ((), ())
    assert len(result.cycle_missing_spans) == len(result.cycles)


def test_short_same_band_gap_bridged_but_not_dwell():
    samples = _head() + [(0.625, None), (0.75, 150.0), (0.875, 150.0)]
    result = find_cycles(samples, CFG)
    assert len(result.cycles) == 1
    c = result.cycles[0]
    assert (c.start_s, c.bottom_s) == (0.0, 0.25)
    # dwell restarted at 0.75 after the gap; 0.5 plateau must not survive
    assert c.end_s == 0.75
    assert result.cycle_missing_spans == (((0.5, 0.75),),)


def test_different_band_gap_rejected():
    samples = _head() + [(0.625, None), (0.75, 100.0), (0.875, 150.0), (1.0, 150.0)]
    result = find_cycles(samples, CFG)
    assert result.cycles == ()
    assert result.partial_spans


def test_overlong_gap_rejected():
    samples = _head() + [(0.625, None), (0.875, 150.0), (1.0, 150.0)]  # 0.375 > 0.25
    result = find_cycles(samples, CFG)
    assert result.cycles == ()
    assert result.partial_spans


def test_turnaround_missing_no_cycle():
    # gap between confirmed high and the low phase: bands differ, no bridge
    samples = [(0.0, 150.0), (0.125, 150.0), (0.25, None), (0.375, 50.0), (0.5, 50.0),
               (0.625, 150.0), (0.75, 150.0)]
    result = find_cycles(samples, CFG)
    assert result.cycles == ()


def test_trailing_gap_partial_honest():
    samples = [(0.0, 150.0), (0.125, 150.0), (0.25, 50.0), (0.375, 50.0), (0.5, None)]
    result = find_cycles(samples, CFG)
    assert result.cycles == ()
    assert result.partial_spans
    assert all(b <= 0.375 for _, b in result.partial_spans)


def test_multiple_consecutive_none_measured_by_endpoints():
    cfg = ReviewConfig(missing_gap_s=0.375, **BASE)
    samples = _head() + [(0.625, None), (0.75, None), (0.875, 150.0), (1.0, 150.0)]
    result = find_cycles(samples, cfg)
    assert len(result.cycles) == 1
    assert result.cycle_missing_spans == (((0.5, 0.875),),)
    assert result.cycles[0].end_s == 0.875


def test_implicit_timestep_jump_still_rejects():
    samples = _head() + [(1.0, 150.0), (1.125, 150.0)]  # 0.5 -> 1.0 > max_gap_s
    result = find_cycles(samples, CFG)
    assert result.cycles == ()


def test_boundary_epsilon_accept_and_reject():
    accept = _head() + [(0.625, None), (0.75, 150.0), (0.875, 150.0)]  # 0.25 gap
    assert len(find_cycles(accept, CFG).cycles) == 1
    reject = _head() + [(0.625, None), (0.875, 150.0), (1.0, 150.0)]  # 0.375 gap
    assert find_cycles(reject, CFG).cycles == ()


def test_invalid_missing_gap_config_rejected():
    for bad in (True, float("nan"), float("inf"), -0.1, 0.5):
        with pytest.raises(ValueError):
            ReviewConfig(missing_gap_s=bad, **BASE)


def test_no_spans_invented_before_initial_high():
    samples = [(0.0, None), (0.125, 150.0), (0.25, 150.0), (0.375, 50.0), (0.5, 50.0),
               (0.625, 150.0), (0.75, 150.0)]
    result = find_cycles(samples, CFG)
    assert len(result.cycles) == 1
    assert result.cycle_missing_spans == ((),)


def test_gaps_around_unconfirmed_initial_high_no_invented_anchors():
    # None arrives while the initial HIGH dwell is still unconfirmed: the
    # attempt resets; no anchors or spans are invented across the gap.
    samples = [(0.0, 150.0), (0.125, None), (0.25, 150.0), (0.375, 150.0),
               (0.5, 50.0), (0.625, 50.0), (0.75, 150.0), (0.875, 150.0)]
    result = find_cycles(samples, CFG)
    assert len(result.cycles) == 1
    c = result.cycles[0]
    assert c.start_s == 0.25  # re-anchored after the reset, never 0.0
    assert (c.start_s, c.bottom_s, c.end_s) == (0.25, 0.5, 0.75)
    assert result.cycle_missing_spans == ((),)


def test_same_band_low_gap_bridged_but_not_counted_toward_dwell():
    # Gap inside the LOW plateau: bridged (same band), but the low dwell
    # restarts at the resume sample, so bottom_s is the restart, not 0.25.
    samples = [(0.0, 150.0), (0.125, 150.0),
               (0.25, 50.0), (0.375, None), (0.5, 50.0), (0.625, 50.0),
               (0.75, 150.0), (0.875, 150.0)]
    result = find_cycles(samples, CFG)
    assert len(result.cycles) == 1
    c = result.cycles[0]
    assert c.bottom_s == 0.5  # not 0.25: missing time never counts as dwell
    assert result.cycle_missing_spans == (((0.25, 0.5),),)


def test_no_cross_cycle_span_leak():
    samples = (_head() + [(0.625, None), (0.75, 150.0), (0.875, 150.0)]
               + [(1.0, 50.0), (1.125, 50.0), (1.25, 150.0), (1.375, 150.0)])
    result = find_cycles(samples, CFG)
    assert len(result.cycles) == 2
    assert result.cycle_missing_spans == (((0.5, 0.75),), ())
    assert result.cycles[1].start_s == result.cycles[0].end_s


def test_metadata_spans_stay_within_cycle_bounds():
    samples = (_head() + [(0.625, None), (0.75, 150.0), (0.875, 150.0)]
               + [(1.0, 50.0), (1.125, 50.0), (1.25, 150.0), (1.375, 150.0)])
    result = find_cycles(samples, CFG)
    assert len(result.cycles) == len(result.cycle_missing_spans)
    for c, spans in zip(result.cycles, result.cycle_missing_spans):
        for a, b in spans:
            assert c.start_s <= a < b <= c.end_s


def test_sequence_input_not_mutated():
    samples = _head() + [(0.625, None), (0.75, 150.0), (0.875, 150.0)]
    snapshot = list(samples)
    find_cycles(samples, CFG)
    assert samples == snapshot
    as_tuple = tuple(samples)
    assert find_cycles(as_tuple, CFG) == find_cycles(samples, CFG)


def test_deterministic_repeat():
    samples = _head() + [(0.625, None), (0.75, 150.0), (0.875, 150.0)]
    assert find_cycles(samples, CFG) == find_cycles(samples, CFG)


def test_all_cycle_anchors_are_observed_samples():
    samples = _head() + [(0.625, None), (0.75, 150.0), (0.875, 150.0)]
    result = find_cycles(samples, CFG)
    observed = {t for t, a in samples if a is not None}
    for c in result.cycles:
        assert c.start_s in observed
        assert c.bottom_s in observed
        assert c.end_s in observed
        assert c.start_s < c.bottom_s < c.end_s
