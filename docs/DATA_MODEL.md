# DATA MODEL

**T02.1 implementation note:** contracts import successfully and reject non-finite
values, missing metrics without reasons, invalid rep intervals and out-of-range scores.
Contracts package and versioned pose/report payloads are now `0.2.0`. Generated JSON
schemas, actual OpenAPI and frontend types are checked in. Structured coaching and
reference-provenance extensions remain T06/T09 work; the dated audit records the old baseline.

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

## Planned contract work from T19 (not current fields)

The schema stays at `0.2.0` until implementation and consumer migration land together.
Do not hand-edit checked-in schemas or frontend types to represent these plans.

| Owner | Required typed data / invariant |
| --- | --- |
| T04/T05 | Artifact reader resolves manifest to immutable observations; signal context carries timestamps, quality masks, side, dimensionality and exercise/config versions. Keep raw and processed values distinct. |
| T04 | Track ID identifies an associated subject, not a recovered measurement. Current matched observations populate joints; stale/predicted positions do not become valid anatomy. |
| T06 | Reference authority/experimental status, immutable input/artifact hashes, selected rep IDs, mapping/normalization versions, applicable rights and reviewer provenance. |
| T06/T07 | Compatibility result with machine-readable refusal reasons; typed alignment input/result with feature order/scales, path/index-time mapping, phase anchors, cost definition and backend/config versions. |
| T07/T11.2 | Per-rep/set score breakdowns and alignment artifact references in the report, with eligibility/null reasons propagated through API and UI. |

Current `ReferenceProfile` approval/source fields and `AnalysisResult.provenance` do not
fully encode these requirements. Current `Any` alignment signatures are scaffold shapes,
not approved long-term public contracts. Existing `VideoAsset` dimensions support
aspect-correct 2D geometry; normalized XY alone is not a Euclidean measurement plane.

## Shared enum definitions

Defined in `enums.py`, all `(str, Enum)` so they serialise to their string value:
`CompletionStatus`, `ReferenceType`, `JobState`, `JobStage`, `CoachingStatus`.

See `docs/API.md` for how these models are exposed over the `/v1` surface and
`docs/SCORING.md` for how `Metric`, `ReferenceProfile`, and `ScoreBreakdown` combine.
