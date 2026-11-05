PYTHON := venv-gpx/bin/python
GPX ?= test.gpx
OUTPUT ?= output/story.png
THEME ?= forest
LANG ?= es

.PHONY: help setup check test analyze clean

help:
	@printf '%s\n' 'make setup                  Create venv and install dependencies' 'make check                  Verify runtime dependencies' 'make test                   Run unittest suite' 'make analyze GPX=path.gpx   Generate infographic (OUTPUT=... THEME=... LANG=...)' 'make clean                  Remove generated output files'

setup:
	@bash scripts/setup.sh

check:
	@bash scripts/check.sh

test:
	@$(PYTHON) -m unittest discover -s tests -v

analyze:
	@$(PYTHON) cli.py --input "$(GPX)" --output "$(OUTPUT)" --theme "$(THEME)" --lang "$(LANG)"

clean:
	@bash scripts/clean.sh
