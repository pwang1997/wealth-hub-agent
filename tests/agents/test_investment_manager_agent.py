import json
from unittest.mock import MagicMock, patch

import pytest

from src.agents.manager.investment.investment_manager_agent import InvestmentManagerAgent
from src.models.fundamental_analyst import FundamentalAnalystOutput
from src.models.investment_manager import InvestmentManagerOutput
from src.models.news_analyst import NewsAnalystOutput
from src.models.research_analyst import ResearchAnalystOutput


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_research_output():
    return ResearchAnalystOutput(
        ticker="AAPL",
        composed_analysis="Strong fundamentals and bullish news.",
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


@pytest.mark.anyio
async def test_investment_manager_agent_process(mock_research_output):
    agent = InvestmentManagerAgent()

    # Mock OpenAI
    with patch("src.agents.manager.investment.pipeline.OpenAI") as MockOpenAI:
        mock_client = MockOpenAI.return_value

        # 1. Mock ReasoningNode response
        mock_reasoning_response = MagicMock()
        mock_reasoning_response.choices[0].message.content = (
            "<thought>Fundamentals strong, news positive. Decision should be strong buy.</thought>\n"
            "<objectives>Highlight confluence of signals.</objectives>"
        )

        # 2. Mock DecisionNode response
        mock_decision_response = MagicMock()
        mock_decision_response.choices[0].message.content = json.dumps(
            {
                "decision": "strong buy",
                "rationale": "Perfect alignment of fundamentals and sentiment.",
                "confidence": 0.95,
            }
        )

        # Setup side effect for multiple calls
        mock_client.chat.completions.create.side_effect = [
            mock_reasoning_response,
            mock_decision_response,
        ]

        with patch.dict("os.environ", {"OPENAI_API_KEY": "fake-key"}):
            result = await agent.process(mock_research_output)

            assert isinstance(result, InvestmentManagerOutput)
            assert result.ticker == "AAPL"
            assert result.decision == "strong buy"
            assert result.confidence == 0.95
            assert "Perfect alignment" in result.rationale
            assert result.reasoning == "Highlight confluence of signals."
