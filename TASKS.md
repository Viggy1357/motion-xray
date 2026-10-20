# TASKS.md — current status, acceptance, dependencies, evidence, next action

All dates Malaysia time, 2026. A date does not make an unfinished task complete.
Primary goal confirmed 19 Oct: a usable personal training MVP. Codex leads; Kiro's
previous editing workflow is paused. Build the first usable **lat-pulldown** flow
(D005) before exercise expansion. Historical date estimates below are superseded by
dependency gates in `docs/DELIVERY.md`, not revised promises.

Read `docs/AUDIT-2026-10-19.md` for the verified baseline and requirement crosswalk.
`docs/SPECIFICATION-v2.0.md` preserves the full original brief. Current PRODUCT FR
numbers remain in use; some differ from the archived brief's FR numbers.

## Legend
- `todo` not started · `wip` in progress · `blocked` waiting · `done` evidence recorded

## T16 — Recovery audit and delivery workflow · status: done · 19 Oct
- **FRs:** FR01–FR12 (traceability and delivery gates).
- **Claim:** Codex; audit and documentation only. Preserve existing uncommitted implementation.
- **Scope:** Recover original specification and Kiro history; inspect implementation;
  run offline container checks; produce evidence-based progress, ordered work packages,
  operating workflow and a project delivery skill.
- **Checks:** Baseline pytest fails collection (3 errors); Ruff 121 findings; mypy 4
  errors. Frontend type-check/build pass. Temporary diagnostic contract/path correction
  permits 30 tests to pass, not an unmodified pass. Details: docs/audit/2026-10-19-checks.txt.
- **Changed files:** AGENTS, README, TASKS; docs audit/delivery/specification/evidence;
  API/DATA_MODEL/OPERATIONS status notes; new delivery skill and targeted corrections
  to existing pose/coaching/search skills. Application implementation left untouched.
- **Validation:** New skill validator passes; archived-spec hash, local document links,
  Markdown fences and task/FR coverage checked in Docker; documentation diff whitespace
  check passes. Two static subagent audits and Kiro snapshot review incorporated critically.
- **Open inputs:** Reviewed reference, runtime/hosting budget caps and optional hackathon
  intent. Future user sets do not establish reference standards. Kiro paused; Codex leads.
- **Next:** T02.1 executable verification, then T01/T04 real pose; docs/DELIVERY.md.

---

## T00 — Repo scaffold  ·  status: done
- **FRs:** (infrastructure)
- **Evidence:** Directory tree per spec §15, docs skeleton, contracts/providers stubs,
  Docker Compose skeleton, skills drafts, `.env.example`, git initialized.
- **Limit:** Structure milestone only; the app is not runnable end-to-end.
- **Next:** T02.1 executable checks, then T01 feasibility spike.

## T01 — Feasibility (Gate A)  ·  status: wip  ·  date: 16 Oct
- **FRs:** FR04, FR12
- **Goal:** Prove the chosen pose provider (MediaPipe) yields usable timestamped
  coordinates, correct anatomical sides, and synchronized playback on the authorized
  **lat pulldown** test clip (`data/demo/lat_pulldown.mp4`, diagonal/side view, ~55s,
  464×832, ~60fps → downsample to 30Hz). Run ONE real Nemotron inference through Token
  Factory and verify structured output. Record hardware, model revision, cold/warm
  runtime, peak memory, artifact size, dependency licenses.
- **Unblocked:** ✅ Docker Desktop running; ✅ test clip provided; ✅ Token Factory key
  present (model ID to confirm from catalog during the spike).
- **Acceptance:** usable coordinates + synchronized playback + stable body identity
  demonstrated (note: a second person is in the clip background — verify single-track
  stability); one Token Factory coaching call returns valid JSON. Pass/fail and provider
  decision recorded in DECISIONS.md.
- **Next:** T02.1 baseline is complete; on pose pass → T03/T08.1/T05; on failure →
  isolate cause and use D009 conditional comparisons before changing provider.
- **19 Oct audit:** No real pose artifact or measured feasibility pass. Latest Kiro
  live smoke returned Nano response with `content=None`; transport works but structured
  coaching is unvalidated. Clip duration 55.111667s exceeds the 30s default. Use a
  documented short segment for the spike. Implement the same real adapter under T04.
