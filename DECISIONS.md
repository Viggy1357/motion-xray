# DECISIONS.md — design decision register

Every decision that changes scope, provider, or contract from the spec default is
recorded here with a date and rationale. Spec = Motion X Ray Product and Software
Specification v2.0 (15 Oct 2026).

---

## D001 — Token Factory alone satisfies the hackathon runtime requirement (no AI Cloud)

- **Date:** 2026-10-16
- **Status:** Accepted
- **Context:** Product owner does not currently have a Nebius AI Cloud account.
- **Decision:** The hackathon rule is satisfied by running on Nebius **Token Factory
  OR AI Cloud** plus using at least one NVIDIA open-source model. The deployed app's
  runtime Nemotron coaching call through Token Factory satisfies both. AI Cloud is
  therefore not required for eligibility.
- **Consequence:** No dependency on AI Cloud GPU for the required submission path.
- **Verification owed:** Confirm with a real Token Factory inference at Gate A (T01),
  and re-confirm the current official rules before submission.

## D002 — MediaPipe is the primary pose provider for this build; GEM-X is a stretch goal

- **Date:** 2026-10-16
- **Status:** Accepted (provisional, revisit at Gate A)
- **Context:** GEM-X is the spec's preferred video-to-3D provider but it is a GPU model,
  and the product owner has no cloud GPU entitlement. The host is Apple Silicon with no
  ML toolchain installed.
- **Decision:** Build the pose pipeline against **MediaPipe Pose Landmarker** as the
  primary provider (CPU-friendly, documented spec fallback, exposes world landmarks).
  Keep the `PoseProvider` contract provider-agnostic so GEM-X can be added later if GPU
  access appears. GEM-X is a documented stretch goal, not a P0 dependency.
- **Consequence (scope):** "True 3D from a dedicated GPU model" is replaced by
  MediaPipe's estimated 3D world landmarks. The 3D viewer requirement (FR10) is met
  with MediaPipe world landmarks, clearly labelled as estimated 3D. This is an explicit
  scope choice per the spec's contingency clause, not a silent satisfaction of the
  GEM-X P0 line.
- **Verification owed:** At Gate A, prove MediaPipe gives usable coordinates with
  synchronized playback and stable body identity on the lat-pulldown segment (D005
  supersedes the original curl-first input). If world-landmark
  quality is inadequate for the 3D overlay, record the reduced capability here.

## D003 — Host stays clean: all runtimes live in Docker containers

- **Date:** 2026-10-16
- **Status:** Accepted
- **Context:** Product owner requires that tests and builds do not affect the host macOS
  install. Host has no Node, uv, pnpm, Docker, and only Python 3.9.
- **Decision:** Containerize everything via Docker Compose (`infra/`). Python 3.12,
  Node, ML stack, and FFmpeg live only inside images. The host installs Docker Desktop
  and nothing else project-related. Kiro's command sandbox is also enabled for agent
  terminal actions.
- **Consequence:** `docker compose down -v` fully removes the runtime from the host.

## D004 — Start with the smallest NVIDIA Nemotron model on Token Factory

- **Date:** 2026-10-16
- **Status:** Accepted (provisional)
- **Context:** Limited Token Factory credits; coaching is short structured text.
- **Decision:** Begin with the smallest account-visible NVIDIA Nemotron model and only
  escalate if measured coaching quality warrants it. Cache coaching by input hash so
  identical analyses never re-spend tokens.
- **Verification owed:** Confirm the exact model ID from the account catalog at Gate A.

## D005 — Add cable lat pulldown as a 4th exercise; it is the first pipeline test

- **Date:** 2026-10-18
- **Status:** Accepted
- **Context:** Product owner has an authorized lat pulldown clip and wants it as the
  first end-to-end pipeline test. The spec's launch set is curl/raise/squat and lists
  cable variations as unsupported "until separately specified"; this is that explicit
  specification.
- **Decision:** Add `lat_pulldown` (`data/exercise_specs/lat_pulldown.yaml`,
  variant `cable_seated_bilateral`) as a supported exercise. Supported view is
  `diagonal_side` based on the first clip (seated machine, filmed ~3/4 side). Scored
  components: elbow_rom, shoulder_drive, torso_lean, phase_tempo, trajectory_error
  (weights sum to 1.0). `bilateral_difference` is informational-only at this view
  because the far arm is occluded.
- **Consequence:** Lat pulldown is tracked and measured first. A frontal lat pulldown
  profile, if ever needed, requires its own view validation and weights.
- **Verification owed:** Confirm metrics on the real clip at the feasibility spike;
  freeze the view/mask once validated.

