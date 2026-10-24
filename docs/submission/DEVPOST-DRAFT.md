# Devpost draft — Motion X Ray

> Concise, scoped, honest. No fabricated metrics, no invented feedback.
> Field-name mapping is **proposed**; the live Devpost form was not
> inspected from this prep environment.

## Proposed field → content mapping

| Devpost field (proposed) | Content |
|---|---|
| Project title | Motion X Ray |
| Tagline | Understand your workout, one set at a time. |
| Inspiration | We wanted a quick, private way to review a single set after filming it on a phone — without requiring a fitness account and without claiming clinical accuracy. |
| What it does | A guest records or uploads a clip (under60s and100MiB). The worker extracts pose, segments completed reps, measures joint angles per exercise, compares against a downloaded publisher reference window, and returns measured movement observations and, where available, a partial experimental reference-resemblance estimate. Top-level technique scores remain null. Coaching is requested separately. |
| How it was built | Dockerised Python 3.12 worker (MediaPipe Pose Landmarker, CPU), FastAPI signed-session API, Next.js web app, SQLite for durable coaching cache. Coaching uses NVIDIA Nemotron via Nebius Token Factory (OpenAI-compatible); the model only selects candidate IDs, local code validates and renders the fixed text. |
| Technical choices / challenges / accomplishments | Choices: CPU-friendly MediaPipe primary; cached search provider by default; signed sessions; atomic coaching quota. Challenges: preserving final recording chunks, mapping source timestamps to replay, and validating structured candidate IDs so the model cannot invent measurements. Accomplishments: 971 Python tests recorded23Oct and54 browser fixture cases passing24Oct; one real owned-lat runtime call (1427 in / 38 out, 1.103s) with a cache hit verified after API restart. |
| Learnings | Separate measured signal coverage from accuracy. Keep the model on a narrow, validated job (candidate IDs) and render text locally. Keep reference resemblance, signal visibility and measurement accuracy distinct. |
| What's next | HM02 durable guest profile/workout logs, free-first hosting for judge access, then professional review of reference calibration. Move / Fuel / Recover concepts are future-only and not in this MVP. |
| Built with | NVIDIA Nemotron (via Nebius Token Factory), MediaPipe Pose Landmarker, FastAPI, Next.js, SQLite, Docker, Cached exercise-source library (Tavily integration is not demonstrated in the submitted runtime path). |
| Track | Best Apps and Agents (recommended) |

## Required URLs — explicit MISSING list

The following URLs **must be filled by the owner** before submit. No fake
URLs are inserted here.

- [MISSING] Public GitHub repo URL — repo is currently PRIVATE; owner to
  authorize a public release.
- [MISSING] Hosted demo / test build URL — no hosting purchased or
  activated in prep.
- [MISSING] Public YouTube demo video URL (UNDER 3 min) — to be recorded
  per `docs/submission/DEMO-SCRIPT.md`.

## Significant update statement (needs owner confirmation)

The original start date has not been established. Confirm whether the project
existed before26August2026; only then decide whether a significant-update
statement is required. Suggested skeleton (owner edits):

> Significant updates during the hackathon period: [owner to list — e.g.,
> grounded Nemotron coaching adapter, four-exercise measurement profiles,
> 54-case browser fixture suite, restrained View Transitions polish].

## Feedback (grounded in observed build experience only)

- **NVIDIA Nemotron via Nebius Token Factory**: used as an OpenAI-compatible
  endpoint; structured candidate-ID output validated locally so the model
  cannot invent measurements, scores, or claim IDs. Useful improvement to evaluate: clearer structured-output and failure diagnostics
  for bounded application workflows. This is a proposed feedback point, not a
  claim about an observed provider outage.
- **Nebius Token Factory**: hosted inference reachable from local dev;
  one real runtime call documented (1427 in / 38 out, 1.103s). No paid
  hosting activated in prep.
- **Tavily**: not invoked at runtime in this build (`SEARCH_PROVIDER=cached`
  default). No Tavily award eligibility claimed.

## Optional owner firsthand-feedback placeholders (not invented)

> Owner to fill from personal experience only — do not invent invoice
> numbers, support praise, or user counts.

- What I asked Nebius for: ___
- What Nebius returned that surprised me: ___
- One thing I'd change about the dev experience: ___

## Explicit non-claims

- No clinical accuracy, technique grading, or injury-risk claims.
- No muscle-activation or nutrition/recovery claims.
- No user counts, paid-customer metrics, or third-party praise.
- No claim that paid development calls satisfy product runtime.
