# Brag (Hyperframes) Quickstart

Isolated, offline-first renderer setup. The environment is **ready for
authoring, checking, and rendering** as soon as you ask — you have not asked
for generation or rendering yet, so nothing has been rendered.

## What this is

- A pinned Docker image (`motion-xray-brag:0.8.195`) containing
  `hyperframes@0.8.195`, Chromium, and ffmpeg/ffprobe, driven through
  `scripts/brag.sh` with a strict command allowlist and a locked-down
  container (read-only root, dropped caps, single output mount).
- No cloud execution, no paid/remote media providers, no telemetry, no host
  secrets, no repo mounts.

## Setup (build image only)

```bash
scripts/brag.sh setup
```

Build context is `infra/brag/` ONLY. Base image `node:22-slim` pinned by
digest; Debian packages (`chromium`, `ffmpeg`, `ca-certificates`) pinned;
`npm ci --omit=dev --ignore-scripts --no-audit --no-fund`. The integrator
generates `infra/brag/package-lock.json` separately with the same pinned
Node container (`npm install --package-lock-only`).

## Verify / init / check

```bash
scripts/brag.sh version        # '--version' also accepted, mapped to 'version'
scripts/brag.sh doctor --json
scripts/brag.sh init .
scripts/brag.sh lint
scripts/brag.sh check
```

`init .` writes only into the mounted output dir (`brag-output/composition/`).

## Output directory rules

`BRAG_OUTPUT_DIR` (default `brag-output`) must be `brag-output` or
`brag-output-<safe>` (`[A-Za-z0-9._-]`), created as a direct child of the
repo root. Absolute paths, slashes, `..`, leading dots, and symlinks (output
or `composition/`) are rejected. Only this directory is mounted (`/work`);
the repo, `.env`, `privatevideo`, `$HOME`, and the Docker socket are never
mounted; no host secret env vars or env-files are passed.

## Runtime isolation

`docker run --rm --init --read-only --cap-drop=ALL
--security-opt=no-new-privileges --shm-size=1g --tmpfs /tmp:rw,nosuid,size=1g
--user <uid>:<gid> --network none`

**Preview exception:** `preview` uses `--network bridge` with
`-p 127.0.0.1:4173:4173` and is forced to `--port 4173 --foreground
--no-open` (user `--port`/`--host`/`--background` overrides are rejected).
`HYPERFRAMES_PREVIEW_HOST=0.0.0.0` (read by the official CLI) plus the
localhost-bound publish make the preview reachable from the host;
`HF_NO_BROWSER=1` (image env) suppresses browser auto-open. The bridge
network can reach outbound — do not pass credentials to preview; only
renders/checks are network-isolated.

## ffmpeg / ffprobe

The entrypoint allowlists `ffmpeg` and `ffprobe` (used by the Brag poster
step); every other command goes to the pinned hyperframes CLI. Note: ffmpeg
cannot fetch URLs at runtime because renders run with `--network none`.

## Offline honesty

`catalog`/`add` run with `--network none`; if they require network they fail
honestly — nothing is auto-fetched.

## Skills restore (fresh machine)

Run from the repo root with the trusted installer
(`~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py`):

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo latent-spaces/brag --path skills/brag \
  --ref 669ab9286aa28b6c3ee30e75f181ee74319d012a --dest .agents/skills
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo heygen-com/hyperframes \
  --path skills/hyperframes skills/hyperframes-cli skills/hyperframes-registry skills/media-use \
  --ref 1776b42736110e29397cd4512cfb1a609c6bbe28 --dest .agents/skills
```

## Guard overlay

A trusted installer integration must apply the instructions in
`infra/brag/skill-guard.md` to the five SKILL.md files (brag, hyperframes,
hyperframes-cli, hyperframes-registry, media-use) via opt-in metadata. The
overlay maps upstream `npx` Hyperframes commands to `./scripts/brag.sh` and
prohibits unpinned `npx` auto-upgrades and remote/paid media.

## Usage (next turn)

Invoke `/brag ...` with a storyboard first. No final render without your
explicit approval. Music credit for any audio: Sascha Ende, CC BY 4.0.

## Verified readiness (25 October2026)

The image is built locally and five project skills are installed with explicit-use
metadata and guard overlays. It will be available on the next turn.38 wrapper tests,
9 Node helper tests and the actual scaffold browser/layout/contrast check pass.
Local preview returned HTTP200 on4173 and was stopped after verification. No MP4
or submission storyboard has been created.

`doctor --json` has overall `ok:false` for optional transcription/voice/MusicGen,
managed-browser unzip and nested Docker. Node/Chromium/FFmpeg/FFprobe pass; our image
uses system Chromium and never needs Docker-inside-Docker. This is ready for local
no-voice authoring; optional providers/models are not installed or activated.

`init .` skips skill freshness installs and localizes the generated GSAP CDN tag to
the renderer's vendored3.15.0 copy. No additional npm package or render-time network
is required. Always initialize through the wrapper; copies generated outside it may
still contain remote assets. Frame extraction cache stays in the output folder.

For the bundled Sascha Ende music, include the CC BY4.0 attribution. Other audio
has its own licensing requirements. See `docs/audit/BRAG-SETUP01-delivery.md`.
