# Motion X Ray — delivery workflow

Updated 21 October 2026, Malaysia time. Goal confirmed by the product owner:
**a usable personal training MVP**, with Codex leading implementation and other
agents, including Kiro, supporting bounded tasks and reviews. Kiro's previous editing
workflow is paused. This plan does not claim the MVP is built.

## Start here

Read `AUDIT-2026-10-19.md` for the evidence baseline and `../TASKS.md` for current task
status. Read the archived full `SPECIFICATION-v2.0.md` for detailed formulas and UI
behavior; accepted decisions D001–D014 override or clarify its earlier choices.

Latest accepted slice: T08.1b.3/T08.1c.1 worker daemon and authenticated lifecycle/
report API. See `audit/T08.1b.3-lifecycle.md`. Results remain pose-only.

## Priority override — 22 October 2026

User prioritizes the core measurement and reviewed-technique comparison first.
Run T05 -> T06 -> T07 comparison validation before more infrastructure/UI work.
Hold artifact streaming, physical cleanup, browser integration, hosting, coaching
and exercise expansion. Retain existing infrastructure. This order supersedes older
"Next" instructions below; no new paid batch is authorized by this document alone.

1. **T05.1 definitions and labels:** specify observable lat-pulldown quantities,
   anatomical side and view/visibility eligibility, coordinate conventions and units.
   Define separate segmentation calibration. Prepare independent timestamped manual
   rep/phase/occlusion labels and an angle-check protocol; do not tune labels to output.
2. **T05.2 measurement proof:** implement valid-span geometry/filtering and complete
   cycle detection; report visible-side ROM, torso lean and original-time phase duration
   with coverage and explicit unavailable reasons. Compare against labels and known
   geometry. Freeze versioned configuration before held-out evaluation.
3. **T06.1 reference sourcing/review (parallel with T05):** identify a matching variant
   and camera view; record source authority and permission separately from technique
   reviewer approval. Existing user sets remain analysis inputs. Public availability
   alone is not reuse permission or technique approval.
4. **T06.2 reference artifact:** run authorized footage through the same pipeline,
   review selected reps, record immutable hashes/version/reviewer, and select a
   deterministic representative. Record evidence for tolerances; invent none.
5. **T07.1 comparison proof:** align compatible complete reps by phase using shared
   multivariate paths; retain source timestamps, component deviations, coverage and
   unwarped tempo. Validate numerical alignment before aggregating a score. Missing
   approval or required quantities produces explicit unavailable comparisons/scores.
6. **T07.2 acceptance:** evaluate frozen settings on separate held-out sets; report
   rep/boundary errors, angle agreement, comparison behavior and sensitivity. Collect
   additional footage if the existing view or sample size cannot support a claim.
   A reviewer checks whether reported deviations match visible movement. Only then
   resume downstream UI/coaching and widen exercise coverage.

First deliverable: an offline evidence report with labelled rep intervals, measured
quantities, reference provenance/eligibility and timestamped differences. It must
demonstrate observable movement comparison; a polished UI or plausible score is
insufficient. Accurate 3D depth, muscle activation and universal technique correctness
are outside the evidence available from one ordinary video.

The dependency order is:

```text
T02.1 executable checks
  -> T01/T04 real pose feasibility
  -> T03 + T08.1 ingestion and durable jobs
  -> T05 first exercise measurements
  -> T11.1 real video/overlay/rep inspector
  -> T06 + T07 reviewed references and deterministic scoring
  -> T09 runtime Nemotron coaching + T11.2 reference/3D results
  -> T12 remaining specified exercises
  -> T13 evaluation -> T14 usable release -> T15 optional hackathon submission

T01b/T10 evidence hardening supports T06/T09; it does not block real pose extraction.
T16 audit and T18/T19 source research are complete; they do not prove video analysis.
```

T01 and T04 share implementation: implement the real adapter once, use a small clip to
prove it, then harden it. Do not write a throwaway alternate pipeline. Likewise, a
simple persistent queue is an early requirement; cloud deployment is a later concern.

