.PHONY: setup lint typecheck test api-dev web-dev web-test all

setup: ## Install Python and web dependencies and the git hooks
	uv sync --locked
	pnpm --dir web install --frozen-lockfile
	uv run pre-commit install

lint: ## Lint and check formatting for Python and web
	uv run ruff check .
	uv run ruff format --check .
	pnpm --dir web lint
	pnpm --dir web format:check

typecheck: ## Type check Python with mypy and web with tsc
	uv run mypy
	pnpm --dir web typecheck

test: ## Run the Python tests
	uv run pytest

api-dev: ## Run the API locally on port 8000
	uv run uvicorn api.main:app --reload --port 8000

web-dev: ## Run the web app locally on port 3000
	pnpm --dir web dev

web-test: ## Run the web tests
	pnpm --dir web test

all: lint typecheck test web-test ## Everything CI runs
