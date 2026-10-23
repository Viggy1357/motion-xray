# HM09 — UX concept & gamification brief (proposal)

> Historical exploration. The owner's later 23 October direction is **analysis first,
> with a lightly gamified customer experience**. The current draft and MVP/future
> blueprint are [HM-UX01-experience-blueprint.md](HM-UX01-experience-blueprint.md)
> and [HM-UX01-review-guide.md](HM-UX01-review-guide.md). Power/Tier and resemblance-led
> rewards below are earlier proposals, not approved MVP mechanics.

Status: **design proposal for owner review.** This is analysis and direction, not an
approved spec and not implementation. No app source has been changed. All numbers in
any companion mockups are mock data.

> **⚠️ Supersession flag — read first.** This brief proposes a direction that
> **conflicts with the current `HM00-screen-flow.md`**, which explicitly states
> *"no gamification, no avatar customisation"* and uses a midnight-navy + electric-lime
> palette. This document proposes the opposite: a stylised customisable avatar, a
> performance-flavoured gamification layer, and a navy/blue/green "Swiss instrument"
> palette. **It does not override HM00 until the product owner signs off.** If accepted,
> HM00's design-language and non-goals sections must be updated to match; if rejected,
> this brief is archived. The *flow* and *honesty* principles in HM00 remain valid and
> are reused here.

---

## 1. Purpose of this document

Capture the UX analysis behind a proposed redesign: **what the product needs to show,
why, and how a motivation layer can be added without violating the honesty rules.** It
is deliberately analysis-first — screen mockups are suggestions, not the deliverable.

## 2. Problem statement

The analysis pipeline is the hard, honest substance of Motion X-Ray, but on its own it
reads as a cold diagnostic tool — a "movement defect report." For a consumer fitness
audience (gym-goers) that is not a reason to return tomorrow. **The product is missing
an emotional engine: a reason to come back between the moments of genuine analytical
value.** The UX challenge is to add that engine *without* implying measurements,
correctness, safety, or physical change the system cannot and does not claim.

## 3. Governing constraints (non-negotiable)

From `AGENTS.md`, `PRODUCT.md`, and decisions **D015 / D016 / D017**:

1. **Resemblance, not correctness.** Scores express similarity to a selected reference,
   never technique correctness, injury risk, muscle activation, or physique.
2. **Null means "not measured, with a reason."** Partial/occluded reps are shown as
   such; they are never silently filled or averaged into a confident number.
3. **Honesty surfaces are mandatory:** formula, version, reference source, eligible
   cycle count, and observation coverage must be visible.
4. **Guest-first, browser-local, no accounts.** Uploaded media is untrusted. No
   biometric capture, no cross-device identity for the MVP.
5. **NVIDIA-model-via-Nebius coaching** is grounded; it cannot invent prose, numbers,
   or scores.

Every idea below is filtered through these. Where a motivational mechanic risks
breaking one, the resolution is written down, not glossed over.

## 4. What the UX must deliver (requirements)

### 4.1 Analytical requirements (the "instrument")

The UI must let a solo user understand one set honestly:

- **Reconstruction** of the movement (estimated 3D + 2D overlay on their own video),
  with occluded/estimated parts visibly distinguished.
- **Resemblance profile** across the exercise's scored components vs. an approved
  reference — a shape comparison, not a single opaque number.
- **Per-rep signal** (e.g. joint angle over a rep) against a reference band, synced to
  video playback/scrubbing.
- **Observation coverage** presented as a measured quantity against a target, not a
  bare percentage.
- **Grounded coaching cue** — one short, next-set, metric-anchored sentence.
- **Honest states by design:** partial reads, unavailable components (with reasons),
  expired video, coaching-provider outage, empty first-run. These are first-class
  screens, not error fallbacks.

### 4.2 Motivational requirements (the "engine") — proposed

The UI should give a reason to return that is *earned by real, trustworthy reads*:

- A **persistent companion** the user feels ownership of.
- **Visible progression** tied to genuine improvement over time.
- **Short-horizon goals** (weekly) that pull the next session.
- **Reward/recognition** for consistency and for *filming well* (better coverage).
- A growth signal that is **defensible** — i.e. it can be explained in one honest
  sentence and survive a skeptical judge.

## 5. Information model — what to depict, and the right depiction

The correct chart per object was derived from the `ui-ux-pro-max` skill's chart data,
not chosen by taste:

| Information object | What it is | Recommended depiction | Rationale |
| --- | --- | --- | --- |
| Reconstruction | estimated movement | athletic figure + **motion-trail / trajectory** in a dark "well"; 2D overlay on video; raw landmarks demoted to an optional "technical view" | motion trails are inspiring and legible; naked skeleton reads as clinical/defect-like |
| Resemblance profile | N scored components vs reference | **Radar / spider**, user shape over a dashed reference "ghost" | skill: radar is correct for multiple components vs a fixed reference (2–3 datasets, ≤8 axes) |
| Single-rep signal | angle over a rep | **Line chart** + reference band + playhead | skill: line chart for a time axis; playhead ties it to video |
| Observation coverage | how much was cleanly seen | **Bullet gauge vs target** | skill: bullet/gauge is for a single KPI vs a threshold |
| Honesty layer | nulls, partial reps, provenance | persistent provenance strip + calm amber annotations (never red) | satisfies D015/D017 as a designed element |
| Coaching cue | one Nemotron line | single quoted callout grounded in the metrics above | D016: references, never invents |