Development allocation is recorded in [TOKEN-BUDGET.md](TOKEN-BUDGET.md) and its
machine-readable ledger. The user permits 100k cumulative tokens per bounded task
with justified heavier allocations. T21.1 improves streaming/usage handling before
resuming T04; it does not reopen product scope or authorize runtime coaching spend.
Historical small output caps are superseded by the task-based allocation policy.

**20 October checkpoint:** T04's three local pose components now pass 131 tests and
real ten-second clip diagnostics. T01 runtime structured coaching is still open.
T21.1 generic helper drafts failed review/deadlines and were deferred so they did not
replace T04; direct workers remained sequential, manually reserved/accounted and
reviewed before integration. Usage and timeout reservations are recorded in
`development-usage-2026-10-20.json`. Next is T03/T08.1, then T05. Do not repeat the
generic tooling loop or treat the diagnostic as the finished product viewer.

For the next run, follow the Nebius-led, light-Codex execution policy in `../AGENTS.md`:
delegate implementation, focused repairs and first-pass review; keep Codex dispatch,
verification and integration concise. This preference does not start another paid batch.

**Next-run checkpoint (20 October):** T08.1a internal SQLite store is delivered with
81 new cases; all 212 Python tests, lint, types and schema-drift checks pass. Durable
metadata/claims/fencing/tombstones are implemented; HTTP session ownership, ingestion,
physical cleanup and real worker integration remain pending. See
`audit/T08.1a-durable-store.md`. Continue T03, then T08.1b; do not recreate the store.

**21 October checkpoint:** T03a private HTTP uploads/session ownership are delivered.
Real Squat.MOV passes upload/hash/metadata/restart checks; unauthorized access and
invalid/over-limit uploads fail clearly. All 341 Python tests and web checks pass.
See `audit/T03a-private-upload.md`. Next T03b/T08.1b connects proxy/PTS mapping, jobs,
the real pose worker and authorized artifacts/cleanup. Original media is not served.
The user permits independent Nebius tasks in parallel, within existing caps, with one
integrating writer. Preserve existing store and ingestion code rather than redrafting.

**Later21 October checkpoint:** Standalone T03b proxy/timestamp mapping is accepted:
real Squat.MOV gives427 frames with actual source/proxy PTS;369 Python tests pass.
T08.1b delegated worker is blocked after99,574/100k task tokens without an accepted
implementation. HTTP/retention drafts remain private and unintegrated. Stop repeating
this generation route and revise the worker approach; no large Codex fallback is implied.
See `audit/T03b-proxy-checkpoint.md` for evidence and a smaller next acceptance packet.

**Parent-only recovery checkpoint (21 October):** T08.1b.1 also remains blocked.
The parent draft passed lint/types, but generated subprocess tests failed real Store
contracts. Five calls79,431 reported tokens (conservative USD0.309477) produced no
accepted component. No product source remains from this attempt. Read
`audit/T08.1b.1-parent-supervisor.md`; next prove a minimal real-Store fixture before
expanding race coverage. Do not repeat the full-suite generation loop or start the
child/lifecycle consumers before parent acceptance.

**Resumed parent accepted (21 October):** T08.1b.1 now passes20 real-Store/subprocess
cases and the full389-test Python suite, lint and types. It supersedes the preceding
blocked parent status; failed usage is retained. The user raised the cumulative task
ceiling to200k; same-task usage is120,986 including the prior79,431. Five resumed calls
used41,555 tokens (conservative USD0.120724). See
`audit/T08.1b.1-resumed-supervisor.md`. Next T08.1b.2 connects real proxy/pose artifacts;
the worker entrypoint, lifecycle routes and physical retention remain pending.

## Working rules and agent roles

**T08.1b.2 accepted (21 October):** The internal supervisor-to-real-child flow now
publishes validated pose-only artifacts on an owned lat excerpt and the full squat
clip.403 Python tests, lint and types pass; six coding calls45,721 tokens (conservative
USD0.143597), no runtime LLM/Tavily. See `audit/T08.1b.2-real-pose-child.md`.
Next T08.1b.3 worker daemon/shutdown, T08.1c owner-scoped lifecycle/artifact routes
and T08.1d retention. Public/browser workflow and movement measurements remain open.

