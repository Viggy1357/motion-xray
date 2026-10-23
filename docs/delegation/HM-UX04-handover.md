# HM-UX04 Development Handover

Baseline: 80a3978 clean main. Mockup reference: [approved board](../design/previews/HM-UX02-concept.png).
Authorization: owner approves planning/spec only. Implementation is NOT authorized by this document. No model comparison or benchmark claims.
Design system: UIUXProMax cobalt direction already approved; do not restart. No Addy skills.
Planning media: NVIDIA SuperVL generated reference only, not real media. Codex review and current NVIDIA vision draft are context, not proof of visual superiority and not a new model design benchmark. UI polish is not clinical proof.
Budget: see docs/development-usage-HM-UX04-2026-10-23.json. Normal task allowance200k, justified one-off ceiling500k; USD70 active/USD30 protected. Planning cost is not a new implementation reservation or verified invoice.
Team: max 3 independent workers, one writer. Model roles are PROPOSED only.

## FR scope (product only)

FR01 capture (proposed next MVP for mockup parity; implementation not approved), FR02 upload, FR03 lifecycle, FR04 pose, FR05 segments, FR06 catalogue, FR07 reference, FR08 score, FR09 coaching, FR10 viewer, FR12 status honesty. Do not invent other FRIDs.

## Phases and work packages

### Phase 0: Spec approval + bounded visual screen check
Inputs: this spec, baseline 80a3978, mockup ../design/previews/HM-UX02-concept.png.
Outputs: reviewed specification; one visual screen check proposed, not dispatched.
Depends: none.
Acceptance: stakeholder sign-off; mockup path and parity matrix verified.
Cutline: no application code changes.

### Phase 1: Capture controller + UI (UX4-02)
FRs: FR01.
Inputs: capture spec, existing upload pipeline.
Outputs: Record a set flow; permission handling; countdown; 60s/100MiB stop; review/retake/cancel; resource release; camera state table C00–C11 and error rows.
Files: apps/web/app/components/CaptureController.tsx, apps/web/app/hooks/useCameraCapture.ts, apps/web/app/components/CountdownOverlay.tsx, apps/web/app/components/ReviewCard.tsx.
Owner: capture engineer (worker 1).
Depends: Phase 0.
Acceptance: all C-state gates traceable; capture requires owner implementation authorization and device capability checks; reuse the existing upload contract without inventing a backend prerequisite.
Fallback: Keep Choose video only; Record remains disabled behind feature flag.
Before each future batch reserve a justified token/cost bound in the shared ledger; the planning-call cost is not a batch budget.

### Phase 2: Player active interval / review card adapter (UX4-03)
FRs: FR05, FR09, FR10.
Inputs: results spec, existing coaching POST, PTS map.
Outputs: playback segment adapter, review card, coaching highlight card (1 card, 1–2 cues), evidence thumbnail adapter, measurements link.
Files: apps/web/app/components/ReviewCardAdapter.tsx, apps/web/app/hooks/useSegmentPlayback.ts, apps/web/app/components/CoachingHighlightCard.tsx, apps/web/app/pose-overlay.ts (existing, integrator-owned; consume its mapping functions).
Owner: results engineer (worker 2).
Depends: Phase 0; UX4-04 for image thumbnail data adapter (does not block all code).
Acceptance: parity matrix rows P15–P21 pass; no null-as-zero; no fabricated cues; coaching POST contract unchanged.
Fallback: coaching card absent; neutral summary shown.

### Phase 3: Owner thumbnail / local metadata (UX4-04)
FRs: FR03, FR12.
Inputs: progress/settings spec, existing PTS map/proxy routes.
Outputs: owner-scoped in-memory thumbnail service, PTS map integration, local history metadata v1 migration, weekly goal opt-in storage.
Files: apps/web/app/lib/thumbnailService.ts, apps/web/app/lib/historyMigration.ts, apps/web/app/hooks/useLocalGoal.ts.
Owner: metadata engineer (worker 3).
Depends: Phase 0.
Acceptance: migration preserves unknown nulls with proof; atomic writes; no base64/faces in localStorage; revocation/expiry implemented.
Fallback: thumbnail service degrades to text placeholder; no durable thumbnail endpoint claimed.

