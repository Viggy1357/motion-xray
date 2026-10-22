# HM01 — API Acceptance Matrix (draft)

Covers normal / partial / invalid / foreign / deleted / expired cases plus generated-type drift. "Owner B" = second anonymous device credential. All mutations require CSRF token; all reads owner-fenced.

## 1. Profile

| Case | Request | Expected |
|---|---|---|
| Normal | GET /v1/profile (first visit) | 200, auto-created profile, default `preferred_load_unit="kg"` |
| Normal | PATCH display_name + unit | 200, persisted across refresh/restart |
| Partial | PATCH `{}` | 200, no-op, unchanged etag/updated_at optional |
| Invalid | PATCH `display_name` 200 chars / bad unit | 422, field errors, nothing written |
| Foreign | Owner B GET/PATCH Owner A profile | 404 (no existence leak) |
| Expired | device credential past lifetime | 401 + clear-browser/no-recovery message; profile data retained server-side |

## 2. Exercises catalogue

| Case | Request | Expected |
|---|---|---|
| Normal | GET /v1/exercises | 200, 4 release entries; incline entry only after HM00 variant freeze |
| Partial | profile unavailable for an exercise | entry present, `reference_status="unavailable"`, `profile_version=null` |
| Invalid | POST/PATCH on catalogue | 405 |

## 3. Analyses (0.2/0.3 dispatch)

| Case | Request | Expected |
|---|---|---|
| Normal pose-only | POST scope omitted | 201, `analysis_scope="pose_only"`, 0.2 result readable |
| Normal report | POST `analysis_scope="prototype_report"` | 201; result validates as 0.3 with quality + prototype_assessment |
| Idempotent | same `request_key` replayed | same `analysis_id`, no duplicate job/charge |
| Partial | report with missing components | 200, `status="partial"`, omitted components named, `estimated_match` only for declared subset |
| Invalid | bad video_id pattern / unknown exercise / scope string | 422 |
| Foreign | Owner B GET status/result/artifacts of A | 404; `lease_owner`/`result_key` always null in payload |
| Deleted | GET after owner delete | 410/404, artifacts unreachable, log rows untouched |
| Expired | result after 7d report retention | 410 `report_expired`; linked WorkoutSet still readable |
| Old format | read stored 0.2.0 result | 200 via v02 reader; strict pose validator unmodified; no score fabricated |
| Unsupported | `schema_version="9.9"` fixture | 501/422 `UnsupportedSchemaVersion`, never coerced |

## 4. Coaching retry

| Case | Request | Expected |
|---|---|---|
| Normal | POST retry after completed report | 200, cached or single bounded live call |
| Partial | provider outage | 200 report + `coaching.status="unavailable"`, no canned text passed off as live |
| Invalid | retry on pose_only/failed analysis | 409 |
| Foreign | Owner B retry A's analysis | 404 |
| Quota | over per-session cap | 429, no new bill |

## 5. Workouts & sets

| Case | Request | Expected |
|---|---|---|
| Normal | POST workout, POST set with `analysis_id` | 201; `count_source="detected"`, detected count copied, logged count null |
| Normal manual | POST set without analysis | 201, `count_source="manual"`, `detected_rep_count=null` |
| Correction | PATCH `logged_rep_count`, load, notes | 200; `detected_rep_count` and measured timeline unchanged; no score/quality change |
| Load semantics | `load_value` without unit/basis; bodyweight with value | 422 |
| Partial | PATCH subset of fields | 200, others unchanged |
| Invalid | negative reps, notes >2000, `analysis_id` of other owner | 422/404 |
| Foreign | Owner B GET/PATCH/DELETE A's workout or set | 404 |
| Deleted | GET deleted workout/set | 410/404; analysis artifacts unaffected |
| Expired | set whose video expired | 200 set; video replay endpoint 410 `video_expired` |
| Idempotent | replay POST with same `request_key` | same id, no duplicate set |
| Pagination | `limit=500` | clamped to 100 + cursor |

## 6. Routines & dashboard

| Case | Request | Expected |
|---|---|---|
| Normal | GET /v1/routines | built-ins (upper/lower/full) + owner customs |
| Foreign | Owner B sees A's custom template | never; built-ins only |
| Normal | GET /v1/dashboard | counts derived from durable log only |
| Expired | dashboard after all videos expired | 200, identical counts (log survives retention) |
| Empty | new owner | 200 zeros + empty lists, no fake streak/sample data |

## 7. Generated-type drift

| Check | Command-level expectation |
|---|---|
| OpenAPI drift | regenerate `apps/api/openapi.json`; diff empty in CI |
| TS drift | regenerate `apps/web/src/api/types.ts`; `tsc --noEmit` passes; diff empty |
| JSON schema drift | regenerate `packages/contracts/schema/*`; diff empty |
| Round-trip | 0.3 fixture → model → JSON → model equality; 0.2 fixtures pass unmodified |
| Cross-side | frontend client compiled against frozen 0.3 types; backend rejects unknown enum values (422) |

## 8. Freeze gate

Integrator must resolve before HM02/03/04/06/08/09 start: (1) A1 — `/v1/dashboard` vs bounded summary on `/v1/workouts` (pick one); (2) incline-press variant ID from HM00 intake (no invented value); (3) confirm `ExerciseId` literal update. Until then all routes/models above are proposals.
