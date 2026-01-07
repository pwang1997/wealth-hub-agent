# Project Context

## Purpose
Wealth Hub Agent is a multi-agent service focused on market-data workflows and stock trading analysis.

The main features and functionality live in:
- `src/agents` (`src.agents`): agent roles plus multi-agent interaction and workflow/orchestration.
- `src/agent_tools` (`src.agent_tools`): MCP-exposed market/research tools (Finnhub, Alpha Vantage proxy, RAG/report tooling) used by agents.

Optional interfaces (CLI/TUI and FastAPI) exist to run and observe these workflows, but the project’s core focus is building multi-agent collaboration patterns for market data and trading analysis.

## Tech Stack
- Language/runtime: Python 3.13.10 with uv
- Web API: FastAPI + Uvicorn.
- CLI/TUI: Rich (Live layout), `websocket-client`, simple command handler.
- Agent/tooling: OpenAI SDK, MCP (`mcp`, `fastmcp`, `langchain-mcp-adapters`), LlamaIndex + LlamaParse, ChromaDB.
- Data/cache: `diskcache`; ChromaDB persistent storage under `storage/chroma` by default; optional Chroma Cloud config.
- DB (present, not heavily exercised yet): SQLAlchemy asyncio + `asyncpg` (Postgres).

## Project Conventions

### Code Style
- Formatting/linting is enforced via Ruff (`[tool.ruff]` in `pyproject.toml`) with a 100-char line length.
- Prefer type hints where practical; Mypy is configured for Python 3.9 with `ignore_missing_imports = true`.
- Keep modules small and grouped by responsibility:
  - `src/` for API + agent logic
  - `src/agents/` for agent implementations and multi-agent workflows
  - `src/agent_tools/` for MCP tool servers and tool-adjacent helpers
  - `clients/` for external API clients
- Configuration is environment-driven (`.env` via `python-dotenv`) and YAML where appropriate (e.g., `stock_config.yml` for tracked symbols).

### Architecture Patterns
- FastAPI entrypoint: `src/main.py` mounts routers (e.g., `src/routes/rag_route.py`) and provides `/health`.
- CLI app: `cli/main.py` owns the main loop, rendering, and command dispatch; `clients/websocket_client.py` handles Finnhub WS.
- Agents and workflows:
  - Agent implementations live under `src/agents/` (e.g., domain-focused subpackages like `src/agents/analyst/`).
  - Multi-agent workflows should be composed by delegating market-data retrieval, research, and synthesis across specialized agents.
- MCP servers:
  - Local MCP servers live under `src/agent_tools/` and are started via `src/agent_tools/mcp_manager.py` / `make mcp`.
  - Servers expose tools using `@mcp_server.tool()` and typically wrap an external API with optional caching.
- Local workflows are driven via `Makefile` targets: `make dev`, `make cli`, `make mcp`, `make lint`.
- Avoid hard-coded secrets; rely on env vars and `.env.example`.

### Testing Strategy
- Test runner: `pytest` (see `pyproject.toml` optional deps).
- Prefer small unit tests for helpers/clients; use integration tests only where needed (e.g., with `testcontainers` for service/DB deps).

### Git Workflow
- Keep changes focused and easy to review; prefer small PRs.
- Use concise, imperative commit messages (e.g., “Add Finnhub reconnection handling”, “Fix RAG upload validation”).

## Domain Context
- “Symbols/tickers” refer to stock tickers subscribed to via Finnhub WebSocket; tracked symbols are persisted in `stock_config.yml`.
- “RAG” refers to indexing PDF-derived and html-derived text into ChromaDB and answering user queries with retrieved context and an OpenAI model.
- “MCP servers” expose market-data and research tools over the MCP protocol for agent workflows.

## Important Constraints
- Compatibility: keep core code Python 3.9-compatible (Ruff target version is `py39`; Mypy is configured for 3.9).
- Secrets: do not commit API keys; use `.env` / environment variables.
- External API rate limits and reliability apply (Finnhub, Alpha Vantage, OpenAI, Llama Cloud, Chroma Cloud).
- Each `agent` should have limited capabilities with focus of no more than two objectives.

## External Dependencies
- Finnhub (WebSocket market feed; REST endpoints via `clients/` and MCP tools) — `FINNHUB_API_KEY`.
- Alpha Vantage remote MCP endpoint proxy — `ALPHA_VANTAGE_API_KEY`.
- OpenAI Responses API — `OPENAI_API_KEY`.
- Llama Cloud (LlamaParse) — `LLAMA_CLOUD_API_KEY`.
- ChromaDB (Cloud or local persistent) — optional `CHROMA_API_KEY`, `CHROMA_TENANT`, `CHROMA_DATABASE`; local uses `CHROMA_PERSIST_DIR`.
