.DEFAULT_GOAL := all

.PHONY: help install check lint format typecheck test build clean all

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install package in editable mode with all deps
	uv sync --extra dev --extra all
	uv run pre-commit install

lint: ## Run ruff linter
	uv run ruff check .

format: ## Run ruff formatter (auto-fix)
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## Run mypy type checker
	uv run mypy src/x402_openai

test: ## Run pytest
	uv run pytest

build: ## Build wheel and sdist
	uv build

clean: ## Remove build artifacts
	uv run python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['dist', 'build', '.mypy_cache', '.pytest_cache']]; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('*.egg-info')]"

check: ## Run all pre-commit hooks (lint + format + typecheck)
	uv run pre-commit run --all-files

all: check test ## Run all checks + tests
