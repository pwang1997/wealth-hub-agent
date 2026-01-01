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
- Building a general-purpose EDGAR ingestion pipeline beyond this agent workflow.
- PDF indexing/ingestion changes.
- Building endpoints/CLI wiring.

## Proposed API
- Module: `src/agents/analyst/retrieval_agent.py`
- Public entrypoint: `AnalystRetrievalAgent.retrieve(query: str, *, company_name: str | None = None, ticker: str | None = None, ...) -> AnalystRetrievalResult`
- Response model: define `AnalystRetrievalResult` (and nested models as needed) as Pydantic `BaseModel` types so downstream agents can reliably consume the output.

## Orchestration Rules
- Always attempt RAG retrieval first when a query is provided.
- If RAG retrieval returns relevant matches, return the top 5.
- If RAG retrieval returns no relevant matches:
  - Discover recent EDGAR filings (within ~6 months) using `search_reports`.
  - Select at most 3 filings per query to fetch/ingest.
  - Fetch the EDGAR primary document (HTML), chunk/embed, and upsert into ChromaDB under `corpus=edgar`.
  - Collection naming SHOULD include the SEC form (e.g., `finance_edgar_<company>_10-K`) so downstream agents can target form-specific context.
  - Rerun RAG retrieval and return the top 5.

## EDGAR API Compliance
- EDGAR ingestion requests MUST be rate-limited to a maximum of 10 requests/second.
- EDGAR ingestion requests MUST be single-threaded (no multi-threading) for now.
- EDGAR ingestion MUST be limited to at most 3 filings per query.
- Reference: https://www.sec.gov/search-filings/edgar-application-programming-interfaces

## Response Shape (Draft)
The agent returns a structured “final answer” model (Pydantic), which is JSON-serializable with keys:
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
