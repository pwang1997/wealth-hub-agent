# Change: Add Aggregation Analyst Agent

## Why
Users need a unified investment signal that combines both fundamental analysis (long-term health, financial metrics) and news sentiment (short-term market perception). Currently, these agents operate independently, requiring the user or downstream systems to manually synthesize conflicting or complementary signals.

## What Changes
- Create a new `AggregationAnalystAgent` capability.
- The agent will take outputs from `FundamentalAnalystAgent` and `NewsAnalystAgent`.
- It will produce a synthesized `AggregationAnalystOutput` containing:
    - A unified investment recommendation (e.g., Buy, Sell, Hold).
    - A confidence score.
    - A summary rationale citing evidence from both sources.

## Impact
- New spec: `specs/aggregation_analyst_agent/spec.md`
- No changes to existing agents (they are upstream dependencies).
