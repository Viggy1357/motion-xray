"""The checked-in API contract must match the route models."""

import json
from pathlib import Path

from app.main import app
from contracts.schema_export import export_json_schema


def test_openapi_snapshot_matches_route_models():
    stored = Path(__file__).resolve().parents[2] / "packages/contracts/openapi.json"
    assert json.loads(stored.read_text()) == app.openapi()


def test_json_schema_snapshots_match_public_models():
    folder = Path(__file__).resolve().parents[2] / "packages/contracts/schemas"
    generated = export_json_schema()
    assert {p.stem for p in folder.glob("*.json")} == set(generated)
    for name, schema in generated.items():
        assert json.loads((folder / f"{name}.json").read_text()) == schema