- **Dependency correction:** T02.1 first; then this gate. See DELIVERY T01/T04.

## T01b — Lat pulldown exercise + evidence/reference flows  ·  status: wip  ·  date: 18 Oct
- **FRs:** FR06, FR11
- **Goal:** (1) lat pulldown is the first exercise wired end-to-end (spec added:
  `data/exercise_specs/lat_pulldown.yaml`); (2) Tavily evidence-discovery flow that finds
  credible technique sources + candidate video URLs and extracts guidance text for
  operator review; (3) a reference-build script that turns product-owner-downloaded clips
  in `data/demo/` into a trajectory + tolerance ranges, flagged `authoritative=false`
  unless an owned/authorized reference (DECISIONS.md D005/D006/D007).
- **Acceptance:** `evidence/refresh` returns a reviewable shortlist from a real Tavily
  call; reference build produces a trajectory from an owned clip; experimental references
  are flagged non-authoritative and cannot yield a displayed valid score.
- **19 Oct audit:** Uncommitted discovery implementation and six fake-provider tests
  exist; live route protection, timeout enforcement, reviewed-cache filtering, persistence,
  reference builder/contracts and score guard remain unfinished. Preserve the diff.
- **Next:** T02.1; then bounded T10 hardening. Reference build waits for T04/T05.

## T02 — Scaffold hardening · status: done via T02.1 · historical estimate: 16–17 Oct
- Locked dependencies, executable Compose/CI checks and generated contracts delivered by
  T02.1; real model checkpoints and functional pipeline acceptance remain T01/T04 onward.

### T02.1 — Executable baseline repair · status: done · Codex, 19 Oct
- **FRs:** FR01–FR12 infrastructure.
- **Steps/files:** Fix Pydantic import configuration and fake enum; enforce meaningful
  contract invariants; resolve pytest package collision; fix lint/type failures; create
  test image/service and real script entrypoints; lock compatible dependencies and patch
  Next.js; generate usable API schemas and establish web/API routing as routes land.
- **Acceptance:** Fresh documented container commands execute actual imports/lint/types/
  unit/contract tests and frontend build; failures return nonzero; no provider credentials
  or host runtimes needed. Full bounded sequence: `docs/DELIVERY.md#t021--make-checks-and-local-startup-trustworthy`.
- **Changed files:** Contract validators/version 0.2.0 and generated schemas/types;
  module docstring order and fake enum; offline test image/Compose/scripts/CI;
  hashed Python locks, pnpm lock and digest-pinned bases; Next 15.5.28/React 19.3.0;
  localhost binding and web/API rewrite; docs/runbook. Paused Kiro evidence code was
  reviewed/adopted as incomplete T01b/T10 work with live route hard-disabled (503).
- **Checks:** `./scripts/test.sh python`: Ruff clean, mypy clean (36 source files),
  61 tests pass; `./scripts/test.sh web`: clean type generation/type-check and build.
  API/worker images build; actual MediaPipe 0.10.14 + NumPy 2.1.2 import succeeds.
  Intentional container-only test failure exits 1. Local smoke: health 200, web 200,
  `/api/exercises` forwards to `/v1/exercises` and honestly returns 501.
- **Evidence:** docs/audit/T02.1-verification.md. No product paid calls or Addy Osmani
  skills used. One upstream TestClient deprecation warning and empty-scaffold Tailwind
  warning remain; neither is suppressed or interpreted as a completed product.
- **Assumptions/blockers:** Verified locally on Linux/aarch64 Docker; remote GitHub CI
  not executed here. No real pose/artifact yet; reference review, coaching and T10 live
  evidence guards still pending. Private diagnostic scripts remain uncommitted.
- **Next:** T01/T04 real pose.

## T03 — Ingestion  ·  status: todo  ·  date: 17 Oct  ·  FR01, FR02, FR03
## T04 — Pose adapter  ·  status: todo  ·  date: 17–18 Oct  ·  FR04
- **T19 TODOs:** Validated frame-artifact reader; PTS/aspect/coordinate fixtures; raw
  observation masks and provenance. Conditional rtmlib/Norfair only on measured failure;
  no predicted joints or silently reduced 3D capabilities. DELIVERY + pose skill.
