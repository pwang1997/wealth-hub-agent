## ADDED Requirements

### Requirement: EDGAR-based assessment of fundamental pillars
The fundamental analyst agent SHALL treat EDGAR filings as the authoritative data source and SHALL use them to evaluate revenue growth, margin trends, cash flow quality, balance sheet strength, and valuation metrics (P/E, EV/EBITDA, FCF yield), emitting each pillar with explicit references to the filings that informed the judgment so downstream orchestrators can verify the evidence.

#### Scenario: Analyze a company using recent EDGAR filings
- **WHEN** a user requests insight into Company X’s fundamentals and fresh EDGAR filings are available
- **THEN** the agent invokes the EDGAR tooling workflow, extracts the requested pillars, cites the filings for each pillar, and reports the per-pillar observations so the caller can trace every claim back to a federal filing.

### Requirement: Emit structured health score, signal summaries, and red flags
The fundamental analyst agent SHALL return a structured payload that includes a numeric fundamental health score, a list of key strengths and weaknesses, and a catalog of red flags (for example, declining margins or leverage spikes) so downstream consumers can programmatically triage risk.

#### Scenario: Provide structured signals for downstream automation
- **WHEN** the agent finishes its analysis
- **THEN** the response contains a health score field, separate collections for strengths and weaknesses, and a red flags array that explains the nature of each concern, enabling orchestration layers to filter or route the result automatically.

### Requirement: Prefer tool-verified calculations and structured metrics
To honor the design constraint about numerical discipline, the fundamental analyst agent SHALL rely on tool-verified calculations and structured metric fields rather than free-form LLM math, using prose only to add context beyond the baseline numeric outputs.

#### Scenario: Respect the numerical constraint during analysis
- **WHEN** EDGAR tooling returns precise revenue, margin, and valuation measurements
- **THEN** the agent uses those structured metrics directly to compute the health score and signals, avoids inventing additional numbers, and logs or surfaces discrepancies only by referencing the tool outputs rather than by writing new ad-hoc calculations in prose.

### Requirement: Declare prerequisite helper functions and tools
The fundamental analyst agent SHALL expect a set of reusable helper functions or tools that normalize financial statements, retrieve historical financial data, compute metrics (revenue growth, margins, cash flow quality, leverage, valuation), score the fundamentals, and validate the structured output before emitting it, with optional helpers for fetching supplementary market data and computing valuation-specific metrics when needed.

#### Scenario: Verify prerequisites before executing the agent
- **WHEN** a downstream orchestrator wires up the fundamental analyst capability
- **THEN** it confirms that helpers such as `normalize_financial_statements`, `retrieve_historical_financials`, relevant `compute_*_metrics`, optional `fetch_market_data` and `compute_valuation_metrics`, `score_fundamentals`, and `validate_fundamental_output` are available so the agent’s analysis pipeline can rely on them for each run.
