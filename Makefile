.PHONY: dev cli lint lint-fix test clean-install test-workflow

dev:
	uv sync --extra dev
	set -a; source .env; set +a
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

cli:
	uv run ./cli/main.py

mcp:
	uv run python ./src/scripts/run_mcp_servers.py

lint:
	uv run --extra dev ruff check .
	uv run --extra dev ruff format --check .
	$(MAKE) typecheck

lint-fix:
	uv run --extra dev ruff check --fix .
	uv run --extra dev ruff format .

test:
	PYTHONPATH=. uv run --extra test pytest ./tests

clean-install:
	rm -rf .venv
	uv venv
	uv sync

test-workflow:
	curl -N -X POST http://localhost:8000/v1/workflow/stream \
		-H "Content-Type: application/json" \
		-d '{
			"query": "Is Apple a good investment?",
			"ticker": "AAPL"
		}'