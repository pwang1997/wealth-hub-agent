# Wealth Hub Agent

Wealth Hub Agent is a sophisticated financial analysis platform powered by a multi-agent AI architecture. It leverages specialized LLM agents and the **Model Context Protocol (MCP)** to perform deep fundamental analysis, news synthesis, and RAG-based (Retrieval-Augmented Generation) information retrieval.

## 🚀 Key Features

- **Multi-Agent Orchestration**: A structured workflow that coordinates specialized agents for end-to-end financial research.
- **Model Context Protocol (MCP)**: Seamless integration with financial data tools (Alpha Vantage, Finnhub, SEC EDGAR) via MCP servers.
- **Advanced RAG Pipeline**: Intelligent document retrieval and indexing using LlamaIndex and ChromaDB.
- **Parallel Processing**: Simultaneous execution of fundamental and news analysis steps for improved performance.
- **Stateful Workflows**: Built-in caching (Diskcache) and partial execution support (run until a specific step).
- **Modern Interfaces**: Includes both a production-ready FastAPI service and an interactive Rich-based CLI/TUI.

## 🤖 Agent Architecture

The project employs a set of specialized agents, each focused on a specific domain:

1.  **Analyst Retrieval Agent**: Performs semantic search across financial documents and fetches real-time market news.
2.  **Fundamental Analyst Agent**: Analyzes company financials, performance metrics, and valuation drivers.
3.  **News Analyst Agent**: Aggregates and synthesizes market news, applying deduplication and recency weighting.
4.  **Research Analyst Agent**: Merges fundamental and news insights into a cohesive research report.
5.  **Investment Manager Agent**: Provides actionable investment recommendations based on the synthesized research.

## 🔄 Workflow Orchestration

Workflows are managed by the `WorkflowOrchestrator`, following a canonical sequence:

[![](https://mermaid.ink/img/pako:eNpdj01PhDAQhv9KM2eWLN_Qg8kuaOJBD8aTwGGyjECkhZSyuhL-u4VVD9tTn3n6zkxnOPUVAYda4dCw16yQzJxD_kJatXTGjh1qkrpku90dO-YPk6xQmMIqJHaXUZe_ke1Fmj_T53ijjpvKTM-RUJ2aG51e9RWyDe7zR3mmUa-T2BNKrEmVYJkt2wq4VhNZIEgJXBHmNVqAbkhQAdxcK1QfBRRyMZkB5Vvfi7-Y6qe6Af6O3WhoGirUlLVo_i_-q4pkRSrtJ6mBe-HWA_gMX4bi2Hb3Xui4SRIkceJYcAHuB7bj-kkURoEXBmHiLxZ8b0P3dhwFyw8Ys22_?type=png)](https://mermaid.live/edit#pako:eNpdj01PhDAQhv9KM2eWLN_Qg8kuaOJBD8aTwGGyjECkhZSyuhL-u4VVD9tTn3n6zkxnOPUVAYda4dCw16yQzJxD_kJatXTGjh1qkrpku90dO-YPk6xQmMIqJHaXUZe_ke1Fmj_T53ijjpvKTM-RUJ2aG51e9RWyDe7zR3mmUa-T2BNKrEmVYJkt2wq4VhNZIEgJXBHmNVqAbkhQAdxcK1QfBRRyMZkB5Vvfi7-Y6qe6Af6O3WhoGirUlLVo_i_-q4pkRSrtJ6mBe-HWA_gMX4bi2Hb3Xui4SRIkceJYcAHuB7bj-kkURoEXBmHiLxZ8b0P3dhwFyw8Ys22_)

## 🛠 Tech Stack

- **Runtime**: Python 3.13 (managed via `uv`)
- **API Framework**: FastAPI + Uvicorn
- **Agent Framework**: Model Context Protocol (MCP), LlamaIndex
- **AI Models**: OpenAI GPT-4o / GPT-4-turbo
- **Vector Database**: ChromaDB
- **Caching**: Diskcache
- **CLI/TUI**: Rich (Interactive live layout)
- **Data Sources**: Finnhub (WebSocket & REST), Alpha Vantage, SEC EDGAR

## 📁 Project Structure

```text
wealth-hub-agent/
├── cli/                # Interactive TUI and command-line entry points
├── clients/            # Low-level clients for external service integrations
├── openspec/           # Project specifications and formal change proposals
├── src/                # Core application logic
│   ├── agents/         # Specialized agent definitions (Analyst, Manager, etc.)
│   ├── agent_tools/    # MCP tool implementations and resource managers
│   ├── factory/        # Component factories (e.g., MCP server factory)
│   ├── models/         # Pydantic data models for structured IO
│   ├── orchestrator/   # Workflow sequencing and state management
│   ├── routes/         # FastAPI router definitions
│   ├── scripts/        # Internal utility and maintenance scripts
│   ├── utils/          # Cross-cutting utilities and configuration modules
│   └── main.py         # FastAPI service entry point
├── tests/              # Comprehensive unit and integration test suite
├── web/                # Next.js frontend for visual interaction
├── AGENTS.md           # Guidelines for agent development and conventions
├── Makefile            # Automation targets for common developer tasks
├── pyproject.toml      # Dependency management and tool configuration
└── stock_config.yml    # Configuration for tracked ticker symbols
```

## 🚦 Getting Started

### Prerequisites

- Python 3.13
- `uv` (Fast Python package installer)

### Installation

1. Clone the repository and navigate to the directory.
2. Install dependencies:
   ```bash
   make install
   ```
3. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Add your API keys for OpenAI, Finnhub, and Alpha Vantage.

### Running the System

- **FastAPI Server**: `make dev` (Runs at `http://localhost:8000`)
- **Interactive CLI**: `make cli` (Requires `make mcp` to be running for full tool access)
- **MCP Servers**: `make mcp` (Starts the underlying tool servers)

## 🧪 Testing

Run the automated test suite to verify the system:
```bash
make test
```

## 📜 Guidelines

For detailed information on contributing, agent development patterns, and the proposal-based development flow, see [AGENTS.md](AGENTS.md).

---
Built with ❤️ for advanced financial intelligence.
