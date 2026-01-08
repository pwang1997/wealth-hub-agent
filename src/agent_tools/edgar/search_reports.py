from __future__ import annotations

from typing import Any

from fastapi.logger import logger

from src.agent_tools.edgar.search_reports_impl import search_reports_impl
from src.agent_tools.edgar.upsert_edgar_report_impl import upsert_edgar_report_impl
from src.models.rag_retrieve import SearchReportsInput, SearchReportsOutput

collection_name = "edgar_filings"


def register_tools(mcp_server: Any) -> None:
    @mcp_server.tool()
    async def search_reports(input: SearchReportsInput) -> SearchReportsOutput:
        """
        Search SEC EDGAR filings for a company and filing category.
        Discovery-only tool. Does not retrieve document content.
        """

        logger.info(
            "[tool] search_reports invoked",
            extra={
                "ticker": input.ticker,
                "filing_category": input.filing_category,
                "limit": input.limit,
            },
        )

        return await search_reports_impl(input, collection_name)

    @mcp_server.tool()
    async def upsert_edgar_report(href: str, metadata: dict):
        logger.info(
            "[tool] upsert_edgar_report invoked",
            extra={
                "href": href,
                "metadata_accession": metadata.get("accession_number"),
                "collection": collection_name,
            },
        )

        return await upsert_edgar_report_impl(href, metadata, collection_name)
