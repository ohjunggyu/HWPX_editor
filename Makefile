.PHONY: help sync fmt lint type test ci

help:
	@echo "Targets:"
	@echo "  sync  - uv sync"
	@echo "  fmt   - ruff format"
	@echo "  lint  - ruff check"
	@echo "  type  - mypy"
	@echo "  test  - pytest"
	@echo "  ci    - sync(frozen) + fmt(check) + lint + type + test"

sync:
	uv sync

fmt:
	uv run ruff format .

lint:
	uv run ruff check .

type:
	uv run mypy src

test:
	uv run pytest -q

ci:
	uv sync --frozen
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy src
	uv run pytest -q