# Motion X Ray — API image (FastAPI).
# Build context is the repo root ('..'); see infra/compose.yaml.
# QUIRK: this image NEVER installs the pose ML extra (mediapipe). The pose stack
# lives only in worker.Dockerfile, so an ML dependency conflict can never break
# the API (DECISIONS.md D002/D003).
FROM python:3.12-slim

# uv for fast, reproducible installs (pinned versions in each pyproject.toml).
RUN pip install --no-cache-dir uv==0.4.18

WORKDIR /app

# Source layout mirrors the repo: installable packages + the api service.
COPY packages/ /app/packages/
COPY services/api/ /app/services/api/

# Install the API and its first-party deps into the system environment.
# NOTE: no '[pose]' extra here — the API must stay ML-free.
RUN uv pip install --system \
    /app/packages/contracts \
    /app/packages/providers \
    /app/services/api

EXPOSE 8000

# Serve the FastAPI app (routes are 501 placeholders until owning tasks land).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
