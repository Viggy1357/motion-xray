# Quickstart — detailed 7-step flow

This guide walks a judge or local contributor from a clean clone to a
running stack on `http://localhost:3000`. It is intentionally explicit:
every command, every path, every diagnostic is listed below.

## Prerequisites

- Docker Compose v2 running.
- Git.
- Bash (WSL2 on Windows; native Windows is **not verified**).
- macOS / Linux: only Apple Silicon has been locally verified.
- Network access on first build (dependency + ~9.4MB model download).

## Step 1 — Clone and pin the demonstrated branch

```bash
git clone --branch codex/hm-ux05-mockup-implementation https://github.com/Viggy1357/motion-xray.git
cd motion-xray
```

> The default branch is currently `main` (older checkpoint). The
> demonstrated build lives on `codex/hm-ux05-mockup-implementation`
> until the owner merges a release. A default clone does **not** select
> the demonstrated build.

## Step 2 — Run the canonical quickstart

```bash
./scripts/quickstart.sh
```

What it does:

1. Generates `.env` from `.env.example` with a persistent `SESSION_SECRET`
   (written once, never printed).
2. Downloads the pinned pose model to `models/pose_landmarker_full.task`
   and verifies its SHA256 against
   `data/pose_models/mediapipe-full-v1.json`.
3. Builds and starts `web`, `api`, and `worker` via
   `docker compose -f infra/compose.yaml up --build`.
4. Checks API `/healthz` and the web root inside the Compose network,
   and confirms the worker remains running. Open the host URL below afterward.

The first build downloads dependencies and the ~9.4MB pose model from
the network. Core analysis needs no external inference after preparation; builds may still
contact image registries.

## Step 3 — Verify the model provenance

The model is downloaded from the versioned official URL recorded in
`data/pose_models/mediapipe-full-v1.json`:

- URL: `https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task`
- SHA256: `5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1`
- Size: 9,398,198 bytes (~9.4MB)
- License: Apache-2.0 per the linked model card

The quickstart script verifies the SHA256 after download. No hardcoded
user paths are used; the model lands at `models/pose_landmarker_full.task`
relative to the repo root.

## Step 4 — Confirm the stack is healthy

```bash
docker compose -f infra/compose.yaml ps
docker compose -f infra/compose.yaml logs --tail=50 api
docker compose -f infra/compose.yaml logs --tail=50 worker
```

The exact diagnostics command (no `.env` values printed):

```bash
docker compose -f infra/compose.yaml logs --tail=100 api worker
```

Expected: `api` reports `/healthz` ready; `worker` reports model
initialization complete (not health-only).

## Step 5 — Open the app

Open `http://localhost:3000` in your browser. Upload your own clip
(under60s, under100MiB) or record from the camera on `localhost` (consent
required). No private clip is bundled.

Analysis is deterministic on CPU and may take several minutes per clip;
no ETA is shown.

## Step 6 — (Optional) Enable grounded Nemotron coaching

Coaching is **off** by default. To enable it:

1. Edit `.env`:
   - `ALLOW_LIVE_COACHING=true`
   - `NEBIUS_MODEL_ID=nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`
   - `NEBIUS_API_KEY=<your key>` (server-side only; never printed)
2. Restart the API explicitly so it re-reads `.env`:
   ```bash
   docker compose --env-file .env -f infra/compose.yaml up -d --force-recreate api
   ```

No fake offline coach is provided. With `ALLOW_LIVE_COACHING=false` or
no `NEBIUS_API_KEY`, the coaching path is disabled and the core
perception path still works.

## Step 7 — Stop the stack (preserve state)

```bash
docker compose -f infra/compose.yaml down
```

Do **not** pass `-v`; the state volume holds the SQLite database and
uploaded media.

## Prepare-only mode

```bash
./scripts/quickstart.sh --prepare-only
```

Generates `.env` and downloads/verifies the model without starting the
stack. Use this to pre-warm a fresh clone.

## Troubleshooting

- **Port in use**: stop the conflicting process or change the host port
  mapping in `infra/compose.yaml`.
- **Docker not running**: start Docker Desktop / the daemon and retry.
- **Network / checksum failure**: re-run `./scripts/quickstart.sh`; the
  missing downloads can be retried. A corrupt existing model is never
  overwritten: inspect the reported path, remove only that model if appropriate,
  then rerun.
- **Windows native**: not verified. Use WSL2 on Windows. Apple
  Silicon on macOS is the only locally verified non-x86_64 path.

## Judge key requirement

- The **offline core** (pose + reference comparison) does **not** require
  a runtime NVIDIA call. It does not by itself demonstrate the required NVIDIA/Nebius runtime use.
- The **coaching path** is the required NVIDIA-model call. It is
  **distinct** from the core perception path and is **off** by default.
  Enabling it requires `ALLOW_LIVE_COACHING=true` and a valid
  `NEBIUS_API_KEY`.
