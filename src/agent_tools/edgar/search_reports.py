from __future__ import annotations

from typing import Any

import aiohttp
import requests
from fastapi.logger import logger
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import HTMLNodeParser, SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore

from clients.chroma_client import ChromaClient
from src.agent_tools.edgar.edgar_client import EdgarClient
from src.models.rag_retrieve import (FilingResult, SearchReportsInput,
                                     SearchReportsOutput)
from src.utils.edgar_config import EdgarConfig

chroma_client = ChromaClient()

collection_name = "edgar_filings"


async def _search_reports_impl(input_data: SearchReportsInput) -> SearchReportsOutput:
    """
    Search Edgar filings with Edgar Api. Prepare embedding content for ChromaDB:edgar_filings.
    """
    cik = EdgarClient.get_cik_for_ticker(input_data.ticker)

    url = EdgarConfig.SEC_SUBMISSIONS_URL.format(cik=cik)
    resp = requests.get(url, headers=EdgarConfig.HEADERS, timeout=10)
    resp.raise_for_status()

    submissions = resp.json()
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

async def _upsert_edgar_report_impl(href: str, metadata: dict, collection_name: str):
    """
    Insert edgar report to Chroma vector database for future agent use.
    Example:
    e.g.1. after invoking function tool 'search_reports' (retrieve corresponding EDGAR fillings), insert relevant fillings to ChromaDb.
    e.g.2. retrieval_agent:[search_reports -> upsert_edgar_report] -> analyst_agent:[retrieve_report]

    :param href: full SEC filing document URL
    :param collection_name: target Chroma collection (e.g. 'edgar_filings')
    :param metadata: normalized filing metadata (ticker, cik, form, filing_date, accession_number, ...)
    """
    try:
        accession = metadata.get("accession_number")
        if not accession:
            raise ValueError("metadata.accession_number is required")
        client = chroma_client.get_client()
        collection = client.get_or_create_collection(name=collection_name)

        existing = collection.get(
            where={"accession_number": accession},
            limit=1,
        )
        if existing and existing.get("ids"):
            logger.info(
                "[upsert_edgar_report] accession %s already ingested, skipping",
                accession,
            )
            return

        async with aiohttp.ClientSession(headers=EdgarConfig.HEADERS) as session:
            content = await EdgarClient.get_filing_content(href, session)

        if not content:
            logger.warning("[upsert_edgar_report] empty content for %s", href)
            return

        doc = Document(text=content, extra_info=metadata | {"source": href})

        parser = HTMLNodeParser(tags=["span", "td", "div"])
        raw_nodes = parser.get_nodes_from_documents([doc])
        cleaned_nodes = EdgarClient._normalize_html_nodes(raw_nodes)

        splitter = SentenceSplitter(chunk_size=512, chunk_overlap=64)
        nodes = splitter.get_nodes_from_documents(cleaned_nodes)

        # Defensive length filter
        MAX_LEN, MIN_LEN = 1200, 50
        nodes = [n for n in nodes if MIN_LEN <= len(n.text) <= MAX_LEN]

        if not nodes:
            logger.warning("[upsert_edgar_report] no valid nodes for %s", href)
            return

        for i, node in enumerate(nodes):
            node.metadata = metadata | {
                "source": href,
                "chunk_index": i,
            }
            node.id_ = f"{accession}:{i}"

        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex(nodes=[], storage_context=storage_context)

        BATCH_SIZE = 64
        for i in range(0, len(nodes), BATCH_SIZE):
            index.insert_nodes(nodes[i : i + BATCH_SIZE])

        logger.info(
            "[upsert_edgar_report] ingested %d nodes for accession %s",
            len(nodes),
            accession,
        )

    except Exception as exc:
        logger.exception(
            "[upsert_edgar_report] failed for %s",
            href,
            exc_info=exc,
        )


def register_tools(mcp_server: Any) -> None:
    @mcp_server.tool()
    async def search_reports(input: SearchReportsInput) -> SearchReportsOutput:
        """
        Search SEC EDGAR filings for a company and filing category.
        Discovery-only tool. Does not retrieve document content.
        """

        return await _search_reports_impl(input)

    @mcp_server.tool()
    async def upsert_edgar_report(href: str, metadata: dict):
        return await _upsert_edgar_report_impl(href, metadata, collection_name)
