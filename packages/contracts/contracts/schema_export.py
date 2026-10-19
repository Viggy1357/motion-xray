"""Export JSON Schema for every public contract model.

These schemas are generated, not committed (see context: downstream code
generates TypeScript types / validates payloads from them). Run as::

    python -m contracts.schema_export [out_dir]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Type

from pydantic import BaseModel

from .analysis import AnalysisResult, CoachingResult, Metric, Rep
from .jobs import AnalysisJob
from .media import VideoAsset
from .pose import JointObservation, PoseFrame, PoseSequence
from .reference import ReferenceProfile, SourceRecord
from .scoring import ScoreBreakdown

#: All models whose JSON Schema we publish, keyed by their class name.
_MODELS: tuple[Type[BaseModel], ...] = (
    VideoAsset,
    JointObservation,
    PoseFrame,
    PoseSequence,
    Rep,
    Metric,
    CoachingResult,
    AnalysisResult,
    ReferenceProfile,
    SourceRecord,
    ScoreBreakdown,
    AnalysisJob,
)


def export_json_schema() -> dict[str, dict]:
    """Return a mapping of model name -> its JSON Schema dict."""

    return {model.__name__: model.model_json_schema() for model in _MODELS}


def write_schemas(out_dir: str | Path) -> list[Path]:
    """Write one ``<ModelName>.json`` file per model into ``out_dir``.

    Returns the list of written paths. The directory is created if missing.
    """

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, schema in export_json_schema().items():
        target = out_path / f"{name}.json"
        target.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
        written.append(target)
    return written


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: write schemas to ``argv[0]`` (default ``./schemas``)."""

    args = sys.argv[1:] if argv is None else argv
    out_dir = args[0] if args else "schemas"
    written = write_schemas(out_dir)
    for path in written:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
