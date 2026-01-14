## ADDED Requirements

### Requirement: Aggregate Multi-Source Signals
The system SHALL expose an `AggregationAnalystAgent` that accepts outputs from both `FundamentalAnalystAgent` (health score, reasoning) and `NewsAnalystAgent` (sentiment score, reasoning). It MUST synthesize these inputs into a unified `AggregationAnalystOutput` containing a final recommendation (strong buy, buy, hold, sell, strong sell), a normalized confidence score (0.0 to 1.0), and a synthesized rationale.

#### Scenario: Strong Agreement
- **WHEN** Fundamental health is high (>80) AND News sentiment is positive (≥0.25)
- **THEN** The agent returns a "buy" or "strong buy" recommendation with high confidence (>0.8) and cites both strong fundamentals and positive market sentiment.

#### Scenario: Conflicting Signals
- **WHEN** Fundamental health is high (>80) BUT News sentiment is negative (≤-0.25)
- **THEN** The agent returns a "hold" or "sell" recommendation with moderate confidence, explicitly highlighting the divergence between long-term value and short-term headwinds.

### Requirement: Weighted Signal Synthesis
The system SHALL apply weighting logic to the inputs, where Fundamental analysis typically carries more weight for the base recommendation, but News sentiment acts as a momentum modifier. The specific weighting parameters SHOULD be tunable or derived from the confidence of the upstream agents if available.

#### Scenario: Fundamental Dominance within neutral news
- **WHEN** Fundamentals are strong and News is neutral
- **THEN** The agent leans towards "buy" driven by the fundamental score.

### Requirement: Unified Rationale Generation
The system SHALL generate a cohesive natural language summary that weaves together the "Why" from both upstream agents. It MUST NOT simply concatenate the two upstream summaries; it MUST synthesize them to explain the final recommendation.

#### Scenario: Explaining the Synthesis
- **WHEN** Generating the final report
- **THEN** The rationale reads like a human analyst report: "While the company shows strong balance sheet health (Fundamentals), recent regulatory concerns (News) suggest short-term volatility, leading to a Hold rating."
