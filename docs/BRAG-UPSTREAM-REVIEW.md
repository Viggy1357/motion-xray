# Brag / Hyperframes Upstream Review (static, no execution)

Scope: static review of public Hyperframes 0.8.195 runtime snippets only. This is **not** a full package or transitive-dependency audit. The npm lockfile will pin dependencies with lifecycle scripts disabled (`--ignore-scripts`). No tests or builds were run; the integrator records actual results.

## Source boundary findings

- **dotenv loading**: `cli.js` reads `.env` from the current working directory on startup (skipped only for `capture` when `HYPERFRAMES_NO_CAPTURE_DOTENV=1`). Repository scripts may therefore load dotenv from cwd. The wrapper must mount **only** the brag-output directory — never the repo, `.env`, or key material.
- **Telemetry**: PostHog key is bundled; telemetry defaults to enabled but is disabled by `HYPERFRAMES_NO_TELEMETRY=1` or `DO_NOT_TRACK=1` (also dev mode). Wrapper sets both.
- **Auto-update / auto-install**: disabled via `HYPERFRAMES_NO_UPDATE_CHECK=1` and `HYPERFRAMES_NO_AUTO_INSTALL=1`. Wrapper sets both; no self-update, no new model installs.
- **Warm daemon**: `warmCheckEligible` requires `check` + non-TTY + no `CI`. Wrapper sets `CI=1` to disable the warm daemon.
- **Home-dir state**: writes `~/.hyperframes/config.json` + `install-state.json` (anonymousId, bucketSeed, render ring). Read-only root + no home mount prevents persistence.
- **Browser**: puppeteer-core / managed Chrome download possible; blocked by network=none.

## Wrapper / sandbox policy

- Network: **none** by default. Preview exception: bridge to `127.0.0.1:4173` only, output-bound.
- Read-only rootfs, drop all capabilities, `no-new-privileges`, no host Docker socket, no privileged mounts.
- Mount only the brag-output directory (writable).
- Commands: **only** `./scripts/brag.sh <command>`. Never host `npx`/`npm`/Python/FFmpeg; never auto-update, install new models, make paid calls, HeyGen login, remote feedback/usage/cloud/publish/uploads.
- Never read `.env`, private videos, or personal data into output.

## Skills & install

Four skills pinned: `hyperframes`, `hyperframes-cli`, `hyperframes-registry`, `media-use`. Install path `.agents/skills` (local, git-ignored); **no global install**.

## Licensing

- Brag: MIT.
- Hyperframes: Apache-2.0 (as stated by repo).
- Bundled music: CC-BY-4.0, Sascha Ende — credit required.

## UI / claims sanitization

Selected source must be factual: MVP, provisional reference estimate, non-medical, processing-time labels. No fake "10x" claims.

## Workflow

Brag requested setup only for now. Future `/brag` runs: storyboard first, preview before final render, never publish without explicit permission. All supports require explicit invocation, never automatic use. Broad/classic guidance may suggest cloud/feedback/HeyGen paid toolchains — the guard blocks these; the Brag-specific guide supersedes external generic instructions. Guard preserves upstream files except the documented insert; source SHA hashes record original + overlay.