- **Codex lead:** owns the active task, shared checkout, integration, contract/config
  review, checks and commits. Per the 20 October instruction, delegate substantive
  coding drafts through authorized Nebius calls to conserve Codex credits. Use no more
  than 3–4 tasks per batch; report results before continuing. One writer integrates.
- **Subagents:** independently review or research a bounded question and return
  file/line evidence. Implementation delegation uses isolated files/checkouts with
  explicit ownership; the lead integrates and verifies the result.
- **External coding calls:** explicit generation/token/retry/time caps; source-only
  context, never credentials or private video. Review returned file scope and code before
  application. Record failed/truncated calls and unknown billing honestly. Catalog access
  is not generation proof. Do not silently move failed external work onto Codex.
- **Kiro:** initially a second reviewer of a concrete diff or proposed algorithm.
  Use a fresh non-interactive session, supply the task and evidence, and grant only
  the tools needed. Do not resume the old scaffold workflow automatically. A Kiro
  review is an opinion, not a test pass or evidence of product runtime inference.
- **Product owner:** supplies consented test clips, identifies intended variants/views,
  decides disputed scope, approves reference use and hosting/provider budgets.
- **Reference reviewer:** reviews proposed trajectories and metric rules. Owning a
  clip permits use; it does not by itself validate the technique or tolerances.

Before a writer starts: inspect git status, claim a task, list touched files and the
acceptance check. Preserve the existing Tavily changes. Commit them only after review
and checks, separately from unrelated work. Do not stage the entire checkout blindly.

Use a targeted review after a working increment, not a planner/coder/reviewer loop for
every scaffold file. If the same tool failure repeats, diagnose it in a fresh execution
session and report the blocker. Do not let a failed terminal consume hours of retries.
Send a progress update at meaningful checkpoints, including a stalled check.

## Work packages

Source-level reuse recommendations and implementation amendments are mapped to these
packages in [T19 integration review](INTEGRATION-REVIEW-2026-10-20.md). These are proposed
methods and acceptance checks, not installed dependencies or measured performance.
Keep the dependency order below; conditional upstream experiments do not block the
first real MediaPipe artifact.

### T02.1 — Make checks and local startup trustworthy

**FRs:** FR01–FR12 infrastructure. **Depends on:** audit only.

1. Correct the invalid contract configuration; retain explicit rejection of non-finite
   measurements. Fix `FakeLLMProvider`'s enum member. Add meaningful contract tests
   for null/reason consistency, temporal ordering and score/coverage bounds.
2. Resolve the `tests/contracts` versus installed `contracts` import collision without
   relying on manual developer shell state. Choose a checked pytest import layout.
3. Fix the 121 baseline Ruff issues and four mypy failures. Correct module docstring /
   future-import ordering rather than suppressing all E402 findings. Handle optional
   SDK typing explicitly; use the provider protocol for selected implementations.
4. Add a pinned test image/service under `infra/` with all first-party packages, dev
   tools and tests mounted/copied. Make `scripts/test.sh` execute checks and propagate
   failures. Make setup/dev scripts execute their advertised actions. Guard unfinished
   analyze/evaluate/cleanup commands with a clear nonzero exit until implemented.
5. Lock direct/transitive dependencies for each actual environment, including the
   OpenAI/httpx pairing and pose image. Add the selected extras only to the image that
   uses them. Pin build dependencies and base-image revisions/digests as appropriate.
6. Patch the vulnerable Next.js version based on current upstream advisories; verify
   the selected supported release rather than assuming an old minimum fix is current.
   Use a committed frontend lockfile and frozen installs in CI.
7. Give local services explicit localhost binding and decide the web `/api` routing
   path. Add smoke checks of web-to-API connectivity, not just separate health checks.

