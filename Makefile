PYTHON ?= python

.PHONY: run test lint all
run:
	$(PYTHON) -m src.pipeline --config config/project.yml
test:
	$(PYTHON) -m pytest -q
lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
all: lint test run
