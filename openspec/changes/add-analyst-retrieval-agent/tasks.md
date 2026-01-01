## 1. Specification
- [ ] 1.1 Define the agent inputs/outputs and routing rules (RAG vs EDGAR) in the spec.
- [ ] 1.2 Define error handling behavior (missing collections, no matches, bad tickers, upstream failures).

## 2. Implementation
- [ ] 2.1 Implement `AnalystRetrievalAgent` (or equivalent) in `src/agents/analyst/retrieval_agent.py`.
- [ ] 2.1.1 Define a Pydantic response model (e.g., `AnalystRetrievalResult`) for the agent’s structured final answer, suitable for downstream agent consumption.
- [ ] 2.2 Add a small adapter layer so the agent can call RAG retrieval and EDGAR search without requiring an MCP server process (preferred), while still reusing the logic in:
  - [ ] 2.2.1 `src/agent_tools/rag/retrieve_report.py`
  - [ ] 2.2.2 `src/agent_tools/edgar/search_reports.py`
- [ ] 2.3 Implement query interpretation:
  - [ ] 2.3.1 Extract optional `ticker` and/or `company_name` hints when present.
  - [ ] 2.3.2 Infer EDGAR `filing_category` when the user asks for a specific form or “latest filing”.
- [ ] 2.4 Ensure EDGAR ingestion compliance (max 10 rps; no multi-threading; max 3 filings/query).
- [ ] 2.5 Implement fallback ingestion when RAG returns no matches:
  - [ ] 2.5.1 Discover relevant recent filings (within ~6 months).
  - [ ] 2.5.2 Fetch filing content and chunk/embed for ChromaDB.
  - [ ] 2.5.3 Upsert to the appropriate ChromaDB collection.
  - [ ] 2.5.4 Rerun retrieval and return top 5.
- [ ] 2.6 Merge outputs into a single structured response with stable keys.

## 3. Tests
- [ ] 3.1 Add unit tests for agent routing and response shaping.
- [ ] 3.2 Add tests for “no Chroma collections found” and “CIK not found” error paths (mocked).
- [ ] 3.3 Add tests for fallback ingestion flow (mock EDGAR fetch + Chroma upsert).

## 4. Documentation
- [ ] 4.1 Document required env vars and local prerequisites (Chroma config, SEC access headers) in `README.md` or a dedicated doc.
