.PHONY: dev cli lint lint-fix

dev:
	# Install dev/test/tooling extras for local development (includes boto3 via dev extra)
	uv sync --extra dev --extra test --extra tooling
	set -a; source .env; set +a
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8100

cli:
	uv run ./cli/main.py

lint:
	uv run --extra dev ruff check .
	uv run --extra dev ruff format --check .
	$(MAKE) typecheck

lint-fix:
	uv run --extra dev ruff check --fix .
	uv run --extra dev ruff format .