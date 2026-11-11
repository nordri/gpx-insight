#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f venv-gpx/pyvenv.cfg ]] || ! venv-gpx/bin/python -c 'import sys; assert sys.prefix != sys.base_prefix' 2>/dev/null; then
  if [[ -e venv-gpx ]]; then
    echo 'Existing venv-gpx is invalid. Move/remove it before setup.' >&2
    exit 1
  fi
  python3 -m venv venv-gpx
fi
venv-gpx/bin/python -m pip install -r requirements.txt
