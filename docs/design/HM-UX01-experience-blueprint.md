# Motion X-Ray — Experience Blueprint (HM-UX01 DRAFT)

Status: **DRAFT for owner review** · Scope: UX/product only · Owner direction supersedes all earlier brainstorm.
This is a proposed product blueprint paired with an isolated interactive UI draft at `/ui-draft/index.html`. The existing analysis pipeline is owned by the technical thread and is **not modified** by this work. The UI draft contains simulated examples, not live analysis.

---

## 1. Product posture (decided)

- **ANALYSIS FIRST.** Motion X-Ray is a posture/movement feedback app for casual/beginner gym users.
- The customer experience is **lightly gamified** — a motivational companion, **not** an RPG dashboard.
- Analysis and the next recommended action are always the primary content; game elements are secondary, illustrative, and dismissible.
- **No claims** of scientific validation, anti-cheat or technique correctness. The companion is illustrative; actual reconstructed movement is estimated, with per-measurement limitations.

### Decisions vs proposals
| # | Type | Item |
|---|------|------|
| D1 | DECIDED | Analysis-first IA; gamification is a companion layer |
| P0 | PROPOSED VISUAL | Light theme requested; warm white / ink / burnt orange proposed for review |
| D3 | DECIDED | Home shows a rotatable stylised 3D athlete (never the user) |
| D4 | DECIDED | Only video-analysed activity earns MVP recognition; manual logs earn none |
| D5 | DECIDED | Four exercises at MVP: bicep curl, lat pulldown, bodyweight squat, incline dumbbell chest press |
| D6 | DECIDED | Top-level technique score is **null** (not shown as a number) |
| D7 | DECIDED | Coaching = ID-selected, locally rendered observations/cues; no free invention |
| D8 | DECIDED | Guest account, same-browser, local-first; no invented backend |
| P1 | PROPOSED | Recognition rule v0.1 (§8) |
| P2 | PROPOSED | Milestone set (§8.4) |
| P3 | PROPOSED | Locker as secondary panel on Progress (§5.4) |
| P4 | PROPOSED | Phased work packages HM-UX02…06 (§10) |

---

## 2. Audience & positioning hypothesis

- **Who:** casual/beginner gym-goers who want to know "am I moving roughly right, and what should I do next?" without jargon.
- **Hypothesis (unproven):** a warm, honest analysis loop plus a modest visual progress companion increases completion of a first analysis and intent to return, better than a numbers-heavy dashboard.
- **Validation plan:** test with **5 casual/beginner users**. Measure: (a) task completion of intake→results, (b) comprehension (can they say what the app did and did not measure?), (c) second-session intent. **Retention is not claimed or proven.**

---

## 3. Design language

### 3.1 Theme tokens (light premium)
| Token | Value | Use |
|---|---|---|
| `color.bg` | warm white `#FAF7F2` | page background |
| `color.surface` | `#FFFFFF` | cards/panels |
| `color.ink` | `#1F1B16` | primary text |
| `color.ink.soft` | `#5C554B` | secondary text |
| `color.accent` | burnt orange `#C2571B` | primary actions, highlights |
| `color.accent.soft` | `#F3E0D2` | highlight washes, target regions |
| `color.ok` / `color.warn` / `color.error` | muted green / amber / red | states only, never decoration |
| `font.body` | 16px minimum, 1.5 line-height | all body copy |
| `radius` | 12px cards, 8px controls | |
| `space` | 4px base grid, generous whitespace (Swiss-style minimal spacing grid) | |
| `control.min` | **44×44px** draft web hit targets | |

### 3.2 Motion & accessibility
- `prefers-reduced-motion`: honoured globally; disables companion idle animation, transitions become fades.
- **No auto-rotation** of the 3D athlete by default; rotation is user-driven (drag / arrow keys).
- WebGL unavailable → static illustrated fallback image with the same region highlights; feature parity in text.
- Contrast: ink on warm white ≥ WCAG AA; accent never used for body text.
- Plain language everywhere; no jargon ("reps", "sets" allowed; "hypertrophy", "EMG" not).

---

## 4. Information architecture

Four top-level destinations. Analysis is the default landing for returning users with no recent result; Home is the landing otherwise.

```
Home ── Analyse ── Results ── Progress (Locker = secondary panel)
```

### 4.1 Desktop hierarchy
- Left rail nav (icons + labels): Home, Analyse, Results (latest), Progress.
- Main column: primary task content. Right column (collapsible): companion summary / next action card.
- Results: video left, replay + observations right, cue list below.

### 4.2 Phone hierarchy
- Bottom tab bar (4 tabs, 44px+ targets).
- One column; companion appears as a card below the primary action, never blocking it.
- Results: stacked — video → overlay toggle → replay → observations → cues → milestone reaction.

