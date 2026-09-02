# Run all checks and tests.
all: check test

# Show all available recipes.
help:
    @just --list

# Install the package in editable mode with all dependencies.
install:
    uv sync --extra dev --extra all
    uv run pre-commit install

# Run Ruff lint checks.
lint:
    uv run ruff check .

# Auto-fix Ruff findings and format the code.
format:
    uv run ruff check --fix .
    uv run ruff format .

# Run the mypy type checker.
typecheck:
    uv run mypy src/qntx/openai

# Run pytest.
test:
    uv run pytest

# Build wheel and source distributions.
build:
    uv build

# Remove build artifacts and caches using the project's Python environment.
clean:
    uv run python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['dist', 'build', '.mypy_cache', '.pytest_cache']]; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('*.egg-info')]"

# Run all pre-commit hooks.
check:
    uv run pre-commit run --all-files
