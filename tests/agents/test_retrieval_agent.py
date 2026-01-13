from __future__ import annotations

import asyncio

from src.agents.retrieval.retrieval_agent import AnalystRetrievalAgent


def test_retrieval_agent_process(monkeypatch):
    async def run():
        agent = AnalystRetrievalAgent()
        upsert_calls: list[dict[str, object]] = []

        async def fake_call(self, server_url, tool_name, tool_input):
            if tool_name == "search_reports":
                return {
                    "ticker": "NVDA",
                    "cik": "0001234",
                    "collection_name": "edgar_filings",
                    "filings": [
                        {
                            "form": "10-K",
                            "filing_date": "2024-01-01",
                            "accession_number": "ACC-1",
                            "href": "https://edgar/ACC-1",
                            "metadata": {
                                "cik": "0001234",
                                "ticker": "NVDA",
                                "company_name": "NVIDIA",
                                "form": "10-K",
                                "filing_date": "2024-01-01",
                                "report_date": "2023-12-31",
                                "accession_number": "ACC-1",
                                "collection_name": "edgar_filings",
                            },
                        }
                    ],
                }
            if tool_name == "upsert_edgar_report":
                upsert_calls.append(tool_input)
                return None
            if tool_name == "retrieve_report":
                return {"context": "rg_context"}
            if tool_name == "news_sentiment":
                return [
                    {
                        "title": "Tech headline",
                        "source": "AlphaVantage",
                        "url": "https://news",
                        "summary": "News summary",
                        "topics": [{"topic": "Technology", "relevance_score": "0.8"}],
                        "overall_sentiment_score": "0.7",
                        "overall_sentiment_label": "Bullish",
                        "ticker_sentiment": [
                            {
                                "ticker": "NVDA",
                                "relevance_score": "0.9",
                                "ticker_sentiment_score": "0.7",
                                "ticker_sentiment_label": "Bullish",
                            }
                        ],
                        "time_published": "20241120T000000",
                    }
                ]
            if tool_name == "extract_financial_statement":
                return {
                    "accession_number": "ACC-1",
                    "statement_type": "income_statement",
                    "statement_text": "net income detail",
                    "chunks_returned": 1,
                    "matches_examined": 1,
                }
            if tool_name == "get_financial_reports":
                return {"cik": "0001234", "symbol": "NVDA", "data": []}
            raise AssertionError(tool_name)

        monkeypatch.setattr(AnalystRetrievalAgent, "call_mcp_tool", fake_call)

        result = await agent.process(
            query="What did NVIDIA disclose?",
            ticker="NVDA",
            filing_category="10-K",
            top_k=1,
            news_limit=1,
        )

        assert result.status == "success"
        assert result.answer == "rg_context"
        assert len(result.edgar_filings.filings) == 1
        assert len(upsert_calls) == 1
        assert result.market_news[0].title == "Tech headline"
        assert result.metadata.warnings == []
        assert result.financial_statement is not None
        assert result.financial_statement.statement_type == "income_statement"
        assert result.financial_reports is not None
        assert result.financial_reports.symbol == "NVDA"

    asyncio.run(run())


def test_retrieval_agent_handles_retriable_error(monkeypatch):
    async def run():
        agent = AnalystRetrievalAgent()

        async def fake_call(self, server_url, tool_name, tool_input):
            if tool_name == "search_reports":
                raise ValueError("search backend busy")
            if tool_name == "upsert_edgar_report":
                return None
            if tool_name == "retrieve_report":
                return {"context": "partial_context"}
            if tool_name == "news_sentiment":
                return []
            if tool_name == "get_financial_reports":
                return {"cik": "000999", "symbol": "COMP", "data": []}
            raise AssertionError(tool_name)

        monkeypatch.setattr(AnalystRetrievalAgent, "call_mcp_tool", fake_call)

        result = await agent.process(
            query="What did Company X say?",
            ticker="COMP",
            top_k=1,
            news_limit=1,
        )

        assert result.status == "partial"
        assert any("search_reports failed" in warning for warning in result.metadata.warnings)
        assert result.answer == "partial_context"
        assert result.market_news == []

    asyncio.run(run())
