#!/usr/bin/env bash
# Brag (Hyperframes) wrapper: isolated Docker renderer.
# No cloud, no paid/remote media providers, no host secrets, no repo mounts.
set -euo pipefail

IMAGE="motion-xray-brag:0.8.195"
ALLOWED_CMDS="version doctor init lint check snapshot render preview timeline info compositions catalog add ffmpeg ffprobe"
BLOCKED_FLAGS="--docker --cloud --lambda --cloudrun"
# User-controllable flags that would break the controlled preview/runtime.
RESERVED_PREVIEW="--port --host --background"

repo_root() {
  local d
  d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  (cd "$d/.." && pwd)
}

usage() {
  cat <<'EOF'
Usage: scripts/brag.sh setup
       scripts/brag.sh <command> [args...]
       scripts/brag.sh init            # scaffolds into '.' (only target allowed)

Commands (allowlist): version doctor init lint check snapshot render preview
                      timeline info compositions catalog add
Notes:
  - 'setup' builds the pinned image only; it never renders.
  - 'preview' is forced to --port 4173 --foreground --no-open; user
    --port/--host/--background overrides are rejected.
  - All commands except 'preview' run with --network none.
  - Output dir: BRAG_OUTPUT_DIR must be 'brag-output' or 'brag-output-<safe>'.
EOF
}

reject_flag() { echo "brag: rejected flag '$1' ($2)" >&2; exit 2; }

reject_blocked() {
  local a b
  for a in "$@"; do
    for b in $BLOCKED_FLAGS; do
      case "$a" in
        "$b"|"$b"=*) reject_flag "$a" "no cloud/remote execution" ;;
      esac
    done
    case "$a" in
      --paid|--paid=*|--paid-media|--paid-media=*|--heygen|--heygen=*)
        reject_flag "$a" "no paid/remote media providers" ;;
    esac
  done
}

reject_preview_overrides() {
  local a b
  for a in "$@"; do
    for b in $RESERVED_PREVIEW; do
      case "$a" in
        "$b"|"$b"=*) reject_flag "$a" "preview port/host/foreground are controlled" ;;
      esac
    done
  done
}

validate_output_dir() {
  local root="$1" name="${BRAG_OUTPUT_DIR:-brag-output}"
  case "$name" in
    brag-output|brag-output-*) ;;
    *) echo "brag: BRAG_OUTPUT_DIR must be 'brag-output' or 'brag-output-<safe>'" >&2; exit 2 ;;
  esac
  case "$name" in
    */*|*..*|.*) echo "brag: BRAG_OUTPUT_DIR must be a simple basename" >&2; exit 2 ;;
  esac
  if [ "$name" != "brag-output" ]; then
    case "${name#brag-output-}" in
      *[!A-Za-z0-9._-]*|"") echo "brag: unsafe characters in BRAG_OUTPUT_DIR suffix" >&2; exit 2 ;;
    esac
  fi
  local path="$root/$name"
  [ -L "$path" ] && { echo "brag: output dir must not be a symlink" >&2; exit 2; }
  mkdir -p "$path/composition"
  [ -L "$path/composition" ] && { echo "brag: composition dir must not be a symlink" >&2; exit 2; }
  printf '%s' "$path"
}

require_image() {
  if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "brag: image '$IMAGE' not built. Run: scripts/brag.sh setup" >&2
    exit 3
  fi
}

cmd="${1:-}"
case "$cmd" in
  ""|-h|--help|help) usage; exit 0 ;;
  setup)
    root="$(repo_root)"
    docker build --tag "$IMAGE" -f "$root/infra/brag/Dockerfile" "$root/infra/brag"
    exit 0
    ;;
  --version) cmd="version"; shift; set -- version "$@" ;;
esac

reject_blocked "$@"

found=0
for c in $ALLOWED_CMDS; do
  if [ "$cmd" = "$c" ]; then found=1; break; fi
done
if [ "$found" -ne 1 ]; then
  echo "brag: command '$cmd' not allowed. Allowed: $ALLOWED_CMDS" >&2
  exit 2
fi
shift

# init is restricted to the current composition dir ('.'); --help passes
# straight through to the CLI and skips the offline prepare step.
if [ "$cmd" = "init" ]; then
  case "${1:-}" in
    -h|--help) ;;
    "") set -- "." ;;
    .) ;;
    *) echo "brag: init target must be '.' (no arbitrary dirs, no global flags)" >&2; exit 2 ;;
  esac
fi

# Official CLI has no 'version' subcommand; map to the --version flag.
if [ "$cmd" = "version" ]; then
  cmd="--version"
fi

root="$(repo_root)"
require_image
out="$(validate_output_dir "$root")"

base_args=(
  --rm --init --read-only
  --cap-drop=ALL
  --security-opt=no-new-privileges
  --shm-size=1g
  --tmpfs /tmp:rw,nosuid,size=1g
  --user "$(id -u):$(id -g)"
  --mount "type=bind,src=$out,dst=/work"
  --workdir /work/composition
  -e TMPDIR=/work
)

if [ "$cmd" = "preview" ]; then
  reject_preview_overrides "$@"
  # Network exception: bridge, localhost-bound port 4173. HYPERFRAMES_PREVIEW_HOST
  # is read by the official CLI; HF_NO_BROWSER (image env) suppresses auto-open.
  exec docker run "${base_args[@]}" --network bridge \
    -e HYPERFRAMES_PREVIEW_HOST=0.0.0.0 \
    -p 127.0.0.1:4173:4173 "$IMAGE" "$cmd" \
    --port 4173 --foreground --no-open "$@"
else
  exec docker run "${base_args[@]}" --network none "$IMAGE" "$cmd" "$@"
fi
