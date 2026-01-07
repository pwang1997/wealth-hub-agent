## 1. Implementation
- [ ] 1.1 Draft the capability spec delta describing the tool workflow requirements, the structured JSON response (matching `RetrievalAgentOutput`), and the error-handling/fallback policy for retries.
- [ ] 1.2 Implement the new `retrieval_agent` that sequentially invokes the search, upsert, retrieve, and market-news/sentiment tools (via `src/agent_tools/alpha_vantage_mcp.py`), logs any failures in `metadata.warnings` without short-circuiting, and formats the structured response so tools do not leak to the user.
- [ ] 1.3 Add integration/unit tests validating the workflow orchestration, metadata warnings, and JSON schema, plus any necessary mocks for the Edgar tooling and Alpha Vantage news.
- [ ] 1.4 Document how to trigger the new agent from the CLI/API, how it maps to the underlying tools, and how the fallback/retry guidance should be consumed by downstream orchestration logic; include a step to run `uv run pytest` before final validation.
