from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

from src.agents.analyst.news.news_analyst_agent import NewsAnalystAgent
from src.agents.analyst.news.pipeline import AggregationNode, NewsAnalystPipelineState
from src.models.news_sentiments import NewsSentiment, NewsTickerSentiment
from src.models.retrieval_agent import RetrievalAgentOutput, RetrievalAgentMetadata


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
                        ticker_sentiment_label="Bullish"
                    )
                ],
                time_published=av_ts(now - timedelta(hours=1))
            ),
            NewsSentiment(
                title="Apple RELEASES NEW iphone", # Duplicate!
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
                        ticker_sentiment_label="Bullish"
                    )
                ],
                time_published=av_ts(now - timedelta(hours=2))
            ),
            NewsSentiment(
                title="Market Crash Looming",
                source="Source C",
                url="url3",
                summary="summary3",
                topics=[],
                overall_sentiment_score="-0.9",
                overall_sentiment_label="Bearish",
                ticker_sentiment=[
                    NewsTickerSentiment(
                        ticker="SPY",
                        relevance_score="0.5",
                        ticker_sentiment_score="-0.9",
                        ticker_sentiment_label="Bearish"
                    )
                ],
                time_published=av_ts(now - timedelta(days=2)) # Older
            )
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
        
        # Verify recency impact
        # The Apple (bullish) news is 1h old, the Crash (bearish) news is 48h old.
        # Apple should dominate.
        assert state.overall_score > 0
        assert state.overall_label == "bullish"
        
        # Verify per-ticker rollups
        assert "AAPL" in state.ticker_rollups
        assert state.ticker_rollups["AAPL"].sentiment_label == "bullish"
        assert state.ticker_rollups["AAPL"].sentiment_score > 0.5
        
        assert "SPY" in state.ticker_rollups
        assert state.ticker_rollups["SPY"].sentiment_label == "bearish"

    asyncio.run(run())