**Files:** contracts/base and validators, fake LLM, pytest/tool configuration,
pyprojects/lockfiles, `infra/`, `scripts/`, CI, web package/config, operations runbook.
**Pass:** documented container command runs imports, Ruff, mypy, unit/contract tests,
frontend type-check and build; a deliberately failing test produces a nonzero exit.
Fresh-clone paths work. No paid calls or host runtimes. Record baseline and new counts.
**Next:** T01/T04. Do not wait for perfect application architecture to start pose proof.

### T01 + T04 — Prove real pose on the existing lat pulldown

**FRs:** FR04, FR12. **Depends on:** T02.1 runnable environment.

1. Build the worker image for the actual Apple Silicon Docker platform. The pinned
   MediaPipe distribution has an aarch64/cp312 wheel advertised; import and dependency
   compatibility still need verification. Pin a checkpoint revision/checksum and terms.
2. Implement lazy MediaPipe inference with decoded presentation timestamps, canonical
   joint names and documented coordinate transforms. Keep source/proxy timing maps.
3. Start with a clearly identified 10–20 second segment of the 55.111667 second clip.
   Record the offset; do not silently raise the 30-second product limit or pretend the
   whole clip passed ingestion. Keep inference samples at a recorded target of 30 Hz.
4. Inspect anatomical left/right, visible-side selection and body tracking. A background
   person is noted in prior history; verify tracking rather than assuming largest/first
   detection is stable. Suppress unreliable far-arm/3D measurements.
5. Persist a real pose artifact and render a simple synchronized 2D preview plus a
   minimal rotatable estimated-3D diagnostic. Check known-geometry transform fixtures.
6. Record hardware/image/model/config IDs, usable coverage, cold/warm times, peak memory,
   artifact size and known limitations. Capture pass/fail in a new decision entry.
7. Separately run one authorized, bounded Token Factory structured-coaching smoke after
   dependency fixes. Confirm exact model ID and record sanitized usage/latency. A model
   listing or `ok` response is not structured coaching acceptance.

**Files:** pose provider, worker dependencies, pose smoke entrypoint, small authorized
fixture manifest, coordinate tests, feasibility report, DECISIONS.
**Pass:** actual timestamped artifacts and synchronized playback on the real clip;
no fabricated frames. Provider failure yields a useful error. Nemotron outcome is
recorded independently; a provider outage does not erase successful pose evidence.
**Next:** T03/T08.1 and T05. If pose fails, isolate the cause before scoring/UI expansion.

**T19 integration TODOs:** Add a validated artifact-reader boundary and aspect-correct
2D transform fixtures. Use only current observations if subject association is needed.
On a measured baseline failure, compare one isolated Sports2D/rtmlib configuration on
the same segment; add Norfair only for a demonstrated association gap. Pin source/model
terms and record lost capabilities; 2D-only output does not satisfy the 3D profiles.

### T03 + T08.1 — Private upload and one durable analysis job

**FRs:** FR01, FR02, FR03, FR12. **Depends on:** T02.1; real pose used for acceptance.

1. Define checked request/response models in contracts; use them in route annotations /
   response models. Generate OpenAPI, frontend types and a schema-drift check.
2. Implement secure anonymous session ownership and mutation protection; no account
   system needed. Store asset/job metadata with migrations in persistent SQLite.
3. Accept supported uploaded bytes only. Check consent, size and actual ffprobe metadata,
   duration/rotation/codecs. Make an audio-free proxy and a timestamp map. Bound decoding.
4. Persist before queueing; use an atomic lease, heartbeat and stage checkpoint. Keep
   transactions short. Run CPU/ML work in the worker process, not the HTTP request.
5. Implement state polling, result/artifact access, cancellation and deletion. Recheck
   lease/cancel/deletion before publishing. Scope deduplication/idempotency to owner.
6. Make cleanup and retention real: separate raw/pose versus report TTLs, revoke access
   immediately on deletion, prevent a cancelled/deleted job recreating artifacts.

**Files:** API routes/services, storage/migrations, job queue, worker, contracts, proxy
utilities, `cleanup.py`, integration tests, Compose mounts/settings, API/operations docs.
**Pass:** upload -> durable queued/running job -> real pose result -> authorized playback;
refresh/restart preserves status; cross-session access is denied; cancel/delete/restart
races tested. Invalid or over-limit media fails clearly. Fake providers only in tests.
**Next:** T05/T11.1. Cloud services remain out of the critical path until local flow works.

