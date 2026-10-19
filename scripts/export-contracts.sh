#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
docker compose -f "$repo_root/infra/checks.yaml" build python web
docker compose -f "$repo_root/infra/checks.yaml" run --rm --no-deps \
  -v "$repo_root:/app" \
  -e PYTHONPATH=/app/packages/contracts:/app/packages/providers:/app/packages/benchmarks:/app/services/api \
  python sh -c 'python scripts/export_openapi.py packages/contracts/openapi.json && python -m contracts.schema_export packages/contracts/schemas'
docker compose -f "$repo_root/infra/checks.yaml" run --rm --no-deps \
  -v "$repo_root:/repo" web \
  pnpm exec openapi-typescript /repo/packages/contracts/openapi.json -o /repo/apps/web/generated/api.d.ts
