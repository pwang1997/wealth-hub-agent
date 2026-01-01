from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace

from src.agents.analyst.retrieval_agent import AnalystRetrievalAgent


@dataclass(frozen=True)
class DummyFiling:
    form: str
    filing_date: str
    accession_number: str
    href: str


def test_returns_rag_when_matches_exist(monkeypatch):
    async def fake_retrieve_report_direct(input_data, *, cache):
        _ = input_data, cache
        return {
            "collection": "finance_analyst_report_acme",
            "query": "q",
            "top_k": 5,
            "num_matches": 1,
            "matches": [{"rank": 1, "id": "x", "distance": 0.1, "document": "doc", "metadata": {}}],
            "context": "ctx",
        }

    def fail_search_reports_direct(_input_data):
        raise AssertionError("EDGAR discovery should not run when RAG has matches")

    def fail_ingest(*_args, **_kwargs):
        raise AssertionError("EDGAR ingest should not run when RAG has matches")

    monkeypatch.setattr(
        "src.agents.analyst.retrieval_agent.retrieve_report_direct", fake_retrieve_report_direct
    )
    monkeypatch.setattr(
        "src.agents.analyst.retrieval_agent.search_reports_direct", fail_search_reports_direct
    )
    monkeypatch.setattr(
        "src.agents.analyst.retrieval_agent.ingest_edgar_primary_documents", fail_ingest
    )

    agent = AnalystRetrievalAgent()
    result = asyncio.run(agent.retrieve("q", ticker="AAPL", company_name="ACME"))
    assert result.rag is not None
    assert result.rag.num_matches == 1
    assert result.edgar is None


def test_fallbacks_to_edgar_when_no_rag_matches(monkeypatch):
    calls = {"search": []}

    async def fake_retrieve_report_direct(input_data, *, cache):
        _ = cache
        if getattr(input_data, "collection", None):
            return {
                "collection": input_data.collection,
                "query": input_data.query,
                "top_k": input_data.top_k,
                "num_matches": 1,
                "matches": [
                    {
                        "rank": 1,
                        "id": "x",
                        "distance": 0.2,
                        "document": "edgar doc",
                        "metadata": {"source": "edgar"},
                    }
                ],
                "context": "ctx",
            }
        return {
            "collection": "finance_analyst_report_acme",
            "query": input_data.query,
            "top_k": input_data.top_k,
            "num_matches": 0,
            "matches": [],
            "context": "",
        }

    def fake_search_reports_direct(input_data):
        calls["search"].append((input_data.ticker, input_data.filing_category, input_data.limit))
        return SimpleNamespace(
            ticker=input_data.ticker,
            cik="0000123456",
            filings=[
                DummyFiling(
                    form=input_data.filing_category,
                    filing_date="2099-01-01",
                    accession_number=f"{input_data.filing_category}-ACC",
                    href="https://example.com/primary.html",
                )
            ],
        )

    def fake_ingest_edgar_primary_documents(filings, *, ticker, cik, rag_input, policy, **_kwargs):
        _ = filings, ticker, cik, rag_input, policy
        return {
            "collections": ["finance_edgar_ACME_10-K"],
            "attempted": 1,
            "ingested": 1,
            "skipped_existing": 0,
        }

    monkeypatch.setattr(
        "src.agents.analyst.retrieval_agent.retrieve_report_direct", fake_retrieve_report_direct
    )
    monkeypatch.setattr(
        "src.agents.analyst.retrieval_agent.search_reports_direct", fake_search_reports_direct
    )
    monkeypatch.setattr(
        "src.agents.analyst.retrieval_agent.ingest_edgar_primary_documents",
        fake_ingest_edgar_primary_documents,
    )

    agent = AnalystRetrievalAgent()
    result = asyncio.run(agent.retrieve("analyze $AAPL latest 10-K", company_name="ACME"))
    assert result.edgar is not None
    assert result.edgar.ticker == "AAPL"
    assert result.rag is not None
    assert result.rag.num_matches == 1
    assert calls["search"][0][0] == "AAPL"
