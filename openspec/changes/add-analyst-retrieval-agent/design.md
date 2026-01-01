## Context
We already have tool implementations for:
- Vector retrieval over analyst reports stored in ChromaDB (`src/agent_tools/rag/retrieve_report.py`).
- SEC EDGAR filing discovery by ticker and form (`src/agent_tools/edgar/search_reports.py`).

This change adds an “analyst retrieval agent” that orchestrates these tools based on a user’s query.

## Goals
- Provide one entrypoint that, given a user query, returns:
  - Relevant analyst-report chunks (with ranked matches + a preformatted context string).
  - Relevant EDGAR filing links when the query calls for filings.
- Keep the agent usable without having to spin up MCP subprocesses (direct Python invocation), while still reusing existing tool logic.

## Non-Goals
- Content fetching of EDGAR filings.
- PDF indexing/ingestion changes.
- Building endpoints/CLI wiring.

## Proposed API
- Module: `src/agents/analyst/retrieval_agent.py`
- Public entrypoint: `AnalystRetrievalAgent.retrieve(query: str, *, company_name: str | None = None, ticker: str | None = None, ...) -> dict`

## Orchestration Rules
- Always attempt RAG retrieval first when a query is provided.
- If RAG retrieval returns relevant matches, return the top 5.
- If RAG retrieval returns no relevant matches:
  - Discover recent EDGAR filings (within ~6 months) using `search_reports`.
  - Fetch filing content and upsert into the appropriate ChromaDB collection.
  - Rerun RAG retrieval and return the top 5.

## Response Shape (Draft)
The agent returns a JSON-serializable dict with keys:
- `query`
- `rag`: `{ collection, num_matches, matches, context }` (from `retrieve_report`, typically `top_k=5`)
- `edgar`: `{ ticker, cik, filings }` when EDGAR was used, else `null`
- `errors`: list of `{ source, message }` for partial failures (RAG can succeed even if EDGAR fails, and vice versa)

## Error Handling
- RAG errors about missing collections should be returned as a structured error (not a crash), so callers can prompt users to upload/index PDFs.
- EDGAR errors (invalid ticker / CIK not found / request failures) should be returned as structured errors.
 - EDGAR ingestion failures should not prevent returning an “empty” RAG result with actionable errors.

## Testing Notes
- Mock Chroma retrieval and EDGAR HTTP calls; test routing and response stability.
- Ensure deterministic behavior for “infer filing_category” from query text.
