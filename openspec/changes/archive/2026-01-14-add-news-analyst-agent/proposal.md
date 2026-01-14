# Change: Add news analyst agent aggregation

## Why
Retrieval results already include `market_news` entries, but consumers need a single, trustworthy sentiment label and score alongside the underlying news items for transparency and auditing.

## What Changes
- Add a `news_analyst_agent` that ingests `RetrievalAgentOutput.market_news` and emits an overall sentiment label/score with per-ticker rollups.
- Preserve and pass through the validated news items so clients can inspect headlines and scores directly.
- Surface rationale (top driver headlines) and warnings when inputs are missing or partially valid.

## Impact
- Affected specs: `news_analyst_agent`
- Affected code: news aggregation agent, output schema consumed by FastAPI/CLI, validation on `NewsSentiment` inputs
