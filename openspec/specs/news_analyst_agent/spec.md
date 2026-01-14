# news_analyst_agent Specification

## Purpose
TBD - created by archiving change add-news-analyst-agent. Update Purpose after archive.
## Requirements
### Requirement: Aggregate news sentiment into a unified label and score
The system SHALL expose a `NewsAnalystAgent` that ingests `RetrievalAgentOutput.market_news` (list of `NewsSentiment`) and outputs an overall sentiment label and normalized numeric score. Scores MUST normalize string/float inputs, weight by relevance (e.g., `relevance_score` or `ticker_sentiment_score`), and apply an exponential decay function for recency-aware weighting so stale articles do not dominate. The system SHALL also perform title-based deduplication to prevent over-weighting repeated headlines. Labels MUST map deterministic thresholds (e.g., score ≥ 0.25 → positive/bullish; score ≤ -0.25 → negative/bearish; otherwise neutral).

#### Scenario: Mixed positive and negative headlines
- **WHEN** the input contains both positive and negative items for the same ticker
- **THEN** the agent returns a neutral overall label with a mid-range score reflecting the offsetting signals and cites the contributing headlines in the rationale.

#### Scenario: Consistently positive recent headlines
- **WHEN** all usable items are recent and positive
- **THEN** the agent returns a positive/bullish label with a high score and lists the top contributing headlines in the rationale.

#### Scenario: Deduplication of repeated headlines
- **WHEN** the input contains multiple identical or near-identical headlines from different sources
- **THEN** the agent clusters them and counts them as a single signal for score calculation to avoid biasing the aggregate.

### Requirement: Preserve and return news items alongside aggregates
The system SHALL include the validated `market_news` entries in the agent output as `news_items`, preserving title, sentiment scores/labels, tickers, and timestamps so clients can audit the aggregation. Invalid entries MUST be skipped with warnings while retaining valid items.

#### Scenario: Skip invalid entries but keep valid news
- **WHEN** some news entries fail validation or lack usable scores
- **THEN** the agent omits those entries, surfaces warnings describing the skips, and still returns the remaining valid `news_items` intact.

### Requirement: Provide per-ticker sentiment rollups when multiple tickers appear
The system SHALL compute per-ticker sentiment rollups with label/score for any ticker present in `ticker_sentiment`, using the same normalization and thresholds as the overall score. Each rollup SHALL include a short driver list of the most influential headlines for that ticker.

#### Scenario: Multiple tickers across the feed
- **WHEN** the feed includes articles tagged to multiple tickers
- **THEN** the agent returns per-ticker sentiment rollups alongside the overall sentiment, each with label/score and top driver headlines.

### Requirement: Explainability and rationale
The system SHALL emit a concise rationale summarizing the top driver headlines (e.g., top 3 by weight) that most influenced the overall sentiment, including their labels/scores.

#### Scenario: Audit the sentiment decision
- **WHEN** a client inspects the agent output
- **THEN** the rationale lists the key headlines and their sentiment signals so the sentiment label/score can be audited.

### Requirement: Graceful handling of missing or partial news
The system SHALL return a neutral/unknown label with a zeroed or null score when no usable news items remain after validation, surfacing warnings that explain the absence. If upstream status is `partial`, the agent SHALL propagate or extend warnings to reflect skipped or missing inputs.

#### Scenario: No usable news items
- **WHEN** `market_news` is empty or all entries are invalid/stale
- **THEN** the agent returns neutral/unknown sentiment, an empty `news_items` list, and warnings describing the missing or invalid inputs.

