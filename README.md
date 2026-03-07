# Wealth Hub Agent

[![Pull Request Tests](https://github.com/pwang1997/wealth-hub-agent/actions/workflows/pull-request-tests.yml/badge.svg?branch=main)](https://github.com/pwang1997/wealth-hub-agent/actions/workflows/pull-request-tests.yml) [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/pwang1997/wealth-hub-agent)

Wealth Hub Agent is a high-performance financial intelligence platform powered by a multi-agent AI architecture. It leverages specialized LLM agents and the **Model Context Protocol (MCP)** to perform deep fundamental analysis, news synthesis, and RAG-based (Retrieval-Augmented Generation) information retrieval, all delivered through a real-time, agent-centric dashboard.

## 🚀 Key Features

-   **Multi-Agent Orchestration**: A sophisticated workflow that coordinates specialized agents (Retrieval, Fundamental, News, Research, Investment Manager) for end-to-end financial research.
-   **Agent-Centric Dashboard**: A modern Next.js interface that visualizes agent activity in real-time, with sequential materialization of insights.
-   **Real-time Event Streaming (SSE)**: Built-in Server-Sent Events (SSE) support for streaming agent progress and results from the backend to the frontend.
-   **Model Context Protocol (MCP)**: Native integration with financial data tools (Alpha Vantage, Finnhub, SEC EDGAR) via high-performance MCP servers.
-   **Advanced RAG Pipeline**: Intelligent document retrieval and indexing using LlamaIndex and ChromaDB for semantic search across financial filings.
-   **Parallel Execution**: Optimal performance through simultaneous execution of independent agent steps (e.g., Fundamental and News analysis).
-   **Stateful & Resumable Workflows**: Robust caching layer (Diskcache) allowing for workflow recovery and partial execution.

## 🤖 Agent Architecture

The system coordinates a hierarchical team of specialized agents:

1.  **Analyst Retrieval Agent**: The "Information Scout" – fetches market news and performs semantic search across financial documents.
2.  **Fundamental Analyst Agent**: The "Quant" – analyzes company financials, performance metrics, and valuation drivers.
3.  **News Analyst Agent**: The "Press Room" – aggregates and synthesizes market news with deduplication and recency weighting.
4.  **Research Analyst Agent**: The "Synthesizer" – merges fundamental and news insights into a comprehensive research report.
5.  **Investment Manager Agent**: The "Decision Maker" – provides actionable investment recommendations based on synthesized research.

[![](https://mermaid.ink/img/pako:eNpdj01PhDAQhv9KM2eWLN_Qg8kuaOJBD8aTwGGyjECkhZSyuhL-u4VVD9tTn3n6zkxnOPUVAYda4dCw16yQzJxD_kJatXTGjh1qkrpku90dO-YPk6xQmMIqJHaXUZe_ke1Fmj_T53ijjpvKTM-RUJ2aG51e9RWyDe7zR3mmUa-T2BNKrEmVYJkt2wq4VhNZIEgJXBHmNVqAbkhQAdxcK1QfBRRyMZkB5Vvfi7-Y6qe6Af6O3WhoGirUlLVo_i_-q4pkRSrtJ6mBe-HWA_gMX4bi2Hb3Xui4SRIkceJYcAHuB7bj-kkURoEXBmHiLxZ8b0P3dhwFyw8Ys22_?type=png)](https://mermaid.live/edit#pako:eNpdj01PhDAQhv9KM2eWLN_Qg8kuaOJBD8aTwGGyjECkhZSyuhL-u4VVD9tTn3n6zkxnOPUVAYda4dCw16yQzJxD_kJatXTGjh1qkrpku90dO-YPk6xQmMIqJHaXUZe_ke1Fmj_T53ijjpvKTM-RUJ2aG51e9RWyDe7zR3mmUa-T2BNKrEmVYJkt2wq4VhNZIEgJXBHmNVqAbkhQAdxcK1QfBRRyMZkB5Vvfi7-Y6qe6Af6O3WhoGirUlLVo_i_-q4pkRSrtJ6mBe-HWA_gMX4bi2Hb3Xui4SRIkceJYcAHuB7bj-kkURoEXBmHiLxZ8b0P3dhwFyw8Ys22_)

## 🛠 Tech Stack

### Backend (AI & Orchestration)
-   **Runtime**: Python 3.13 (managed via [uv](https://github.com/astral-sh/uv) for high-speed performance)
-   **Framework**: FastAPI + Uvicorn
-   **Agent Intelligence**: OpenAI GPT-5
-   **Orchestration**: Model Context Protocol (MCP), LlamaIndex
-   **Storage**: ChromaDB (Vector Store), Diskcache (Workflow State)
-   **Data Sources**: Finnhub, Alpha Vantage, SEC EDGAR

### Frontend (User Interface)
-   **Framework**: Next.js 16 (React 19)
-   **Styling**: Tailwind CSS 4
-   **Components**: Radix UI, Lucide Icons, Shadcn/ui (Tailored)
-   **State Management**: Tanstack Query (React Query) for robust data fetching

## 📁 Project Structure

```text
wealth-hub-agent/
├── cli/                 # Interactive Rich-based TUI
├── clients/             # Low-level service clients (Finnhub, Alpha Vantage)
├── openspec/            # Technical specifications and design docs
├── src/                 # Core Backend Logic
│   ├── agents/          # Specialized Agent definitions
│   ├── agent_tools/     # MCP tool implementations & server management
│   ├── orchestrator/    # Workflow sequencing & SSE streaming
│   ├── models/          # Shared Pydantic schemas
│   └── main.py          # FastAPI application entry
├── tests/               # Comprehensive pytest suite
└── web/                 # Next.js Frontend application
```

## 🚦 Developer Commands

The project uses a `Makefile` for streamlined development:

| Command | Action |
| :--- | :--- |
| `make compose-up` | **Build and Run Local Services**: Build docker images and start local backend services in docker container |
| `make dev` | **Start Backend**: Launches the FastAPI server at `localhost:8000` |
| `make web` | **Start Frontend**: Launches the Next.js dev server at `localhost:3000` |
| `make mcp` | **Start MCP Servers**: Bridges Alpha Vantage, Finnhub, and RAG tools |
| `make cli` | **Start TUI**: Launches the terminal-based interactive UI |
| `make test` | **Run Tests**: Executes the full backend test suite |
| `make lint` | **Lint & Format**: Runs Ruff for code quality |

## 🧪 Quick Start

1.  **Install dependencies**:
    ```bash
    make dev  # This will also sync python env via uv
    ```
2.  **Configure Environment**:
    Create a `.env` file based on `.env.example` with your `LLM_API_KEY`, `FINNHUB_API_KEY`, and `ALPHA_VANTAGE_API_KEY`.
3.  **Run the full stack**:
    ```bash
    # This will build docker images and start local backend services in docker container.
    make compose-up
    ```
    
    ```bash
    # This will start MCP servers in separate terminal.
    make mcp
    ```
    
    ```bash
    # This will start FastAPI server in separate terminal.
    make dev
    ```
    
    ```bash
    # This will start Next.js dev server in separate terminal.
    make web
    ```

---
Built with ❤️ for advanced financial intelligence.
