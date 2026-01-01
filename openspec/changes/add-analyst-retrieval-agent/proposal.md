# Change: Add analyst/report retrieval agent

## Why
We need an agent that can answer user questions about financial research by combining (1) internal vector-search over indexed analyst reports and (2) discovery of relevant SEC EDGAR filings for further research.

## What Changes
- Add an analyst retrieval agent in `src/agents/analyst/retrieval_agent.py` that orchestrates retrieval across RAG + EDGAR tooling.
- Use existing tool modules:
  - RAG retrieval: `src/agent_tools/rag/retrieve_report.py`
  - EDGAR discovery: `src/agent_tools/edgar/search_reports.py`
- EDGAR results SHOULD be relatively new (within the last 6 months).
- SEC filing categories SHOULD include all annual, quarterly, and current reports (e.g., 10-K, 10-Q, 8-K) by default.
- EDGAR ingestion MUST comply with SEC EDGAR API guidance: maximum request rate 10 requests/second, and do not use multi-threading for EDGAR ingestion requests for now (see https://www.sec.gov/search-filings/edgar-application-programming-interfaces).
- EDGAR ingestion MUST be limited to at most 3 filings per query to control cost/latency.
- Workflow:
  - First, look up the appropriate ChromaDB collection and attempt vector retrieval.
  - If relevant documents exist, return the top 5 matches (and the prompt-ready context).
  - Otherwise, use EDGAR tooling to find relevant recent filings, fetch their content, and upsert into ChromaDB; then rerun retrieval and return the top 5.
- EDGAR-derived documents MUST be indexed under `corpus=edgar`, and the target collection name SHOULD include the SEC form (so downstream agents can pick the right corpus/form context deterministically).
- Return a structured result that contains:
  - RAG matches + a ready-to-prompt `context` string
  - EDGAR filing links (form/date/href) when EDGAR is used (for traceability)
- The agent MUST produce a structured “final answer” for downstream agents to consume (prefer a Pydantic model, serialized to JSON as needed).
- Add tests covering orchestration logic and “no results” behavior.

## Impact
- Affected specs: new capability `analyst-retrieval-agent`
- Affected code: `src/agents/analyst/retrieval_agent.py`, plus small public wrappers/utilities in the tool modules if needed for direct (non-MCP) invocation.
- External dependencies: uses existing integrations (ChromaDB, SEC EDGAR, env-driven configuration).

## Non-Goals
- Building a UI (CLI/API routes) for this agent.
- Reworking the indexing pipeline (`/rag/upload_pdf`) or Chroma collection naming conventions.

## Open Questions
