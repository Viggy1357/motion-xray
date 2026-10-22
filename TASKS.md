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

## T23 — Hackathon MVP execution plan · status: done (planning only) ·22 October

- Owner accepts the analysis-first direction, asks for exact work/delegation steps,
  confirms same-browser profile first and free-first hosting. No implementation agents
  or paid model requests launched in this planning turn.
- **FRs:** FR01–FR12 plus explicit personal workout/profile product scope.
- **Plan:** `docs/HACKATHON-EXECUTION-PLAN.md`: HM00–HM13, dependencies, file boundaries,
  acceptance gates, screen states, contract/ownership/media/report/quality/LLM paths,
  four-clip exercise rollout, free hosting feasibility, release/submission checklist.
- **Ready packets:** `docs/delegation/HM-BATCH-A.md`; next delegation starts onlyBatch A.
  All HM packages remain todo. Existing accepted code checkpoint1548920 is preserved.
- **Current gap verified:** main web page and runtime Nemotron provider are still
  scaffolds; published reports remain pose-only. Current30s caps reject55.11s lat and
 39.92s press originals; plan includes coordinated60s limit and full-set acceptance.
- **Checks:** current sources/clip metadata inspected read-only in Docker; official
  hackathon/FAQ/3D docs checked; plan/links/whitespace checked. No application behavior
  changed, no new dependency, tests not rerun for documentation-only work.
- **Next:** HM00 flow/mockup + HM01 contract proposal + read-only deployment/runtime
  readiness in parallel; one integration gate before dependent source implementation.

## Active priority — measurement and reviewed comparison (22 October)

**Latest owner override:** benchmark assessment is frozen at its current provisional
baseline. Tie off this run, then brainstorm a functional Nebius hackathon product.
Do not spend another batch on calibration/accuracy or build new product features before
the requested discussion. See `docs/HACKATHON-MVP-DIRECTION.md` and D015. The older
measurement-first hold below is superseded by this explicit scope change.

### Active run — steps4–7 (22 October, owner-authorized)
- Claim T08.1c.2 private artifact ranges, T08.1d conservative physical retention,
  T06.2 benchmark/endpoint calibration and T07.1 component comparison in order.
- Nebius drafts independent bounded packets (maximum3 concurrent); one integrator.
  Each task retains200k cumulative tokens, USD70 active/USD30 protected resource gates.
- Public pose-only reports stay honest; experimental references cannot produce a
  valid technique score. Unsupported calibration/endpoint automation stays explicit.
- Checks/results/remaining blockers recorded in the T047 checkpoint below.

### T047 — steps4–7 checkpoint · accepted bounded slices; benchmark frozen
- **FRs:** FR02/03/04/07/08/10/12. T08.1c.2 owner-scoped artifact ranges accepted;
  T08.1d manual completed-artifact cleanup accepted with retry receipts; ambiguous/
  cancelled cleanup still deferred. T06.2 manual endpoint geometry and pending policy;
  T07.1 event-level comparison/conditional score engine, no public aggregate or DTW.
- **Evidence:** `docs/audit/T047-checkpoint.md`; real10.01s lat upload->separate worker
  ->300 pose samples->private ranges and separate TTL cleanup. Public reports pose-only.
- **Checks:**767 offline Python tests; Ruff clean; mypy61 sources; frontend types/build
  pass; generated OpenAPI/TS consistent.19 Nebius requests298,021 tokens across bounded
  tasks, conservativeUSD2.192830 including failed/rejected drafts; no task exceeds200k.
- **Limits:**120 descriptive comparisons over8 user reps/3 sources; no current numeric
  scores because the frozen policy remains pending.12 local endpoint point proposals
  are not automatic detection or ground truth. No confidence index implemented yet.
- **Next:** owner-directed hackathon feature discussion, then proposed T11 product-flow
  slice and T09 real runtime NVIDIA/Nebius call. Further benchmark assessment held per
  D015. See `docs/HACKATHON-MVP-DIRECTION.md`; new UI/features are not yet approved.

User-directed order: T05 -> T06 -> T07 comparison validation. Hold new work on
artifact streaming, physical cleanup, browser UI, hosting, coaching and exercise
expansion until this core is demonstrated. Preserve the accepted local infrastructure.
This supersedes earlier "next" entries recommending T08.1c.2 first.

