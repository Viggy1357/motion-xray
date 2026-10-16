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