## D006 — Solo-user scope: curated reference only; trainer/personal-best deferred to P1

- **Date:** 2026-10-18
- **Status:** Accepted
- **Context:** The target user trains alone with no personal trainer present — that is
  the product's reason to exist. "Trainer reference" and "personal best" are optional
  reference *sources*, not a requirement for a coach to be present.
- **Decision:** Current scope ships only the **curated** reference type (a known-good
  comparison trajectory that ships with the app). The user never needs a second person.
  The "operator/reviewer" role is a BUILD-TIME role (the developer approving a
  reference), not an end-user-facing feature. Trainer-provided and personal-best
  references stay P1 and are out of current scope.
- **Consequence:** Reference UI/flows for trainer/personal-best are deferred; the
  `ReferenceProfile` contract still carries the `type` field so P1 can add them without
  a schema break.

## D007 — Experimental references from third-party video: dev-only, flagged, never shipped

- **Date:** 2026-10-18
- **Status:** Accepted (guarded)
- **22 October user override:** The owner explicitly asks Codex to retrieve the three
  shortlisted demos as needed and prepare a diagnostic ranking/rep/score review.
  Automated retrieval in isolated local development containers is authorized for
  this experiment; the older owner-only manual-download restriction below is
  superseded for these clips. No downloader enters the product or CI. This grants
  task authorization, not third-party redistribution rights or technique approval.
  Record unavailable sources and retain experimental/non-authoritative status.
- **Context:** Product owner wants to test the full pipeline using reference clips
  sourced from public technique videos. Tavily extracts TEXT/pages, not video files,
  and cannot certify a video or grant platform access. Public social clips carry reuse
  rights that saving "only the skeleton" does NOT remove.
- **Decision — split evidence by type:**
  - **Tavily (automated, legitimate):** discovers + ranks CREDIBLE technique sources
    and candidate video URLs per exercise, and extracts guidance TEXT. This text feeds
    metric tolerance *ranges* and coaching claims, with operator review. Satisfies the
    runtime-search path (and the Tavily bonus).
  - **Download (manual, product owner):** the product owner personally downloads the
    clips they judge credible/usable from Tavily's shortlist into `data/demo/`
    (gitignored). No automated video scraping; no `yt-dlp` in the product.
  - **Reference build:** owned/downloaded clips run through the SAME MediaPipe pipeline
    to build a trajectory.
- **Guardrails:** References built from third-party clips are flagged
  `source=experimental`, `authoritative=false`, and MUST NOT (a) appear in the public
  submission repo/demo, or (b) produce a displayed overall score presented as valid.
  Accuracy limitation is real and stated: do NOT average unaligned cross-view
  trajectories into a single "normalized" reference. The public submission uses only
  an owned/authorized reference, or ships measurements-only with no overall score.
- **Verification owed:** Enforce the `authoritative` flag in scoring + UI before any
  public build; confirm no experimental assets are committed.

---

## D008 — Executable baseline and contract version 0.2.0

- **Date:** 19 Oct 2026; **Status:** Accepted implementation hardening under T02.1.
- **Context:** Imports failed with an invalid Pydantic configuration; test-package
  shadowing and placeholder scripts concealed the absence of executable checks.
- **Decision:** Reject non-finite values at validation, enforce missing-metric reasons,
  ordered rep intervals and score/coverage bounds. Bump contracts to 0.2.0 and migrate
  versioned pose/report payloads, fake provider and fixtures together. Generate actual
  OpenAPI/JSON schemas and TypeScript types; check generated artifacts for drift.
- **Execution:** Separate offline Compose checks have no runtime credentials, state
  volumes or network. Hashed Python locks and a frozen pnpm lockfile pin dependencies;
  compatible OpenAI/httpx remain 1.51.0/0.27.2. Python and Node bases are digest-pinned.
  Next.js moves from 14.2.15 to supported Maintenance LTS 15.5.28 with React 19.3.0,
  following the 14 Oct 2026 advisory; this is security maintenance of the empty scaffold.
- **Evidence policy:** Paused Kiro evidence work is reviewed/adopted as unfinished T01b/T10
  code. Live refresh now fails closed with 503 until operator/spend controls exist.
  Cached discovery is not an approved technique library and cannot justify scoring.
- **Limits:** No model, exercise threshold or scoring weight changed. Successful builds
  and MediaPipe import are environment proof only; real clip inference remains T01/T04.
- **Source:** https://nextjs.org/blog/nextjs-security-update-october-14-2026

## D009 — Selective upstream reuse with conditional adoption