First prove lat pulldown: observable metric/side/view definitions and segmentation
calibration; independently annotated real reps/angles/occlusions; deterministic
measurement engine; authorized technique reference with separate technique review;
compatible phase-aware comparison with timestamped component differences; frozen
config held-out validation. Score aggregation follows validated comparison, not the
other way round. Missing reference approval blocks a valid technique score, while
measurement implementation and candidate research can proceed independently.

Latest review: T05.1 raw observations and T06.1b experimental review packet exist.
The owner reports ten reps but **more than five usable reps suffice** for the first
posture/scoring proof; exact counting is not the acceptance target. QMotion's corrected
form is preferred. The trial omitted torso lean/sway; its92-point agreement is not an
accepted technique score. Current sequence: existing repo fit assessment -> roughly
five credible sources consolidated into the exercise metric rubric -> two/three
reference-video calibration -> user component deviations and scoring -> detailed
timestamped guidance. Reference-derived3D is distant future scope, not user multi-camera
capture. The sourced metric matrix is now delivered as research pending calibration:
`docs/measurement/LAT-PULLDOWN-RUBRIC-v0.1.md`. T05.2b now delivers raw torso/window
measurements and a reference crop-quality experiment. T05.2c now measures ten selected
reference reps and eight selected user reps; seven user reps have all current torso/arm
components after a fixed-crop experiment. Next is compatible source/view calibration,
provisional component policy and bar-endpoint measurement; see
`docs/measurement/LAT-PULLDOWN-REUSE-AND-CALIBRATION.md`. Other work stays held.

### T05.2c — labelled rep measurement proof · status: done (bounded measurement slice)
- **Date/FRs:**22 Oct; FR05/FR07/FR08/FR12. Seven direct Nebius generation/QC calls,
  first batch4 and second batch3; Codex coordinates/integrates and checks local frames.
- **Delivered:** movement.rep_observations, analytic fixture and independent tests;
  offline rep runner and reusable diagnostic renderer; versioned provisional labels;
  source-wise observed profiles for4QMotion/3Catalyst/3IMSA reps and8 user rep intervals.
- **Result:** Same labels before/after local user crop;4/8 ->7/8 have all32 current
  generated components, preserving the remaining arm-gap reasons. Bar endpoint is not
  one of those32. No new aggregate score, approved tolerance, public schema or old
  segmentation/scoring threshold change. Eight physical reps are not counted twice.
- **Review:** http://localhost:8865/t052c.html ; docs/audit/T05.2c-rep-review.md and JSON;
  docs/measurement/T05.2c-rep-protocol.md. Tables retain original PTS, missing reasons,
  camera/view and source-hash provenance; private videos/images/pose arrays stay local.
- **Checks:**625 full offline Python tests pass;26 focused checks; Ruff clean/mypy57
  source files. Browser8user/10reference rows, source switching/seek verified; repeated
  numeric/render output hashes checked. Existing AnyIO warning. Contract-invalid test
  fixtures and renderer field mappings corrected without skipped tests/relaxed masks.
- **Usage:**82,641 reported Nebius tokens/200k; conservativeUSD0.451828; aggregate
  commitment incl historic unknown contingencyUSD5.76842365. ProtectedUSD30 untouched;
  no private footage/pose arrays/user measurement values in prompts, runtime coaching
  call or Tavily spend. Initial rejected drafts/repairs remain in the ledger.
- **Limits:** Labels are model-assisted and visually checked at3 event frames, not
  independent human/expert ground truth. Timing allowances are provisional. Projected
  torso differences across cameras are descriptive, not validated physical deviations.
- **Next:**T06.2 reviewable compatible-reference/component policy and bar-endpoint proof;
  then T07 partial component scoring with versioned fixtures before any aggregate.

### T05.2b — projected torso and reference observations · status: done (bounded slice)
- **Date/FRs:**22 Oct; FR05/FR07/FR08/FR12. Codex one integrating writer; seven direct
  Nebius drafting/independent-test/repair/report calls, first batch4 and second batch3.
- **Delivered:** movement.posture signed aspect-correct shoulder/hip angle and strict
  original-PTS window summaries; offline hash-verified reference runner; analytic
  fixture/tests; two explicit experimental diagnostic configs. Rubric no longer permits
  an unvalidated wrist proxy to satisfy required bar-endpoint coverage.
