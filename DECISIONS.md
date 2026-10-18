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
  synchronized playback and stable body identity on a real curl clip. If world-landmark
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

## Open decisions (to close during implementation)

| Decision | Owner | Closure point |
| --- | --- | --- |
| Final pose provider, model revision, 3D capability | Implementer | Gate A (T01) |
| Valid camera profiles, confidence masks, supported variants | Implementer + reviewer | Before held-out testing |
| Reference rights, reviewer, metric tolerances | Product owner / reviewer | Before publishing scored profiles |
| Exact Nemotron ID, JSON behavior, endpoint, credits | Implementer | Gate A (T01) |
| Budget cap + retention implementation | Product owner + implementer | Before paid deployment |
| Score weights and experimental claims | Product owner / reviewer | Before config freeze |
