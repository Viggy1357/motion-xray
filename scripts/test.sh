#!/usr/bin/env bash
set -euo pipefail

# Motion X Ray — run the test suite inside containers (STRUCTURE-ONLY stub).
# Test execution happens inside the images, never on the host.
echo "[test] STRUCTURE-ONLY stub."
echo "[test] TODO(T01): run pytest in the api image, e.g."
echo "[test]   docker compose -f infra/compose.yaml run --rm api \\"
echo "[test]     pytest tests/contracts tests/unit"
echo "[test] Web type-check: pnpm tsc --noEmit (in the web image)."
exit 0
