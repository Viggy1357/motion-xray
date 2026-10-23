# HM-UX01 — analysis-first UI draft and experience blueprint

23 October 2026, Malaysia time. Status: **draft delivered for owner review**;
production integration remains a separate task.

## Delivered

- `apps/web/public/ui-draft/index.html`, `styles.css`, `app.js`: separate light UI
  prototype, served by the existing web service at `/ui-draft/index.html`.
- Original procedural 3D companion; region selection, rotation buttons/keyboard,
  optional auto-rotation and appearance dialog. Companion is never analysis evidence.
- Four exercise intake examples; local-only file-preview code; explicitly simulated
  processing/replay, measurements, cue and provisional comparison.
- Save-only example recognition, fixed fixture identity per exercise, duplicate save
  disabled, validated isolated browser state, regional progress and history.
- `docs/design/HM-UX01-experience-blueprint.md`: current decisions vs proposals,
  screen/state flow, six delivery packages, existing API boundaries, MVP cut lines,
  acceptance and gated future roadmap.
- Review guide, desktop/mobile screenshots and pinned Three.js MIT attribution.
- Earlier `.mockups/` and HM09 exploration retained with current-direction pointers.

## Verification performed

- Existing Docker web container: `node --input-type=module --check` on `app.js` passed.
- HTTP checks: working `/`, draft HTML/CSS/JS and local Three.js module all returned200.
- In-app browser: Home region selection updated selected exercise and filming guidance;
  navigation, appearance dialog and front/back controls operated without console errors.
- Example intake -> explicitly simulated stage -> Results completed. Cue replay sought
  to the expected sample moment (3.0s). No live analysis or provider call occurred.
- Explicit save created exactly one Back example event. Duplicate save was disabled;
  Progress showed one event and the same history survived page refresh.
- Limited visibility: replay hidden, missing value and reason shown, recognition disabled.
- Failure: measurements, comparison and save UI hidden; retry path retained.
- Coaching unavailable: example measurements retained and cue absent.
- Expired video: replay unavailable, measurements retained.
- Desktop1365x1000 and phone375x812 checked; phone scroll width matched375px viewport.
  Screenshots retained in `docs/design/previews/`. Viewport override reset afterwards.
- `git diff --check` and staged whitespace check passed. Scoped source secret scan
  found no key/token/private-key patterns; no credentials, raw media, private pose
  or ignored worker outputs staged.

## Review corrections

Nebius supplied blueprint, prototype and focused repairs. Integrator corrected
server-vs-browser privacy copy, post-set coaching semantics, missing-state handling,
local fixture save identity, unsupported sample metric claims, region selection,
canvas fitting/cleanup, fallback visibility and input semantics. Final minor visual
refinements improve the companion silhouette and lighting. The draft uses standard
geometry rather than a final character art asset.

## Limits / next work

- Example data only. No production API, upload, measurement config, score or schema
  changed. No claim of scientific validation, anti-cheat or measured retention.
- WebGL-unavailable, blocked-storage and reduced-motion branches were reviewed in
  source; fault injection and real phone Safari/Android tests were **not** performed.
- Local video preview was reviewed in source; no private video was selected/uploaded
  during browser QA. Full production app test suite was not rerun for static draft assets.
- Recognition rule, milestones, final character asset and appearance remain proposals.
  Stronger cross-upload duplicate detection and server recognition are future work.
- Next: owner reviews draft; then HM-UX02 shell / HM-UX03 real intake/results bridge,
  preserving the technical thread's working contracts and honesty gates.

## Provider accounting

Three sequential source-only Nebius Kimi-K3 calls:56,240 total tokens;
USD0.587676 at conservative guard rates (not invoice cost). Aggregate prior maximum
commitments retained: USD15.54938365 against USD70 active ceiling; USD30 backup unused.
No runtime coaching, Tavily, hosting or additional provider calls. Ledger:
`docs/development-usage-HM-UX01-2026-10-23.json`.
