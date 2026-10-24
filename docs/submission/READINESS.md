# Submission readiness — checked24 October2026

Sources: https://nebiusglobalaihackathon.devpost.com/rules and
https://nebiusglobalaihackathon.devpost.com/ . Live form fields not inspected.

Preparation is authorized. Repository visibility, new hosting spend, publication
of private footage and final submission remain owner-controlled. Routine
preparation, checks and updates to the existing private branch can proceed. All evidence below is grounded
in observed build artefacts in this repository; nothing is fabricated.

## 1. Official-rule requirement / status / evidence / remaining-action matrix

| # | Official requirement | Status | Evidence in repo | Remaining owner action |
|---|---|---|---|---|
| R1 | Working Nebius runtime + NVIDIA model call | Met (local dev only) | `docs/audit/HM057-HM06-delivery.md` — one real owned-lat set call: 1427 input / 38 output tokens, 1.103s, candidate IDs validated locally; `ALLOW_LIVE_COACHING=false` default in `.env.example` | Owner decides hosting path; no new runtime call made during this preparation |
| R2 | Public GitHub repo with licence + setup | Not ready | `LICENSE` present locally (MIT); remote default branch is `main`, currently PRIVATE; `README.md` setup commands verified in `docs/OPERATIONS.md` | Owner authorizes changing visibility or a separate sanitized public release; confirm licence detection on GitHub (currently Other) |
| R3 | Functioning demo / test build URL | Not ready | Local Docker stack only (`docker compose -f infra/compose.yaml up --build`); no hosted URL | Owner chooses free-tier hosting or hosted-app route; do not buy hosting in prep |
| R4 | English project description on Devpost | Draft only | `docs/submission/DEVPOST-DRAFT.md` (this pack) | Owner pastes into Devpost form fields manually |
| R5 | Public YouTube demo video UNDER 3 min | Not ready | `docs/submission/DEMO-SCRIPT.md` (2m40s script + capture checklist) | Owner records, edits, uploads; mark real-time waits visibly |
| R6 | Tools used feedback (NVIDIA / Nebius / Tavily) | Partial, honest | 14 Nebius dev calls + 1 runtime guard call documented in `HM057-HM06-delivery.md`; Tavily not used at runtime (cached provider default) | Owner writes first-hand feedback; no invented praise |
| R7 | Significant update statement (if pre-existing) | Needs owner confirmation | Original project start date not established; current branch `codex/hm-ux05-mockup-implementation` @ `64b7bc3` | Owner confirms original build start date and writes the statement |
| R8 | Free judge access through 15 Dec 2026 noon PST | Not ready | No hosted app yet; local Docker works for owner only | Owner stands up free-tier hosted instance or hosted-app route |
| R9 | Four criteria coverage (implementation / design / impact / idea) | Mapped | See §2 below | Owner reviews mapping before submit |
| R10 | Tavily award eligibility (functional Tavily call) | Not established | `SEARCH_PROVIDER=cached` default; current demonstrated app path uses cached evidence; no app-runtime Tavily proof in this assessment | Owner may opt in later; do not claim eligibility now |
| R11 | Deadline 30 Oct 10am PDT = 31 Oct 1am MYT | Tracked | This prep pack | Owner submits before deadline |
| R12 | Track recommendation: Best Apps and Agents | Recommended | App + grounded coaching agent pattern in `HM057-HM06-delivery.md` | Owner confirms track on Devpost |

## 2. Four-criteria mapping (equally weighted)

- **Implementation** — Containerised Docker stack (web + api + worker), 971
  Python tests recorded23Oct and54 browser fixture cases passing24Oct, deterministic movement
  reports for four exercises, signed-session API, durable SQLite coaching
  cache with atomic quotas. Evidence: `docs/audit/HM057-HM06-delivery.md`,
  `docs/audit/HM-UX09-delivery.md`.
- **Design** — Restrained 220ms cross-fade via native View Transitions,
  reduced-motion respected, segment thumbnails at measured start times,
  static Home athlete preserved. Evidence: `docs/design/HM-UX09-roadmap.md`,
  `docs/audit/HM-UX09-delivery.md`.