---

## 5. Screen-by-screen

### 5.1 Home
- **Hero:** central **rotatable stylised 3D athlete** (D3). It is a generic companion figure — **never presented as a reconstruction of the user**.
- Anatomical exercise-target highlight: regions corresponding to analysed exercises glow softly (`accent.soft`).
- Modest regional "virtual development" (e.g., subtle fill level per region) shown as **earned illustrative progress** — copy must say so: *"This is a fun picture of your effort, not a measurement of your body."*
- Primary CTA: **"Analyse a set"** (accent button, 44px+).
- Secondary: "View latest result", "See progress".
- **Empty state (new guest):** companion in neutral pose, no highlights; copy: *"Analyse your first set and your companion starts tracking your effort."* Demo entry point offered (§7).

### 5.2 Analyse (intake)
1. Pick exercise (4 cards, plain names + one-line description).
2. Choose source: **record/upload video** (earns recognition) or **log manually** (record only, no recognition — stated upfront: *"Manual logs keep your history but don't earn companion progress."*).
3. **Optional local preview** before submitting: plays in-browser; bytes stay local until user confirms.
4. Submit → handoff to existing pipeline (owned by technical thread; unchanged).
- **Partial state:** video chosen but exercise not picked → submit disabled with reason.
- **Failed state (pipeline error):** measurements preserved where available; clear retry; no recognition awarded; no blame language.
- **Expired/revoked state:** show the known reason returned by the service, such as retention expiry or access revocation. Do not infer that the user deleted a file from a generic fetch failure; preserve only summaries actually retained.

### 5.3 Results
- **Layout:** user video + **2D overlay** (keypoints/angles) + **estimated 3D replay** (planned) — all **synchronised to original presentation timestamps (PTS)** and addressable by **segment IDs** so cues can deep-link to moments.
- Actual 3D replay is labelled *"estimated movement"*; measured geometry, observation support and uncertainty stay separately identifiable. The draft's synthetic replay is explicitly an illustration.
- **Top-level technique score: null** — no invented aggregate number.
- **Prototype reference resemblance** (if shown) is always labelled **provisional**; **exercise coverage is a separate fact** from resemblance; never merged into one score.
- **No radar/spider summary** with invented axes.
- **Coaching panel:** ID-selected, locally rendered observations and cues from a fixed library. Each item shows: observation → cue → "why" in one plain sentence.
- **Progressive disclosure:** tap any observation → detail sheet with **provenance** (which segment IDs, which measurement), and **missing reasons** when data was unavailable (e.g., "arm occluded in frames 120–160"). Experimental reference material lives in this detail layer, **separate from the visible summary**.
- **Runtime coaching** means a provider call after set analysis, not live during-set coaching. It is an **explicit separate request** by the user; if it fails, **available measurements are preserved** and the failure is shown inline. Reopening results does not trigger paid calls.
- **Coach unavailable state:** show *"Coaching isn't available for this set. You can still review the available measurements."* Provider availability does not establish measurement accuracy.
- **Milestone reaction:** if recognition was earned (§8), a small, single, non-blocking celebration (one line + subtle region glow on companion thumbnail). No confetti cannons, no streak pressure.
- **Save once:** result is saved a single time with a stable analysis ID; re-visiting never re-awards.

### 5.4 Progress
- Primary: history list of analyses (exercise, date, recognition earned or not, link to result).
- **Locker (secondary panel, P3):** earned milestones and region development summary. Collapsed by default on phone.
- Copy throughout: illustrative progress, not physique/health measurement.
- **Empty state:** *"Nothing here yet — analyse a set to begin."*

---

## 6. Account model (decided)

- **Guest, same-browser continuity; no cross-device sign-up at MVP.** Current uploads and analysis use owner-scoped server storage; browser logs and companion preferences are distinct from server media.
- Draft-only copy: *"This preview stores example progress in this browser. Files you preview are not uploaded."* Production copy must describe actual server processing/retention separately. Clearing browser identity may lose access to server analyses; it does not itself erase their media.
- Existing server analysis infrastructure remains unchanged. Durable recognition events are a proposed addition (§9), not an existing feature.

---

## 7. Demo mode (decided)

- Entry from Home empty state and Analyse: **"See a demo"**.
- Uses a **bundled fixture**: explicitly labelled *"Simulated example — no real processing"*.
- The demo **never uploads the user's bytes and never runs analysis**; it walks the Results screen with fixture data.
- All example media labelled as examples. Privacy preserved by construction.

---

## 8. Recognition rule v0.1 (PROPOSED — P1)

