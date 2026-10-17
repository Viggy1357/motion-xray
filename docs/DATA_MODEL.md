# DATA MODEL

The Pydantic v2 models in `packages/contracts` are the single schema source of truth for
Motion X Ray (AGENTS.md rule 4). TypeScript types and JSON Schemas are generated from
these models (via `python -m contracts.schema_export`), never hand-authored. Any change
to a public contract either preserves it or bumps the schema version and updates every
consumer together. All models derive from a shared `MXRModel` base that forbids extra
fields, rejects NaN/inf floats, and keeps datetimes UTC-aware. A value that could not be
measured is `None` with a machine-readable reason — null means "no value, with a reason",
never a fabricated number (rule 3).

## Models

Source of truth: `packages/contracts/contracts/` (re-exported from the `contracts`
package root).

| Model | Module | Purpose |
| --- | --- | --- |
| `VideoAsset` | `media.py` | An uploaded workout video and its verifiable metadata (hash, dimensions, duration, storage key). |
| `PoseSequence` | `pose.py` | Versioned descriptor/manifest for a pose capture; points at out-of-band per-frame data. |
| `PoseFrame` | `pose.py` | All observed joints at a single video frame, with index and timestamp. |
| `JointObservation` | `pose.py` | One joint at one frame; `valid`/`interpolated` flags instead of a fabricated coordinate. |
| `Rep` | `analysis.py` | A single detected repetition with its phase boundaries in seconds. |
| `Metric` | `analysis.py` | One measured quantity for a rep; `value=None` + `reason` when unmeasurable. |
| `ReferenceProfile` | `reference.py` | A versioned, human-approved comparison target for one exercise/variant/view. |
| `ScoreBreakdown` | `scoring.py` | Per-component inputs and the resulting raw/displayed scores (explainable or null). |
| `AnalysisResult` | `analysis.py` | The complete rep-by-rep report for one analyzed video. |
| `SourceRecord` | `reference.py` | A single reviewable source backing one or more reference profiles. |
| `AnalysisJob` | `jobs.py` | One unit of pipeline work with its state, stage, and lease bookkeeping. |
| `CoachingResult` | `analysis.py` | LLM-generated coaching text, kept separate from deterministic metrics. |

## Shared enums

Defined in `enums.py`, all `(str, Enum)` so they serialise to their string value:
`CompletionStatus`, `ReferenceType`, `JobState`, `JobStage`, `CoachingStatus`.

See `docs/API.md` for how these models are exposed over the `/v1` surface and
`docs/SCORING.md` for how `Metric`, `ReferenceProfile`, and `ScoreBreakdown` combine.