- **Date:** 20 Oct 2026; **Status:** Accepted direction, implementation pending.
- **Basis:** T18 screening and T19 source review; user requested project-wide updates.
- **Decision:** Retain MediaPipe and the existing pipeline. Adapt Sports2D geometry/
  filtering and Good-GYM hysteresis patterns behind canonical contracts. Evaluate
  DTAIDistance as the T07 numerical kernel, with our phase, quality and scoring wrapper.
  Norfair identity association and rtmlib inference are conditional on a measured T04
  failure, not parallel default stacks. AIFit informs methodology; restricted assets
  are not adopted. ALEX/PoseRAC learned models remain optional later evaluators.
- **Promotion gate:** Exact source/model revisions and applicable terms; isolated
  container dependency resolution; same-input comparison; capability/coordinate tests;
  relevant deterministic fixtures; recorded runtime/quality evidence before adoption.
- **Limits:** No dependency, runtime provider, threshold or score weight changed by
  this decision. Code, weights, body models and data require separate rights checks.
- **Evidence:** docs/INTEGRATION-REVIEW-2026-10-20.md.

## D010 — Measurement and comparison semantics for upstream integration

- **Date:** 20 Oct 2026; **Status:** Accepted requirements; implementation pending.
- **Decision:** Use original presentation timestamps, actual matched observations and
  explicit gap masks. No predicted tracker positions, static depth exports or long-gap
  fills as measured anatomy. Complete reps need full return; preserve partial/uncertain
  cycles. Define observable geometry rather than activation or spinal-curvature claims.
- **Comparison:** Use one shared multivariate path within established phases, explicit
  feature scales/band semantics and path-normalized cost. Keep tempo unwarped and retain
  original index/time mappings. Pin a backend; no silent numerical fallback.
- **Contracts:** Typed numerical context/alignment results and immutable reference
  provenance are T04–T07 work. Public changes require schema/consumer migration together.
  Segmentation calibration and score-reference approval are distinct review obligations.
- **Consequence:** Complete 3D profiles stay incompatible with 2D-only providers.
  Missing calibration/reference/measurements yield unavailable outputs, not defaults.
  These requirements clarify intent; formulas, thresholds and weights remain unchanged.

## D011 — Task-based development token allocation

- **Date:** 20 Oct 2026; **Status:** Accepted user authorization; forecast provisional.
- **Decision:** Allow up to 100k cumulative input+completion tokens per development task,
  with reasoned increases for heavier tasks. Allocate enough request completion for
  reasoning plus final code, within verified model limits. Stream and preserve accounting
  even on failed drafts. Codex coordinates; Nebius performs substantive coding/review.
- **21 October update:** User raises the bounded task allowance to200k. Preserve prior
  same-task usage when resuming, keep USD70 active/USD30 protected backup and no hidden
  retries. More tokens do not replace smaller executable acceptance increments.
- **Forecast:** 30 bounded tasks, 2.47M development tokens plus 25% reserve, 3.0875M total.
  Reforecast after three accepted tasks. Estimates are not measured usage or an account
  spend cap. No successful implementation baseline exists yet.
- **Separation:** This supersedes tiny development draft caps, not runtime coaching
  controls or D004. Per-request limits, retries and environment controls remain explicit.
- **Sources:** docs/TOKEN-BUDGET.md; docs/development-budget.json. Published rates and
  actual usage must be reconciled; missing historic usage remains unknown.

## D012 — Resource ceilings and efficient delegation

- **Date:** 20 Oct 2026; **Status:** Accepted user instruction.
- **Resources:** User reports $100 Nebius allowance; use up to $70 for active work and
  retain $30 backup. Tavily has a separate 8,000-credit allowance. Balances unverified.
- **Decision:** Ceilings are not consumption targets. Expand D011 task token allocations
  only with justified need; measure cost per accepted/tested change, not cheap tokens.
  Establish one functioning worker before independent parallel work; no duplicate coding,
  unnecessary multi-model comparisons or automatic review/search loops. Keep batches small.
- **Accounting:** Nebius development and bounded runtime validation share $70; preserve
  backup pending user activation. Separate Tavily credit ledger, cache-first/deduplicated
  targeted refreshes. Include failed costs/in-flight commitments and reconcile unknowns.
- **Limits:** No new paid call, live-route activation, provider-side cap, infrastructure
  purchase or change to product scope occurs in this documentation update.

## D013 — Retain MediaPipe after the first real local pose validation

