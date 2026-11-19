#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"

command -v make >/dev/null || { echo "GNU Make is required" >&2; exit 1; }

echo "==> Running Python tests"
make -C "$ROOT" test

echo "==> Building and pushing the image to FloCI ECR"
make -C "$ROOT" floci-ecr-push

echo "==> Applying Terraform (Lambda and HTTP API)"
make -C "$ROOT" floci-api-apply

echo "==> Testing HTTP API to PNG"
make -C "$ROOT" floci-api-test
