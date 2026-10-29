# Devpost draft — Motion X Ray

> Copy-ready draft for owner review. Field mapping remains proposed until registration and the live form are checked.

## Project title

Motion X Ray

## Tagline

Understand your workout, one set at a time.

## Inspiration

When you train alone, a workout video can be easy to record and hard to act on. I wanted a private way to review one set, see what the camera could actually measure, and get one grounded cue for the next set — without a fitness account and without pretending the result is clinical.

## What it does

A guest records or uploads a short clip (under 60s and under 100 MiB). The worker extracts pose on CPU, segments completed reps, measures joint angles per exercise, compares against a downloaded publisher reference window, and returns measured movement observations. Where available, a partial experimental reference-resemblance estimate is shown. Top-level technique scores remain null. Coaching is requested separately as an explicit user action.

## How it was built

Dockerised Python 3.12 worker (MediaPipe Pose Landmarker, CPU), FastAPI signed-session API, Next.js web app, SQLite for durable coaching cache. Coaching uses NVIDIA Nemotron via Nebius Token Factory (OpenAI-compatible); the model only selects candidate IDs, local code validates and renders the fixed text. The main value is accountable video evidence — measured moments the user can replay — not chat or safety advice.

## Technical choices, challenges, and accomplishments

Choices: CPU-friendly MediaPipe primary; cached search provider by default; signed sessions; atomic coaching quota. Challenges: preserving final recording chunks, mapping source timestamps to replay, and validating structured candidate IDs so the model cannot invent measurements. Accomplishments: 1109 Python tests recorded this run and 108 browser fixture cases passing across 360 / 375 / 1365 viewports; one real owned-lat runtime call (1427 in / 38 out, 1.103s) with a cache hit verified after API restart.

## Why NVIDIA is central

NVIDIA Nemotron is the only model used for the coaching path. Its job is narrow and bounded: pick a candidate ID from a fixed list. Local code inspects the ID, validates it against the measured signal, and renders the text. The model never invents numbers, angles, or rep counts. This separation is the point — bounded semantic selection, inspected, not invented.

## Pip — a quiet gym companion

Pip is a small illustrated companion who rests beside the athlete on the home screen and shows three local encouragement bubbles during processing. A gentle breathing pose and attentive reactions give the app a consistent character through the review flow. These are local animations and messages.

## Learnings

Separate measured signal coverage from accuracy. Keep the model on a narrow, validated job (candidate IDs) and render text locally. Keep reference resemblance, signal visibility, and measurement accuracy distinct. Concrete challenges I worked through: chunked upload finalisation, source-time to replay mapping, and structured-output validation that fails closed when the model returns an unknown ID.

## What's next

Durable guest profile and workout logs, free-first hosting for judge access, then professional review of reference calibration. Move / Fuel / Recover concepts are future-only and not in this MVP.

## Built with

NVIDIA Nemotron via Nebius Token Factory (model `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`), MediaPipe Pose Landmarker, FastAPI, Next.js, SQLite, Docker, cached exercise-source library. Tavily integration is not demonstrated in the submitted runtime path.

## Track

Best Apps and Agents (recommended)

## Required URLs — explicit MISSING list

The following URLs **must be filled by the owner** before submit. No fake URLs are inserted here.

- [MISSING] Public GitHub repo URL — repo is currently PRIVATE; owner to authorise a public release.
- [MISSING] Hosted demo / test build URL — no hosting purchased or activated in prep.
- [MISSING] Public YouTube demo video URL (UNDER 3 min) — to be recorded per `docs/submission/DEMO-SCRIPT.md`.

## Significant update statement

Not required. First commit `09d0ca7` dated 16 Oct 2026 23:30:56 +08; GitHub API `created_at` 16 Oct 2026 15:50:33Z. New project within the hackathon period; no pre-existing update block applies.

## Coaching access plan

Current coaching limits are 20 global reservations per UTC day, 4 per owner per day and 100 lifetime. These limits are safeguards, not a judge-access plan: hosting, remaining balance and sufficient capacity through judging are still unresolved.

## Feedback (grounded in observed build experience only)

- **NVIDIA Nemotron via Nebius Token Factory**: used as an OpenAI-compatible endpoint; structured candidate-ID output validated locally so the model cannot invent measurements, scores, or claim IDs. Useful improvement to evaluate: clearer structured-output and failure diagnostics for bounded application workflows. This is a proposed feedback point, not a claim about an observed provider outage.
- **Nebius Token Factory**: hosted inference reachable from local dev; one real runtime call documented (1427 in / 38 out, 1.103s). No paid hosting activated in prep.
- **Tavily**: not invoked at runtime in this build (`SEARCH_PROVIDER=cached` default). No Tavily award eligibility claimed.
- **Model control standardisation**: during this session, model-specific reasoning controls at first consumed the completion with no visible output. Verifying `thinking_mode=disabled` restored complete worker output. A useful standardisation would be clearer reasoning/visible-budget diagnostics across model variants.

## Optional owner firsthand-feedback placeholders (not invented)

> Owner to fill from personal experience only — do not invent invoice numbers, support praise, or user counts.

- What I asked Nebius for: ___
- What Nebius returned that surprised me: ___
- One thing I'd change about the dev experience: ___

## Explicit non-claims

- No clinical accuracy, technique grading, or injury-risk claims.
- No muscle-activation or nutrition/recovery claims.
- No user counts, paid-customer metrics, or third-party praise.
- No claim that paid development calls satisfy product runtime.
- No 3D skeleton in the main app (separate diagnostic, not a feature).
- No real-time / live / hardware claims.
- No retention metrics.
- No chat or safety advice from the model.