### 8.1 Rule (deterministic)
- An analysis is **eligible** iff: it is one of the four MVP exercises **and** it contains **at least one measured completed cycle** (full rep detected by the pipeline).
- **Partial eligibility:** if no completed cycle was measured → **no award**. Uncertainty is **never penalised**; copy encourages rest and retry: *"We couldn't measure a full rep this time — no penalty. Rest up and try again when you're ready."*
- Each eligible analysis earns recognition **exactly once**, keyed by analysis ID + rule version (`recognition.v0.1`).
- **No score multiplier; limited rep-count incentive:** one analysis = one recognition event regardless of rep count. Splitting/reuploading footage can still farm events; do not claim this rule prevents abuse. Any future daily/session cap needs explicit balancing review.
- **Manual logs never earn recognition** (D4).

### 8.2 Region mapping (illustrative, not exhaustive)
| Exercise | Region |
|---|---|
| Bicep curl | Upper arms |
| Lat pulldown | Back |
| Bodyweight squat | Legs |
| Incline dumbbell chest press | Chest |

### 8.3 Pending numeric balance
- Per-award region increment value: **user-confirm pending** (placeholder `+1` unit per award; owner to confirm before HM-UX04 build).

### 8.4 Milestones (PROPOSED — P2)
- A few milestones based on **counts of qualifying analysed sets** (e.g., 1st / 5th / 15th analysed set per region).
- **No physique claims** in milestone copy; **no randomised measurement** of any kind.
- Rewards are **committed only after durable local save succeeds** — no optimistic fake progress; on save failure, award is queued and retried, UI shows nothing earned yet.

### 8.5 Future backend (not MVP)
- Later: server-side, owner-scoped, **idempotent event ledger** keyed by `(analysis_id, rule_version)`.
- Distinguish **deleted-video** vs **deleted-log** events.
- Known unsolved: replay/duplicate detection **across separate uploads** of the same footage.

---

## 9. Roadmap beyond MVP (FUTURE, gated)

1. Professional evaluation + compatible repeat trends (same exercise, comparable setups).
2. Personalisation: body types for the companion figure.
3. Challenges (opt-in, effort-based).
4. Bounded exchange and **optional cosmetic randomness** (skins/gear — strictly optional cosmetics).
5. Accounts/social — **much later**, behind explicit gates.
- Rewards/penalties/trading/randomness are **options, not a required checklist**; each needs owner sign-off.

---

## 10. Phased delivery (PROPOSED — P4)

No timeline is guaranteed; dependencies are explicit. The analysis pipeline is a hard external dependency owned by the technical thread.

| WP | ID | Scope | Depends on | Acceptance cut line |
|---|---|---|---|---|
| 1 | **HM-UX01** | This blueprint draft | — | Owner approves decisions + P1 rule |
| 2 | **HM-UX02** | App shell: nav, theme tokens, 4 screens skeleton, empty states | HM-UX01 | All screens reachable; 16px body, 44px controls, AA contrast pass |
| 3 | **HM-UX03** | Intake→results bridge: local preview, demo fixture, results layout, states (failed/expired/coach-unavailable) | HM-UX02, pipeline API contract | Demo runs with zero user bytes; failed analysis preserves measurements |
| 4 | **HM-UX04** | Recognition v0.1 + locker panel + milestone reaction | HM-UX03, owner confirms §8.3 value | Idempotent award per analysis ID; manual log earns nothing; no-award copy on partial |
| 5 | **HM-UX05** | Accessible 3D companion: user-rotated, reduced-motion, WebGL fallback, region highlights | HM-UX02 | No auto-rotation; keyboard rotation works; fallback image parity |
| 6 | **HM-UX06** | QA & release: 5-user test, a11y audit, copy review | HM-UX03–05 | Test metrics recorded; all checklist items (§12) pass |

### MVP few-days scope
- **MUST:** screens + states (§5), demo mode, recognition v0.1, null score posture, plain-language copy, reduced motion + fallback.
- **SHOULD:** locker panel, milestone reaction, provenance detail sheets.
- **FUTURE:** §9 items, runtime coaching polish, skins/gear.

---

## 11. Known limits (must appear in-app where relevant)

- No scientific validation; feedback is indicative, not medical/health advice.
- No anti-cheat; recognition trusts the pipeline's cycle detection.
- No claim of technique correctness; cues are general, ID-selected observations.
- 3D (replay and companion) is stylised/estimated; **no reliable depth** from single-camera video.
- Guest data is same-browser only; clearing storage loses history.
- Coverage is limited to four exercises; resemblance to any reference is provisional.

---

## 12. Acceptance checklist

