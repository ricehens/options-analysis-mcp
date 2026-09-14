.PHONY: sync format lint type test check build release-check run

UV ?= uv

sync:
	$(UV) sync --all-groups

format:
	$(UV) run ruff format .

lint:
	$(UV) run ruff check .

type:
	$(UV) run mypy

test:
	$(UV) run pytest

check:
	$(UV) run ruff format --check .
	$(UV) run ruff check .
	$(UV) run mypy
	$(UV) run pytest

build:
	$(UV) build

release-check: check build

run:
	$(UV) run options-analysis-mcp
