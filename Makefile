.PHONY: test
test:
	uv run pytest --random-order

.PHONY: lint
lint:
	uvx ruff check src

.PHONY: fmt
fmt:
	uvx ruff format

.PHONY: build
build:
	uv build

.PHONY: coverage
coverage:
	uv run coverage run -m pytest --random-order
	uv run coverage report

.PHONY: coverage-html
coverage-html:
	uv run coverage html

.PHONY: clean
clean:
	rm -rf htmlcov
	rm .coverage
	rm -rf dist