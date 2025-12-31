from __future__ import annotations

from typing import Any

import requests
from fastapi.logger import logger

from src.agent_tools.edgar.edgar_client import build_filing_href, get_cik_for_ticker
from src.models.rag_retrieve import FilingResult, SearchReportsInput, SearchReportsOutput
from src.utils.edgar_config import EdgarConfig


def _search_reports_impl(input_data: SearchReportsInput) -> SearchReportsOutput:
    cik = get_cik_for_ticker(input_data.ticker)

    url = EdgarConfig.SEC_SUBMISSIONS_URL.format(cik=cik)
    resp = requests.get(url, headers=EdgarConfig.HEADERS, timeout=10)
    resp.raise_for_status()

    submissions = resp.json()
    recent = submissions.get("filings", {}).get("recent", {})

    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    documents = recent.get("primaryDocument", [])

    filings: list[FilingResult] = []

    for form, date, acc, doc in zip(forms, dates, accessions, documents):
        if form != input_data.filing_category:
            continue

        filings.append(
            FilingResult(
                form=form,
                filing_date=date,
                accession_number=acc,
                href=build_filing_href(cik, acc, doc),
            )
        )

        if len(filings) >= input_data.limit:
            break

    logger.info(
        "search_reports",
        extra={
            "ticker": input_data.ticker,
            "cik": cik,
            "filing_category": input_data.filing_category,
            "results": len(filings),
        },
    )

    return SearchReportsOutput(
        ticker=input_data.ticker.upper(),
        cik=cik,
        filings=filings,
    )


def register_tools(mcp_server: Any) -> None:
    @mcp_server.tool()
    def search_reports(input: SearchReportsInput) -> SearchReportsOutput:
        """
        Search SEC EDGAR filings for a company and filing category.
        Discovery-only tool. Does not retrieve document content.
        """

        return _search_reports_impl(input)

