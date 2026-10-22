FROM python:3.12.15-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
RUN pip install --no-cache-dir uv==0.4.18
WORKDIR /app
COPY infra/requirements/test.lock /tmp/requirements.lock
RUN uv pip install --system --require-hashes -r /tmp/requirements.lock
COPY packages/ packages/
COPY services/ services/
RUN uv pip install --system --no-deps --no-build-isolation \
    ./packages/contracts ./packages/providers ./packages/movement \
    ./packages/scoring ./packages/benchmarks ./services/api
COPY pyproject.toml ./
COPY tests/ tests/
COPY data/exercise_specs/ data/exercise_specs/
COPY data/review_configs/ data/review_configs/
COPY scripts/ scripts/
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["sh", "scripts/check-python.sh"]
