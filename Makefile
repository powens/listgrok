.PHONY: test
test:
	uv run pytest

.PHONY: typecheck
typecheck:
	uv run ty check src/

.PHONY: lint
lint:
	uv run --group lint ruff check .

.PHONY: format
format:
	uv run --group lint ruff format .

.PHONY: build
build:
	uv build

.PHONY: coverage
coverage:
	uv run coverage run -m pytest
	uv run coverage report

.PHONY: coverage-html
coverage-html:
	uv run coverage html

.PHONY: clean
clean:
	rm -rf htmlcov
	rm .coverage
	rm -rf dist