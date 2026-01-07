from __future__ import annotations

import asyncio

from src.agents.analyst.retrieval_agent import AnalystRetrievalAgent


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
                        "topics": "semi",
                        "overall_sentiment": "0.7",
                        "sentiment_label": "positive",
                        "ticker_sentiment": ["NVDA:positive"],
                        "time_published": "2024-11-20T00:00:00Z",
                    }
                ]
            raise AssertionError(tool_name)

        monkeypatch.setattr(AnalystRetrievalAgent, "_call_mcp_tool", fake_call)

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
            raise AssertionError(tool_name)

        monkeypatch.setattr(AnalystRetrievalAgent, "_call_mcp_tool", fake_call)

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
