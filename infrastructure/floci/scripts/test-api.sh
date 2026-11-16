#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
FLOCI_DIR="$ROOT/infrastructure/floci"
TERRAFORM_DIR="$ROOT/infrastructure/terraform"
GPX_FILE="$ROOT/test.gpx"
OUTPUT_PATH="${API_OUTPUT:-$ROOT/output/floci-api.png}"

if [[ -f "$FLOCI_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$FLOCI_DIR/.env"
  set +a
fi

FLOCI_ENDPOINT="${FLOCI_ENDPOINT:-http://127.0.0.1:${FLOCI_PORT:-4566}}"
if [[ ! "$FLOCI_ENDPOINT" =~ ^http://(127\.0\.0\.1|localhost):([0-9]{1,5})$ ]]; then
  echo "FLOCI_ENDPOINT must be an HTTP loopback URL with a port, got: $FLOCI_ENDPOINT" >&2
  exit 2
fi
port_number=$((10#${BASH_REMATCH[2]}))
if (( port_number < 1 || port_number > 65535 )); then
  echo "FLOCI_ENDPOINT contains an invalid TCP port" >&2
  exit 2
fi

command -v aws >/dev/null || { echo "AWS CLI is required" >&2; exit 1; }
command -v curl >/dev/null || { echo "curl is required" >&2; exit 1; }
command -v python3 >/dev/null || { echo "Python 3 is required" >&2; exit 1; }
command -v terraform >/dev/null || { echo "Terraform is required" >&2; exit 1; }
[[ -r "$GPX_FILE" ]] || { echo "GPX fixture is not readable: $GPX_FILE" >&2; exit 1; }

curl --silent --show-error --max-time 5 --output /dev/null "$FLOCI_ENDPOINT" || {
  echo "FloCI is not reachable at $FLOCI_ENDPOINT" >&2
  exit 1
}

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION="${TF_VAR_aws_region:-${AWS_DEFAULT_REGION:-eu-west-1}}"
export AWS_EC2_METADATA_DISABLED=true
export AWS_CONFIG_FILE=/dev/null
export AWS_SHARED_CREDENTIALS_FILE=/dev/null
unset AWS_PROFILE AWS_DEFAULT_PROFILE AWS_SESSION_TOKEN

API_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw api_id)"
API_ENDPOINT="$(terraform -chdir="$TERRAFORM_DIR" output -raw api_endpoint)"
API_INVOKE_URL="$(terraform -chdir="$TERRAFORM_DIR" output -raw api_invoke_url)"
if [[ -z "$API_ID" || -z "$API_ENDPOINT" || -z "$API_INVOKE_URL" ]]; then
  echo "Terraform did not return the API ID and invocation URL" >&2
  exit 1
fi
API_ROUTE_PATH="${API_INVOKE_URL#"$API_ENDPOINT"}"
if [[ "$API_ROUTE_PATH" != "/v1/generate" ]]; then
  echo "Unexpected Terraform API route URL: $API_INVOKE_URL" >&2
  exit 1
fi

# FloCI's API control plane is not its execute-api listener. Its public
# listener dispatches requests below /_aws/execute-api/{api-id}/{stage}.
API_BASE_URL="http://127.0.0.1:${port_number}/_aws/execute-api/${API_ID}/\$default"
API_URL="${API_BASE_URL}${API_ROUTE_PATH}"

OUTPUT_DIR="$(dirname -- "$OUTPUT_PATH")"
mkdir -p "$OUTPUT_DIR"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf -- "$TEMP_DIR"' EXIT

echo "Testing local API URL: $API_URL"
metadata="$(
  curl --silent --show-error --max-time 60 \
    --output "$TEMP_DIR/success.png" \
    --write-out '%{http_code} %{content_type} %{time_total}' \
    --header 'Content-Type: application/gpx+xml' \
    --data-binary "@$GPX_FILE" \
    "$API_URL"
)"
read -r status response_type duration <<<"$metadata"
if [[ "$status" != "200" || "${response_type%%;*}" != "image/png" ]]; then
  echo "API success request returned HTTP $status with Content-Type '$response_type'" >&2
  exit 1
fi

python3 - "$TEMP_DIR/success.png" <<'PY'
import pathlib
import struct
import sys

png = pathlib.Path(sys.argv[1]).read_bytes()
if len(png) < 24 or png[:8] != b"\x89PNG\r\n\x1a\n" or png[12:16] != b"IHDR":
    raise SystemExit("API returned HTTP 200 but the body is not a valid PNG")
width, height = struct.unpack(">II", png[16:24])
if (width, height) != (1080, 1920):
    raise SystemExit(f"API PNG dimensions are {width}x{height}, expected 1080x1920")
PY

mv -- "$TEMP_DIR/success.png" "$OUTPUT_PATH"
png_size="$(wc -c <"$OUTPUT_PATH")"
echo "API response: HTTP $status, Content-Type ${response_type%%;*}, ${duration}s"
echo "PNG saved: $OUTPUT_PATH (1080x1920, ${png_size} bytes)"

query_metadata="$(
  curl --silent --show-error --max-time 60 \
    --output "$TEMP_DIR/query.png" \
    --write-out '%{http_code} %{content_type}' \
    --header 'Content-Type: application/gpx+xml' \
    --data-binary "@$GPX_FILE" \
    "${API_URL}?theme=alpine&lang=es"
)"
read -r query_status query_type <<<"$query_metadata"
if [[ "$query_status" != "200" || "${query_type%%;*}" != "image/png" ]]; then
  echo "API query options returned HTTP $query_status with Content-Type '$query_type'" >&2
  exit 1
fi
python3 - "$TEMP_DIR/query.png" <<'PY'
import pathlib
import struct
import sys

png = pathlib.Path(sys.argv[1]).read_bytes()
if len(png) < 24 or png[:8] != b"\x89PNG\r\n\x1a\n" or png[12:16] != b"IHDR":
    raise SystemExit("API query-option response is not a valid PNG")
if struct.unpack(">II", png[16:24]) != (1080, 1920):
    raise SystemExit("API query-option response has incorrect PNG dimensions")
PY
echo "query options theme=alpine&lang=es: HTTP $query_status, image/png"

check_error() {
  local label="$1"
  local expected_status="$2"
  local expected_code="$3"
  local output_file="$TEMP_DIR/${label}.response"
  shift 3

  local metadata
  metadata="$(
    curl --silent --show-error --max-time 60 \
      --output "$output_file" \
      --write-out '%{http_code} %{content_type} %{time_total}' \
      "$@"
  )"
  local actual_status actual_type actual_duration
  read -r actual_status actual_type actual_duration <<<"$metadata"

  python3 - "$output_file" "$actual_status" "$actual_type" "$expected_status" "$expected_code" "$label" <<'PY'
import json
import pathlib
import sys

body_path, status, content_type, expected_status, expected_code, label = sys.argv[1:]
allowed_statuses = {int(value) for value in expected_status.split("|")}
if int(status) not in allowed_statuses:
    raise SystemExit(f"{label}: expected HTTP {expected_status}, got {status}")
if int(status) >= 500:
    raise SystemExit(f"{label}: unexpected server error HTTP {status}")
if "application/json" not in content_type.lower():
    raise SystemExit(f"{label}: expected JSON error, got Content-Type {content_type!r}")
try:
    payload = json.loads(pathlib.Path(body_path).read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as error:
    raise SystemExit(f"{label}: response is not valid JSON: {error}") from error
if expected_code and payload.get("code") != expected_code:
    raise SystemExit(f"{label}: expected error code {expected_code}, got {payload.get('code')!r}")
error_code = payload.get("code")
suffix = f", code={error_code}" if error_code else ""
print(f"{label}: HTTP {status}, JSON error response{suffix}")
PY

  if [[ "$label" == "method" && "$actual_status" == "404" ]]; then
    echo "The HTTP API has no GET route; FloCI rejected the method before Lambda (404)."
  fi
}

: >"$TEMP_DIR/empty.gpx"
printf 'not a valid GPX document' >"$TEMP_DIR/invalid.gpx"

check_error empty-body 400 '' \
  --header 'Content-Type: application/gpx+xml' \
  --data-binary "@$TEMP_DIR/empty.gpx" \
  "$API_URL"
check_error invalid-gpx 422 INVALID_GPX \
  --header 'Content-Type: application/gpx+xml' \
  --data-binary "@$TEMP_DIR/invalid.gpx" \
  "$API_URL"
check_error wrong-content-type 415 UNSUPPORTED_MEDIA_TYPE \
  --header 'Content-Type: text/plain' \
  --data-binary "@$GPX_FILE" \
  "$API_URL"
check_error invalid-theme 400 INVALID_PARAMETERS \
  --header 'Content-Type: application/gpx+xml' \
  --data-binary "@$GPX_FILE" \
  "${API_URL}?theme=invalid"
check_error method '404|405' '' \
  --request GET \
  "$API_URL"
check_error missing-route 404 '' \
  --header 'Content-Type: application/gpx+xml' \
  --data-binary "@$GPX_FILE" \
  "${API_BASE_URL}/v1/missing"
