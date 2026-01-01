# Change: Add analyst/report retrieval agent

## Why
We need an agent that can answer user questions about financial research by combining (1) internal vector-search over indexed analyst reports and (2) discovery of relevant SEC EDGAR filings for further research.

## What Changes
- Add an analyst retrieval agent in `src/agents/analyst/retrieval_agent.py` that orchestrates retrieval across RAG + EDGAR tooling.
- Use existing tool modules:
  - RAG retrieval: `src/agent_tools/rag/retrieve_report.py`
  - EDGAR discovery: `src/agent_tools/edgar/search_reports.py`
- EDGAR results SHOULD be relatively new (within the last 6 months).
- Workflow:
  - First, look up the appropriate ChromaDB collection and attempt vector retrieval.
  - If relevant documents exist, return the top 5 matches (and the prompt-ready context).
  - Otherwise, use EDGAR tooling to find relevant recent filings, fetch their content, and upsert into ChromaDB; then rerun retrieval and return the top 5.
- Return a structured result that contains:
  - RAG matches + a ready-to-prompt `context` string
  - EDGAR filing links (form/date/href) when EDGAR is used (for traceability)
- Add tests covering orchestration logic and “no results” behavior.

## Impact
- Affected specs: new capability `analyst-retrieval-agent`
- Affected code: `src/agents/analyst/retrieval_agent.py`, plus small public wrappers/utilities in the tool modules if needed for direct (non-MCP) invocation.
- External dependencies: uses existing integrations (ChromaDB, SEC EDGAR, env-driven configuration).

## Non-Goals
- Building a UI (CLI/API routes) for this agent.
- Reworking the indexing pipeline (`/rag/upload_pdf`) or Chroma collection naming conventions.

## Open Questions
- Which SEC filing categories should be considered by default when the user does not specify a form (e.g., prefer 10-K/10-Q, include 8-K)?
- Should EDGAR ingestion be limited to a fixed number of filings per query (e.g., 1–3) to control cost/latency?
- Should the agent produce a natural-language “final answer” (LLM-backed), or only a structured retrieval bundle for downstream use?
