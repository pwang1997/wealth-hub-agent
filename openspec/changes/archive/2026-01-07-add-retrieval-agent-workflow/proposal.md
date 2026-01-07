# Change: Add retrieval_agent Edgar filing automation

## Why
Investor research workflows should be able to chain existing Edgar filing tools (search, upsert, and RAG retrieve) and related data sources (news/sentiment) without manual orchestration so that users can simply ask for insights and receive a structured JSON response derived from the most relevant filings and contextual signals.

## What Changes
- Introduce a `retrieval_agent` capability that orchestrates the Edgar tooling pipeline plus news/sentiment enrichment in a single user-facing workflow that is implemented under `src/agents/analyst/retrieval_agent.py`.
- Define how the agent invokes search → upsert → retrieve, augments the response with news/sentiment from `src/agent_tools/alpha_vantage_mcp.py`, tracks progress, and produces a predictable JSON payload for downstream consumers.
- Specify how the agent handles partial failures (e.g., no filings found) and surfaces helpful error info within the structured response format.

## Impact
- Affected specs: `retrieval-agent`
- Affected code: `src/agents/analyst/retrieval_agent.py` (new agent), `src/agent_tools/edgar/research_reports.py` (assumed existing tools integration), and any orchestration helpers, plus relevant tests/documentation.
