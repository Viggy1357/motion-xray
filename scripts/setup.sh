#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -e "$repo_root/.env" ]]; then
  (umask 077; cp "$repo_root/.env.example" "$repo_root/.env")
fi
docker compose -f "$repo_root/infra/compose.yaml" build "$@"