- **Evidence:** docs/audit/T05.2b-posture-observations.md and
  T05.2b-reference-observations.json; docs/measurement/T05.2b-projected-posture-protocol.md.
  Original3 demos inspected plus QMotion's bad example and two recorded crop derivatives.
- **Finding:** High-confidence landmarks sometimes place shoulder/hip on wrong regions.
  Fixed ROI experiment reduces Catalyst projected shoulder-below-hip frames44->3 and
  90->0 in separate windows; does not establish accurate landmarks. Corrected/bad
  QMotion angle ranges overlap. Do not turn these ranges into scoring thresholds.
- **Checks:** ./scripts/test.sh python:599 passed, Ruff clean, mypy56 sources;83 focused
  tests. Existing AnyIO warning. Repeat real diagnostic artifacts checked separately.
  Failed drafts were repaired without skipping/deleting tests; two test setups and
  small typing/statistics integration corrections recorded. No new dependency.
- **Budget:**96,038 reported Nebius tokens/200k; conservativeUSD0.467750; aggregate
  commitment incl unknown-history contingencyUSD5.31659565. ProtectedUSD30 untouched;
  no private media in prompts, paid runtime coaching or Tavily spending.
- **Limits:** No approved ranges/reference profile, physical gravity calibration,
  per-rep phase labels, validated bar measurement or technique score. This is not the
  six-user-rep posture proof. Existing public reports, old thresholds and UI untouched.
- **Next:** T05.2c checked reference phase/landmark annotations, then source-wise per-rep
  components and T06.2 provisional benchmark. Compare at least six eligible user reps
  after compatible measurements exist; exact ten remains secondary.

### T05.2/T06.1 sourced posture rubric · status: done (research slice) · 22 Oct
- **FRs:** FR05/FR07/FR08/FR11/FR12. Codex coordinates; all four model drafting/review
  requests via direct Nebius. User requests approximately95% substantive work on Nebius;
  cross-provider token percentage was not measured. No Codex subagent generation.
- **Delivered:** Five-source consolidated rubric, eight candidate measurement entries,
  source conflicts, observable/proxy limits, required-component coverage and separate
  tempo; repo fit/defer assessment and narrow calibration handoff. References: ACE,
  NASM, Catalyst, QMotion and Jeff Nippard's original automatic caption excerpt.
- **Files:** docs/measurement/LAT-PULLDOWN-RUBRIC-v0.1.md and
  LAT-PULLDOWN-REUSE-AND-CALIBRATION.md; docs/audit/T05.2-rubric-qc.md;
  docs/development-usage-T05.2-rubric-2026-10-22.json; TASKS/DELIVERY.
- **Checks:** Primary-source retrieval/caption provenance, Nebius QC plus bounded
  integration corrections, offline document/ledger checks and diff whitespace.
  No runtime behavior changed or application test suite rerun. Existing scratch probes
  included in the requested source checkpoint after syntax/secret checks, not executed.
- **Budget:** 51,787 reported tokens/200,000; conservativeUSD0.206662; aggregate
  commitment including earlier unknown-history contingencyUSD4.84884565. ProtectedUSD30
  untouched. No private media sent, live coaching call or Tavily credit used.
- **Limits:** Research pending calibration, not approved numerical ranges or a score.
  Automatic captions need audio verification before numerical cue adoption. No new
  dependency/data adoption, threshold/config/public schema change or claimed video accuracy.
- **Next:** T05.2 torso-axis/dynamic observations and manual reference measurements from
  existing immutable artifacts; T06.2 versioned provisional benchmark, then T07 user
  comparison on at least six eligible reps. Exact ten-rep recovery stays secondary.

### T05.2/T06.1 workflow clarification · 22 Oct · FR05/FR07/FR08/FR11/FR12
- **Claim:** Codex; bounded documentation clarification, not a new implementation batch.
- **Changed:** Current posture benchmark workflow, feedback note, TASKS and DELIVERY.
- **Checks:** Existing reuse/integration reviews inspected for fit and gaps; documentation
  whitespace checks. No new dependency, threshold, runtime code or paid provider call.
- **Limits:** The five-source synthesis and reference calibration remain to be completed;
  no benchmark range or validated score was established by this documentation update.
