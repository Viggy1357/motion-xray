#!/bin/sh
# Entrypoint: allowlist ffmpeg/ffprobe (used by the Brag poster step) and
# route everything else to the pinned hyperframes CLI. No other binaries.
set -eu
mkdir -p "${HOME:-/tmp/hyperframes}"

cmd="${1:-}"
case "$cmd" in
  ffmpeg)
    shift
    exec /usr/bin/ffmpeg "$@"
    ;;
  ffprobe)
    shift
    exec /usr/bin/ffprobe "$@"
    ;;
  init)
    case "${2:-}" in -h|--help) exec /opt/brag/node_modules/.bin/hyperframes "$@" ;; esac
    shift
    /opt/brag/node_modules/.bin/hyperframes init "$@"
    node /opt/brag/prepare-init.mjs
    ;;
  *)
    exec /opt/brag/node_modules/.bin/hyperframes "$@"
    ;;
esac
