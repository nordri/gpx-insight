#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
FRONTEND_DIR="$ROOT/frontend"
TERRAFORM_DIR="$ROOT/infrastructure/terraform"

for command in python3 terraform curl; do
  command -v "$command" >/dev/null || {
    echo "$command is required to serve the frontend" >&2
    exit 1
  }
done

if [[ -f "$ROOT/infrastructure/floci/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/infrastructure/floci/.env"
  set +a
fi

FLOCI_ENDPOINT="${FLOCI_ENDPOINT:-http://127.0.0.1:${FLOCI_PORT:-4566}}"
if [[ ! "$FLOCI_ENDPOINT" =~ ^http://(127\.0\.0\.1|localhost):([0-9]{1,5})$ ]]; then
  echo "FLOCI_ENDPOINT must be an HTTP loopback URL with a port, got: $FLOCI_ENDPOINT" >&2
  exit 2
fi
FLOCI_PORT_NUMBER=$((10#${BASH_REMATCH[2]}))
if (( FLOCI_PORT_NUMBER < 1 || FLOCI_PORT_NUMBER > 65535 )); then
  echo "FLOCI_ENDPOINT contains an invalid TCP port" >&2
  exit 2
fi

[[ -f "$FRONTEND_DIR/index.html" && -f "$FRONTEND_DIR/app.js" && -f "$FRONTEND_DIR/styles.css" && -f "$FRONTEND_DIR/config.js" ]] || {
  echo "Frontend files are missing from $FRONTEND_DIR" >&2
  exit 1
}

curl --silent --show-error --max-time 5 --output /dev/null "$FLOCI_ENDPOINT" || {
  echo "FloCI is not reachable at $FLOCI_ENDPOINT; start it with make floci-start" >&2
  exit 1
}

if ! API_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw api_id 2>/dev/null)" ||
   ! API_INVOKE_URL="$(terraform -chdir="$TERRAFORM_DIR" output -raw api_invoke_url 2>/dev/null)"; then
  echo "Terraform API outputs are unavailable; deploy the API with make floci-api-apply first" >&2
  exit 1
fi
if [[ ! "$API_ID" =~ ^[[:alnum:]]+$ || "$API_INVOKE_URL" != */v1/generate ]]; then
  echo "Terraform returned invalid API Gateway outputs; verify api_id and api_invoke_url" >&2
  exit 1
fi

SERVE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/gpx-insight-frontend.XXXXXX")"
cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -rf -- "$SERVE_DIR"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cp -R "$FRONTEND_DIR/." "$SERVE_DIR/"
API_URL="http://127.0.0.1:${FLOCI_PORT_NUMBER}/_aws/execute-api/${API_ID}/\$default/v1/generate"
python3 - "$SERVE_DIR/config.js" "$API_URL" <<'PY'
import json
import pathlib
import sys

config_path, api_url = sys.argv[1:]
config_path = pathlib.Path(config_path)
config_path.write_text(
    "window.GPX_INSIGHT_CONFIG = Object.freeze({ apiUrl: "
    + json.dumps(api_url)
    + " });\n",
    encoding="utf-8",
)
PY

echo "Serving static frontend at http://127.0.0.1:8080"
echo "Using FloCI API id $API_ID; no infrastructure will be started or deployed."
python3 -m http.server 8080 --bind 127.0.0.1 --directory "$SERVE_DIR" &
SERVER_PID=$!
wait "$SERVER_PID"