- **Next:** T05.2/T06.1 sourced metric matrix first, using existing resources before
  targeted web research. Preserve independent quality gates without an all-ten-rep gate.

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
- **20 Oct pose outcome:** Real T04 adapter passes 131 tests and produces a 300-frame
  artifact for source10–20s at29.96Hz, with synchronized browser overlay/rotatable
  estimated3D. Visible-side coverage supports proceeding to measurements; far-arm
  occlusion and unverified identity/depth remain explicit. Other clips have real
  artifacts with gaps. Structured runtime Nemotron remains unvalidated, so T01 stays wip.

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

## T03 — Ingestion  ·  status: wip  ·  date: 21 Oct  ·  FR01, FR02, FR03
- **Claim:** T03a anonymous signed session/CSRF boundary and real bounded private upload,
  using T08.1a metadata storage. Nebius drafts/tests; Codex verifies/integrates. Proxy
  creation and worker invocation remain T03b/T08.1b; no analysis success implied here.
- **T03a done (21 Oct):** HMAC-signed anonymous identity, same-origin CSRF checks,
  explicit upload consent, bounded streaming and real ffprobe metadata validation.
  `/v1/session`, POST `/v1/videos` and private GET `/v1/videos/{id}` metadata work.
  SessionInfo, OpenAPI, JSON Schema and generated TypeScript are migrated together.
- **Files:** `services/api/app/{session,ingest,uploads,main}.py`, contracts/session and
  schema exporter/generated artifacts, API Dockerfile, Compose VIDEO_ROOT, env example;
  session/ingestion/HTTP tests, updated API/operations/architecture/delivery guidance.
- **Checks:** `./scripts/export-contracts.sh` and `./scripts/test.sh all` exit 0;
  Ruff/types clean, 341 tests pass after the final identifier guard; frontend checks pass. Existing AnyIO and
  empty-scaffold Tailwind warnings remain. Provider smoke checks made no paid calls.
- **Real acceptance:** Isolated HTTP API accepted owned Squat.MOV (27,808,876 bytes,
  14.248333s, rotation -90), verified stored hash/mode0600; cross-owner404, badCSRF403,
  invalid media422 and full55s lat rejection422. API restart preserved private metadata.
  No staging/rejected-file leaks. Evidence: `docs/audit/T03a-private-upload.md`.
- **Usage:** Eight direct Nebius draft/repair calls, 121,654 reported tokens across
  three bounded tasks, conservative USD0.440195 (not invoice prices); two independent
  workers overlapped following user authorization. Usage ledger records failures too.
- **Remaining/next:** T03b/T08.1b audio-free proxy + original/proxy PTS map, worker loop
  invoking actual MediaPipe, lifecycle/artifact routes and physical TTL cleanup/race
  tests. Browser capture/upload UI remains T11.1. Current session expires after24h;
  anonymous identity recovery/renewal needs review before release. No raw media serving,
  scoring, coaching or end-to-end analysis claim. Missing SESSION_SECRET fails503.
- **T03b standalone component done (21 Oct):** `providers/pose/proxy.py` creates a
  private audio-free H264 proxy and typed `contracts/proxy.py` actual timestamp map.
  Source bytes/hash/metadata, rotation, even-dimension padding, frame preservation and
  timestamp drift are checked; owned partial outputs are cleaned on failure.
  Generated JSON schemas and 28 focused cases are included. `./scripts/test.sh python`
  exits0:369 tests, Ruff and mypy45 files clean. Existing AnyIO warning only.
- **Real proxy evidence:** Owned Squat.MOV ->427 frames,1080x1920 proxy, one video stream,
  no audio/subtitle/data; source/proxy PTS verified. `docs/audit/T03b-proxy-checkpoint.md`.
  This helper is not invoked automatically by uploads; VideoAsset timestamp_map_key
  remains null until worker publication is implemented.
## T04 — Pose adapter  ·  status: done (local adapter)  ·  20 Oct  ·  FR04, FR12
- Local canonical extraction/artifacts/diagnostic delivered by batch C; the historical
  failed batches below are superseded. Service job integration remains T03/T08.1;
  subject association, broader quality validation and scoring are not claimed complete.
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
### T04 batch C — Real pose components · status: done · 20 Oct · FR04, FR12
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
- **T04.3 done:** Real ffprobe PTS/rotation, bounded FFmpeg decode/cleanup, lazy local
  verified MediaPipe checkpoint, explicit no/multiple-person gaps, content-addressed
  frames, local smoke scripts and source-hash-verified video/2D/rotatable3D diagnostic.
  Nebius supplied drafts/tests; Codex integrated targeted contract/runtime/test fixes.
