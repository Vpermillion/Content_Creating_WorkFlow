#!/bin/sh
set -eu
python -m whatif pilots
exec python -m whatif serve --host 0.0.0.0 --port 8090
