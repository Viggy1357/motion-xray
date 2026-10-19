# OPERATIONS

**Implementation status, 19 Oct:** this runbook contains intended operations, not
verified running services. Upload/jobs/deletion/retention are not implemented, script
entrypoints are stubs, and Python checks fail. See `AUDIT-2026-10-19.md` and T02.1 in
`DELIVERY.md` before using these commands as evidence of readiness.

This is the runbook for operating Motion X Ray locally. Everything runs in containers so
nothing installs on the host beyond Docker Desktop (DECISIONS.md D003). It covers the
Compose commands, environment and secret handling, the data-retention and deletion policy,
and a per-component license / model-terms inventory. Commands are listed here only once
they are verified; do not assume a command works until it appears in this file.

## Compose commands

The Compose build context is the repo root (`..`) with Dockerfiles under `infra/`.

```bash
# Start the full stack (web + api + worker); nothing touches the host
docker compose -f infra/compose.yaml up --build

# Validate the compose file without starting anything
docker compose -f infra/compose.yaml config

# Build the api, worker, and web images
docker compose -f infra/compose.yaml build

# Stop services while retaining state/model volumes
docker compose -f infra/compose.yaml down

# Explicit full reset only: also deletes state, models and web_node_modules volumes
docker compose -f infra/compose.yaml down -v
```

`web` is published on `localhost:3000`, `api` on `localhost:8000`. The `worker` exposes no
port — it leases jobs from the durable queue. In-container checks (once Docker Desktop is
available): `pytest tests/contracts tests/unit`, `ruff check`, `mypy`, and `pnpm install
&& pnpm tsc --noEmit`.

## Environment and secrets

Runtime configuration is read from a `.env` file (copy `.env.example` → `.env`). `.env` is
gitignored and MUST NOT be committed. Secrets are server-side only, read from environment
variables, never behind a public frontend prefix, and never hardcoded. The build must fail
clearly when a selected provider needs an unset credential rather than silently switching
models (AGENTS.md; `.env.example`).

Keys used by the providers:

| Variable | Purpose | Secret? |
| --- | --- | --- |
| `NEBIUS_BASE_URL` | Token Factory OpenAI-compatible endpoint | No |
| `NEBIUS_MODEL_ID` | NVIDIA Nemotron model id (discover from the account catalog) | No |
| `NEBIUS_API_KEY` | Token Factory credential | **Yes** |
| `TAVILY_API_KEY` | Enables operator-triggered evidence refresh | **Yes** |
| `SESSION_SECRET` | Server session signing secret | **Yes** |
| `POSE_PROVIDER` / `POSE_CHECKPOINT_PATH` | Pose provider selection + checkpoint location | No |

Other operational knobs (provisional, revise before hosted release): `MAX_UPLOAD_MB=100`,
`MAX_VIDEO_SECONDS=30`, `WORKER_CONCURRENCY=1`, `JOB_TIMEOUT_SECONDS=300`.

## Retention and deletion

| Data | TTL | Env var |
| --- | --- | --- |
| Raw uploaded media | 24 hours | `RAW_MEDIA_TTL_HOURS=24` |
| Analysis reports / derived artifacts | 7 days | `REPORT_TTL_DAYS=7` |

Deletion flow: raw media expires 24 hours after upload; reports and derived artifacts
expire 7 days after creation. Expiry is reflected in the contracts via `expires_at`
(`VideoAsset`), and a request against expired data returns the `JOB_EXPIRED` error code
(`docs/API.md`). A user can delete an analysis and its private artifacts on demand via
`DELETE /v1/analyses/{analysis_id}`. All durable state lives in the `state` volume, which
`docker compose down -v` removes entirely, leaving no host-level data behind.

## License / model-terms inventory

Each third-party component's license and usage terms must be confirmed against its current
upstream terms before a hosted release; the summary below is for orientation, not legal
advice.

| Component | Role | License / terms (verify upstream) |
| --- | --- | --- |
| MediaPipe Pose Landmarker | Primary pose provider | Apache-2.0 (library); confirm model-asset terms. |
| NVIDIA Nemotron via Nebius Token Factory | Runtime coaching LLM | NVIDIA open-model license + Nebius Token Factory terms; credits metered. |
| Tavily | Operator-triggered evidence search | Tavily API terms of service; retrieved content treated as untrusted. |
| Next.js | Web client framework | MIT. |
| FastAPI | API framework | MIT. |

Paid provider calls (Token Factory, Tavily) run only in authorized environments; CI uses
fixtures and never spends credits (AGENTS.md).