- **Final checks:** ./scripts/test.sh python: Ruff/mypy clean, 131 tests pass. Actual
  lat10–20s:300 frames29.96Hz, no all-invalid samples, cold9.8039s/second8.913s, same
  artifact hash. Curl0–10s:300 frames/3 gaps; squat:300/24; press:299/3. Browser verified
  source playback, frame seek at10.005/15.045/19.717s, overlay alignment and yaw rotation.
  No general accuracy, verified identity, rep count, metric or score claim.
- **Budget:** 15 coding generations,162,809 known-final tokens plus12,809 reported
  partial tokens. Conservative batch commitment USD0.958405 retains full USD0.263922
  timeout reservation. USD30 backup untouched; old unknown usage is not reconciled.
  No Tavily or paid runtime coaching. Ledger: docs/development-usage-2026-10-20.json.
- **Next:** T03/T08.1 upload/queue integration, then T05 visible-side measurements with
  explicit calibration/eligibility. T01 structured coaching and T21.1 tooling remain open.
## T05 — First exercise engine (lat pulldown, D005) · status: wip · FR05, FR06, FR07
- **Claim T05.1 (22 October) · done (raw arithmetic/protocol only) · FR05/FR07/FR12:** Raw visible-side geometry
  extraction, explicit coordinate/side eligibility and independent manual-label protocol.
  Parallel Nebius implementation/tests/measurement-reference design; sequential review
  and one integrator. T06.1 candidate guidance research overlaps; no reference approval,
  rep calibration, score or coaching implied. Per-task ceiling200k, max3 concurrent;
  active USD70/protected USD30 unchanged, no paid product-runtime/search calls.
- **Accepted:** `movement/observations.py` extracts elbow and upper-arm/torso angles
  in aspect-correct projected2D and qualified estimated3D. Explicit side, timestamp,
  per-metric missing/invalid/interpolated/degenerate reasons. Existing core rep/metric
  scaffolds, thresholds, public schemas and API reports remain unchanged.
- **Evidence:**300 immutable lat frames (10.005–19.983333 sourcePTS),2,400 observations,
  identical repeat hash. Left elbow296/300 valid; left upper-arm/torso300/300;
  right elbow93/300, right upper-arm/torso94/300. Coverage is not anatomical accuracy.
- **Checks:**48 focused cases; final full Docker Python476 passed, Ruff clean,
  mypy53 files clean; existing AnyIO warning only. Analytic versioned fixtures and
  independent700-digit Decimal checks resolve numerical QC concerns. No web change.
- **Usage:**8 Nebius calls65,779 tokens, conservative USD0.209432 incl rejected drafts
  and repairs. Peak3 workers; separate sequential QC. See
  `docs/audit/T05.1-raw-observations.md` and linked ledger/results/review resolutions.
- **Next T05.2:** independent rep/angle labels, valid-span filtering and calibrated
  complete-cycle detection; require originalPTS, retained partials and frozen config.
  Anatomical accuracy, actual per-rep ROM/timing and technique comparison remain open.
- **T19 TODOs:** Typed signal/config/side context; contiguous filtering; full-cycle
  state machine adapted from reviewed patterns; separate segmentation calibration;
  observable shoulder_drive definition without activation claims. Tests: gaps, occlusion,
  plateaus, stillness, partials, incomplete excursion and processing-speed invariance.
## T06 — References  ·  status: todo  ·  date: 20 Oct  ·  FR07, FR11
- **Claim T06.1b (22 October) · done as experimental review packet · FR05/FR07/FR11/FR12:** User requests local
  retrieval of Catalyst/QMotion/IMSA demos as needed, diagnostic comparison, rep counts
  and a provisional reference ranking for their review. This authorizes local
  experimental retrieval/inspection, not a claim of redistribution rights, approved
  technique or a production-valid score. Record actual retrieval failures honestly.
