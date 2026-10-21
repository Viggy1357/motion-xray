# Motion X Ray — pose worker image (isolated ML stack).
# Build context is the repo root ('..'); see infra/compose.yaml.
# This image owns the pose ML dependencies (mediapipe via the providers '[pose]'
# extra) and ffmpeg for frame extraction. It is intentionally separate from the
# API image so the ML stack can never break the API (DECISIONS.md D002/D003).
FROM python:3.12.15-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258

# ffmpeg is required for deterministic frame/timestamp extraction.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# uv for fast, reproducible installs (pinned versions in each pyproject.toml).
RUN pip install --no-cache-dir uv==0.4.18

WORKDIR /app
COPY infra/requirements/worker.lock /tmp/requirements.lock
RUN uv pip install --system --require-hashes -r /tmp/requirements.lock

# Source layout mirrors the repo: installable packages + all services.
COPY packages/ /app/packages/
COPY services/ /app/services/

# Install the first-party packages plus the pose ML extra (mediapipe). The
# '[pose]' extra is what makes this the ONLY image carrying the ML stack.
RUN uv pip install --system --no-deps --no-build-isolation \
    /app/packages/contracts \
    /app/packages/providers \
    /app/packages/benchmarks \
    /app/packages/movement \
    /app/packages/scoring

ENV PYTHONPATH=/app/packages/contracts:/app/packages/providers:/app/packages/benchmarks:/app/packages/movement:/app/packages/scoring:/app/services/api

# The worker claims jobs from the durable queue; it never serves HTTP.
CMD ["python", "services/pose/worker.py"]
