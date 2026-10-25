#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
command -v python >/dev/null
command -v docker >/dev/null
python -m whatif init
python -m whatif pilots
if [ ! -f .env ]; then python scripts/configure_local.py; fi
# Keep Buildx cache metadata writable without replacing Docker's credentials/config.
export BUILDX_CONFIG="${BUILDX_CONFIG:-/tmp/whatif-buildx}"
env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
  docker --host=unix:///var/run/docker.sock compose build worker