### T04 batch A — Canonical pose implementation · status: blocked · 20 Oct · FR04, FR12
- **Claim:** Codex coordinates/reviews; Nebius Token Factory generates bounded coding
  drafts. Three tasks only: (1) immutable pose artifacts, (2) named joint/quality mapping,
  (3) timestamped MediaPipe adapter. One writer applies reviewed outputs.
- **Call cap:** Four coding generations including at most one repair; no SDK retries;
  Qwen/Qwen3-30B-A3B-Instruct-2507; explicit output/time caps per call. This does not
  change runtime Nemotron or prove coaching. No secrets/private media sent as prompts.
- **Acceptance:** Relevant container checks; measured real smoke if model/runtime are
  available; preserve honest capability/quality failures. Record code, usage and limits.
- **Outcome:** No product code accepted. First three generations timed out after about
  90 seconds each; fourth streamed draft was truncated/malformed and failed source review.
  Four-call batch cap reached; no automatic retries or Codex implementation fallback.
- **Evidence:** docs/audit/T04-batch-a-nebius.md. Account model catalog succeeded;
  generation availability/quality did not. Billed usage is unknown for these failed calls.
- **Next:** Resolve coding model/route in a separately bounded batch, then implement
  artifacts, canonical mapping and adapter. T04 and real-pose Gate A remain incomplete.
### T04 batch B — Canonical mapping only · status: blocked · 20 Oct · FR04, FR12
- **Claim:** Codex reviews/verifies; one streamed Nebius Kimi-K2.7-Code draft, no retries,
  at most 5,000 output tokens. Smaller source-only prompt and strict file allowlist.
- **Acceptance:** Complete scoped output, source review and relevant offline container
  tests. No contracts or runtime model changes; real video adapter remains separate.
- **Outcome:** Request completed in 21.66s: 987 input + 5,000 completion tokens;
  all completion reported as reasoning; finish_reason=length; no final code accepted.
  Connection/authentication work. Development request policy is corrected under D011;
  the local 12k replacement request was prepared but not sent. Resume after T21.1.
### T04 batch C — Real pose components · status: wip · 20 Oct · FR04, FR12
- **Claim:** Codex coordinates, reviews and integrates direct Nebius scoped drafts.
  Clips inventoried in data/demo-clips.json; model provenance/checksum in
  data/pose_models/mediapipe-full-v1.json. Private video/frames remain local and ignored.
- **T04.1 done:** Qwen 235B JSON-mode mapping draft plus one defect-guided repair;
  reviewed integration corrections address invalid-derived provenance and faulty test
  assertions. Canonical MP33 mapping, finite/type masks, qualified estimated XYZ,
  derived midpoint provenance and no-detection gaps are implemented.
- **Checks:** ./scripts/test.sh python exit0; Ruff clean, mypy37 files clean, 78 tests
  pass (17 new mapping cases), existing dependency deprecation warning only. No paid
  runtime coaching or Tavily calls. No threshold/weight/schema changes.
- **Next:** T04.2 immutable frame artifacts, then T04.3 timestamped adapter + diagnostic.
  T21.1 generic tooling deferred after rejected drafts; manually bounded accounting,
  one worker at a time and no automatic draft execution/application remain enforced.
- **Evidence:** docs/audit/T04-resumed-pose-batch.md. One-frame diagnostics detect poses
  in all four clips; this is not a temporal tracking or real-sequence acceptance pass.
- **T04.2 done:** Nebius artifact draft plus one targeted repair; Codex integrated bounded
  fixes for the missing tempfile import, exclusive-install race, line bound and test
  fixtures. Canonical JSONL, SHA256 checks, bounded validated reading, symlink/traversal
  rejection, immutable/idempotent writing and cleanup are implemented.
- **Latest checks:** ./scripts/test.sh python exit0; Ruff/mypy38 files clean, 94 tests
  pass (16 artifact cases), existing deprecation warning only. Next T04.3 is in progress.