- **Delivered:** All3 public demos retrieved locally, hashed and analysed with the
  accepted pipeline. IMSA full-frame824/840 entirely invalid; explicit right-panel
  crop reduces that to5/840. QMotion setup/red-X example excluded; Catalyst camera
  windows separated. Videos/pose data/per-pair mappings remain ignored.
- **Trial library:** `movement/review_cycles.py`, `scoring/review_comparison.py`,
  explicit `data/review_configs/lat-reference-v1.json` and40 focused tests. No production
  threshold/schema/score/API changes. Full Python516 passed; Ruff/mypy55 files clean.
- **User review:** http://localhost:8865/ ; pipeline-usability rank QMotion, cropped
  IMSA, Catalyst. Selected-window trial counts3/6/0 respectively; user excerpt1.
  Unvalidated angle-pattern agreement92.47/92.68/unavailable. This is NOT technique
  correctness, an approved reference or whole-video rep counts. Known misses/merges
  are explicit: Catalyst0 is a detector failure, not absence of repetitions.
- **Usage/QC:**68,982 reported development tokens; conservative USD0.315914 including
  rejected drafts/vision review and KimiK3 escalation. One local SDK failure before
  HTTP; no paid runtime coaching/Tavily/backup. See `docs/audit/T06.1b-review.md`.
- **Next:** User reviews videos/counts/ranking/formula; T05.2 independent event labels,
  calibrated segmentation and true-turnaround timing must fix observed misses before
  any comparison/score accuracy claim. Reference approval and held-out proof remain open.
- **T06.1 research checkpoint (22 October):** ACE/NASM guidance checked; Catalyst,
  QMotion and IMSA demo pages shortlisted with source/reuse/view/reviewer gaps recorded
  in `docs/measurement/T06.1-reference-plan.md`. User asks us to find demos; their
  reviewer may assess the links, not supply a trainer recording. Video playback,
  extraction permission and technique approval remain unverified; no approved reference.
- **T19 TODOs:** Typed eligibility reasons; authority/rights/reviewer/artifact hashes;
  same-pipeline reference builder and deterministic representative/medoid. No automatic
  restricted-dataset import. Schema migration and generated consumers before exposure.
## T07 — Scoring  ·  status: todo  ·  date: 20–21 Oct  ·  FR07, FR08
- **T19 TODOs:** Narrow DTAIDistance experiment and typed alignment result; shared
  multivariate phase paths, tested band/endpoints, explicit cost normalization, unwarped
  tempo and pinned backend. Report index maps and breakdowns; maintain null/approval gates.
## T08 — Jobs & cloud  ·  status: todo  ·  date: 21–22 Oct  ·  FR03, FR12
### T08.1 — Local durable queue/lifecycle · status: wip (daemon/API implemented; streaming/cleanup pending) · FR03, FR12
- **Claim T08.1b.3 + T08.1c.1 (21 Oct) · done · FR02/03/04/12:** Worker daemon,
  graceful shutdown/reclaim and authenticated enqueue/status/cancel/delete/report API.
  Add safe pose-only public request/status contracts; bind job versions to the configured
  checkpoint and processing recipe. Worker and HTTP drafts may overlap after contracts.
  Artifact streaming/ranges and physical cleanup remain T08.1c.2/T08.1d. Each bounded
  task ceiling200k; no runtime LLM/Tavily/backup activation. One integrating writer.
- **Accepted files:** `services/pose/worker.py`, API `analyses.py`,
  `processing_config.py`, supervisor publication-race fix, lifecycle contracts and
  generated schemas/TS, Docker configuration and focused tests. API/worker share a
  canonical checkpoint/recipe version. Public status redacts lease tokens/storage keys.
- **Checks:** Docker full Python suite428 passed; Ruff/mypy52 files clean; generated
  contracts, web typecheck and production build pass. Existing AnyIO warning remains.
  Evidence and real-video outcome: `docs/audit/T08.1b.3-lifecycle.md`.
- **Usage:** seven Nebius calls48,099 tokens, conservative USD0.151299; peak two
  concurrent calls, one integrating writer. Includes rejected drafts and repairs.
- **Next T08.1c.2:** authenticated artifact streaming with byte ranges; then T08.1d
  physical expiry/deletion cleanup and T10 usable browser upload/poll/result flow.
