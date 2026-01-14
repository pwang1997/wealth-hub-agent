import asyncio
import logging

from src.agents.manager.investment.investment_manager_agent import InvestmentManagerAgent
from src.models.fundamental_analyst import FundamentalAnalystOutput
from src.models.news_analyst import NewsAnalystOutput
from src.models.research_analyst import ResearchAnalystOutput

logging.basicConfig(level=logging.INFO)


async def main():
    agent = InvestmentManagerAgent()

    # Mock ResearchAnalystOutput
    mock_research = ResearchAnalystOutput(
        ticker="AAPL",
        composed_analysis=(
            "Apple (AAPL) shows exceptional fundamental health with a score of 85, "
            "driven by strong revenue growth and healthy margins. Market sentiment "
            "is also bullish (0.45) following positive iPhone sales data and "
            "optimistic analyst forecasts. The convergence of strong financials "
            "and positive sentiment suggests a robust outlook."
        ),
        fundamental_analysis=FundamentalAnalystOutput(
            ticker="AAPL",
            health_score=85,
            summary="Strong fundamentals",
            strengths=[],
            weaknesses=[],
            red_flags=[],
            citations=[]
        ),
        news_analysis=NewsAnalystOutput(
            query="AAPL",
            overall_sentiment_score=0.45,
            overall_sentiment_label="Bullish",
            rationale="Bullish news",
            ticker_rollups=[],
            news_items=[],
            warnings=[]
        )
    )

    print(f"\n--- Processing Investment Decision for {mock_research.ticker} ---")
    result = await agent.process(mock_research)
    print("\n--- Investment Manager Decision ---")
    print(f"Ticker: {result.ticker}")
    print(f"Decision: {result.decision}")
    print(f"Rationale: {result.rationale}")
    print(f"Confidence: {result.confidence}")
    print(f"Reasoning: {result.reasoning}")


if __name__ == "__main__":
    asyncio.run(main())
