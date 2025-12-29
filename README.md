# Wealth Hub Agent

Wealth Hub Agent provides a terminal-based stock ticker experience with live Finnhub data, local configuration, and an extensible command-driven workflow.

## Key Features

- Real-time market feed via Finnhub WebSocket, with automatic subscriptions for tracked symbols and graceful reconnection handling.
- Interactive Rich-powered terminal UI that displays live prices, percentage changes, timestamps, and an input prompt for user commands.
- Persistent symbol list saved in `stock_config.yml` with helpers for loading and storing configuration consistently across runs.
- Lightweight CLI architecture split into dedicated modules for the websocket client, UI rendering, configuration utilities, and command handling.

## Quick Start

1. Get Started 
   ```
   git clone git@github.com:pwang1997/wealth-hub-agent.git
   cd wealth-hub-agent
   ```
2. Install dependencies
   ```
   uv sync
   ```
3. Get your Finnhub API key `https://finnhub.io/register`
4. Import `FINNHUB_API_KEY=YOUR_FINNHUB_API_KEY` in .env
5. Run the project in CLI
   ```
   make cli
   ```
6. Use the built-in commands at the prompt:
   - `add <SYMBOL>` to track a new ticker.
   - `remove <SYMBOL>` to stop tracking a ticker.
   - `list` to view the current symbol set.
   - `clear` to reset all tracked symbols.
   - `save` to force-write the current configuration.
   - `help` to show available commands.
   - `quit` / `exit` to stop the app (auto-saves before exiting).
7. Configuration lives in `stock_config.yml`, which updates with every save or exit.

## MCP Servers

This repo includes small MCP servers under `src/agent_tools/` that expose market-data tools over MCP.

### Run all local MCP servers

- Run: `make mcp`
- Logs are prefixed per server as `[alpha_vantage][stdout] ...` / `[finnhub][stderr] ...`

### Finnhub MCP

- Requires `FINNHUB_API_KEY` in your environment (see Quick Start step 4).
- Run locally: `uv run python src/agent_tools/finnhub_mcp.py`
- Configure port with `FINNHUB_MCP_PORT` (default `8002`).
