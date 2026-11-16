#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
FLOCI_DIR="$ROOT/infrastructure/floci"
TERRAFORM_DIR="$ROOT/infrastructure/terraform"

if [[ -f "$FLOCI_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$FLOCI_DIR/.env"
  set +a
fi

ACTION="${1:-}"
case "$ACTION" in
  init|validate|plan|lambda-plan|api-plan)
    ;;
  apply|destroy|lambda-apply|api-apply)
    ;;
  *)
    echo "Usage: $0 {init|validate|plan|apply|destroy|lambda-plan|lambda-apply|api-plan|api-apply}" >&2
    exit 2
    ;;
esac

FLOCI_ENDPOINT="${FLOCI_ENDPOINT:-http://127.0.0.1:${FLOCI_PORT:-4566}}"
if [[ ! "$FLOCI_ENDPOINT" =~ ^http://(127\.0\.0\.1|localhost):([0-9]{1,5})$ ]]; then
  echo "FLOCI_ENDPOINT must be an HTTP loopback URL with a port, got: $FLOCI_ENDPOINT" >&2
  exit 2
fi
registry_port_number=$((10#${BASH_REMATCH[2]}))
if (( registry_port_number < 1 || registry_port_number > 65535 )); then
  echo "FLOCI_ENDPOINT contains an invalid TCP port" >&2
  exit 2
fi

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION="${TF_VAR_aws_region:-${AWS_DEFAULT_REGION:-eu-west-1}}"
export AWS_EC2_METADATA_DISABLED=true
export AWS_CONFIG_FILE=/dev/null
export AWS_SHARED_CREDENTIALS_FILE=/dev/null
unset AWS_PROFILE AWS_DEFAULT_PROFILE AWS_SESSION_TOKEN

export TF_VAR_aws_region="$AWS_DEFAULT_REGION"
export TF_VAR_floci_endpoint="$FLOCI_ENDPOINT"
export TF_VAR_project_name="${TF_VAR_project_name:-gpx-insight}"
export TF_VAR_force_delete_repository=true

case "$ACTION" in
  init)
    exec terraform -chdir="$TERRAFORM_DIR" init -input=false
    ;;
  validate)
    exec terraform -chdir="$TERRAFORM_DIR" validate
    ;;
  plan)
    exec terraform -chdir="$TERRAFORM_DIR" plan -input=false \
      -target=aws_ecr_repository.gpx_insight
    ;;
  lambda-plan)
    exec terraform -chdir="$TERRAFORM_DIR" plan -input=false
    ;;
  api-plan)
    exec terraform -chdir="$TERRAFORM_DIR" plan -input=false
    ;;
  apply)
    exec terraform -chdir="$TERRAFORM_DIR" apply -input=false -auto-approve \
      -target=aws_ecr_repository.gpx_insight
    ;;
  lambda-apply)
    command -v aws >/dev/null || { echo "AWS CLI is required" >&2; exit 1; }
    command -v curl >/dev/null || { echo "curl is required" >&2; exit 1; }
    curl --silent --show-error --max-time 5 --output /dev/null "$FLOCI_ENDPOINT" || {
      echo "FloCI is not reachable at $FLOCI_ENDPOINT" >&2
      exit 1
    }
    aws ecr describe-images \
      --repository-name "$TF_VAR_project_name" \
      --image-ids imageTag=1.1.0 \
      --region "$AWS_DEFAULT_REGION" \
      --endpoint-url "$FLOCI_ENDPOINT" \
      --no-cli-pager \
      --query 'imageDetails[0].imageDigest' \
      --output text >/dev/null || {
      echo "ECR image tag 1.1.0 is required before deploying Lambda" >&2
      exit 1
    }
    exec terraform -chdir="$TERRAFORM_DIR" apply -input=false -auto-approve
    ;;
  api-apply)
    command -v curl >/dev/null || { echo "curl is required" >&2; exit 1; }
    curl --silent --show-error --max-time 5 --output /dev/null "$FLOCI_ENDPOINT" || {
      echo "FloCI is not reachable at $FLOCI_ENDPOINT" >&2
      exit 1
    }
    exec terraform -chdir="$TERRAFORM_DIR" apply -input=false -auto-approve
    ;;
  destroy)
    exec terraform -chdir="$TERRAFORM_DIR" destroy -input=false -auto-approve
    ;;
esac
