from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from src.agents.analyst.news.news_analyst_agent import NewsAnalystAgent
from src.agents.analyst.news.pipeline import AggregationNode, NewsAnalystPipelineState
from src.models.news_sentiments import NewsSentiment, NewsTickerSentiment
from src.models.retrieval_agent import RetrievalAgentMetadata, RetrievalAgentOutput


def test_aggregation_logic():
    async def run():
        agent = NewsAnalystAgent()

        # Helper to create Alpha Vantage style timestamp
        def av_ts(dt: datetime) -> str:
            return dt.strftime("%Y%m%dT%H%M%S")

        now = datetime.now(UTC)

        # 1. Duplicate headlines
        # 2. Different recency
        news = [
            NewsSentiment(
                title="Apple releases new iPhone",
                source="Source A",
                url="url1",
                summary="summary1",
                topics=[],
                overall_sentiment_score="0.8",
                overall_sentiment_label="Bullish",
                ticker_sentiment=[
                    NewsTickerSentiment(
                        ticker="AAPL",
                        relevance_score="0.9",
                        ticker_sentiment_score="0.8",
                        ticker_sentiment_label="Bullish",
                    )
                ],
                time_published=av_ts(now - timedelta(hours=1)),
            ),
            NewsSentiment(
                title="Apple RELEASES NEW iphone",  # Duplicate!
                source="Source B",
                url="url2",
                summary="summary2",
                topics=[],
                overall_sentiment_score="0.8",
                overall_sentiment_label="Bullish",
                ticker_sentiment=[
                    NewsTickerSentiment(
                        ticker="AAPL",
                        relevance_score="0.9",
                        ticker_sentiment_score="0.8",
                        ticker_sentiment_label="Bullish",
                    )
                ],
                time_published=av_ts(now - timedelta(hours=2)),
            ),
            NewsSentiment(
                title="Irrelevant News",
                source="Source D",
                url="url4",
                summary="summary4",
                topics=[],
                overall_sentiment_score="0.5",
                overall_sentiment_label="Bullish",
                ticker_sentiment=[
                    NewsTickerSentiment(
                        ticker="AAPL",
                        relevance_score="0.5",  # Should be ignored (> 0.8 required)
                        ticker_sentiment_score="0.5",
                        ticker_sentiment_label="Bullish",
                    )
                ],
                time_published=av_ts(now - timedelta(minutes=5)),
            ),
            NewsSentiment(
                title="NVIDIA Breakthrough",
                source="Source E",
                url="url5",
                summary="summary5",
                topics=[],
                overall_sentiment_score="0.9",
                overall_sentiment_label="Bullish",
                ticker_sentiment=[
                    NewsTickerSentiment(
                        ticker="NVDA",
                        relevance_score="0.95",  # Highly relevant but WRONG TICKER
                        ticker_sentiment_score="0.9",
                        ticker_sentiment_label="Bullish",
                    )
                ],
                time_published=av_ts(now - timedelta(minutes=1)),
            ),
        ]

        retrieval_output = RetrievalAgentOutput(
            query="Apple news",
            status="success",
            answer="",
            edgar_filings={
                "ticker": "AAPL",
                "cik": "123",
                "filings": [],
                "collection_name": "edgar_filings",
            },
            market_news=news,
            metadata=RetrievalAgentMetadata(),
        )

        state = NewsAnalystPipelineState(retrieval_output=retrieval_output)
        node = AggregationNode()

        await node.run(agent, state)

        # Verify deduplication
        assert any("Deduplicated 1 articles" in w for w in state.warnings)

        # Verify relevance and ticker filtering
        # 1. 'Irrelevant News' (relevance 0.5) skipped.
        # 2. 'NVIDIA Breakthrough' (wrong ticker NVDA) skipped.
        # 3. AAPL rollup based on Item #1 (Item #2 is duplicate).
        RELEVANCE_THRESHOLD = 0.8
        assert "AAPL" in state.ticker_rollups
        assert state.ticker_rollups["AAPL"].sentiment_label == "bullish"
        assert state.ticker_rollups["AAPL"].sentiment_score == RELEVANCE_THRESHOLD

        # 'NVDA' or 'SPY' shouldn't be here
        assert "NVDA" not in state.ticker_rollups
        assert "SPY" not in state.ticker_rollups

        # Only AAPL headlines should be in the rollups
        all_headlines = []
        for r in state.ticker_rollups.values():
            all_headlines.extend(r.top_headlines)
        assert "Irrelevant News" not in all_headlines
        assert "NVIDIA Breakthrough" not in all_headlines
        assert "Apple releases new iPhone" in all_headlines

    asyncio.run(run())