### Phase 4: Home progress / settings presentation (UX4-05)
FRs: FR06, FR09, FR12 plus the local-history extension; no reference/scoring change.
Inputs: home/progress/settings spec.
Outputs: home last-focus card with thumbnail, weekly goal opt-in UI, progress region bars, recent sessions, View all, settings guest/local UI.
Files: apps/web/app/components/HomeLastFocus.tsx, apps/web/app/components/ProgressRegionBars.tsx, apps/web/app/components/SettingsGuest.tsx.
Owner: UX lead / writer (shared, disjoint source).
Depends: Phase 0, UX4-04.
Acceptance: parity matrix rows P01–P07, P22–P28 pass; mobile 375/360 and desktop 1365 layouts verified.
Fallback: text placeholders; rolling 7 unchanged.

### Phase 5: Final acceptance (UX4-06)
FRs: all.
Inputs: all prior packages, spec acceptance gates.
Outputs: executed acceptance gates (26 GWT cases), parity matrix sign-off, handover closure.
Depends: UX4-01 through UX4-05.
Acceptance: all26 gates pass, or an explicit owner-accepted deviation is recorded; no auto export/publish or unsupported backend fields. A capability fallback must be recorded as a device limitation, not full camera parity.
Cutline: stop milestones before core camera and review are complete.

### UX4-01: Art / control contract decision
FRs: FR06/FR10 presentation only; no pose or scoring changes.
Inputs: mockup, art contract.
Outputs: character front/back coherence decision; asset choice gate; high-quality mesh art gate.
Owner: art lead.
Acceptance: explicit gate recorded; no dummy placeholder shipped. Initial model visual pilot is one screen PROPOSED, no already-compared claim.

## File ownership

- docs/design/HM-UX04-screen-state-spec.md: UX/design.
- docs/delegation/HM-UX04-handover.md: delivery lead.
- Existing app direct paths preserved: page.tsx and globalCSS are integrator-owned only; workers must not modify them in parallel.

## Constraints

- No new dependencies without pinned license check.
- Reuse current pipeline; backend evidence gaps called out, not filled by UI claims.
- Camera browser compatibility, secure context, and mobile codec tests are requirements, not current certification.
- Freeze mockup and baseline.
- Future clinical/PT review is a separate technical thread.
- Thumbnails require permissions, data retention, and PTS before implementation; durable thumbnail endpoint is a backend gate.
- No autosaving browser media; no automatic goal of 3.
- Harness validates docs only, not device tests.
- Max 3 workers; disjoint source; do not parallel modify page.tsx.

## Open product decisions (max 5)

1. Main companion: controllable high-quality mesh versus matching front/back renders as an explicit interim option. Current single poster and separate primitive map do not pass parity. Resolve before art integration.
2. Evidence links: validated existing segment-prefix adapter versus versioned structured IDs. Reuse the adapter first; omit unsupported links. No invented source IDs.
3. Calendar week Mon–Sun vs rolling 7: explicit decision; default rolling 7 until implemented.
4. Facing mode: rear/environment recommended; front toggle where available.
5. Audio: off by default; no microphone permission unless granted.

## Ready-to-run prompt

Read docs/design/HM-UX04-screen-state-spec.md, this handover, current TASKS/AGENTS and the current diff. Inspect the existing services/contracts; preserve the80a3978 UI baseline and generated concept. This packet authorizes planning only: verify direct owner authorization for the bounded implementation slice before dispatch; do not infer it from these documents. Use disjoint workers and one integrating writer; no private footage in provider prompts, no paid product calls from rendering. Implement and verify one package before claiming parity. Do not create new user-owned chats unless explicitly requested.
