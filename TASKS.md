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
- **Next:** on pass → T02 lock environments; on fail → isolate + fallback.
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

## T02 — Scaffold hardening  ·  status: todo  ·  date: 16–17 Oct
- Locked dependency versions, working Compose, CI (fixtures only), contracts exported.

### T02.1 — Executable baseline repair · status: todo · next implementation task
- **FRs:** FR01–FR12 infrastructure.
- **Steps/files:** Fix Pydantic import configuration and fake enum; enforce meaningful
  contract invariants; resolve pytest package collision; fix lint/type failures; create
  test image/service and real script entrypoints; lock compatible dependencies and patch
  Next.js; generate usable API schemas and establish web/API routing as routes land.
- **Acceptance:** Fresh documented container commands execute actual imports/lint/types/
  unit/contract tests and frontend build; failures return nonzero; no provider credentials
  or host runtimes needed. Full bounded sequence: `docs/DELIVERY.md#t021--make-checks-and-local-startup-trustworthy`.
- **Evidence:** Audit baseline in docs/audit/2026-10-19-checks.txt. Not started.
- **Next:** T01/T04 real pose.

## T03 — Ingestion  ·  status: todo  ·  date: 17 Oct  ·  FR01, FR02, FR03
## T04 — Pose adapter  ·  status: todo  ·  date: 17–18 Oct  ·  FR04
## T05 — First exercise engine (lat pulldown, D005) · status: todo · FR05, FR06, FR07
## T06 — References  ·  status: todo  ·  date: 20 Oct  ·  FR07, FR11
## T07 — Scoring  ·  status: todo  ·  date: 20–21 Oct  ·  FR07, FR08
## T08 — Jobs & cloud  ·  status: todo  ·  date: 21–22 Oct  ·  FR03, FR12
### T08.1 — Local durable queue/lifecycle · status: todo · FR03, FR12
- Build with T03 before the first browser analysis; cloud deployment remains later.
- Acceptance: persistent job/status, lease/restart safety, cancellation/deletion and
  private artifact access. Steps and files: docs/DELIVERY.md T03/T08.1.
## T09 — Coaching  ·  status: todo  ·  date: 22 Oct  ·  FR09
## T10 — Evidence  ·  status: todo  ·  date: 23 Oct  ·  FR11 (P1)
## T11 — X Ray UI  ·  status: todo  ·  date: 23–25 Oct  ·  FR10
### T11.1 — Real measurements inspector · status: todo · FR01, FR02, FR03, FR10, FR12
- Upload/status/video/2D/estimated-3D/rep inspection using real pipeline output.
- Explicit missing score/coaching states; intermediate milestone, not full MVP acceptance.
### T11.2 — Reference/score/coaching inspector · status: todo · FR09, FR10, FR11, FR12
- Complete reference overlay, phase mapping, score breakdown, sources and limitations.
## T12 — Other exercises  ·  status: todo  ·  date: 25–26 Oct  ·  FR06
## T13 — Evaluation  ·  status: todo  ·  date: 27–28 Oct
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

## Immediate next action
Finish the T16 audit handoff, then claim **T02.1**. No more scaffold review loop.
After its checks work, implement **T01/T04** on a documented lat-pulldown segment.
Every remaining task's steps, files, dependencies and acceptance are in docs/DELIVERY.md.
Additional user clips are analysis inputs, not approved references. Budget caps and a
reviewed reference remain open; neither prevents offline baseline and pose work.
