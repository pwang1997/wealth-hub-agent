import json
from unittest.mock import MagicMock

import pytest

from clients.model_client import ModelClient
from src.agents.analyst.fundamental.fundamental_analyst_agent import FundamentalAnalystAgent
from src.models.fundamental_analyst import FundamentalAnalystOutput
from src.models.fundamentals import (
    FinancialReportEntry,
    FinancialReportLineItem,
    FinancialReportSection,
    FundamentalDTO,
)
from src.models.rag_retrieve import EdgarSearchMetaData, FilingResult, SearchReportsOutput
from src.models.retrieval_agent import RetrievalAgentMetadata, RetrievalAgentOutput


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_retrieval_output():
    # Setup mock data
    item_rev = FinancialReportLineItem(
        concept="Revenues", unit="USD", label="Revenue", value=1000000
    )
    item_ni = FinancialReportLineItem(
        concept="NetIncomeLoss", unit="USD", label="Net Income", value=100000
    )
    item_ocf = FinancialReportLineItem(
        concept="NetCashProvidedByUsedInOperatingActivities", unit="USD", label="OCF", value=120000
    )

    report = FinancialReportSection(ic=[item_rev, item_ni], cf=[item_ocf], bs=[])

    entry = FinancialReportEntry(
        accessNumber="0001234567-21-000001",
        symbol="AAPL",
        cik="0000320193",
        year=2021,
        quarter=4,
        form="10-K",
        startDate="2020-09-27",
        endDate="2021-09-25",
        filedDate="2021-10-29",
        acceptedDate="2021-10-29",
        report=report,
    )

    fundamentals = FundamentalDTO(cik="0000320193", symbol="AAPL", data=[entry])

    filing = FilingResult(
        form="10-K",
        filing_date="2021-10-29",
        accession_number="0001234567-21-000001",
        href="https://www.sec.gov/...",
        metadata=EdgarSearchMetaData(
            cik="0000320193",
            ticker="AAPL",
            company_name="Apple Inc.",
            form="10-K",
            filing_date="2021-10-29",
            report_date="2021-09-25",
            accession_number="0001234567-21-000001",
            collection_name="edgar_filings",
        ),
    )

    edgar_filings = SearchReportsOutput(
        ticker="AAPL", cik="0000320193", filings=[filing], collection_name="edgar_filings"
    )

    return RetrievalAgentOutput(
        query="Analyze Apple's fundamentals",
        status="success",
        answer="Apple is doing well.",
        edgar_filings=edgar_filings,
        market_news=[],
        metadata=RetrievalAgentMetadata(),
        financial_statement=None,
        financial_reports=fundamentals,
    )


@pytest.mark.anyio
async def test_fundamental_analyst_agent_process(mock_retrieval_output):
    mock_model_client = MagicMock(spec=ModelClient)
    agent = FundamentalAnalystAgent(model_client=mock_model_client)

    # Mock ModelClient response
    mock_content = json.dumps(
        {
            "ticker": "AAPL",
            "health_score": 85,
            "strengths": [
                {"name": "Strong Margin", "description": "10% net margin", "impact": "positive"}
            ],
            "weaknesses": [],
            "red_flags": [],
            "summary": "Great company",
        }
    )
    mock_model_client.generate_completion.side_effect = [
        "<thought>Thinking...</thought><objectives>Analyze metrics</objectives>",  # ReasoningNode
        mock_content,  # AnalyzeWithLLMNode
    ]

    result = await agent.process(mock_retrieval_output)
    expected_health_score = 85
    assert isinstance(result, FundamentalAnalystOutput)
    assert result.ticker == "AAPL"
    assert result.health_score == expected_health_score
    assert result.citations == ["0001234567-21-000001"]

    # Verify calculations were included in prompt
    # Extract the actual call arguments for AnalyzeWithLLMNode
    call_args = mock_model_client.generate_completion.call_args_list[1]
    user_msg = call_args.kwargs["prompt"]
    assert "Net Margin: 10.00%" in user_msg
    assert "OCF / Net Income Ratio: 1.20" in user_msg
