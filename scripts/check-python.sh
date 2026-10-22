#!/bin/sh
set -eu
ruff check --no-cache packages services scripts tests
mypy --cache-dir=/tmp/motion-xray-mypy packages services
python -m pytest -p no:cacheprovider tests/unit tests/contracts tests/integration
python scripts/smoke_nemotron.py
python scripts/smoke_tavily.py
