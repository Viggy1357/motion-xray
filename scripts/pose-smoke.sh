#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACTS_DIR="${REPO_ROOT}/artifacts"
IMAGE="motion-xray-worker"

mkdir -p "${ARTIFACTS_DIR}"

if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    echo "ERROR: Docker image '${IMAGE}' not found." >&2
    echo "Build it with: docker compose -f infra/compose.yaml build worker" >&2
    exit 1
fi

docker run --rm \
    --network none \
    -v "${REPO_ROOT}:/workspace:ro" \
    -v "${ARTIFACTS_DIR}:/out" \
    -w /workspace \
    -e PYTHONPATH=/workspace/packages/providers:/workspace/packages/contracts \
    --entrypoint python \
    "${IMAGE}" \
    -m scripts.pose_smoke "$@"
