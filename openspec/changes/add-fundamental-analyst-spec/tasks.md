## 1. Implementation
- [x] 1.1 Capture the agent’s observation from `src/agents/analyst/fundamental_analyst_agent.py` into a capability spec (EDGAR data focus, metric coverage, structured outputs).
- [x] 1.2 Add scenarios that verify the agent uses tool-verified calculations, emits the health score/strengths/red flags, and cites EDGAR filings as the authoritative source.
- [x] 1.3 Document the prerequisite helper functions and tools (e.g., financial statement normalization, historical data retrieval, metric computation, scoring, optional market and valuation fetchers) that the capability depends on.
- [x] 1.4 Run `openspec validate add-fundamental-analyst-spec --strict` and mark the change ready for review once all deltas pass.
- [x] 1.5 Implement `src/agents/analyst/fundamental_analyst_agent.py` logic to process `AnalystRetrievalAgent` output and analyze fundamentals.

## 2. Approval
- [ ] 2.1 Share the proposal with the team and collect approval for the new capability spec.
