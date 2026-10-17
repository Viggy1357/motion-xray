# Motion X Ray — web client image (Next.js / TypeScript).
# Build context is the repo root ('..'); see infra/compose.yaml.
FROM node:20-slim

# pnpm via corepack (version is pinned in apps/web/package.json 'packageManager').
RUN corepack enable

WORKDIR /app/apps/web

# Install dependencies first for better layer caching, then copy the source.
COPY apps/web/ /app/apps/web/
RUN pnpm install

EXPOSE 3000

# Dev server for the local stack (mounted source is hot-reloaded via compose).
CMD ["pnpm", "dev"]
