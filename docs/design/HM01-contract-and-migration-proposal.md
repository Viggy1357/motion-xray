# HM01 — Contract & Data Migration Proposal (draft, pre-freeze)

Status: **proposal**. No source/model/schema files are edited in this batch. Freeze happens only after the integrator resolves the A1 conflict (route naming `/v1/dashboard` vs bounded summary on `/v1/workouts`, and the incline-press variant ID) with HM00 intake. Current artifacts are `0.2.0` pose-only; the strict `PoseJobArtifacts` validator stays untouched.

## 1. Schema versioning & migration

- Integrator correction: keep global `SCHEMA_VERSION="0.2.0"` and existing `AnalysisResult` unchanged. Add a separate `PrototypeAnalysisResult` with literal `"0.3.0"`; do not widen or subclass the old literal discriminator. The following original migration suggestions require this correction before implementation. `AnalysisResult.schema_version` becomes `Literal["0.2.0","0.3.0"]` with a format-dispatched reader:
  - `read_analysis_result(data)`: if `schema_version == "0.2.0"` → validate with the frozen 0.2 model (kept as `contracts/analysis_v02.py`, byte-identical semantics); if `"0.3.0"` → new model; else `UnsupportedSchemaVersion`.
  - 0.2 results are **never rewritten**; they read as pose/metric-only reports with `analysis_scope="pose_only"`, `quality=None`, `prototype_assessment=None`. No backfill of scores.
- The existing strict pose-only validator (`PoseJobArtifacts`) is not relaxed; a 0.3 report is a separate artifact key (`report_key`), never passed through the pose validator.
- Generated artifacts regenerated in one commit: OpenAPI (`packages/contracts/openapi.json`), TS client types (`apps/web/generated/api.d.ts`), JSON schema (`packages/contracts/schemas/`). CI drift check: regenerate → `git diff --exit-code`.

## 2. New/changed contract models (packages/contracts)

### 2.1 Enums (contracts/enums.py, additive)
- `AnalysisScope = Literal["pose_only","prototype_report"]`
- `LoadUnit = Literal["kg","lb"]`; `LoadBasis = Literal["total","per_hand","bodyweight"]`
- `CountSource = Literal["detected","user","manual"]`
- `PrototypeMatchStatus = Literal["matched","partial","unavailable"]`
- `CoachingStatus` unchanged; `ViewReviewStatus = Literal["reviewed","unreviewed","incompatible"]`

### 2.2 Exercise catalogue (new `contracts/catalogue.py`)
`ExerciseInfo { id: ExerciseId, variant: Optional[Variant], display_name: str, supported_views: list[str], capabilities: list[str], profile_version: Optional[str], target_muscles: list[str], reference_status: Literal["available","provisional","unavailable"] }`.
`ExerciseId` gains `"incline_chest_press"` **only after** HM00 confirms implement/bench/view; until then the literal stays pending and this doc invents no variant ID. `lateral_raise` stays out of the release catalogue.

### 2.3 Report 0.3 (contracts/analysis.py, additive subclass)
`AnalysisResultV3(AnalysisResult)` with `schema_version: Literal["0.3.0"]`, plus:
- `analysis_scope: AnalysisScope`
- `detected_rep_count: int >= 0` (measured; distinct from any logged count)
- `quality: Optional[ReportQuality]`
- `prototype_assessment: Optional[PrototypeAssessment]`
- `profile_version: Optional[str]`; `recipe_version: str`

`ReportQuality { expected_supporting_samples: int>=0, valid_observed_samples: int>=0 (<= expected), per_metric_coverage: dict[str, float 0..1], usable_reps: int>=0, total_reps: int>=0, missing_reasons: list[str], view_review: ViewReviewStatus }`. Zero expected samples ⇒ coverage fields omitted + reason; coverage is observation coverage, never a correctness probability.

`PrototypeAssessment { status: PrototypeMatchStatus, policy_version: str, included_components: list[str], omitted_components: list[str], estimated_match: Optional[float 0..100] }`. `estimated_match` is reference-similarity under the versioned prototype policy — **not** coverage and not a form-correctness score. No default score; `status="unavailable"` ⇒ `estimated_match=None` with reason in `omitted_components`/warnings. Existing `score` field stays `None` for 0.3 prototype reports (no silent threshold change, no revival of the old 92 trial).

### 2.4 Personal log (new `contracts/log.py`)
- `PersonalProfile { owner_id: str, display_name: Optional[str<=64], preferred_load_unit: LoadUnit, created_at, updated_at }`
- `WorkoutSet { id, workout_id, owner_id, exercise_id, variant, detected_rep_count: Optional[int], logged_rep_count: Optional[int], count_source: CountSource, load_value: Optional[FiniteFloat>0], load_unit: Optional[LoadUnit], load_basis: Optional[LoadBasis], notes: Optional[str<=2000], analysis_id: Optional[str], performed_at, created_at, updated_at }`
  - Validators: `load_value` requires `load_unit` **and** `load_basis`; `bodyweight` basis forbids `load_value`; `count_source="detected"` requires `analysis_id`; `logged_rep_count` never overwrites `detected_rep_count`.
  - Volume aggregation only when unit+basis known; `per_hand` doubles only at aggregation time with basis recorded; bodyweight without load ⇒ volume unavailable, not zero.
- `Workout { id, owner_id, started_at, name: Optional[str], sets: list[WorkoutSet] (read-side only) }`
- `RoutineTemplate { id, owner_id: Optional[str] (None = built-in), name, exercises: list[RoutineExercise] }`; `RoutineExercise { exercise_id, variant, planned_sets: int>=1, planned_reps: Optional[int] }`

