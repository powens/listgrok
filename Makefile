.PHONY: test
test:
	uv run pytest

.PHONY: lint
lint:
	uvx ruff check

.PHONY: fmt
fmt:
	uvx ruff format

.PHONY: build
buiild:
	uv build