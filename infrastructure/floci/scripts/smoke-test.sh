#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi
PORT="${FLOCI_PORT:-4566}"
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-eu-west-1}"
export AWS_EC2_METADATA_DISABLED=true
command -v aws >/dev/null || { echo 'AWS CLI is required' >&2; exit 1; }
command -v curl >/dev/null || { echo 'curl is required' >&2; exit 1; }
URL="http://127.0.0.1:${PORT}"
echo "Checking TCP/HTTP response from ${URL} ..."
curl --silent --show-error --max-time 5 --output /dev/null "$URL" || { echo 'FloCI is not reachable' >&2; exit 1; }
echo 'Checking S3 ListBuckets API ...'
aws --endpoint-url "$URL" s3api list-buckets --output json
echo 'FloCI smoke test passed.'
