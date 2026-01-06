## 1. Implementation
- [ ] 1.1 Draft the capability spec delta describing the tool workflow requirements and structured JSON response for the Edgar agent.
- [ ] 1.2 Implement the new `retrieval_agent` that sequentially invokes the search, upsert, retrieve, and market-news/sentiment tools (via `src/agent_tools/alpha_vantage_mcp.py`) and formats the structured response so tools do not leak to the user.
- [ ] 1.3 Add integration/unit tests validating the workflow orchestration and JSON schema, plus any necessary mocks for the Edgar tooling.
- [ ] 1.4 Document how to trigger the new agent from the CLI/API and how it maps to the underlying tools.
