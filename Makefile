.PHONY: help install test test-unit test-integration test-all format lint typecheck precommit clean example

help:
	@echo "opencode-manager development commands (using uv)"
	@echo ""
	@echo "  make install          Install dependencies with uv"
	@echo "  make test            Run unit tests"
	@echo "  make test-integration Run integration tests (safe mode)"
	@echo "  make test-all        Run all tests"
	@echo "  make format          Format code with black"
	@echo "  make lint            Lint code with ruff"
	@echo "  make typecheck       Type check with pyright"
	@echo "  make example         Run the basic usage example"
	@echo "  make clean           Remove build artifacts"
	@echo ""
	@echo "For integration tests with real config:"
	@echo "  OPENCODE_USE_REAL_CONFIG=true make test-integration"

install:
	uv sync
	@if [ -f package.json ]; then \
		echo "Installing Node.js dev tools (pyright)..."; \
		npm install; \
	fi
	@if command -v pre-commit &> /dev/null; then \
		echo "Installing pre-commit hooks..."; \
		pre-commit install --install-hooks; \
	fi

test: test-unit

test-unit:
	uv run python -m pytest tests/test_server.py -v

test-integration:
	uv run python -m pytest tests/test_integration.py -v

test-all:
	uv run python -m pytest -v

format:
	uv run black src/ tests/ examples/

lint:
	uv run ruff check src/ tests/ examples/

typecheck:
	@if [ ! -d node_modules ]; then \
		echo "Error: pyright not installed. Run 'make install' first."; \
		exit 1; \
	fi
	npm run typecheck

precommit:
	uv run pre-commit run --all-files

example:
	uv run python examples/basic_usage.py

clean:
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf __pycache__/
	rm -rf src/opencode_manager/__pycache__/
	rm -rf tests/__pycache__/
	rm -rf test_run*/
	rm -rf test_run_*/
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