### T05 — First real lat-pulldown measurements

**FRs:** FR05, FR06, FR07 (specification §7–8 supplies metric obligations).
**Depends on:** canonical pose artifacts from T04.

1. Specify observable lat-pulldown metric definitions and phase conventions, including
   shoulder_drive's geometric definition. Do not infer muscle engagement from joints.
   Put thresholds, joint subsets, smoothing, gap limits and versions in configuration.
2. Implement geometry, contiguous valid-sample filtering and the low/high/dwell state
   machine. Preserve partial/uncertain edge segments; do not create turnarounds from
   interpolation or normalize each tiny movement into a full rep.
3. Compute visible-side ROM, torso lean and unwarped phase times with units and quality
   coverage. Return null plus reasons for missing/unsupported quantities. Trajectory
   error remains unavailable until a compatible reference exists.
4. Hand-label the test segment's count/boundaries/occlusion and compare output. Save
   deterministic artifact regression fixtures; collect additional held-out sets later.

**Files:** movement package, versioned lat-pulldown config, metric contracts if needed,
unit/regression tests, fixture/annotation manifests, EXERCISES/EVALUATION.
**Pass:** actual rep intervals and measured quantities on real pose; known geometry,
standing-still, noise, gaps, plateaus and partial cycles tested. Reruns match on identical
artifacts/config. One development clip is not a general accuracy claim.
**Next:** T11.1, then T06/T07.

**T19 integration TODOs:** Adapt Sports2D geometry/filtering and Good-GYM hysteresis
concepts without importing full pipelines. Introduce typed timestamp/mask/side/config
context for `smooth_series` and `compute_metrics`; define artifact resolution explicitly.
Separate segmentation calibration from score-reference approval. If excursion calibration
is unavailable, expose raw angles/uncertain candidates rather than inventing bounds.
Require return completion and processing-speed invariance; suppress occluded-side values.

### T11.1 — First usable measurements report

**FRs:** FR01, FR02, FR03, FR10, FR12. **Depends on:** T03/T08.1/T05.

Build upload/preview, exercise/view selection, real processing states, video with 2D
overlay and a shared rep timeline. Add recording with consent and camera-denied upload
fallback. Rep selection seeks playback and shows measured values, units and quality
reasons. Use one video clock; test seek/speed/loop behavior. Implement basic rotatable
estimated-3D inspection from actual artifacts. Preserve video if WebGL fails.

**Files:** web routes/components, generated client types, artifact route, browser checks.
**Pass:** a user can upload a supported set and inspect measured reps without a developer
script. No reference means explicitly unavailable score; no technique advice invented.
This is an intermediate milestone, not a silent reduction of the full MVP.
**Next:** T06/T07, T09/T11.2.

### T01b + T10 — Complete and constrain evidence discovery

**FRs:** FR06, FR11. **Depends on:** T02.1. Supports reference/coaching work.

Preserve and review the unfinished Tavily diff. Add bounded async execution/timeouts,
operator authentication, rate/budget limits, domain-boundary matching, defensive URL
validation and post-search count/allowlist enforcement. Fail closed for unknown provider
names. Do not expose raw provider exceptions. Include the search extra in the runtime
that selects Tavily; lazy import alone does not make live execution work.

Persist draft sources separately from approved claims/profiles. Cached reads must filter
approved status and exercise/variant, validate full records, reject malformed/unrelated
records and keep review provenance. Keep snippets/extracts available for actual review;
discovery leads alone are not a grounding library. Implement reviewed cached fallback.

**Pass:** offline API tests cover operator denial, fake live success/failure, deadlines,
limits, publisher spoofing, malformed/pending caches and no auto-approval. Separately,
one authorized search/extract yields persisted reviewable drafts with usage recorded.
**Next:** T06; useful runtime Tavily integration is independent of eligibility claims.

### T06 + T07 — Reviewed reference and explainable similarity

**FRs:** FR07, FR08, FR11. **Depends on:** T04/T05, suitable authorized reference.