### 2.5 Lifecycle (contracts/lifecycle.py)
- `AnalysisCreateRequest` gains `analysis_scope: AnalysisScope = "pose_only"` (explicit opt-in to prototype report).
- `AnalysisStatus.analysis_scope` widens to `AnalysisScope`; `lease_owner`/`result_key` stay nulled. Internal-only fields (lease, storage keys, reaping records) never appear in public models.

## 3. Routes (all owner-scoped, CSRF on mutations, paginated lists `limit<=100`)

| Method/Route | Request → Response | Notes |
|---|---|---|
| GET /v1/profile | → PersonalProfile | auto-create on first device credential |
| PATCH /v1/profile | partial PersonalProfile → PersonalProfile | only `display_name`,`preferred_load_unit` |
| GET /v1/exercises | → list[ExerciseInfo] | replaces scaffold |
| GET /v1/videos | → page[VideoAsset] | no storage keys exposed (existing rule) |
| POST /v1/analyses | AnalysisCreateRequest → AnalysisStatus | idempotent on `request_key` per owner |
| GET/DELETE /v1/analyses/{id}, GET .../result, .../artifacts | existing | result dispatches 0.2/0.3 by stored schema_version |
| POST /v1/analyses/{id}/coaching/retry | → CoachingResult | owner+CSRF, cache-first, capped; never reruns pose |
| GET/POST /v1/workouts | → page / Workout | POST idempotent via `request_key` |
| GET/PATCH/DELETE /v1/workouts/{id} | | DELETE removes sets, keeps analysis artifacts per retention |
| POST /v1/workouts/{id}/sets | WorkoutSet-in → WorkoutSet | idempotent via `request_key`; `analysis_id` must belong to same owner |
| PATCH/DELETE /v1/workout-sets/{id} | | PATCH cannot change `detected_rep_count`/`analysis_id` |
| GET /v1/routines | → list[RoutineTemplate] | built-ins + owner customs |
| GET /v1/dashboard | → DashboardSummary | **A1 conflict**: vs bounded `?summary=true` on /v1/workouts — integrator picks one, not both |

`DashboardSummary { weekly_sessions, weekly_sets, weekly_reps, recent_workouts: list[WorkoutSummary<=10], muscle_activity: list[{muscle, set_count}] }` — derived from durable log only, never from raw video/report retention.

## 4. Ownership, idempotency, retention

- Same-browser anonymous owner: durable revocable device credential (Secure/HttpOnly/SameSite cookie, ~90d, defined in HM02) + short mutation/CSRF token. No localStorage keys, no cross-device auth, no sign-in. Guest judges use the same anonymous path.
- Idempotency: `(owner_id, request_key)` unique on analyses, workouts, sets; replay returns the original record (200/201 with same id), never duplicates.
- Retention split: raw video/pose 24h and report 7d defaults unchanged; `PersonalProfile`/`Workout`/`WorkoutSet`/`RoutineTemplate` are durable and survive video/report expiry. A saved set remains readable after its video expires (`video_expired` UI state, not deletion).
- Deletion: deleting a workout/set never touches analysis artifacts; deleting a video never deletes log rows. Cancelled/failed reaping still requires supervisor fencing proof — no time-based destructive guess.

## 5. Follow-up implementation files (HM02+)

- `packages/contracts/contracts/{analysis.py,analysis_v02.py,enums.py,lifecycle.py,catalogue.py,log.py,base.py}` + schema regen (`packages/contracts/openapi.json`, `apps/web/generated/api.d.ts`, `packages/contracts/schemas/*.json`).
- Backend: `services/api/app/{profile.py,workouts.py,routines.py,dashboard.py,exercises.py}`, `services/api/app/store/{migrations/0003_log_tables.sql,workouts.py,profile.py}`, session/device credential in `app/session.py`.
- Frontend callers change together with backend in the same PR: `apps/web/src/api/client.ts` (new endpoints), dashboard/new-set/history pages (HM08), results viewer report dispatch (HM09).
- Migration tests: `tests/contracts/test_report_v03_roundtrip.py`, `test_v02_reader_compat.py` (existing 0.2 fixtures must pass unmodified), `tests/api/test_log_routes_owner_isolation.py`, `test_idempotent_create.py`, `test_schema_drift.py`.
- Valid fixture construction: build 0.3 reports via `AnalysisResultV3(**payload)` with real validator-satisfying values (ordered rep boundaries, reason on null metrics, coverage ≤1) — **no `model_construct` bypass, no invented Store methods**.

## 6. Explicit non-goals / honesty guards
No default score, no threshold changes, no claim that reports are already integrated, no cross-device auth, no lateral-raise release entry, no invented incline variant. Reports are **not yet integrated**; this doc only freezes the interface for HM02/03/04/06/08/09.

## Integration gate —22 October

Accepted direction with corrections: use `GET /v1/dashboard`; keep current source paths under `services/api/app`, generated TS at `apps/web/generated/api.d.ts`. Preserve global0.2.0 and old strict pose manifest unchanged; additive standalone0.3 report model and explicit reader only. Do not create a fictitious Store migration directory: Store is currently `app/store.py`; a separate product store may share SQLite with additive tables. Press variant remains pending owner intake. Anonymous sessions need no sign-in. This is an interface proposal, not migrated source. HM01 source implementation is next.
