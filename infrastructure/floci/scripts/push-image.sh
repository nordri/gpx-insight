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

FLOCI_ENDPOINT="${FLOCI_ENDPOINT:-http://127.0.0.1:${FLOCI_PORT:-4566}}"
if [[ ! "$FLOCI_ENDPOINT" =~ ^http://(127\.0\.0\.1|localhost):([0-9]{1,5})$ ]]; then
  echo "FLOCI_ENDPOINT must be an HTTP loopback URL with a port, got: $FLOCI_ENDPOINT" >&2
  exit 2
fi
registry_port="${BASH_REMATCH[2]}"
registry_port_number=$((10#$registry_port))
if (( registry_port_number < 1 || registry_port_number > 65535 )); then
  echo "FLOCI_ENDPOINT contains an invalid TCP port" >&2
  exit 2
fi
registry_port="$registry_port_number"

DOCKER_IMAGE="${DOCKER_IMAGE:-gpx-insight:latest}"
ECR_IMAGE_TAG="${ECR_IMAGE_TAG:-1.1.0}"
if [[ ! "$ECR_IMAGE_TAG" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$ ]]; then
  echo "Invalid ECR image tag: $ECR_IMAGE_TAG" >&2
  exit 2
fi

command -v aws >/dev/null || { echo "AWS CLI is required" >&2; exit 1; }
command -v docker >/dev/null || { echo "Docker is required" >&2; exit 1; }
command -v terraform >/dev/null || { echo "Terraform is required" >&2; exit 1; }

repository_url="$(terraform -chdir="$TERRAFORM_DIR" output -raw repository_url)"
repository_name="$(terraform -chdir="$TERRAFORM_DIR" output -raw repository_name)"
aws_region="$(terraform -chdir="$TERRAFORM_DIR" output -raw aws_region)"
if [[ -z "$repository_url" || "$repository_url" != */* ]]; then
  echo "Terraform returned an invalid ECR repository URL" >&2
  exit 1
fi
repository_path="${repository_url#*/}"
registry_host="${repository_url%%/*}"
account_id="${registry_host%%.dkr.ecr.*}"
if [[ ! "$account_id" =~ ^[0-9]{12}$ || "$repository_path" != "$repository_name" ]]; then
  echo "Terraform returned an ECR URL that cannot be mapped to FloCI's path-style URI" >&2
  exit 1
fi

docker info >/dev/null
if ! docker image inspect "$DOCKER_IMAGE" >/dev/null 2>&1; then
  make -C "$ROOT" docker-build "DOCKER_IMAGE=$DOCKER_IMAGE"
fi

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION="$aws_region"
export AWS_EC2_METADATA_DISABLED=true
export AWS_CONFIG_FILE=/dev/null
export AWS_SHARED_CREDENTIALS_FILE=/dev/null
unset AWS_PROFILE AWS_DEFAULT_PROFILE AWS_SESSION_TOKEN

DOCKER_CONFIG="$(mktemp -d)"
chmod 700 "$DOCKER_CONFIG"
export DOCKER_CONFIG
trap 'rm -rf -- "$DOCKER_CONFIG"' EXIT

registry="localhost:${registry_port}"
target_image="${registry}/${account_id}/${aws_region}/${repository_path}:${ECR_IMAGE_TAG}"

# FloCI supports this path-style URI for its HTTP data plane; Docker attempts
# HTTPS for the provider's AWS-shaped repository URI.
echo "Authenticating Docker against the local FloCI ECR registry..."
aws ecr get-login-password \
  --region "$aws_region" \
  --endpoint-url "$FLOCI_ENDPOINT" \
  --no-cli-pager |
  docker login --username AWS --password-stdin "$registry"

docker tag "$DOCKER_IMAGE" "$target_image"
docker push "$target_image"

echo "Verifying image tag ${ECR_IMAGE_TAG} in repository ${repository_name}..."
aws ecr describe-images \
  --repository-name "$repository_name" \
  --image-ids "imageTag=$ECR_IMAGE_TAG" \
  --region "$aws_region" \
  --endpoint-url "$FLOCI_ENDPOINT" \
  --no-cli-pager \
  --query 'imageDetails[0].imageTags' \
  --output text