- **Impact** — Personal-training MVP for short workout clips; similarity-to-
  reference framing (not technique grading); grounded coaching with local
  allowlist of public summaries; no clinical or medical claims.
  Evidence: `docs/PRODUCT.md`, `HM057-HM06-delivery.md` §"Grounded coaching".
- **Idea** — Pose extraction → rep segmentation → exercise metrics →
  reference comparison → deterministic similarity → grounded Nemotron
  coaching, with explicit separation of measured signal coverage vs.
  accuracy. Evidence: `README.md` "Intended product (P0)",
  `docs/ANALYSIS-PROCESSING.md`.

## 3. Priority-ordered next steps (P0 demo / public repo / reproducible assets / runtime / demo video)

### P0 — Demo must work for a judge without the owner's paid key
1. Confirm hosted-app route OR free-tier hosting that exposes the existing
   Docker stack publicly. Judges must not need the owner's Nebius key.
2. If hosted-app route: ensure the hosted instance uses its own
   `NEBIUS_API_KEY` and `SESSION_SECRET`; do not embed owner secrets.
3. Local contributors continue to use their own `.env` per `.env.example`.

### P1 — Public repo
1. Owner confirms licence (MIT local; GitHub detection currently shows
   "Other" — verify after push).
2. Owner authorizes changing visibility or a separate sanitized public release of current branch.
3. Confirm `README.md` setup commands still match `docs/OPERATIONS.md`.

### P2 — Reproducible assets
1. Verify `./scripts/test.sh all` exits 0 on a fresh clone.
2. Verify `./scripts/check-browser.sh` exits 0 (54 cases).
3. Verify `./scripts/pose-smoke.sh --video demo/lat_pulldown.mp4 --start-s 10 --duration-s 10 --repeat`
   runs against the pinned local checkpoint (sha256 in `.env.example`).
4. Do NOT commit the model checkpoint blob; obtain from the pinned official model manifest.

### P3 — Runtime proof for demo video
1. Record one real `Generate coaching` interaction on an owned lat set.
2. Capture distinct cached-result replay (no second model call).
3. Redact any private frames before publishing.

### P4 — Demo video (UNDER 3 min, target 2m40s)
1. Follow `docs/submission/DEMO-SCRIPT.md` time table.
2. Mark real-time pipeline waits with visible "[real-time wait — edited]" cards.
3. Upload to public YouTube; do not mark unlisted unless owner decides.

## 4. Owner-controlled declarations (IRL city / registration / final submit)

- **IRL city**: owner to declare on Devpost profile; not asserted here.
- **Registration**: owner completes Devpost registration; this pack does not
  register on owner's behalf.
- **Final submit**: owner clicks Submit on Devpost. This pack prepares only.

## 5. Historical vs. current proof (do not conflate)

- **Historical (23 Oct 2026, owned lat set, local dev)**: real Nebius
  Nemotron call, 1427 input / 38 output tokens, 1.103s. See
  `HM057-HM06-delivery.md`. This is **not** current hosted validation.
- **Current (24 Oct 2026, branch `codex/hm-ux05-mockup-implementation`
  @ `64b7bc3`)**: 54 browser fixture cases pass; web typecheck + production
  build pass; no hosted runtime. See `HM-UX09-delivery.md`.
- **Not claimed**: clinical accuracy, technique grading, muscle-activation
  measurement, camera-derived injury risk, nutrition/recovery scoring.

## 6. Judge access — operational / cost guard

- Judges reach the app via the public URL the owner stands up.
- Hosted instance uses its own Nebius key; owner key is not exposed.
- Default `ALLOW_LIVE_COACHING=false`; owner flips to `true` on hosted env
  only after confirming quota headroom.
- Quota: 20 global reservations / UTC day, 4 per owner / day, 100 lifetime.
  Cache hits do not consume quota. See `HM057-HM06-delivery.md` §"Grounded
  coaching".
- No Tavily runtime calls in default config.
- No automatic retries; failed reservations fail closed.

## 7. Upload owner isolation / security

