# HM-UX09 delivery —24 October2026

Baseline b716bf0, existing codex/hm-ux05-mockup-implementation branch.
Owner authorizes source-video segment thumbnails, smooth transitions, unchanged
Home athlete, focused final QC, roadmap updates and push. No merge/deploy implied.
FR01/02/03/10/12; one integrating writer. Nebius drafts substantive implementation,
test cases and first-pass review; Codex integrates and runs local checks.

## Delivered

- Completed-cycle buttons include full-frame video previews at measured segment
  start times. Reuse existing timestamp mapping, authenticated proxy access,
  memory cache/invalidation and missing-media fallback. Clicking still seeks by
  source time. No generated evidence, crop inference or new API endpoint.
- Main-content220ms cross-fade through progressive native View Transitions,
  restrained180ms control feedback and existing focus semantics. Static Home
  artwork retained. No anatomical morph/character animation. Reduced motion,
  unsupported APIs and active video/camera skip transitions. Once guard prevents
  history duplication after transition failures. No new dependencies/contracts.
- Roadmap updated;3D and loading content deferred. Ask your set/Show me why excluded.

## Verification

- ./scripts/test.sh web: exit0, type generation/typecheck and production build
  including framework lint pass.
- ./scripts/check-browser.sh: exit0,54 passed in48.4s.18 cases across360/375/1365
  Chromium viewports. Original30 regression checks plus24 new checks. Synthetic
  canvas/MediaRecorder WebM is actually decoded into thumbnail with4:3 native
  aspect verified; source seek, missing-map fallback, results overflow, reduced
  motion and throwing transition API tested. Recording/review/retake and track
  cleanup regression tests remain green. No runtime API spending.
- Follow-up ./scripts/check-browser.sh --grep 'renders decoded segment image':
  exit0,3 passed in3.4s after adding visual evidence capture. Inspected360px and
  desktop screenshots under ignored artifacts/browser-qc/ux9-segments-*.png.
  Fixture uses a blue video and intentionally missing pose, not user media.
- Nebius final correctness review: no blocking findings, minor CSS maintainability
  notes only. git diff --check passes. No full Python rerun: backend unchanged.

## Limits and next

Owner personally tested Mac camera->record->upload->processing and accepts MVP.
Broad hardware/browser and network/storage/quota/result-edge testing stays deferred,
not passed. This does not establish calibrated scoring or clinical validation.
PR remains draft; branch push is not merge or deployment. Next HM-RELEASE01 is
judge access/hosting/submission readiness and deferred reliability work.

Seven Nebius calls216,021 reported tokens, including one truncated response;
USD1.348455 conservative cost, not invoice. Justified300k one-off under existing
500k authorization; aggregate maximum including UX08 planningUSD31.51024765<70.
Protected30 untouched. No private media sent, no paid product runtime/Tavily calls.
Sanitized accounting: docs/delegation/HM-UX09-usage.json.
