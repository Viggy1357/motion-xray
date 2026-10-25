# syntax=docker/dockerfile:1
# Isolated Brag (Hyperframes) renderer image. Build context: infra/brag ONLY.
FROM node:22-slim@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      chromium=156.0.8078.47-1~deb12u1 \
      ffmpeg=7:5.1.9-0+deb12u1 \
      ca-certificates=20250419~deb12u2 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/brag

# package-lock.json is generated separately by the integrator using the
# pinned Node container above (npm install --package-lock-only).
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts --no-audit --no-fund

COPY entrypoint.sh /opt/brag/entrypoint.sh
COPY prepare-init.mjs /opt/brag/prepare-init.mjs
RUN chmod 755 /opt/brag/entrypoint.sh

ENV CI=1 \
    DO_NOT_TRACK=1 \
    HYPERFRAMES_NO_TELEMETRY=1 \
    HYPERFRAMES_NO_UPDATE_CHECK=1 \
    HYPERFRAMES_NO_AUTO_INSTALL=1 \
    HYPERFRAMES_SKIP_SKILLS=1 \
    HYPERFRAMES_BROWSER_PATH=/usr/bin/chromium \
    HYPERFRAMES_FFMPEG_PATH=/usr/bin/ffmpeg \
    HYPERFRAMES_FFPROBE_PATH=/usr/bin/ffprobe \
    HYPERFRAMES_EXTRACT_CACHE_DIR=/work/.hyperframes/extract-cache \
    HOME=/tmp/hyperframes \
    HF_NO_BROWSER=1

ENTRYPOINT ["/opt/brag/entrypoint.sh"]