- **Claim T08.1b.2 (21 Oct) · done · FR03, FR04, FR10, FR12:** Connect the accepted
  supervisor to real proxy/MediaPipe child processing through typed private request/
  artifact manifests. Validate actual artifact hashes, ownership and pose-only honesty
  before publication. Nebius drafts bounded components in parallel after contracts
  are fixed; one integrator. Verify a lat excerpt and eligible full clip in Docker.
  Ceiling200k cumulative tokens; no runtime LLM/Tavily or protected backup use.
- **Accepted:** private PoseJobInput/PoseJobArtifacts contracts + JSON schemas;
  `services/pose/child.py`, `services/api/app/pose_jobs.py`, artifact/CLI tests. Original
  video inference covers full duration; proxy/pose/request hashes, identity binding,
  actual timestamps and expected sample set validated before fenced publication.
- **Real proof:** lat excerpt10.01s:600 source/proxy frames,300 pose samples; full squat
  14.248333s:427 source/proxy frames,425 pose samples. Both real queued jobs published
  pose-only manifests, null scores, no rep/metric/reference/coaching claims.
- **Checks:** `./scripts/test.sh python` exit0:403 tests, Ruff clean, mypy49 files clean;
  pre-existing AnyIO warning only. No web/public route change; provider smokes offline.
- **Usage:** six Nebius calls45,721 reported tokens, conservative USD0.143597; up to
  three independent calls overlapped, one writer. Scope ceiling200k. See
  `docs/audit/T08.1b.2-real-pose-child.md` and its linked results/ledger.
- **Historical next, now advanced above:** worker loop and lifecycle routes are
  implemented. Artifact streaming, physical retention and browser analysis remain open.
- **Resume (21 Oct, user-authorized): T08.1b.1 · done · FR03, FR12.** Raise this
  task's cumulative ceiling to200k, retaining the prior79,431 tokens. Prove only a
  real-Store success/timeout fixture first. In parallel, Nebius reviews the small
  parent draft for concrete defects; one writer integrates. Then add race tests in
  small accepted groups. Addy debugging/incremental skills authorized for this work.
  USD70 active ceiling/USD30 protected backup remain unchanged. No runtime paid calls.
- **Accepted:** `services/api/app/supervisor.py`, three `tests/unit/test_supervisor*.py`
  modules. Real Store + real subprocesses prove renewal, timeout, cancel/delete/reclaim,
  final publication fencing, collision preservation, invalid output and exception cleanup.
  Owned attempts only are cleaned; direct children reaped and surviving group descendants
  killed. Trusted quick callbacks and a private artifact root are required; no OS sandbox.
- **Checks:** focused20 cases pass; `./scripts/test.sh python` exit0:389 tests, Ruff
  clean, mypy46 files clean. Existing AnyIO warning only; provider smokes offline.
- **Resumed usage:** five calls41,555 tokens, conservative USD0.120724; same-task total
  120,986/200k includes previous failed usage. Independent Nebius work overlapped,
  one writer integrated. See `docs/audit/T08.1b.1-resumed-supervisor.md` and linked ledger.
- **Next:** T08.1b.2 real child adapter/typed pose-only artifacts, then worker entrypoint,
  authenticated lifecycle/artifact routes and physical retention. Worker remains inactive;
  no automatic analysis, score or coaching is implied by controlled subprocess tests.
- **Revised claim (21 Oct): T08.1b.1 parent-only supervisor · blocked · FR03, FR12.**
  Nebius drafts one internal subprocess supervisor and focused tests using the real
  Store. Prove heartbeat, timeout, cancellation/deletion, stale-lease fencing and
  process reaping with controlled child processes. No ML/HTTP/schema/retention changes.
  Keep the existing worker entrypoint inactive; accept this component before the child
  adapter. New bounded scope has a100k cumulative token ceiling; previous failed worker
  usage stays recorded. Preserve existing attempt directories and validate before finish.
- **T08.1b.1 outcome:** No source/test component accepted or activated. Reviewed parent
  draft passed Docker lint/types; private second-draft subprocess suite had10 failures
  and16 passes. Test-only reasoning request returned no final source; final coding-model
  test draft failed against real Store with nonexistent `migrate()` API. Stopped the
  route rather than rewriting the suite in Codex. Existing product sources preserved.
  Five calls79,431 reported tokens, conservative USD0.309477; three no-spend preflight
  rejections. No runtime coaching/Tavily/backup. See
  `docs/audit/T08.1b.1-parent-supervisor.md` and linked ledger. Next remains T08.1b.1
  acceptance with a minimal verified real-Store fixture, then T08.1b.2 child adapter.