- Signed-session clients only; CSRF, expired raw pose, deletion, and
  owner checks run before cache use and again before returning results.
- Cache does not extend video/pose access.
- Raw media TTL 24h, report TTL 7d (`.env.example`).
- No raw video or pose arrays sent to the runtime LLM; only measured
  observations + one sourced general cue.
- Physical cleanup of the new text-cache ledger is future work; flagged
  in `HM057-HM06-delivery.md`.

## 8. Specific run checks (source commands, existing README only)

These are the only commands referenced; all exist in repo today.

- `./scripts/test.sh all` — offline Python + web checks (per `README.md`).
- `./scripts/check-browser.sh` — 54 browser fixture cases (per
  `HM-UX09-delivery.md`).
- `./scripts/pose-smoke.sh --video demo/lat_pulldown.mp4 --start-s 10 --duration-s 10 --repeat`
  — local pose diagnostic (per `README.md`).
- `docker compose -f infra/compose.yaml up --build` — full stack (per
  `README.md`).
- `docker compose -f infra/compose.yaml down` — stop, preserve state
  (per `README.md`).

No additional commands are invented here. Anything not listed above is
out of scope for this prep pack.

## Current branch and reproducibility gates

The latest implementation is on `codex/hm-ux05-mockup-implementation`; remote
`main` is an older checkpoint (c395ecf). A default GitHub clone currently does not
select the demonstrated build. Resolve with a reviewed release merge or explicitly
pin the judge test-build branch/commit. No merge or visibility change performed.

The tracked-file extension inventory found only original avatar/concept images,
not user videos, model binaries or databases. This is NOT a full Git-history secret
or licensing audit. Inspect history, logs, fixture content and third-party terms
before any public release. GitHub currently reports licence `Other` despite local
MIT text; investigate detection rather than claiming recognisable MIT status.

Fresh-clone setup has NOT been rerun. The documented pose diagnostic command uses
ignored private sample footage; replace that dependency with owner-approved public
sample footage or clear judge-upload instructions. Download the model from the
pinned URL in data/pose_models/mediapipe-full-v1.json and verify its SHA256; setup
scripts do not automatically obtain it.

Existing coaching limits20/day globally,4/day per owner,100 lifetime could exhaust
before judging ends. Check actual remaining reservations and design a judge-access
plan within an approved budget. Do not silently disable spending controls or promise
unrestricted live coaching. Persist server secrets and storage, verify HTTPS upload,
proxy limits, cookies/CSRF, expiry, restart and owner isolation on the chosen host.

No hosting account, entitlement, public URL, Devpost registration/draft or YouTube
upload has been verified. Owner reports no existing submission. Hosting needs a
concrete provider/uptime/cost proposal; Sites alone cannot run the Python worker.

## Suggested schedule (proposal)

-24–25Oct: hosting choice, sanitized release audit, fresh-clone instructions.
-25–27Oct: deploy approved target and verify actual judge upload/results/coaching.
-27–28Oct: capture permitted footage and record/edit demo under3minutes.
-29Oct: fill Devpost, verify all links in a signed-out browser and review claims.
-30Oct MYT: submit after owner review, ahead of31Oct01:00MYT cutoff.
-Through16Dec04:00MYT: retain free judge access and an operator monitoring plan.

Dates are planning targets, not evidence that these steps are complete.

## 25 October local onboarding update

HM-RELEASE02 now supplies scripts/quickstart.sh, docs/QUICKSTART.md and docs/INDEX.md.
A tracked-files-only clean export with fresh config/model/state passed Docker startup
and worker initialization; alternate ports isolated it from the existing app.
1,071 offline Python regressions pass. Source cues load in installed-package mode.
No private demo footage is needed for setup; judges can record/upload their own clip.
A synthetic no-person upload failed honestly; successful human-clip processing in
this fresh export and other host architectures remain unverified. See
docs/audit/HM-RELEASE02-delivery.md. This supersedes the earlier “fresh-clone setup
not rerun” note for the bounded tracked-export test only. Public visibility, default
release branch, video, actual form and judge-access/quota planning remain open.
