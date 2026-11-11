#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Only remove generated images; preserve source GPX files and other output files.
find output -maxdepth 1 -type f -name '*.png' -delete 2>/dev/null || true