## T05 — First exercise engine (lat pulldown, D005) · status: todo · FR05, FR06, FR07
- **T19 TODOs:** Typed signal/config/side context; contiguous filtering; full-cycle
  state machine adapted from reviewed patterns; separate segmentation calibration;
  observable shoulder_drive definition without activation claims. Tests: gaps, occlusion,
  plateaus, stillness, partials, incomplete excursion and processing-speed invariance.
## T06 — References  ·  status: todo  ·  date: 20 Oct  ·  FR07, FR11
- **T19 TODOs:** Typed eligibility reasons; authority/rights/reviewer/artifact hashes;
  same-pipeline reference builder and deterministic representative/medoid. No automatic
  restricted-dataset import. Schema migration and generated consumers before exposure.
## T07 — Scoring  ·  status: todo  ·  date: 20–21 Oct  ·  FR07, FR08
- **T19 TODOs:** Narrow DTAIDistance experiment and typed alignment result; shared
  multivariate phase paths, tested band/endpoints, explicit cost normalization, unwarped
  tempo and pinned backend. Report index maps and breakdowns; maintain null/approval gates.
## T08 — Jobs & cloud  ·  status: todo  ·  date: 21–22 Oct  ·  FR03, FR12
### T08.1 — Local durable queue/lifecycle · status: todo · FR03, FR12
- Build with T03 before the first browser analysis; cloud deployment remains later.
- Acceptance: persistent job/status, lease/restart safety, cancellation/deletion and
  private artifact access. Steps and files: docs/DELIVERY.md T03/T08.1.
## T09 — Coaching  ·  status: todo  ·  date: 22 Oct  ·  FR09
## T10 — Evidence · status: todo · historical estimate: 23 Oct · FR11
- Reviewed evidence supports P0 technique advice/reference rules; live discovery and
  bonus eligibility are separate optional runtime proofs, not gates for real pose.
## T11 — X Ray UI  ·  status: todo  ·  date: 23–25 Oct  ·  FR10
### T11.1 — Real measurements inspector · status: todo · FR01, FR02, FR03, FR10, FR12
- Upload/status/video/2D/estimated-3D/rep inspection using real pipeline output.
- Explicit missing score/coaching states; intermediate milestone, not full MVP acceptance.
### T11.2 — Reference/score/coaching inspector · status: todo · FR09, FR10, FR11, FR12
- Complete reference overlay, phase mapping, score breakdown, sources and limitations.
## T12 — Other exercises  ·  status: todo  ·  date: 25–26 Oct  ·  FR06
## T13 — Evaluation  ·  status: todo  ·  date: 27–28 Oct
- **T19 TODOs:** Subject/session-held-out clips; separate count/boundary/quality/metric
  measures; no oracle class selection or leakage. External skeleton sets are optional
  rights-cleared downstream tests, not phone-pose validation. See EVALUATION matrix.
## T14 — Release  ·  status: todo  ·  date: 29 Oct
## T15 — Submission  ·  status: todo  ·  date: 30 Oct
- Optional workstream pending confirmation; personal MVP is the current primary goal.
- Official cutoff checked 19 Oct: 31 Oct 01:00 MYT. Budget/deployment still undecided.

## T17 — Incline bench chest press intake/spec · status: todo · FR04, FR05, FR06
- **Input:** User will upload their own set, alongside curl and bodyweight squat.
- **Scope:** Candidate exercise, not accepted support. Inspect implement/bench angle,
  view, visible joints and phase signal, then propose a bounded spec/decision and fixtures.
- **Acceptance:** Accepted exercise/variant/view and measurable outputs, versioned config,
  authorized test/reference inputs and evaluation plan before advertising support.
- **Next:** T12 expansion only after first exercise passes; do not block baseline/pose.

---

## T18 — Adjacent repositories and dataset screening · status: done · FR04, FR05, FR07, FR08, FR10
- **Scope:** Documentation-only screen of sports biomechanics, rehabilitation,
  tracking, repetition counting and temporal alignment; rank reuse candidates.
- **Acceptance:** Primary-source links, reuse/access limitations and bounded benchmark
  recommendations recorded; no dependency/provider changes or claims of runtime validation.
