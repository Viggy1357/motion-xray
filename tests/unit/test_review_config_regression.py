"""Frozen local-review assumptions, not technique-approved calibration."""

import json
from pathlib import Path

from movement.review_cycles import ReviewConfig, find_cycles


def test_lat_reference_v1_frozen_ramp_and_gap() -> None:
    path = Path(__file__).parents[2] / "data/review_configs/lat-reference-v1.json"
    data = json.loads(path.read_text())
    assert data["version"] == "lat-reference-review-v1"
    assert data["authoritative"] is False
    config = ReviewConfig(**{k: data[k] for k in (
        "version", "low_degrees", "high_degrees", "dwell_s", "max_gap_s",
    )})
    assert (config.low_degrees, config.high_degrees, config.dwell_s, config.max_gap_s) == (100, 135, 0.1, 0.1)
    angles = [150]*4 + [120]*2 + [90]*4 + [120]*2 + [150]*4
    samples = [(i*0.04, a) for i, a in enumerate(angles)]
    result = find_cycles(samples, config)
    assert len(result.cycles) == 1
    cycle = result.cycles[0]
    assert (cycle.start_s, cycle.bottom_s, cycle.end_s) == (0, 0.24, 0.48)
    assert result.status == "experimental"
    samples[7] = (samples[7][0], None)
    assert find_cycles(samples, config).cycles == ()


def test_confirmed_start_survives_sustained_high_and_partial_head() -> None:
    config = ReviewConfig("fixture-v1", 80, 140, 0.25, 0.5)
    samples = [(0, 90), (0.25, 150), (0.5, 150), (0.75, 150),
               (1, 150), (1.25, 100), (1.5, 70), (1.75, 70),
               (2, 100), (2.25, 150), (2.5, 150), (2.75, 150)]
    result = find_cycles(samples, config)
    assert len(result.cycles) == 1
    assert result.cycles[0].start_s == 0.25
    assert result.partial_spans[0] == (0, 0.25)
    assert all(start >= 2.25 for start, _ in result.partial_spans[1:])
