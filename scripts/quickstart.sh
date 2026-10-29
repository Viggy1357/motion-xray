#!/usr/bin/env bash
# Motion X Ray — bounded local onboarding.
#
# Resolves the repo root regardless of the current working directory, prepares
# .env from .env.example (preserving any existing configuration), downloads the
# pinned pose model with checksum verification, then builds and starts the
# docker compose stack. Supports --prepare-only and --help.
#
# Only configuration preparation and the model download are delegated to scripts/bootstrap_local.py running inside the
# pinned Python 3.12 base image extracted from infra/api.Dockerfile.

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/quickstart.sh [--prepare-only] [--help]

  --prepare-only  Prepare .env and download the pinned model, but do not
                  build or start the docker compose stack.
  --help          Show this help and exit.

Environment:
  COMPOSE_PROJECT_NAME  Optional. Isolates docker compose project state from
                        any other checkout on this host. Defaults to the
                        project name declared in infra/compose.yaml
                        ("motion-xray"). Set a different name AND host ports for another clone.

Examples:
  scripts/quickstart.sh --prepare-only
  scripts/quickstart.sh
USAGE
}

prepare_only=0
for arg in "$@"; do
  case "$arg" in
    --prepare-only) prepare_only=1 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "quickstart.sh: unknown argument: $arg" >&2; usage; exit 2 ;;
  esac
done

# Resolve repo root from this script's location so it works from any cwd.
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

# Prerequisite: docker compose v2 must be available on the host.
if ! command -v docker >/dev/null 2>&1; then
  echo "quickstart.sh: docker is required but was not found on PATH." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "quickstart.sh: docker compose v2 is required (the legacy 'docker-compose' binary is not supported)." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "quickstart.sh: start Docker Desktop or the Docker daemon first." >&2
  exit 1
fi

# Extract the pinned Python 3.12 base image from infra/api.Dockerfile so the
# bootstrap container uses the exact same immutable image as the API service.
api_dockerfile="$repo_root/infra/api.Dockerfile"
if [[ ! -f "$api_dockerfile" ]]; then
  echo "quickstart.sh: expected $api_dockerfile to exist." >&2
  exit 1
fi
python_base="$(awk 'tolower($1) == "from" { print $2; exit }' "$api_dockerfile")"
if [[ -z "$python_base" ]]; then
  echo "quickstart.sh: could not parse FROM line from $api_dockerfile." >&2
  exit 1
fi

# Map host uid/gid into the container so bind-mounted files keep host ownership.
uid_args=()
if [[ -n "${UID:-}" && -n "${GID:-}" ]]; then
  uid_args+=(--user "${UID}:${GID}")
else
  uid_args+=(--user "$(id -u):$(id -g)")
fi

# Forward only the variables the bootstrap script is allowed to see. We do not
# pass any provider credentials; the container reads .env from the bind mount.
run_bootstrap() {
  local prepare_flag="$1"
  docker run --rm \
    "${uid_args[@]}" \
    -e QUICKSTART_PREPARE_ONLY="$prepare_flag" \
    -v "$repo_root:/workspace" \
    -w /workspace \
    --entrypoint python \
    "$python_base" \
    scripts/bootstrap_local.py
}

if [[ "$prepare_only" -eq 1 ]]; then
  run_bootstrap 1
  echo "quickstart.sh: --prepare-only complete. .env and model are ready."
  echo "  Run scripts/quickstart.sh (no flag) to build and start the stack."
  exit 0
fi

# First-time warning: the first build pulls base images and the pinned model.
echo "quickstart.sh: first run will build images and download the pinned pose model." >&2
echo "quickstart.sh: this can take several minutes on a cold cache." >&2

run_bootstrap 0

# Compose orchestration: build, start, then verify health. The compose project
# name is taken from COMPOSE_PROJECT_NAME if set, otherwise from the project
# name declared in infra/compose.yaml (motion-xray). We never derive it from
# the repo path; use COMPOSE_PROJECT_NAME and different ports for another clone.
compose=(
  docker compose
  --env-file "$repo_root/.env"
  -f "$repo_root/infra/compose.yaml"
)

"${compose[@]}" build
echo "quickstart.sh: compose build complete." >&2

"${compose[@]}" up -d
echo "quickstart.sh: compose up -d complete." >&2

# Verify the worker service is actually running. A healthy API/web does not
# matter if the worker is not up.
worker_status="$("${compose[@]}" ps --status running --services 2>/dev/null || true)"
if ! printf '%s\n' "$worker_status" | grep -qx 'worker'; then
  echo "quickstart.sh: worker service is not running." >&2
  echo "quickstart.sh: compose ps output:" >&2
  "${compose[@]}" ps >&2 || true
  echo "quickstart.sh: tail logs with: ${compose[*]} logs --tail=200" >&2
  exit 1
fi

# Health verification: bounded 90 s total budget across both endpoints.
# We use docker compose exec so we do not need curl on the host and we do
# not need to expose the docker socket into the container.
health_deadline=$(( $(date +%s) + 90 ))

check_endpoint() {
  local service="$1" path="$2"
  local now
  while :; do
    now=$(date +%s)
    if (( now >= health_deadline )); then
      echo "quickstart.sh: timed out waiting for $service$path after 90s." >&2
      return 1
    fi
    local remaining=$(( health_deadline - now ))
    if "${compose[@]}" exec -T "$service" python -c "
import sys, urllib.request
try:
    urllib.request.urlopen('$path', timeout=min(5, $remaining)).read()
    sys.exit(0)
except Exception:
    sys.exit(1)
" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
}

if ! check_endpoint api http://127.0.0.1:8000/healthz; then
  echo "quickstart.sh: API /healthz did not become healthy." >&2
  echo "quickstart.sh: tail logs with: ${compose[*]} logs --tail=200 api" >&2
  exit 1
fi

if ! check_endpoint api http://web:3000/; then
  echo "quickstart.sh: web root did not become healthy." >&2
  echo "quickstart.sh: tail logs with: ${compose[*]} logs --tail=200 web" >&2
  exit 1
fi

# Recheck the worker after API/web warm-up, then print shell-quoted commands.
if ! "${compose[@]}" ps --status running --services | grep -qx worker; then
  echo "quickstart.sh: worker exited during startup; inspect worker logs." >&2
  exit 1
fi
printf -v compose_display '%q ' "${compose[@]}"
# Print the local URLs and the stop command. We never dump .env contents.
cat <<NEXT

Motion X Ray is running.
  Web UI:    http://127.0.0.1:3000
  API docs:  http://127.0.0.1:8000/docs

Tail logs:
  ${compose_display}logs -f

Stop the stack (keeps state volume):
  ${compose_display}down

NEXT
