PYTHON := venv-gpx/bin/python
GPX ?= test.gpx
OUTPUT ?= output/story.png
THEME ?= forest
LANG ?= es
DOCKER_IMAGE ?= gpx-insight:latest

.PHONY: help setup check test analyze clean docker-build

help:
	@printf '%s\n' 'make setup                  Create venv and install dependencies' 'make check                  Verify runtime dependencies' 'make test                   Run unittest suite' 'make analyze GPX=path.gpx   Generate infographic (OUTPUT=... THEME=... LANG=...)' 'make docker-build           Build Lambda base image (DOCKER_IMAGE=...)' 'make clean                  Remove generated output files'

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
