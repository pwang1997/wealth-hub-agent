# Change: Document the Fundamental Analyst Agent

## Why
- The `fundamental_analyst_agent` class currently only documents its responsibilities (revenue growth, margin, cash flow, balance sheet, and valuation) and desired outputs, which means there is no authoritative specification describing what downstream clients can expect from this capability.
- Without a spec, we cannot ensure the implementation stays aligned with the design note that emphasizes EDGAR-driven analysis, structured metrics, and red flag reporting.

## What Changes
- Add a new OpenSpec capability for the fundamental analyst agent that codifies the EDGAR-based data sourcing, metric coverage, and structured outputs described in `src/agents/analyst/fundamental_analyst_agent.py`.
- Capture the agent’s numerical constraints (tool-verified calculations, structured metrics) and explicit outputs (health score, strengths/weaknesses, red flags) so downstream orchestrators know the expected response schema.
- Record the prerequisite helper functions (e.g., retrieving EDGAR filings, computing metrics, scoring fundamentals) that future implementations should provide to satisfy the agent’s requirements.
- Document the proposal and related tasks to guide future implementation work and validation.

## Impact
- Affected specs: `specs/fundamental_analyst_agent/spec.md` (new capability)
- Affected code: `src/agents/analyst/fundamental_analyst_agent.py` (source of responsibilities and output requirements)
