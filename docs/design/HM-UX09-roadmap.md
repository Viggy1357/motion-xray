# HM-UX09 — Restrained transition polish (roadmap)

This document records what UX09 ships in this pass, what is intentionally
deferred, and what is explicitly **not** planned for the MVP. It is a
working note for the owner, not a marketing promise.

## Scope of this pass

- **CSS polish** (`apps/web/app/globals.css`):
  - Scoped transitions on buttons, chips, cards, nav buttons, icon
    buttons, exercise options/cards, intro/focus primaries, manage
    summary, and text links (180ms ease, background/color/border/
    box-shadow/transform).
  - Subtle hover lift (`translateY(-1px)`) and press settle
    (`translateY(0) scale(.985)`) on the same elements.
  - Focus-visible ring (`box-shadow` halo) on the same elements.
  - Card hover shadow lift.
  - No `.view` entry animation. The avatar artwork (`.heroart`,
    `.athstage`, `.athwrap`, `.athimg`, `.regiondot`, `.viewtoggle`)
    is explicitly excluded so the existing illustration never moves
    or changes.
  - Native same-document View Transitions (`@supports
    (view-transition-name: a)`) cross-fade on the main view node only.
    `.main` is assigned `view-transition-name: main-view`. The root
    pseudo animation is disabled (root grouping still captures the
    rest), and the cross-fade is opacity-only — no vertical avatar
    motion. The camera/avatar DOM is never frozen.
  - `prefers-reduced-motion: reduce` disables every transition and
    both the root and `main-view` view-transition pseudo animations.

- **JS patch** (`apps/web/app/page.tsx`):
  - Wraps the existing `navigate` callback with a
    progressive-enhanced `document.startViewTransition` call.
  - Adds a local TS type intersection (`DocWithViewTransition`) so
    `startViewTransition` is callable without global declarations.
    The `document` reference and typecast are inside the callback so
    SSR never touches `document`.
  - Imports `flushSync` from `react-dom` and wraps the existing
    `pushState` + `setRoute` inside it so the View Transition captures
    the actual route DOM update.
  - Skips the transition when:
    - `prefers-reduced-motion: reduce` is set,
    - `document.startViewTransition` is not a function (fallback),
    - any DOM `<video>` has a live `srcObject` (camera capture)
      regardless of `paused`, or is actively playing
      (`!paused && currentTime > 0 && !ended`), so the camera is
      never frozen.
  - A once-guard `apply()` ensures a sync throw or a rejected
    `updateCallbackDone` navigates exactly once via the fallback.
    `ready`/`finished`/`updateCallbackDone` rejections are caught to
    avoid unhandled rejections. **No double navigation** is possible.
  - Does **not** alter routes, state, camera, or the avatar.

- **Segment chips** (`apps/web/app/movement-report.tsx` +
  `apps/web/app/movement-report.module.css`):
  - `SegmentChip` takes the parent `analysisId` as an explicit prop
    and forwards it to `SessionThumbnail`. (`Rep` has no
    `analysis_id` field.)
  - The chip has a bounded width (~132px) at all sizes so the
    thumbnail does not grow to its intrinsic size. The narrow
    viewport rule (`<=360px`) keeps the card readable.
  - Thumbnails are sourced from the segment thumbnails
    (`SessionThumbnail`), not from the history layout.

## Deferred (not in this pass)

- **Avatar 3D / new poses.** The existing 2D illustration is preserved
  verbatim. No new poses, no 3D model, no rotation animation.
- **Thumbnail cross-fade.** Segment thumbnails are not animated in
  this pass; they remain static images inside the chip.
- **Loading screen content.** The loading screen copy is unchanged in
  this pass and remains a future improvement.

## Explicitly not planned for MVP

- **"Ask your set" / "Show me why" conversational features.** These
  were rejected during scoping. They are not on the MVP roadmap.
- **Move / Fuel / Recover concepts.** These are future concepts that
  have not been validated with users. They are **not** implemented in
  this pass and are not promised. Possible future features and
  dependencies (if pursued) would include:
  - Move: per-exercise cue library, requires validated cue taxonomy.
  - Fuel: nutrition logging, requires a separate data model and
    consent flow.
  - Recover: recovery scoring, requires validated recovery model and
    external data sources.
- **Sponsorship, comparisons, trainer review.** Optional, future
  ideas only. Not promised, not implemented.

## Test scope (deferred by owner)

- Broad device, network, and storage edge-case tests are deferred by
  the owner. The Mac camera is accepted as working in development but
  has **not** passed formal certification. No certification claim is
  made in this pass.

## Delivery sequence after this pass

1. **Submission readiness:** judge-accessible build, fresh-clone setup, documented
   actual NVIDIA/Nebius runtime path and concise demo. Hosting, publication and
   final submission are separate release actions; this push does not deploy.
2. **Reliability:** resume the deferred physical iOS/Android/browser matrix,
   interruption, quota, ownership/expiry and result-edge cases. The existing
   Docker Chromium suite is a regression gate, not physical-device certification.
3. **Movement development:** professional review/calibration, comparable-session
   replay, one-adjustment retry experiments and trainer review packets. Preserve
   raw measurements and uncertainty; comparisons need compatible exercise/view
   and version rules before claiming improvement.
4. **Experience exploration:** useful waiting-screen education and optional
   sponsorship; a rigged avatar only after a cheap one-exercise proof demonstrates
   value. Neither sponsorship SDKs nor asset purchases are authorized here.
5. **Ecosystem discovery:** Move (movement/training), Fuel (preferences, budget,
   ingredients and meal planning), Recover (self-reported sleep, soreness, energy
   and routine). A future assistant could coordinate a short session and meal
   around the user's actual day. Validate demand first; no video-derived medical,
   nutrition-deficiency or recovery-readiness claims. Wearables, data consent,
   nutrition uncertainty and professional review need separate designs.

This is dependency order rather than a promised calendar. No broad ecosystem
module should delay the current record-upload-analysis-results flow.
