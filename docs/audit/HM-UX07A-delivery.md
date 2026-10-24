# HM-UX07A — Docker browser QC delivery

24 October2026 · baseline87d3af4 · FR01/02/03/09/10/12 verification.

## Delivered

One command, ./scripts/check-browser.sh, builds a cached production-frontend/test
image and runs headless Chromium with fresh browser contexts. Test dependencies
and their lockfile are separate from the production app. The browser image is
pinned by version and digest. The wrapper passes the real test exit status back
to its caller and forwards normal Playwright arguments.

The container has no runtime network, exposed ports, application credentials,
host browser profiles, private footage or server-state mounts. Its own Next
server runs on loopback. Only /api/session is fulfilled as a test fixture; other
API calls and external requests are recorded, aborted and fail the test. Uncaught
page errors also fail. Real MediaRecorder uses Chromium's synthetic camera input;
no MediaRecorder or pose/score/coaching output is fabricated.

The suite contains ten cases across three Chromium CSS viewports:
360x820,375x820,1365x900. Every layout case verifies the actual project viewport,
preventing a discarded-context-options bug from silently testing1280px instead.

Cases: first-use Continue/unchecked consent; Skip persistence; empty Progress;
Settings Cancel returning to Analyse and discarding draft edits; saved local
profile/goal persistence; missing camera API; denied camera; countdown cancellation
stopping all captured tracks; short recording/review/retake/use with upload still
disabled; page overflow and visible button/link/summary44px targets on four screens.
Native input boxes, native video-player chrome and complete font sizing are not
claimed by the target assertions. WebM positive duration may be Infinity; playable
metadata checks are not a proof of the60-second duration limit.

## Observed verification

- Docker production app build and browser-test TypeScript check pass.
- Main suite:30 passed,0 skipped,0 flaky,0 unexpected; first run33.250s.
- Final cached-wrapper run after enabling forbidOnly:30 pass in32.766s;0 skipped/flaky/unexpected.
- Successful run retained no screenshots or trace archives.
- Negative control: an intentionally attempted POST /api/videos was aborted by the
  fixture, produced the expected unexpected-API assertion and exit1, and retained
  a failure screenshot and trace. Its one failed test is intentional gate evidence,
  not a passing application acceptance case. Negative control source/results stay
  ignored under artifacts; it is not included in the normal suite.
- No interactive computer-use calls, private-media upload or paid product/Tavily call.
- No production application source, scoring threshold or backend contract changed.

Commands and artifacts:
- ./scripts/check-browser.sh
- ./scripts/check-browser.sh --project=desktop
- artifacts/browser-qc/results.json and html/index.html
- artifacts/browser-qc-negative/results.json (expected failure)
- artifacts/development/ux7-browser-final.log and ux7-negative-run.log

## Delegation and limits

Five Nebius development requests;88,489 reported input+completion tokens of the
bounded100k allowance. All usage, including rejected drafts and a reasoning-only
length failure, is retained in ../delegation/HM-UX07A-usage.json.
USD0.929919 conservative task cost, not invoice; aggregate prior maximum plus this
task USD29.95235665, belowUSD70 active ceiling. USD30 backup untouched; account
balance unverified. No measured Codex credit savings are claimed.

MiniMax drafted container/package/runner infrastructure. Initial test drafts and
a partial DeepSeek reroute contained incorrect states/selectors and dropped
viewport options; those parts were rejected. A focused Kimi file completed after
increasing its reasoning-plus-output allowance once. Codex integrated accepted
files, corrected literal UI labels, session allowlist accounting, camera launch
flags and Compose command forwarding, pinned the verified image digest, generated
the lock inside Docker, and ran the checks. No large Codex substitute implementation
was used. Documentation and actual outcomes supersede worker claims.

## Release decision and next task

This is a reusable frontend fixture-browser suite, not the original26 acceptance
gates passing or a physical-device/real-backend certification. The earlier byte-limit
Review mismatch, actual camera hardware/mobile interruption, usable-pose/zero-cycle
reports, storage/network/quota UI faults and full accessibility still need closure.
Keep PR#1 draft. Next HM-UX07B resolves those release gates separately.

Use the scripted suite before interactive inspection; reserve computer use for a
small final visual/device pass or a specific unresolved browser defect. Setup,
scope, version updates and local report paths are in ../BROWSER-QC.md.
