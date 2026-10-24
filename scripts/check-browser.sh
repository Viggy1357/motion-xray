#!/bin/sh
# scripts/check-browser.sh — POSIX sh wrapper that runs the browser-QC
# suite inside the dedicated container. It does NOT start the web server
# itself: the Playwright config owns the production server lifecycle via
# its webServer block, so the same image can be reused for `list`,
# `grep`, or single-file runs without leaking processes.
#
# Responsibilities:
#   1. Resolve the repository root from this script's location.
#   2. Ensure the artifacts directory exists.
#   3. Build the browser-qc image (idempotent).
#   4. Run the container with `docker compose run --rm --no-deps`,
#      forwarding "$@" to Playwright.
#   5. Propagate the real exit status.
#
# The script never touches the user's docker stack, never reads .env,
# and never installs browsers at runtime (the base image already provides
# the matching Chromium for @playwright/test 1.64.0).

set -eu

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
COMPOSE_FILE="${REPO_ROOT}/infra/browser-checks.yaml"
ARTIFACTS_DIR="${REPO_ROOT}/artifacts/browser-qc"

log() {
  printf '[browser-qc] %s\n' "$*"
}

mkdir -p "${ARTIFACTS_DIR}"

log "building browser-qc image"
docker compose --env-file /dev/null -f "${COMPOSE_FILE}" build browser-qc

log "running browser-qc (args: $*)"
docker compose --env-file /dev/null -f "${COMPOSE_FILE}" run --rm --no-deps browser-qc npx playwright test "$@"
