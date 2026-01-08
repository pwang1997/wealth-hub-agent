from __future__ import annotations

import aiohttp
from fastapi.logger import logger

from src.agent_tools.edgar.edgar_client import EdgarClient
from src.models.rag_retrieve import FilingResult, SearchReportsInput, SearchReportsOutput
from src.utils.edgar_config import EdgarConfig


async def search_reports_impl(
    input_data: SearchReportsInput, collection_name: str
) -> SearchReportsOutput:
    """
    Search Edgar filings with Edgar Api. Prepare embedding content for ChromaDB:edgar_filings.
    """
    cik = await EdgarClient.get_cik_for_ticker(input_data.ticker)

    logger.info(
        "[search_reports] start",
        extra={
            "ticker": input_data.ticker,
            "cik": cik,
            "filing_category": input_data.filing_category,
            "limit": input_data.limit,
        },
    )

    url = EdgarConfig.SEC_SUBMISSIONS_URL.format(cik=cik)
    timeout = aiohttp.ClientTimeout(total=10)
    async with (
        aiohttp.ClientSession(
            headers=EdgarConfig.HEADERS,
            timeout=timeout,
        ) as session,
        session.get(url) as resp,
    ):
        resp.raise_for_status()
        submissions = await resp.json()

    recent = submissions.get("filings", {}).get("recent", {})
    entity_name = submissions.get("name", "")
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    documents = recent.get("primaryDocument", [])
    filing_dates = recent.get("filingDate", [])
    report_dates = recent.get("reportDate", [])

    filings: list[FilingResult] = []

    for form, acc, doc, filing_date, report_date in zip(
        forms, accessions, documents, filing_dates, report_dates
    ):
        if form != input_data.filing_category:
            continue
        href = EdgarClient.build_filing_href(cik, acc, doc)

        metadata = {
            "cik": cik,
            "ticker": input_data.ticker.upper(),
            "company_name": entity_name,
            "form": form,
            "filing_date": filing_date,
            "report_date": report_date,
            "accession_number": acc,
            "collection_name": collection_name,
        }

        filings.append(
            FilingResult(
                form=form,
                filing_date=filing_date,
                accession_number=acc,
                href=href,
                metadata=metadata,
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
            "collection_name": collection_name,
        },
    )

    return SearchReportsOutput(
        ticker=input_data.ticker.upper(),
        cik=cik,
        filings=filings,
        collection_name=collection_name,
    )
