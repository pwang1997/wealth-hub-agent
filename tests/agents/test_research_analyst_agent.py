import json
from unittest.mock import MagicMock

import pytest

from clients.model_client import ModelClient
from src.agents.analyst.research.research_analyst_agent import ResearchAnalystAgent
from src.models.fundamental_analyst import FundamentalAnalystOutput
from src.models.news_analyst import NewsAnalystOutput
from src.models.research_analyst import ResearchAnalystOutput


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_fundamental_output():
    return FundamentalAnalystOutput(
        ticker="AAPL",
        health_score=85,
        summary="Strong financial health with consistent margins.",
        citations=[],
    )


@pytest.fixture
def mock_news_output():
    return NewsAnalystOutput(
        query="Apple news",
        overall_sentiment_score=0.6,
        overall_sentiment_label="bullish",
        rationale="Market is positive on new product launches.",
    )


@pytest.mark.anyio
async def test_research_analyst_agent_process(mock_fundamental_output, mock_news_output):
    mock_model_client = MagicMock(spec=ModelClient)
    agent = ResearchAnalystAgent(model_client=mock_model_client)

    # 1. Mock ReasoningNode response
    mock_reasoning_content = (
        "<thought>Compose analysis from strong health and positive news.</thought>\n"
        "<objectives>Highlight synergy between metrics and sentiment in a report.</objectives>"
    )

    # 2. Mock SynthesisNode response
    mock_synthesis_content = json.dumps(
        {
            "composed_analysis": "Perfect alignment between fundamentals and news trends.",
            "warnings": [],
        }
    )

    # Setup side effect for multiple calls
    mock_model_client.generate_completion.side_effect = [
        mock_reasoning_content,
        mock_synthesis_content,
    ]

    expected_health = 85
    expected_sentiment = 0.6

    result = await agent.process(mock_fundamental_output, mock_news_output)

    assert isinstance(result, ResearchAnalystOutput)
    assert result.ticker == "AAPL"
    # Ensure recommendation and confidence_score are NOT in the result
    assert not hasattr(result, "recommendation")
    assert not hasattr(result, "confidence_score")

    assert result.fundamental_analysis.health_score == expected_health
    assert result.news_analysis.overall_sentiment_score == expected_sentiment
    assert "Perfect alignment" in result.composed_analysis
