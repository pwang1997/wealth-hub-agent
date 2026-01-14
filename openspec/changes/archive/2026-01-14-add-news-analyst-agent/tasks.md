## 1. Specification
- [x] 1.1 Draft ADDED requirements for `news_analyst_agent` (aggregation, passthrough, per-ticker rollups, explainability, warnings)
- [x] 1.2 Validate change with `openspec validate add-news-analyst-agent --strict`

## 2. Implementation
- [x] 2.1 Add output schema for aggregated sentiment (overall + per-ticker + rationale + news_items passthrough)
- [x] 2.2 Implement `news_analyst_agent` to consume `RetrievalAgentOutput.market_news` and compute scores/labels
- [x] 2.3 Handle partial/invalid entries with warnings and neutral/unknown fallback

## 3. Testing
- [x] 3.1 Add unit tests covering positive, negative, mixed, and empty news inputs
- [x] 3.2 Verify integration path from retrieval agent into new agent output