- **Changed:** docs/REUSE-SCREEN-2026-10-19.md and TASKS.md.
- **Checks:** Primary-source documentation/licence screen; git diff whitespace check.
  Documentation only; no runtime tests, model execution or dataset downloads performed.
- **Open:** Checkpoint terms, runtime fit and dataset-specific permissions/access require
  verification before adoption. No new approved lat-pulldown reference identified.
- **Next:** T01/T04 real MediaPipe artifact; conditional Sports2D comparison and T07
  DTAIDistance evaluation as documented in the screen. Existing private probes untouched.

## T19 — Critical upstream method and integration review · status: done · 20 Oct · FR04, FR05, FR07, FR08, FR10, FR11, FR12
- **Claim:** Codex consolidator with three user-authorized, read-only repository reviews.
- **Scope:** Source-level assessment of shortlisted pose, segmentation, alignment,
  tracking and reference/evaluation methods against current contracts and delivery gates.
- **Acceptance:** Exact existing/proposed integration files, benefits, incompatibilities,
  required adaptations and adoption checks; distinguish source review from runtime proof.
- **Output:** docs/INTEGRATION-REVIEW-2026-10-20.md; no application/dependency changes.
- **Changed:** Review report, DELIVERY cross-link and TASKS. T18 screening report retained.
- **Findings:** Adapt Sports2D/Good-GYM methods; evaluate DTAIDistance kernel; conditional
  Norfair/rtmlib. Defer paired-view learned assessors. Exact methods, local integration
  points, contract gaps, evaluation caveats and promotion checks recorded in the report.
- **Checks:** Current source/contracts/specs inspected; three read-only upstream reviews
  consolidated; documentation diff whitespace checks. No runtime benchmark or model/data
  download; no claimed accuracy or speed improvement. Private probe scripts untouched.
- **Open:** Pin adoption revisions/terms; prove runtime/quality in isolated containers;
  approved reference and typed alignment/provenance work remain implementation tasks.
- **Next:** T01/T04 real MediaPipe artifact, then T05; use T19 amendments during those
  tasks and T06/T07, without treating recommendations as completed integrations.

## T20 — Synchronize project guidance after upstream review · status: done · 20 Oct · FR01–FR12
- **Claim:** Codex, one writer; documentation and nonfunctional config comments only.
- **Scope:** Propagate T19 methods, conditional adoption gates, contract gaps and
  acceptance checks into active specs, delivery tasks, agent guidance and operations.
- **Acceptance:** Consistent scope/order/status; exact task ownership for follow-ups;
  archived evidence and generated schemas preserved; no algorithm or threshold changes.
- **Changed:** README/AGENTS/DECISIONS/TASKS; active product, architecture, delivery,
  contract/API, exercise/scoring/evaluation/operations docs; pose-service README and four
  project skills; lat-pulldown YAML comments only; docs/audit/T20-documentation-sync.md.
- **Checks:** `./scripts/test.sh python` exit 0: Ruff/mypy clean, 61 tests pass; one
  existing dependency deprecation warning. Offline container doc check: 18 Markdown
  files, local links/fences/routing pass; parsed YAML equals HEAD. Diff whitespace clean.
- **Limits:** No algorithm, schema, lockfile or dependency implementation; no real pose,
  paid call or new benchmark. Archived brief/audits and private probe scripts preserved.
- **Next:** T01/T04 real canonical pose, with D009/D010 and updated DELIVERY gates.

## T21 — MVP token forecast and allocation · status: done · 20 Oct · FR01–FR12 delivery
- **Scope:** Estimate remaining four-exercise MVP through T14; current model pricing,
  separate development/runtime accounting, user-authorized per-task allocations.
- **Output:** docs/TOKEN-BUDGET.md and docs/development-budget.json; D011; routing in
  AGENTS/DELIVERY. Forecast 2.47M tokens, 3.0875M with 25% reserve across 30 bounded tasks.
- **Limits:** Provisional engineering forecast, no measured successful-task baseline.
  No paid generation in this planning task. Earlier unaccounted calls stay unknown.
- **Checks:** Offline container verification passes allocation sums, 30-task count,
  per-task averages, reserve and price arithmetic; local links/fences and diff whitespace
  pass. No application code changed; no application tests or live inference rerun.