- **Claim (21 Oct):** T03b/T08.1b queued pose-only vertical slice: private proxy/PTS
  map, fenced subprocess worker, authenticated lifecycle/artifact routes and retention.
  Up to four bounded Nebius work tasks; independent drafts may overlap, one integrator.
  Success at this checkpoint must explicitly identify missing measurements/scoring.
- **Batch outcome (21 Oct):** Only the standalone proxy component passed acceptance.
  T08.1b worker drafts failed review/checks; four requests used99,574/100,000 task tokens.
  Final reasoning-enabled request consumed32,768 completion tokens with no final source.
  Stop this retry route; do not silently replace it with a large Codex implementation.
  T08.1c HTTP and T08.1d janitor drafts are private and NOT accepted/enabled.
- **Failure evidence:** Wrong checkpoint-vs-frame hashes, unsafe attempt ownership/
  cleanup, process reaping defects, invented Store APIs/fixture fields, unsafe artifact
  resolution and invalid database state strings. Prior working service files preserved.
- **Resource record:** Four bounded work tasks,10 generations,193,333 reported tokens,
  conservative USD0.734405 including failures; no Tavily/runtime coaching/backup use.
  See `docs/development-usage-T03b-2026-10-21.json`. Remaining active resource allocation
  is not verified account credit. Next worker approach must change before more requests.
- **Claim (20 Oct, next run):** T08.1a durable owner-scoped SQLite asset/job repository.
  Nebius drafts implementation/tests; Codex runs offline checks and integrates.
  No HTTP upload/worker completion is implied by this internal foundation.
- **T08.1a done:** `services/api/app/store.py`, `tests/unit/test_job_store.py` implement
  schema-v1 SQLite metadata, ownership checks, owner-scoped idempotency, atomic claims,
  unique lease fencing, heartbeat/stage updates, cancellation and deletion tombstones.
  Raw-asset expiry blocks processing; unexpired report/job status remains accessible.
  Connection cleanup, concurrent claims, stale workers and malformed paths are tested.
- **Checks:** `./scripts/test.sh python` exit 0: Ruff clean, mypy clean, 212 tests pass
  (81 new store cases); existing Starlette/AnyIO deprecation warning only. Contract drift
  tests pass. Provider smoke checks are offline dry runs, not runtime acceptance.
- **Usage:** Three Nebius generations, 61,368 reported tokens; conservative USD0.237798,
  not verified billing. First draft rejected; two repairs reviewed before integration.
  See `docs/audit/T08.1a-durable-store.md` and its linked usage report.
- **Remaining/next:** T03 private ingestion/session ownership at HTTP boundary, then
  T08.1b worker + lifecycle routes + real pose acceptance. Physical retention cleanup,
  upload/proxy validation and full application integration remain open. Internal store
  assumes its caller authenticates owner and verifies uploaded media; it is not an auth
  system and does not validate or serve files. No new public schema/dependency.
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
T02.1, local T04, T08.1a store, T03a private HTTP ingestion and the standalone T03b proxy
are complete. **T08.1b is blocked on a rejected delegated implementation**; revise the
worker approach before another paid generation. Reuse the accepted proxy/store/pose
components. The exact next acceptance packet is `docs/audit/T03b-proxy-checkpoint.md`.
Then complete one durable job invoking the actual provider, private lifecycle/artifact
access and physical cleanup. No worker/HTTP/retention draft from this batch is accepted.
Then T05 visible-side measurements, calibration and full-cycle segmentation. Do not
restart scaffold/source-screening or the failed generic-tooling loop. T21.1 remains
unfinished; use bounded requests, explicit reservations and the actual usage
ledger while its reusable implementation is deferred. T01 runtime coaching is separate.
Independent Nebius workers may run in parallel within the three-task concurrency cap;
keep one integrating writer and avoid duplicate reviews or context resends.
Every remaining task's steps, files, dependencies and acceptance are in docs/DELIVERY.md.
Additional user clips are analysis inputs, not approved references. The $70 active/$30
backup ceiling is recorded; actual account balance/history reconciliation and a reviewed
reference remain open. Neither prevents the local upload/measurement work.
