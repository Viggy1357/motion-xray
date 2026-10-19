#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
case "${1:-all}" in
  python|web) check_services=("$1") ;;
  all) check_services=(python web) ;;
  *) echo "Usage: $0 [all|python|web]" >&2; exit 2 ;;
esac
docker compose -f "$repo_root/infra/checks.yaml" build "${check_services[@]}"
for check_service in "${check_services[@]}"; do
  docker compose -f "$repo_root/infra/checks.yaml" run --rm --no-deps "$check_service"
done
