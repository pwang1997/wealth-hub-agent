# manager_agent Specification

## Purpose
The `ManagerAgent` is the final decision-making layer in the investment pipeline. It consumes the synthesized research from `ResearchAnalystAgent` and produces an actionable investment decision with a clear rationale.

## Requirements

### Requirement: Investment Decision Generation
The system SHALL expose a `ManagerAgent` that accepts a `ResearchAnalystOutput`. It MUST produce a `ManagerOutput` containing a specific investment decision, a rationale, and a confidence score.

#### Decision Categories
The agent MUST choose from the following five categories:
- **Strong Buy**: Exceptional fundamentals aligned with strongly positive market sentiment.
- **Buy**: Solid fundamentals with positive sentiment, or a clear value play where fundamentals outweigh temporary negative sentiment.
- **Hold**: Fair valuation, mixed signals, or significant uncertainty in either fundamentals or news.
- **Sell**: Deteriorating fundamentals or significant negative sentiment that poses a risk to the investment thesis.
- **Strong Sell**: Severely weak fundamentals coupled with overwhelmingly negative market sentiment.

### Requirement: Decision Rationale
The agent SHALL provide a concise (2-3 sentence) rationale that explains the primary driver(s) behind the decision. 

#### Scenario: Alignment (Confluence)
- **WHEN** Fundamental health and News sentiment are both strongly positive.
- **THEN** The decision is "Strong Buy" and the rationale highlights the synergy between financial health and market perception.

#### Scenario: Conflict (Divergence)
- **WHEN** Fundamental health is strong but News sentiment is negative.
- **THEN** The agent must weigh the signals. If the news is transient (e.g., a one-time charge), it may maintain a "Buy" or "Hold". If the news is structural (e.g., fraud), it may downgrade to "Sell".

### Requirement: Confidence Scoring
The agent SHALL provide a confidence score between 0.0 and 1.0, reflecting the certainty of the decision based on the clarity and consistency of the input signals.

#### Scenario: High Certainty
- **WHEN** Both fundamental and news signals are strong and aligned.
- **THEN** The confidence score should be high (e.g., > 0.8).

#### Scenario: Low Certainty
- **WHEN** Signals are conflicting or weak (e.g., strong fundamentals but terrible news).
- **THEN** The confidence score should be lower to reflect the risk/ambiguity.

## Data Model

```python
class ManagerOutput(BaseModel):
    ticker: str
    decision: Literal["strong buy", "buy", "hold", "sell", "strong sell"]
    rationale: str
    confidence: float
```
