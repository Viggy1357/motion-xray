from __future__ import annotations

"""Unit tests over the exercise-spec YAMLs (structure scaffold).

These checks need neither the ML stack nor the LLM/search SDKs, so they are the
natural first occupants of ``tests/unit``. They assert the invariants the
scoring layer relies on: every spec declares the expected shape and its metric
``weights`` map sums to exactly 1.0 (a missing/extra weight would silently
skew a score, which AGENTS.md rule 2 forbids). The real metric/scoring math is
exercised elsewhere once T05/T07 land; this is structure-only verification.
"""

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

# tests/unit/ -> repo root is two parents up.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPEC_DIR = _REPO_ROOT / "data" / "exercise_specs"

_EXPECTED_SPECS = ("dumbbell_curl.yaml", "lateral_raise.yaml", "squat.yaml")


def _spec_paths() -> list[Path]:
    return [_SPEC_DIR / name for name in _EXPECTED_SPECS]


@pytest.mark.parametrize("spec_path", _spec_paths(), ids=[p.name for p in _spec_paths()])
def test_spec_exists_and_parses(spec_path: Path) -> None:
    """Each expected exercise spec exists and parses as a YAML mapping."""
    assert spec_path.is_file(), f"missing exercise spec: {spec_path}"
    data = yaml.safe_load(spec_path.read_text())
    assert isinstance(data, dict), f"{spec_path.name} is not a YAML mapping"


@pytest.mark.parametrize("spec_path", _spec_paths(), ids=[p.name for p in _spec_paths()])
def test_spec_has_expected_shape(spec_path: Path) -> None:
    """Each spec declares the scaffold's fixed shape and segmentation gate."""
    data = yaml.safe_load(spec_path.read_text())
    assert data["spec_version"] == "0.1.0"
    assert data["required_capabilities"] == ["estimated_3d", "timestamps"]
    assert data["segmentation"] == {"low": 0.2, "high": 0.8, "dwell_s": 0.15}
    assert data["missing_required_metric"] == "null_overall_score"
    assert isinstance(data["weights"], dict) and data["weights"]


@pytest.mark.parametrize("spec_path", _spec_paths(), ids=[p.name for p in _spec_paths()])
def test_spec_weights_sum_to_one(spec_path: Path) -> None:
    """The metric weights for each exercise must sum to exactly 1.0."""
    data = yaml.safe_load(spec_path.read_text())
    total = sum(float(v) for v in data["weights"].values())
    assert abs(total - 1.0) < 1e-9, f"{spec_path.name} weights sum to {total}, not 1.0"
