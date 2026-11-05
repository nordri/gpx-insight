#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x venv-gpx/bin/python ]]; then
  echo 'Missing venv-gpx. Run make setup.' >&2
  exit 1
fi
venv-gpx/bin/python - <<'PY'
import sys
assert sys.prefix != sys.base_prefix, 'Not running inside a virtual environment'
import gpxpy, numpy, pandas, matplotlib, PIL, scipy
print('Environment OK:', sys.executable)
PY
