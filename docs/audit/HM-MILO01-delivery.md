# HM-MILO01 — Milo Pip local delivery

25 October 2026. Selected design: Milo Pip. Local candidate verified; owner visual
review remains useful. No deployment or public release performed.

## Delivered behaviour

- Home shows Pip; compact versions accompany processing/results. The separate body
  map is retained. Show Milo in Settings persists across reload; off restores the
  original Home athlete.
- Three layered head actions: gentle idle movement, attentive tilt, encouraging nod.
  No blink, paw wave, exercise imitation, rigged 3D, voice, XP or progression claim.
- A newly submitted analysis can trigger one acknowledgement when the existing
  recognition predicate confirms matching movement evidence, a completed cycle and
  a measured metric. Partial reports stay attentive; failure/cancellation/error stays
  static; recording hides the companion. Reopened old reports do not get a new reward.
- The renderer owns bounded session event deduplication and the 1.6s cheer timeout.
  Save keeps its existing confirmation rather than triggering a second celebration.
- Reduced-motion preferences and page visibility suppress animation. Missing layers
  fall back to the neutral asset, then a small decorative placeholder if unavailable.
- `/milo-preview` is the isolated action/fallback/reduced-motion review surface.

## Assets and implementation

Built-in imagegen produced a neutral master, headless body and isolated head from the
selected original concept. Container FFmpeg converted these to three alpha WebP files,
768 square, **212,842 bytes total**, with hashes and provenance in
`apps/web/public/companion/milo-pip/provenance.json`. Source PNGs stay in ignored local
artifacts. Geometry is fixed-view layered artwork, not an animation rig or model training.

Main files: `components/MiloCompanion.tsx`, its CSS module, `lib/milo-assets.ts`,
`milo-preview/page.tsx`, `page.tsx`, `globals.css`, `lib/ux-metadata.ts`, and
`components/SettingsPanel.tsx`, under `apps/web/app`.

`lib/milo-state.ts` plus `scripts/check-milo-state.cjs` provide a standalone tested
controller utility. The shipped app uses the narrow direct adapter in `page.tsx` and
renderer deduplication; those utility tests must not be presented as end-to-end proof
of the app adapter. Browser coverage verifies the renderer and integration separately.

## Checks actually run

- `./scripts/check-browser.sh`: **87/87 passed in 53.1s**, Chromium at 360, 375 and
  1365 widths. Existing capture/consent/recording, results seek/thumbnail and navigation
  regressions remain passing. New tests cover visible layout, persistent hide setting,
  idle/attentive/cheer, same-key replay suppression, reduced motion and asset fallback.
- Docker: `node scripts/check-milo-state.cjs` — 49 passed;
  `node scripts/check-ux-metadata.cjs` — 13 passed; `pnpm typecheck` — exit 0.
- `./scripts/test.sh web` — exit 0, lint/typecheck and production build. Final browser
  image also compiles/lints/builds the final source including the last preview fix.
- `git diff --check` — clean. Desktop and mobile rendered screenshots inspected.

Logs: `artifacts/development/milo-browser-final-pass.log`, `milo-final-unit-types.log`,
`milo-web-final.log`. Screenshots: `artifacts/browser-qc/milo-home-desktop.png`,
`milo-home-mobile375.png`, and corresponding `milo-preview-*` files.

## Delegation and accounting

All substantive drafts came from scoped Nebius workers. MiniMax-M3 supplied most
drafts; DeepSeek-V4-Pro handled bounded correctness/integration attempts. Rejected and
repaired drafts remain accounted. No specialized VL call was needed. Codex forwarded
packets, inspected scoped output, ran container checks and made narrow integration
corrections to identifiers/anchors, expectation mismatches, asset frame/source handling,
settings merging and preview prop wiring. No measured Codex-savings claim is made.

Usage: **289,095 reported tokens**, **USD2.038989 conservative guard cost**, not invoice
cost. Initial 200k envelope increased to 300k for demonstrated repair/verification work
under existing justified one-off authority. Shared known maximum commitment including
the concurrent audit is USD34.49088265 against the USD70 ceiling; USD30 backup untouched.
Actual account balance/other unknown concurrency remain unverified. Full records:
`docs/delegation/HM-MILO01-usage.json`. Three imagegen calls have separate, unverified
billing. No added paid product-runtime or Tavily calls; no private media sent to workers.

## Limits and next work

This is a fixed-view 2D companion. No fresh human-video analysis or live coaching call
was rerun in this task; browser fixtures do not prove pose accuracy or physical-device
coverage. No changes to measurement thresholds, scores, public schemas or runtime quotas.
Known retained feature limits from earlier delivery remain applicable.

Disable via Settings > Show Milo; rollback the coherent Milo commit if needed. No data
migration required. Next: HM-RELEASE03 judge access/release readiness and owner visual
feedback. Leave unrelated concurrent BRAG audit files outside the Milo commit.