- **Next:** T21.1, then T01/T04; do not expand product scope.

### T21.1 — Reliable external coding request/usage handling · status: wip · FR04, FR12 delivery
- **20 Oct resumed claim:** Codex coordinates one direct Nebius Kimi coding worker;
  bounded first batch T21.1 plus T04 mapping/artifacts/adapter. No parallel generation
  before a reviewed, tested first result. Each request has no automatic retries, 600s
  total/90s idle timeout and sufficient completion space. Private clips stay local.
- **Accounting bootstrap:** First request reserves under $0.25 at conservative USD2/5
  per million input/completion tokens; 50k cumulative T21.1 allocation. Prior four
  unknown calls remain unknown, with $1 contingency (not measured spend or balance).
  Known historical Kimi usage remains approximately $0.02094. Protected $30 excluded.
- **Scope correction:** Broader Kimi draft truncated (975 input, 24,576 completion;
  20,787 reasoning); Qwen draft (923 input, 5,455 completion) rejected for placeholder
  dispatch and missing budget enforcement. Neither applied. Third request separates
  pure accounting/stream core from CLI; T21.1 allocation raised to 75k for this measured
  integration difficulty, still within the $70 ceiling. No blind generation retries.
- **Further diagnosis:** Kimi K2.6 generic thinking control still yielded no visible
  output. Template control yielded a complete but incorrect core (4,506 tokens);
  source review rejected locking/accounting/validation defects. Focused Kimi Code
  repair now has 49,152 output ceiling and a justified 150k cumulative task allocation
  to accommodate reasoning plus final code. Generation remains sequential.
- **Checkpoint:** Focused repair hit its 600s deadline with no final content; latest
  reported usage 973 input + 11,836 completion is partial, not final billing proof.
  Generic tooling remains unfinished. Per TOKEN-BUDGET's "not a replacement for T04"
  rule, resume one small mapping worker using the manually capped/accounted bootstrap;
  no parallel dispatch, no auto-application and no Codex product implementation fallback.
  Reusable CLI glue was removed while its required core is unavailable.
- **Budget:** 50k initial cumulative tokens, expandable under D011; first supporting task.
- **D012:** Optimize accepted progress within $70 Nebius operating ceiling; keep $30
  backup. Add cumulative cost/in-flight accounting and preserve unknown historic costs.
- **Scope:** Streaming, verified model output/parameter limits, sufficient reasoning/final
  allowance, idle vs total deadline, usage/finish-reason persistence on errors, scoped file
  validation and per-task aggregate ledger. SDK automatic retries off.
- **Acceptance:** Offline fake-stream tests cover reasoning-only exhaustion, truncation,
  invalid/scoped JSON, transport errors and usage capture. One valid scoped implementation
  can be reviewed/tested before parallel dispatch. No automatic execution of drafts.

## T22 — Resource ceilings and delegation efficiency · status: done · 20 Oct · FR01–FR12 delivery
- **Scope:** Record user-reported $100 Nebius ($70 operating/$30 backup) and separate
  8,000 Tavily credits; ceilings not targets, needs-based task resizing and efficient agents.
- **Changed:** Budget JSON/guide, AGENTS, D012, DELIVERY, Tavily skill and this task record.
- **Checks:** Offline JSON validation passes $70/$30 arithmetic, separate 8,000 credits,
  no target spend and unchanged token forecast; diff whitespace check clean.
- **Next:** T21.1 reliable single worker, then independent T04 tasks. No paid call or
  application/schema/runtime change in this update; previous forecasts remain estimates.

## Immediate next action
T02.1 is complete. Claim **T01/T04** and process a documented lat-pulldown segment
through the real canonical pose adapter. Do not restart the scaffold review loop.
First resolve T21.1 request handling using D011 allocation; the old tiny draft limits
are historical. Then resume the three pose tasks with meaningful final-code allowance.
Every remaining task's steps, files, dependencies and acceptance are in docs/DELIVERY.md.
Additional user clips are analysis inputs, not approved references. Budget caps and a
reviewed reference remain open; neither prevents offline baseline and pose work.
