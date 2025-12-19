.PHONY: dev cli

dev:
	# Install dev/test/tooling extras for local development (includes boto3 via dev extra)
	uv sync --extra dev --extra test --extra tooling
	set -a; source .env; set +a
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8100

cli:
	uv run ./cli/main.py