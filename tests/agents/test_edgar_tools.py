from __future__ import annotations

import asyncio

import pytest

from src.agent_tools.edgar import search_reports
from src.models.rag_retrieve import SearchReportsInput


class DummyResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_search_reports_respects_limit(monkeypatch):
    async def run():
        sample_submissions = {
            "name": "TestCorp",
            "filings": {
                "recent": {
                    "form": ["10-K", "10-Q"],
                    "accessionNumber": ["ACC-1", "ACC-2"],
                    "primaryDocument": ["doc-1", "doc-2"],
                    "filingDate": ["2024-01-01", "2024-02-01"],
                    "reportDate": ["2023-12-31", "2023-09-30"],
                }
            },
        }

        monkeypatch.setattr(
            search_reports.EdgarClient,
            "get_cik_for_ticker",
            lambda ticker: "0000000001",
        )
        monkeypatch.setattr(
            search_reports.EdgarClient,
            "build_filing_href",
            lambda cik, acc, doc: f"https://edgar/{cik}/{acc}/{doc}",
        )

        def fake_requests_get(url, headers, timeout):
            return DummyResponse(sample_submissions)

        monkeypatch.setattr(search_reports.requests, "get", fake_requests_get)

        input_data = SearchReportsInput(ticker="AAPL", filing_category="10-K", limit=1)
        output = await search_reports._search_reports_impl(input_data)

        assert len(output.filings) == 1
        filing = output.filings[0]
        assert filing.form == "10-K"
        assert filing.metadata.ticker == "AAPL"
        assert filing.href.startswith("https://edgar/")
        assert output.collection_name == "edgar_filings"

    asyncio.run(run())


def test_upsert_edgar_report_skips_existing_accession(monkeypatch):
    async def run():
        class DummyCollection:
            def __init__(self) -> None:
                self.get_called_with: dict[str, object] | None = None

            def get(self, *, where: dict[str, object], limit: int):
                self.get_called_with = {"where": where, "limit": limit}
                return {"ids": ["already-ingested"]}

        dummy_collection = DummyCollection()

        class DummyClient:
            def get_or_create_collection(self, name: str):
                return dummy_collection

        monkeypatch.setattr(
            search_reports.chroma_client,
            "get_client",
            lambda: DummyClient(),
        )

        async def should_not_be_called(*args, **kwargs):
            pytest.fail("Content fetch should not be invoked for already ingested accession")

        monkeypatch.setattr(
            search_reports.EdgarClient,
            "get_filing_content",
            should_not_be_called,
        )

        metadata = {
            "accession_number": "ACC-EXIST",
            "ticker": "AAPL",
            "form": "10-K",
            "filing_date": "2024-01-01",
            "report_date": "2023-12-31",
        }

        await search_reports._upsert_edgar_report_impl(
            href="https://example.com/ACC-EXIST",
            metadata=metadata,
            collection_name="edgar_filings",
        )

        assert dummy_collection.get_called_with == {
            "where": {"accession_number": "ACC-EXIST"},
            "limit": 1,
        }

    asyncio.run(run())