1. Add authoritative/source/provenance and immutable reference version fields through
   a coordinated contract version change. Version actual payload schemas as well as
   package metadata; update generated consumers together.
2. Build references through the same pose/movement pipeline. Require compatible view,
   variant, provider and mapping. Preserve selected rep IDs, artifact hashes, rights and
   reviewer metadata. Separate permission from technique/range review.
3. Select a reviewed representative or deterministic medoid; never average unaligned
   cross-view paths. Record metric ranges/tolerances and rationale. Do not generate
   plausible defaults, especially the old scratch plan's keyed placeholder tolerances.
4. Implement fixed normalization, phase-aware banded DTW, alignment provenance, component
   formula, scalar subweights, required-component null policy and deterministic ties.
   Compute tempo before warping. Include per-rep and set ScoreBreakdown in the report.
5. Enforce D007 in scoring, result assembly and UI: experimental/unapproved/incompatible
   references cannot produce a displayed valid score, best/worst claims or hidden API
   values that appear valid. Missing components never improve a comparable score.

**Files:** reference/scoring/report contracts and exports, benchmarks/scoring packages,
reference builder, review flow, configs, unit/contract/integration fixtures, scoring docs.
**Pass:** owned and reviewed reference produces reproducible, explainable results;
experimental/unreviewed/missing references produce explicit null reasons end-to-end.
**Next:** T09/T11.2. If reference unavailable, keep measurements usable and seek a scope
decision before calling the full scored MVP complete.

**T19 integration TODOs:** T06 owns provenance/eligibility plus deterministic representative
selection; T07 owns typed `AlignmentResult` and a narrow DTAIDistance adapter. Verify shared
multivariate paths, per-phase anchors, library band/endpoint semantics and path-normalized
cost. Keep tempo unwarped, pin backend and preserve original index mappings. Contract
changes must include reference authority/hashes, refusal reasons, alignment artifacts and
per-rep/set breakdowns with generated consumers. Follow SCORING and DATA_MODEL checklists.

### T09 + T11.2 — Grounded coaching and complete X Ray inspection

**FRs:** FR09, FR10, FR11, FR12. **Depends on:** T05/T06/T07; T10 for technique advice.

Define CoachingInput and structured observations carrying existing rep/metric/source IDs.
Implement the real Nemotron adapter with time/budget bounds, explicit SDK retry settings,
input/prompt/model/reference cache keys and strict output validation. Reject unsupported
IDs/numbers/claims. On failure show measured results and unavailable coaching.

Finish rotatable 3D user/reference overlay, phase-to-time mapping, highlighted deviations,
paths, score breakdown, sources and limitations. Reference playback follows normalized
phase; user tempo follows real timestamps. Add responsive layout, keyboard/focus controls,
text equivalents and WebGL-failure handling.

**Pass:** application runtime calls the selected NVIDIA model through Token Factory and
returns validated coaching on real measured inputs; cache and injected failures verified.
Actual video/2D/3D/reps stay synchronized. Fake output never appears as a real result.
**Next:** T12/T13.

### T12 — Expand only through specified, evaluated exercises

**FRs:** FR04–FR10. **Depends on:** first end-to-end exercise passing its gates.

Add curl, squat and lateral raise by configuration plus genuinely required measurement
code; each needs authorized clips, supported-view validation, reviewed references and
held-out checks. Product owner will upload curl, squat and incline bench chest press sets.
The latter is **a candidate exercise, not an existing supported exercise**. Identify
incline/implement/bench setup, supported view, observable joints and complete-rep phase
rules; record an accepted scope decision before implementing or advertising support.
Do not replace one of the four accepted exercises implicitly.

**Pass:** each advertised exercise has its own evidence, confidence mask/config version,
reference/score coverage and browser result. A YAML file does not count as support.
**Next:** T13.

### T13 — Evaluation and real-user acceptance

**FRs:** FR01–FR12. **Depends on:** implemented advertised flows.

