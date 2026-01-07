## ADDED Requirements
### Requirement: Edgar filing automation retrieval_agent
The system SHALL expose a `retrieval_agent` that orchestrates the Edgar tooling workflow, invoking the filing search tool, then automatically upserting results into the vector database, calling the RAG retrieve tool to answer the user query, and augmenting the response with relevant market news and sentiment via `src/agent_tools/alpha_vantage_mcp.py`. Implementation expectations align with `src/agents/analyst/retrieval_agent.py`, even if the current functions and comments are incomplete.

#### Scenario: Orchestrate the full workflow for a user question
- **WHEN** a user asks for insight derived from Edgar filings (e.g., "What did Company X disclose about its recent acquisition?")
- **THEN** the agent calls the search tool, falls back to no-op upsert when no new documents arrive, invokes the retrieve tool with the upserted content, supplements the answer with relevant news/sentiment via `alpha_vantage_mcp`, and returns a final structured JSON response that includes the generated answer plus references to the filings used.

### Requirement: News and sentiment context enrichment
The `retrieval_agent` SHALL query `src/agent_tools/alpha_vantage_mcp.py` for news and sentiment relevant to the user query and include this context (e.g., headlines, sentiment scores) inside the response `metadata` or `filings` entries.

#### Scenario: Provide news sentiment alongside filings
- **WHEN** the Edgar workflow runs for a company or topic with recent news
- **THEN** the agent returns a JSON payload whose `metadata` includes a `news` array summarizing headlines and sentiment tags so clients can correlate filings with live market sentiment.
