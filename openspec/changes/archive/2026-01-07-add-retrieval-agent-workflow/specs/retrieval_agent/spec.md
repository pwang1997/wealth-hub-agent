## ADDED Requirements
### Requirement: Edgar filing automation retrieval_agent
The system SHALL expose a `retrieval_agent` that orchestrates the Edgar tooling workflow, invoking the filing search tool, automatically upserting results into the vector database, calling the RAG retrieve tool to answer the user query, and augmenting the response with relevant market news and sentiment via `src/agent_tools/alpha_vantage_mcp.py`. Implementation expectations align with `src/agents/analyst/retrieval_agent.py`, and the structured JSON schema produced by the agent SHALL match `src/models/retrieval_agent.py`’s `RetrievalAgentOutput` (with `edgar_filings` derived from `SearchReportsOutput` and `market_news` represented by `MarketNewsSource`).

#### Scenario: Orchestrate the full workflow for a user question
- **WHEN** a user asks for insight derived from Edgar filings (e.g., "What did Company X disclose about its recent acquisition?")
- **THEN** the agent calls the search tool, falls back to no-op upsert when no new documents arrive, invokes the retrieve tool with the upserted content, supplements the answer with relevant news/sentiment via `alpha_vantage_mcp`, and returns a final structured JSON response that includes the generated answer plus references to the filings used.

### Requirement: News and sentiment context enrichment
The `retrieval_agent` SHALL query `src/agent_tools/alpha_vantage_mcp.py` for news and sentiment relevant to the user query and include this context (e.g., headlines, sentiment scores) inside the response `metadata` or `filings` entries.

#### Scenario: Provide news sentiment alongside filings
- **WHEN** the Edgar workflow runs for a company or topic with recent news
- **THEN** the agent returns a JSON payload whose `metadata` includes a `news` array summarizing headlines and sentiment tags so clients can correlate filings with live market sentiment.

### Requirement: Error reporting for FastAPI orchestrators
The `retrieval_agent` SHALL capture MCP/tool errors, log them, and surface the information in `metadata.warnings` so a FastAPI-based orchestrator can decide whether to retry the workflow. All tool failures SHOULD result in a `partial` status and never short-circuit the agent, allowing the API layer to re-call the pipeline with adjusted inputs if desired.

#### Scenario: Surface diagnostics without terminal exits
- **WHEN** a tool call fails for any reason (validation, downstream error, timeout, etc.)
- **THEN** the agent appends a warning entry describing the failure, keeps running the remaining steps, and returns a `partial` status so the FastAPI caller can retry if needed instead of the agent terminating early.
