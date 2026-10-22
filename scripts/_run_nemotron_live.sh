#!/usr/bin/env sh
# Temporary helper to run the Nemotron live smoke test inside the container.
# Not committed; a dev convenience to avoid fragile inline shell quoting.
# Pin httpx<0.28 because openai==1.51.0 breaks with httpx 0.28's removed
# 'proxies' kwarg (known incompatibility).
set -e
pip install -q "openai==1.51.0" "httpx==0.27.2"
python /scripts/smoke_nemotron.py --live