- [ ] Analysis is the first and loudest action on every screen
- [ ] Companion never labelled or implied to be the user's body
- [ ] "Illustrative, not measured" copy on all region/development visuals
- [ ] Manual log path shows no-recognition notice before submit
- [ ] Demo labelled simulated; uses fixture only
- [ ] Results: no top-level score, no radar chart, provenance + missing reasons in detail layer
- [ ] Runtime coaching is opt-in; failure preserves measurements
- [ ] Award idempotent per analysis ID; committed only after durable save
- [ ] Reduced motion, no auto-rotation, WebGL fallback, 44px targets, 16px body
- [ ] All four exercises mapped; no completed measurable cycle → no award + calm filming guidance; mixed complete/partial sets can qualify under §8.1

## 13. Open decisions

1. §8.3 numeric increment value (owner confirm).
2. Milestone thresholds (1/5/15 proposed).
3. Whether provisional resemblance appears in summary or only in detail layer.
4. Companion figure style direction (realistic-stylised vs geometric).
5. Wording of the privacy line for guest storage.

*Source guidance adopted: minimal Swiss spacing grid, touch targets, contrast, reduced motion — user direction overrides any generic dark/marketing styling.*

## 14. MVP integration blueprint and handoff boundaries

The static `/ui-draft/index.html` prototype is a design review artifact. Do not replace the
working application with its simulated data or reuse its example recognition as a
production event ledger. Keep the current application available at `/`.

| UI boundary | Existing foundation | MVP integration work / acceptance |
|---|---|---|
| Intake | Existing `/api/session`, `/api/analyses` POST and exercise catalogue | Reuse signed owner/CSRF flow and server limits. Actual byte progress only; explicit upload consent; recoverable retry. No duplicate job from a double tap. |
| Processing | Existing analysis status, cancellation and resumable job identity | Display real queued/stage/elapsed fields; preserve refresh continuity. No fabricated percent or completion time. |
| Results | Existing strict `/result` and additive `/movement-report` | Adapter validates report version, preserves null reasons and original segment IDs. Pose-only results never acquire invented reps. |
| Replay | Private owner-scoped artifact streaming | Bind actual video, pose timestamps and selected segment; expired/revoked media keeps usable summaries where actually retained. Never substitute the Home character for measured pose. |
| Feedback | Explicit `/api/analyses/{id}/coaching` POST | Preserve quota/cache controls and candidate IDs. Generate only on deliberate user action; replay uses returned segment evidence. |
| History | Current local logs; durable log work tracked separately | Save detected and user-corrected counts distinctly; no reward from manual correction. Browser identity loss and media deletion have distinct copy. |
| Recognition | No production feature assumed | Versioned pure eligibility reducer + atomic owner-scoped event persistence; idempotency and failure checks before progress appears. Local-only MVP alternative must be labelled mutable/non-competitive. |

### Implementation slices and cut order

1. **Navigation and real intake:** replace visual shell only; complete one owned
   upload/status/cancel/resume journey. Existing backend and private-media controls stay.
2. **Results clarity:** wire available measurements, missing reasons, sample-free
   replay and one grounded cue. Exercise and variant names come from the catalogue.
3. **Companion:** add the lightweight Home renderer and target map with a text/static
   fallback. It must never block upload or reading a result.
4. **Recognition:** integrate the proposed rule only after the owner accepts it and
   persistence is available. Hide progression rather than shipping fake earned state.
5. **Release checks:** one actual owner journey per advertised exercise, honest partial
   squat acceptance, mobile scrolling/rotation/keyboard checks, storage failure,
   expired-media and provider-quota checks. Browser/device claims require actual checks.

If time is short, cut appearance customisation, decorative charts, extra animations,
then recognition. Preserve working analysis, honest results, replay, privacy and clear
feedback. A useful analysis MVP with a polished companion is an acceptable cut;
unreliable analysis with a reward system is not.

### Future gates (proposals, not a dated promise)

- **After first-user testing:** evaluate first-set completion, interpretation of
  missing data and whether the character adds motivation or distraction. Record
  observed behaviour separately from stated second-session intent.
- **After measurement evaluation:** qualified reviewer rubric, held-out clips across
  views/body types, disagreement/error ranges and versioned compatibility gates before
  promising technique confidence or comparing trends across model versions.
- **After persistence/identity:** cloud continuity and recovery; explicitly review
  access, retention and deletion before any social feature.
- **After a useful return loop exists:** optional challenges, appearance collections,
  bounded resource exchange and cosmetic randomness. Rest never causes body decay;
  hidden analysis uncertainty never changes odds/rewards. No monetary trading proposed.
- **Photo-derived avatars:** later consent/retention/licensing/performance review,
  never required for analysis. No facial/biometric input added by this draft.