Freeze configs before held-out evaluation. Keep people/clips separate between tuning
and evaluation; annotate counts, boundaries and visibility. Report sample size, per-exercise
count error, boundary errors including missed/spurious reps, determinism, synchronization,
runtime and memory. Targets from specification §17 remain targets until measured.
Test desktop Chrome, Android Chrome and iOS Safari before declaring those supported.
For optional learned counters, choose exercise before inspecting ground-truth count;
do not repeat oracle selection from the reviewed PoseRAC evaluator. Do not use random
row splits as evidence of subject-independent performance. External skeleton fixtures
need rights/mapping review and cannot establish phone-video perception accuracy.
Exercise camera denial, long/invalid media, queue load, restarts, budget/timeouts, deleted
artifacts and broken WebGL. Record defects and known limitations explicitly.

**Pass:** repeatable evidence for every advertised requirement, no misleading scores or
data exposure, user completes their own supported set without developer intervention.
**Next:** T14.

### T14 — Operable personal MVP

**FRs:** FR01–FR12 deployment/operations. **Depends on:** T13, approved hosting budget.

Choose local-only personal use or a hosted single persistent machine based on the user's
access needs. Keep SQLite on local persistent disk, run API/worker privately behind HTTPS
and the same web origin, configure health/readiness/restart behavior, bounded queue/spend,
retention, restore and rollback. No GPU or new orchestration service is required by default.
If shared/public hosting is chosen, verify ownership, CSRF, TLS, rate limits and private
media access in that topology. Test a fresh clone/build and recovery from restart.

**Pass:** user can reliably access and use the actual app; setup, deletion, budget limits,
versions, model/data terms, troubleshooting and rollback are documented and demonstrated.
**Next:** T15 only if hackathon entry is still wanted; otherwise normal MVP iteration.

### T15 — Optional hackathon release/submission

The user's stated goal is the personal MVP; submission is a separate release choice.
If retained: official deadline is 31 October 2026 at 01:00 MYT (30 October 10:00 PDT).
Aim to finish on 30 October MYT rather than at the cutoff. This is not a promised build
schedule. Provide public licensed code, working demo/test build, English description,
public YouTube video under three minutes and clear runtime NVIDIA/Nebius evidence.
Check current official rules again and retain free judge access through judging.
Prepare materials locally; user controls final submission/publication and spending.

## Definition of a completed usable MVP

- A supported workout set can be captured/uploaded, analysed and inspected by its owner.
- Real pose, rep segmentation and observable metrics carry provenance and limitations.
- Compatible reviewed references support deterministic explainable similarity; unsuitable
  references and insufficient observations produce explicit nulls.
- The rotatable estimated-3D view and 2D overlay share video timing and rep selection.
- Nemotron coaching uses actual measured evidence and approved claims; failures preserve
  measured results. No fake/provider-fixture output is presented as live perception.
- Restart, cancel, delete, retention, ownership, spend limits and errors work in the
  selected deployment. Checks and evaluation results are reproducible from the repo.

## Outstanding inputs, not reasons to stop offline implementation

1. Upload additional user-set clips when available. Inspect actual variant/view/duration
   before assigning exercise support or accuracy claims.
2. Obtain a separate suitable reference and identify its reviewer/rules. User clips are
   currently analysis inputs, not approved standards.
3. Reconcile current balances and per-run controls: user reports $100 Nebius allowance,
   $70 operating ceiling and $30 backup, plus 8,000 separate Tavily credits. These are
   ceilings, not spend targets; hosting scope/budget remains undecided. See TOKEN-BUDGET.
4. Decide whether hackathon submission remains an additional goal; the personal MVP
   remains the primary finish line.

## Source checks

- [Official hackathon rules](https://nebiusglobalaihackathon.devpost.com/rules), checked
  19 Oct 2026: runtime NVIDIA/Nebius requirement and submission timing/materials.
- [MediaPipe Python guide](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker/python):
  timestamped VIDEO mode and pose/world outputs. Not evidence that this adapter works.
- [Next.js security advisory](https://nextjs.org/blog/security-update-2025-12-11): the
  pinned 14.2.15 App Router release requires patching; recheck latest fixes during T02.1.
