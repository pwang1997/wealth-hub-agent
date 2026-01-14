## ADDED Requirements

### Requirement: Compose Multi-Source Signals
The system SHALL expose a `ResearchAnalystAgent` that accepts outputs from both `FundamentalAnalystAgent` (health score, summary) and `NewsAnalystAgent` (sentiment score, rationale). It MUST synthesize these inputs into a unified `ResearchAnalystOutput` containing a composed analysis that weaves together the fundamental health and market sentiment.

#### Scenario: Alignment between Fundamentals and Sentiment
- **WHEN** Fundamental health is high (>80) AND News sentiment is positive (≥0.25)
- **THEN** The agent returns a composed analysis that highlights the synergy between strong financial health and bullish market sentiment.

#### Scenario: Divergence between Fundamentals and Sentiment
- **WHEN** Fundamental health is high (>80) BUT News sentiment is negative (≤-0.25)
- **THEN** The agent returns a composed analysis that clearly contrasts the long-term fundamental strength with short-term market headwinds.

### Requirement: Synthesized Analysis Generation
The system SHALL generate a cohesive natural language report that explains the interaction between the two upstream signals. It MUST NOT simply concatenate the summaries; it MUST synthesize them to explain how they contextualize each other.

#### Scenario: Explaining the Interaction
- **WHEN** Generating the final report
- **THEN** The composed analysis reads like a professional synthesis: "While the company shows strong balance sheet health (Fundamentals), recent regulatory concerns (News) suggest short-term volatility that may impact near-term performance."
