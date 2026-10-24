# Repeatable browser QC

Run from a checkout with Docker available:

    ./scripts/check-browser.sh

The script builds a cached test image and runs an ephemeral container. No host
Node/Python/browser installation is needed. First build downloads dependencies;
subsequent builds reuse layers. The wrapper forwards Playwright arguments:

    ./scripts/check-browser.sh --project=mobile360
    ./scripts/check-browser.sh --grep "Settings"
    ./scripts/check-browser.sh --list

Reports are ignored local artifacts:

- artifacts/browser-qc/results.json: structured assertions and outcomes.
- artifacts/browser-qc/html/index.html: human-readable report.
- artifacts/browser-qc/test-results/: failure screenshots and retained traces.
- Video capture is off. Successful tests do not retain screenshots/traces.

Read the delivery audit for actual executed counts. Listing tests or building an
image is not a passed browser test.

## Isolation and scope

The production Next.js frontend and headless Chromium share one container, using
127.0.0.1:3000. Runtime networking is disabled. No host ports, credentials, private
clips, user browser profiles, server state or application source mounts are exposed.
Compose explicitly uses /dev/null as its environment file. Only the ignored results
folder is mounted. The normal local app/worker stack is not stopped or changed.

Each test gets a fresh Playwright browser context. API/session is a test fixture;
all other API requests and external requests are aborted and fail the test. No paid
coaching or real uploads are allowed. The camera is Chromium's synthetic test device,
with the browser's actual MediaRecorder. This is not a physical camera grant.

Projects exercise Chromium at360x820,375x820 and1365x900 CSS pixels. They do not claim
Safari/iOS/Android compatibility. Assertions cover onboarding, local Settings,
empty Progress, camera absence/denial, consent separation, countdown cleanup,
short-clip review and selected responsive layout controls. No generated pose, score
or coaching response is substituted for measured output.

Physical camera permissions, hardware switching/background interruption, the complete
original26-case acceptance matrix, real processing and professional technique
validation remain separate. Keep the release PR draft until its open gates close.

## Dependencies and provenance

- Official Playwright Docker image v1.64.0-noble, pinned by digest in the Dockerfile.
- @playwright/test1.64.0 matches that browser image; Apache-2.0.
- TypeScript5.6.2; Apache-2.0. @types/node20.16.11; MIT.
- pnpm9.12.1 matches the app. The app uses its existing frozen lockfile.
- Tests have a separate package-lock.json and npm ci; no production dependency added.

Official guidance: https://playwright.dev/docs/docker and
https://playwright.dev/docs/mock-browser-apis. Browser binaries/system packages retain
their respective upstream notices in the official image. Trusted local testing only.

To update versions, update the test package and matching image together, generate
the lock in a Docker container, then rebuild and rerun. Never generate a lock by
guessing integrity hashes.

Prefer this command and a compact failure summary before interactive computer use.
A small final visual/device check is still useful. Test execution needs no model
decision per click, but orchestration and reviewing results still use allowance;
no percentage of Codex savings has been measured.
