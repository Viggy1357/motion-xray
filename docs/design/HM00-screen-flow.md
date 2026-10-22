# HM00 — Screen flow and reviewable mockup

Status: **design draft for review only.** Companion artifact:
`artifacts/development/hm00-motion-xray-mockup.html` — a standalone, network-free
HTML/CSS/JS mockup (no CDN, no tracking, no remote assets, no dependencies, no app
source mutation). It is **not a working product** and must never be presented as one.
All values in it are labelled mock data; nothing is fabricated analysis evidence.
Integrator/user review is required before any production UI implementation (HM08+).

## Flow (FR01/02/03/06/07/08/09/10/12)

```
Dashboard (/) ── Start new set ──▶ New set (/new)
   ▲                                 1. pick exercise + variant (4 supported)
   │                                 2. consent → file pick / drag-drop
   │                                    (camera = progressive enhancement only)
   │                                 3. optional load (kg/lb, total/per-hand/bodyweight), notes
   │                                 4. upload progress (real bytes) → cancel/retry (idempotent)
   │                                 5. queued → processing (real stage + elapsed, no fake ETA/%)
   │                                 refresh resumes the job
   │                                        │
   │                                        ▼
   │                              Results (/sets/[id])
   │                                 video + 2D overlay + estimated 3D (shared source PTS)
   │                                 play/pause/scrub/speed/rep select
   │                                 metrics vs provisional reference band, per-metric coverage
   │                                 explicit unavailable components + reasons
   │                                 short Nemotron coaching (grounded, one next-set cue)
   │                                 save/edit logged reps/load/notes
   │                                        │ save set (idempotent link to analysis_id)
   ▼                                        ▼
Dashboard ◀────────────────────── History (/workouts, /workouts/[id])
 recent workouts + muscle view      grouped by workout/date, filter by exercise,
 (illustrative silhouette)          replay while retained, manual sets without video,
                                    same-variant/profile-version trends only,
                                    remove set / delete video explained separately
```

## States covered in the mockup

| State | Where shown |
| --- | --- |
| Upload progress + cancel/retry | New set (state box, real-bytes copy) |
| Processing stage + real elapsed, no invented % | New set |
| File too long / codec fallback to plain upload | New set (error box) |
| Partial result | Dashboard recent list |
| Coaching unavailable (provider outage; results still readable) | Results |
| Expired video (log + metrics survive 24 h raw retention) | Results + History |
| Empty first-run dashboard | Dashboard (toggle) |
| Empty history | History (toggle) |
| Manual set without video (detected vs logged kept distinct) | History |

## Smallest reusable components (for HM08/HM09, not a design system)

1. **ScreenShell** — header, logo, "mock/not a product" style banner slot, top nav
   (desktop) / bottom nav (mobile), skip link.
2. **ExerciseCard** — name, variant, view guidance, targeted muscles; `aria-pressed`
   selection. Used by New set and (later) routine templates.
3. **UploadPanel** — drop zone + file input + consent + metadata errors + progress +
   cancel/retry; camera capture as an enhancement branch only.
4. **StatusPill** — `ok / warn / bad` pill for report ready, partial, expired, manual,
   unavailable.
5. **MetricTable** — observed value, reference band, coverage %, status pill,
   unavailable-with-reason row.
6. **StateBox** — bordered callout (ok/warn/bad) for processing, errors, expiry,
   coaching-unavailable, empty states.
7. **MuscleSilhouette** — original inline SVG silhouette with toggleable muscle-group
   highlights fed by logged exercise targets. Strictly illustrative: no physique
   reconstruction, no inferred activation/growth.
8. **WorkoutListItem** — exercise, date, detected vs logged reps, status pill,
   replay/remove actions.

## Design language

Midnight navy (`#0b1220`) surfaces, warm off-white (`#f4efe6`) text, electric lime
(`#c8f542`) reserved for primary actions, current nav and muscle highlights; amber/red
only for warning/error states. Restrained system typography, spacious desktop grid,
bottom nav under 720 px. No purple gradients, no gamification, no avatar customisation.

## Accessibility / review notes

- Opens locally with no services or network; hash-based navigation works with real
  `<button>`s; skip link; focus-visible outlines; heading focus on screen change.
- Primary action ("Start new set" / "Save set") is always visually unambiguous.
- Text contrast: off-white on navy and lime-on-navy both pass WCAG AA at used sizes.
- Model/provider API credentials are server-side concerns and appear nowhere in UI
  settings or copy.

## Explicit non-goals for this mockup

No design system, no routing library, no real data, no working upload/analysis, no
publication of sample media, no accuracy claims. Production implementation begins only
after integrator review, against frozen HM01 contracts.