**Design consequence:** the earlier "flat grid of equal-weight boxes" failed because
nothing led. Swiss discipline requires **one clear focal hierarchy per screen** — on the
Readout, the motion-trail well and the radar dominate; everything else recedes into
quiet type and whitespace.

## 6. The emotional engine — avatar + gamification analysis

### 6.1 Why an avatar

A personal companion that visibly reacts to training is a proven retention mechanic
(Whoop's recovery score, Duolingo's streak, Strava's fitness curve): a living thing
that mirrors effort. It converts a one-off analysis into an ongoing relationship.

### 6.2 The honesty trap, and the resolution

A companion that "levels up" can accidentally imply the system *certified your form* or
*grew your muscles*. Neither is permitted (D015). Resolution — be precise about what the
avatar represents:

> The avatar reflects **consistency and your resemblance *trend over time*** — i.e.
> "you showed up and you're improving against a reference" — **never** "your technique
> is correct/safe" and **never** "your body changed." Framing is *train your athlete*,
> not *your real muscles levelled up.*

The single most important word choice: a **"form confidence"** signal is the *trend of
resemblance*, or the system's confidence in *reading* you — not confidence that your
form is correct.

### 6.3 What the avatar/progression may legitimately track

| Layer | What grows / reacts | Honest basis | Payoff |
| --- | --- | --- | --- |
| Sessions / streak | companion energy, aura, streak flame | you logged a set — a real event | showing up is rewarded |
| Reps analysed | progression toward next rank | reps the system actually observed (not partial/occluded) | effort accumulates visibly |
| **Resemblance trend** *(dominant driver)* | **Power** / rank, "form confidence" meter | the existing resemblance score over multiple sets | improvement over time, not a single-set verdict |
| Observation coverage | companion "clarity" + challenge criteria | your filming quality (coverage %) | nudges honest, well-filmed captures |
| Exercise variety | unlockable stances/kit | which of the 4 exercises done | encourages full-body training |

**Design decisions taken (owner-confirmed in discussion):**

- **Avatar style:** stylised & customisable (body type, skin tone, kit/colour).
  **Local, private, no photo** — ships first. A photo-derived likeness is a later,
  consent-gated roadmap item only (it is biometric-adjacent, a privacy surface, and
  needs infra the guest-first/browser-local MVP does not have).
- **Dominant growth driver:** the **resemblance trend** (improvement), with streak and
  reps-analysed as secondary contributors.
- **Product centrality:** **balanced dual-mode** — a motivating game layer *and* the
  precise instrument, co-existing. Not game-forward, not instrument-only.
- **Vocabulary:** **performance-flavoured** — Power, Tier, Challenge, Streak, Badge.
  *Not* RPG framing (no "XP / quests / loot").

### 6.4 How the engine threads through the product (not a bolted-on toy)

The avatar does a job on each screen rather than sitting in a corner:

1. **Dashboard = the companion's home.** First thing seen: the athlete in its current
   state, Tier/Power, rank progress, streak, weekly challenges, a resemblance-trend
   chart that *feeds* Power, and a badges/unlocks rail. Replaces a boring stats wall.
2. **Readout = an earned reaction moment.** After a set processes, the companion reacts
   to the *honest* result: a celebratory flourish + "+Power" on a clean, well-covered
   set; a calm "partial read — try filming side-on next time" when coverage was low.
   **Low-coverage / partial reads grant no Power** — so the game *reinforces* honesty
   instead of fighting it.
3. **History / Progress = the growth timeline.** The companion's evolution over weeks,
   alongside the resemblance trend line.

### 6.5 Gamification mechanics (proposed, honesty-bound)

- **Power** (a strength number) and **Tier** ladder (e.g. Bronze → Diamond).
- **Weekly Challenges** such as "3 clean pulldowns ≥75% coverage" or "try all 4
  exercises" — note these reward *coverage quality and variety*, steering users toward
  honest captures.
- **Badges & unlocks** (streaks, auras, kits, higher tiers) as the reward currency.
- **Mandatory honesty label on every gamified surface:** *"Power rises with your
  resemblance trend & consistency — not a health or technique score."*
- **Leaderboards / social** are explicitly **out of MVP scope** — they pull against
  guest-first, no-account, browser-local, and add a moderation/identity surface.

## 7. Visual design system (proposed)

Derived from the `ui-ux-pro-max` design-system search for a "precise, trustworthy,
data-forward" tool (which returned Minimalism / Swiss, *not* the generic "vibrant dark
OLED gym app" — deliberately overridden because this is an instrument, not a hype app):

- **Style:** Minimalism / Swiss — grid-based, high-contrast, spacious, one focal
  hierarchy per screen.
- **Light-first + dark-mode toggle.** Bright, trustworthy chrome; **hero visuals sit in
  dark "wells"** so glowing content pops. Resolves white-preference vs. futuristic drama.
- **Palette:** Navy `#1E3A5F` (primary), Blue `#2563EB` (secondary), Green `#059669`
  (accent/positive), Background `#F8FAFC`, Ink `#0F172A`, hairline border `#E4E7EB`.
- **Semantic honesty colours:** cyan = measured/confident, amber `#B45309` =
  partial/estimated/occluded, grey = no-data/null.
- **Type:** Fira Code (headings + all numerics, the "instrument" feel) + Fira Sans (body).
- **Motion:** low–medium, purposeful; respects `prefers-reduced-motion`; no autoplay video.
- **Icons:** SVG set (Phosphor / Heroicons / Lucide) — no emoji as structural icons.

> Note: this palette differs from HM00's midnight-navy + lime. One palette must win at
> sign-off; they should not both ship.

## 8. Screen flow (reuses HM00's validated flow)

`Dashboard → New Scan → Readout → History`, with the companion woven across. The flow,
states, and honest-state coverage from `HM00-screen-flow.md` remain valid and are not
re-litigated here — this brief changes the **design language and adds the motivation
layer**, not the route graph.

| Screen | Analytical job | Motivational job |
| --- | --- | --- |
| Dashboard | recent sets, resemblance trend, coverage | companion home: Tier/Power, streak, challenges, unlocks |
| New Scan | exercise pick → consent → upload → honest processing stages | — (keep it focused; no gamification noise mid-capture) |
| Readout | reconstruction + radar + per-rep line + coverage + cue | earned companion reaction + Power tick |
| History | past sets, trends, manual sets | companion growth timeline |

## 9. Reusable components (extends HM00's list)

HM00 already defines ScreenShell, ExerciseCard, UploadPanel, StatusPill, MetricTable,
StateBox, MuscleSilhouette, WorkoutListItem. This brief adds:

- **TrajectoryWell** — dark panel rendering the athletic figure + motion trails (2.5D/
  pre-rendered MVP; real-time Three.js glTF a stretch) with a "technical view" toggle.
- **ResemblanceRadar** — radar/spider of components vs a dashed reference ghost.
- **CoverageGauge** — bullet gauge vs target.
- **RepSignalChart** — per-rep line + reference band + synced playhead.
- **AthleteStage** — the companion hero: figure, Tier badge, Power/rank bar, customise entry.
- **ChallengeCard**, **BadgeTile**, **ProvenanceStrip** (persistent honesty line),
  **ReactionToast** (earned companion reaction after a Readout).

## 10. Build-reality & cost notes (honest)

- A **true real-time rigged 3D character** (model + rig + animation states + Three.js
  scene) is a meaningful build. The honest MVP is a **high-quality 2.5D / pre-rendered
  companion with a few states** (idle, level-up, celebrate); full real-time 3D is a
  stretch goal. Mockups depict the *vibe*, not the shippable asset.
- Charts are standard (Chart.js / Recharts) and low-risk.
- The motion-trail hero is achievable in 2D/SVG/canvas even before any 3D work.
- No new paid services are implied by this UX; the only runtime provider remains the
  grounded NVIDIA coaching call already decided (D004/D016).

## 11. Open decisions for the owner

1. **Accept or reject the supersession** of HM00's "no gamification / no avatar"
   stance. (If accepted, HM00 must be updated.)
2. **Palette:** navy/blue/green Swiss (this brief) vs. midnight-navy + lime (HM00).
3. **Power formula weighting:** exact mix of resemblance-trend vs. streak vs. challenges.
4. **Companion asset pipeline & owner:** 2.5D states (MVP) vs. real-time 3D (stretch).
5. **Photo-derived avatar:** confirm it stays post-MVP and consent-gated.
6. **Hackathon scope realism:** is the gamification layer in-scope for Oct 30, or a
   post-submission enhancement with only the analytical redesign shipping first?

## 12. Suggested next steps

1. Owner decision on §11.1–§11.2 (these gate everything else).
2. If accepted: update `HM00-screen-flow.md`; generate the `ui-ux-pro-max` `MASTER.md`
   design system (+ per-screen overrides) into `apps/web/design-system/` as the build
   source of truth.
3. Mock the remaining screens (Readout reaction moment; New Scan) for review.
4. Pin the Power formula and the companion asset approach before any implementation.

---

### Appendix A — Mockup drafts produced during exploration (suggestions only)

Hand-authored SVG mockups were created to explore direction (images not stored in the
repo; they were illustrative, not assets):

- **Readout, three early directions** (Clinical Light / Carbon Performance / Glass
  Instrument) — rejected: boxy, equal-weight grid, skeleton hero felt clinical.
- **Readout v2 (Swiss, radar-led)** — better focal hierarchy; skeleton still rejected.
- **Readout v3 (athletic figure + motion trails)** — hero direction accepted in principle.
- **Dashboard v1 (flat avatar)** → **Dashboard v2 (3D-style athlete, performance-
  gamified)** — current proposed direction for the companion home.

All mockups were hand-written SVG grounded in `ui-ux-pro-max` data, not AI image-model
output, and are not final assets.
