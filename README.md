# Wealth Hub Agent

Wealth Hub Agent is a sophisticated financial analysis platform powered by an agentic AI architecture. It leverages stylized LLM agents to perform tasks ranging from fundamental analysis and news synthesis to RAG-based (Retrieval-Augmented Generation) information retrieval.

## 🚀 Key Features

- **Multi-Agent Architecture**: Specialized agents for different financial analysis tasks.
  - **Fundamental Analyst**: Analyzes company financials and performance metrics.
  - **News Analyst**: Aggregates, deduplicates, and synthesizes market news with recency weighting.
  - **Retrieval Agent**: Performs semantic search and retrieval across financial documents.
- **Extensible Tooling**: A robust set of tools for interacting with financial data sources (Alpha Vantage, Finnhub, EDGAR).
- **Agent Pipelines**: Structured processing workflows for agent reasoning and execution.
- **FastAPI Integration**: A production-ready API for interacting with the agentic service.
- **Modern CLI**: An interactive command-line interface for local agent interaction and testing.

## 🛠 Tech Stack

- **Language**: Python 3.13
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **AI/LLM**: [OpenAI](https://openai.com/), [LlamaIndex](https://www.llamaindex.ai/)
- **Database**: [ChromaDB](https://www.trychroma.com/) (Vector Store)
- **Tooling**: `uv` for dependency management, `make` for task automation.
- **Integrations**: Finnhub, Alpha Vantage, SEC EDGAR.

## 📁 Project Structure

```text
wealth-hub-agent/
├── cli/                # Interactive command-line interface
├── clients/            # Client libraries for external services
├── openspec/           # Project specifications and guidelines
├── src/                # Core application logic
│   ├── agents/         # Agent implementations (Fundamental, News, Retrieval)
│   ├── agent_tools/    # Reusable tools for agents (Data providers, RAG)
│   ├── models/         # Pydantic data models
│   ├── routes/         # FastAPI route definitions
│   └── main.py         # API entry point
├── tests/              # Automated test suite
├── AGENTS.md           # Developer guidelines for agent development
├── Makefile            # Automation targets
└── pyproject.toml      # Project dependencies and configuration
```

## 🚦 Getting Started

### Prerequisites

- Python 3.13
- `uv` (Fast Python package installer and resolver)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd wealth-hub-agent
   ```

2. Install dependencies using the Makefile:
   ```bash
   make install
   ```

3. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your API keys (OpenAI, Finnhub, Alpha Vantage, etc.)

### Running the Application

#### Development Server (API)
```bash
make dev
```
The API will be available at `http://localhost:8000`. You can access the health check at `/health`.

#### Interactive CLI
```bash
uv run python -m cli.main
```

## 🧪 Testing & Validation

Run the full test suite:
```bash
make test
```

## 📜 Development Guidelines

Please refer to [AGENTS.md](AGENTS.md) for detailed information on:
- Project conventions and coding style.
- Creating and applying change proposals.
- Agent development patterns and pipelines.
- Deployment notes.

---
Built with ❤️ by the Wealth Hub Team.
