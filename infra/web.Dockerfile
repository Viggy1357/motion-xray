# Motion X Ray — web client image (Next.js / TypeScript).
# Build context is the repo root ('..'); see infra/compose.yaml.
FROM node:22-slim@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392

# pnpm via corepack (version is pinned in apps/web/package.json 'packageManager').
RUN corepack enable

WORKDIR /app/apps/web

# Install dependencies first for better layer caching, then copy the source.
COPY apps/web/ /app/apps/web/
RUN pnpm install --frozen-lockfile

EXPOSE 3000

# Dev server for the local stack (mounted source is hot-reloaded via compose).
CMD ["pnpm", "dev"]
