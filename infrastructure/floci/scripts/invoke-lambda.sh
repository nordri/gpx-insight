#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
FLOCI_DIR="$ROOT/infrastructure/floci"
TERRAFORM_DIR="$ROOT/infrastructure/terraform"
GPX_FILE="$ROOT/test.gpx"
OUTPUT_PATH="${LAMBDA_OUTPUT:-$ROOT/output/floci-lambda.png}"

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

FUNCTION_NAME="$(terraform -chdir="$TERRAFORM_DIR" output -raw lambda_function_name)"
[[ -n "$FUNCTION_NAME" ]] || { echo "Terraform did not return a Lambda function name" >&2; exit 1; }

OUTPUT_DIR="$(dirname -- "$OUTPUT_PATH")"
mkdir -p "$OUTPUT_DIR"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf -- "$TEMP_DIR"' EXIT
EVENT_FILE="$TEMP_DIR/event.json"
RESPONSE_FILE="$TEMP_DIR/response.json"

python3 - "$GPX_FILE" "$EVENT_FILE" <<'PY'
import base64
import json
import sys

with open(sys.argv[1], "rb") as source:
    gpx = source.read()

event = {
    "version": "2.0",
    "rawPath": "/v1/generate",
    "headers": {"content-type": "application/gpx+xml"},
    "queryStringParameters": None,
    "requestContext": {"http": {"method": "POST"}},
    "body": base64.b64encode(gpx).decode("ascii"),
    "isBase64Encoded": True,
}
with open(sys.argv[2], "w", encoding="utf-8") as destination:
    json.dump(event, destination, separators=(",", ":"))
PY

started_at=$SECONDS
aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --endpoint-url "$FLOCI_ENDPOINT" \
  --cli-binary-format raw-in-base64-out \
  --log-type Tail \
  --payload "fileb://$EVENT_FILE" \
  --no-cli-pager \
  "$RESPONSE_FILE" >"$TEMP_DIR/invoke-metadata.json"
duration=$((SECONDS - started_at))

python3 - "$RESPONSE_FILE" "$OUTPUT_PATH" "$TEMP_DIR/invoke-metadata.json" "$duration" <<'PY'
import base64
import json
import struct
import sys

response_path, output_path, metadata_path, duration = sys.argv[1:]
with open(metadata_path, encoding="utf-8") as metadata_file:
    metadata = json.load(metadata_file)
if metadata.get("FunctionError"):
    detail = ""
    try:
        with open(response_path, encoding="utf-8") as error_file:
            error = json.load(error_file)
        detail = f": {error.get('errorType', 'Error')}: {error.get('errorMessage', '')}"
    except (OSError, json.JSONDecodeError):
        pass
    print(f"Lambda invocation reported FunctionError: {metadata['FunctionError']}{detail}", file=sys.stderr)
    if metadata.get("LogResult"):
        try:
            logs = base64.b64decode(metadata["LogResult"]).decode("utf-8", errors="replace")
            print(logs, file=sys.stderr)
        except (ValueError, TypeError):
            pass
    raise SystemExit(1)

with open(response_path, encoding="utf-8") as response_file:
    result = json.load(response_file)
if result.get("statusCode") != 200:
    raise SystemExit(f"Lambda returned statusCode={result.get('statusCode')!r}")
if result.get("isBase64Encoded") is not True:
    raise SystemExit("Lambda response body is not marked as Base64 encoded")
if result.get("headers", {}).get("Content-Type") != "image/png":
    raise SystemExit("Lambda response Content-Type is not image/png")
try:
    png = base64.b64decode(result["body"], validate=True)
except (KeyError, ValueError) as error:
    raise SystemExit(f"Lambda response body is not valid Base64: {error}") from error

if len(png) < 24 or png[:8] != b"\x89PNG\r\n\x1a\n":
    raise SystemExit("Lambda response does not contain a valid PNG signature")
if png[12:16] != b"IHDR":
    raise SystemExit("PNG response does not contain an IHDR header")
width, height = struct.unpack(">II", png[16:24])
if (width, height) != (1080, 1920):
    raise SystemExit(f"Unexpected PNG dimensions: {width}x{height}")

with open(output_path, "wb") as output_file:
    output_file.write(png)
print(f"PNG saved: {output_path}")
print(f"Dimensions: {width}x{height}")
print(f"PNG size: {len(png)} bytes")
print(f"Duration: {duration} seconds")
PY
