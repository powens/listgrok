.PHONY: test
test:
	@echo "Running tests..."
	uv run pytest

.PHONY: lint
lint:
	uvx ruff check

.PHONY: fmt
fmt:
	uvx ruff format