- **Date:** 20 Oct 2026; **Status:** Local adapter accepted with explicit limitations.
- **Evidence:** T04 batch C; docs/audit/T04-resumed-pose-batch.md and sanitized result
  JSON. Pinned SDK0.10.14, Full float16/1 checkpoint SHA256
  `5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1`.
- **Outcome:** Source10–20s lat pulldown yields300 frames at29.96Hz; cold9.8039s,
  second-run8.913s, identical artifacts on this CPU/runtime. Real artifacts also exist
  for curl, squat and incline-press diagnostic segments; this adds no scoring support.
- **Semantics:** Preserve original PTS/source indices and qualify estimated XYZ.
  Microsecond-formatted PTS need1us sampling-comparison tolerance; record sampling-v1
  in provenance. No exercise threshold/scoring weight changed. Missing/multiple poses
  remain gaps, not predicted anatomy. Physical scale and verified identity stay false.
- **Limits:** Foreground alignment inspected at start/middle/end and during playback;
  this is not general identity tracking or 3D accuracy proof. Far arm is poorly covered.
  Squat has24/300 all-invalid samples. Metrics, reviewed reference and scores remain
  pending. T01 runtime structured Nemotron remains unvalidated; coding calls are separate.
- **Next:** Keep MediaPipe primary. T03/T08.1/T05 proceed; D009 conditional alternatives
  remain gated on a measured need, not installed by this result.

## D014 — Shared pose processing version and safe lifecycle projection

- **Date:** 21 October 2026. **Status:** accepted for local pose-only jobs.
- **Decision:** API and worker hash a canonical recipe containing pipeline, checkpoint
  SHA256, mapping, sample rate and visibility threshold. Worker startup verifies the
  actual checkpoint; mismatched queued versions fail before child launch.
- **Public contract:** Add AnalysisCreateRequest and AnalysisStatus without changing
  existing artifact schema0.2.0. Status adds explicit pose_only scope and always nulls
  internal lease_owner/result_key. Report access requires the owning signed session,
  live report retention, and a validated committed manifest. Raw expiry does not by
  itself expire an already-published report. Deletion revokes access immediately;
  physical removal and private artifact streaming remain separate tasks.
- **Evidence:** T08.1b.3/T08.1c.1 audit; generated OpenAPI/TS and contract tests.

## Remaining implementation choices

| Decision | Owner | Closure point |
| --- | --- | --- |
| Final pose provider, model revision, 3D capability | Implementer | Gate A (T01) |
| Valid camera profiles, confidence masks, supported variants | Implementer + reviewer | Before held-out testing |
| Visible-side policy, phase calibration and shoulder_drive geometry | Implementer + reviewer | T05 before scored metric/config freeze |
| Typed signal/alignment contracts and provenance migration | Implementer | T04–T07 before exposing new payloads |
| Exact adopted upstream revisions, backend and model/data terms | Implementer | Before each D009 candidate is promoted |
| Reference rights, reviewer, metric tolerances | Product owner / reviewer | Before publishing scored profiles |
| Exact Nemotron ID, JSON behavior, endpoint, credits | Implementer | Gate A (T01) |
| Budget cap + retention implementation | Product owner + implementer | Before paid deployment |
| Score weights and experimental claims | Product owner / reviewer | Before config freeze |

## D015 — Freeze benchmark research; prioritise a functional hackathon prototype

- **Date:**22 October2026; **Status:** accepted owner scope direction; feature list
  and UI interaction choices remain discussion proposals.
- The owner asks to tie off steps4–7, leave benchmark assessment as-is, defer improved
  accuracy/additional measurements, and prioritise a functional Nebius hackathon app.
- The personal prototype may use transparent estimated reference comparisons and an
  observation-quality indicator. Coverage is not a calibrated probability of correct
  technique. Choosing an owner reviewer does not turn the baseline into clinical or
  qualified ground truth. This decision alone implements no confidence formula, score
  weight, threshold or tolerance; numeric configuration changes still need versions and
  fixtures. Preserve unavailable quantities rather than fill them with fake evidence.
- Existing descriptive baseline/conditional comparison engine is the checkpoint;
  deeper benchmark assessment no longer blocks product-flow work. Current public API
  remains pose-only until a coordinated product integration slice is implemented.
- Brainstorm rep counting, logs, routines, avatar/muscle visualisation and video
  library before implementing those features. Tiny external-camera capture is future
  scope, feeding the same clip/analysis boundary; no hardware build is started.
- Actual app use of an NVIDIA model through Nebius remains a submission requirement;
  development coding calls do not satisfy it. No paid hosting/publication implied.
- See `docs/HACKATHON-MVP-DIRECTION.md` and `docs/audit/T047-checkpoint.md`.
