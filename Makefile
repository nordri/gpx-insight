PYTHON := venv-gpx/bin/python
GPX ?= test.gpx
OUTPUT ?= output/story.png
THEME ?= forest
LANG ?= es
DOCKER_IMAGE ?= gpx-insight:latest
ECR_IMAGE_TAG ?= 1.1.0

.PHONY: help setup check test analyze clean docker-build floci-start floci-stop floci-test floci-ecr-init floci-ecr-apply floci-ecr-push floci-ecr-destroy floci-lambda-apply floci-lambda-invoke floci-api-apply floci-api-test floci-deploy

help:
	@printf '%s\n' 'make setup                  Create venv and install dependencies' 'make check                  Verify runtime dependencies' 'make test                   Run unittest suite' 'make analyze GPX=path.gpx   Generate infographic (OUTPUT=... THEME=... LANG=...)' 'make docker-build           Build Lambda image (DOCKER_IMAGE=...)' 'make floci-start            Start the local FloCI emulator' 'make floci-test             Run the FloCI smoke test' 'make floci-ecr-init         Initialize local ECR Terraform' 'make floci-ecr-apply        Create the local ECR repository' 'make floci-ecr-push         Build and publish the image (ECR_IMAGE_TAG=...)' 'make floci-ecr-destroy      Remove all local FloCI Terraform resources' 'make floci-lambda-apply     Deploy Lambda from the existing ECR image' 'make floci-lambda-invoke    Invoke Lambda directly' 'make floci-api-apply        Deploy HTTP API Gateway' 'make floci-api-test         Test binary PNG and HTTP errors' 'make floci-deploy           Test, build, push, apply Lambda/API, and verify PNG' 'make clean                  Remove generated output files'

setup:
	@bash scripts/setup.sh

check:
	@bash scripts/check.sh

test:
	@$(PYTHON) -m unittest discover -s tests -v

analyze:
	@$(PYTHON) cli.py --input "$(GPX)" --output "$(OUTPUT)" --theme "$(THEME)" --lang "$(LANG)"

docker-build:
	docker build --tag "$(DOCKER_IMAGE)" .

clean:
	@bash scripts/clean.sh

floci-start:
	./infrastructure/floci/scripts/start.sh

floci-stop:
	./infrastructure/floci/scripts/stop.sh

floci-test:
	./infrastructure/floci/scripts/smoke-test.sh

floci-ecr-init:
	./infrastructure/floci/scripts/terraform-ecr.sh init

floci-ecr-apply:
	./infrastructure/floci/scripts/terraform-ecr.sh apply

floci-ecr-push: docker-build
	DOCKER_IMAGE="$(DOCKER_IMAGE)" ECR_IMAGE_TAG="$(ECR_IMAGE_TAG)" ./infrastructure/floci/scripts/push-image.sh

floci-ecr-destroy:
	./infrastructure/floci/scripts/terraform-ecr.sh destroy

floci-lambda-apply:
	./infrastructure/floci/scripts/terraform-ecr.sh lambda-apply

floci-lambda-invoke:
	./infrastructure/floci/scripts/invoke-lambda.sh

floci-api-apply:
	./infrastructure/floci/scripts/terraform-ecr.sh api-apply

floci-api-test:
	./infrastructure/floci/scripts/test-api.sh

floci-deploy:
	./infrastructure/floci/scripts/deploy.sh
