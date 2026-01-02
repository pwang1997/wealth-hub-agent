from __future__ import annotations

from typing import Any

import aiohttp
import requests
from chromadb import Collection
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


async def _search_reports_impl(input_data: SearchReportsInput) -> SearchReportsOutput:
    cik = EdgarClient.get_cik_for_ticker(input_data.ticker)

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
                href=EdgarClient.build_filing_href(cik, acc, doc),
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


async def preflight_chroma_collection(collection_name: str) -> Collection | None:
    try:
        collection = chroma_client.get_client().get_collection(collection_name)
    except Exception:
        # Collection does not exist
        return None

    # Production-safe emptiness check
    if collection.count() == 0:
        return None

    logger.info(
        "[upsert_edgar_report] collected %d nodes from %s",
        collection.count(),
        collection_name,
    )
    return collection


def batch_insert(index, nodes, href):
    BATCH_SIZE = 64  # intentionally conservative
    for i in range(0, len(nodes), BATCH_SIZE):
        index.insert_nodes(nodes[i : i + BATCH_SIZE])

    logger.info(
        "[upsert_edgar_report] Upserted %d nodes from %s",
        len(nodes),
        href,
    )

async def _upsert_edgar_report_impl(href: str):
    """
    Insert edgar report to Chroma vector database for future agent use.
    Example: 
    e.g.1. after invoking function tool 'search_reports' (retrieve corresponding EDGAR fillings), insert relevant fillings to ChromaDb.
    e.g.2. retrieval_agent:[search_reports -> upsert_edgar_report] -> analyst_agent:[retrieve_report]
    """
    try:
        collection = await preflight_chroma_collection(collection_name="edgar_aapl_10k_2025")
        if collection is None:
            content = None
            async with aiohttp.ClientSession(headers=EdgarConfig.HEADERS) as session:
                content = await EdgarClient.get_filing_content(href, session)

            doc = Document(text=content, extra_info={"source": href})

            parser = HTMLNodeParser(tags=["span", "td", "div"])
            raw_nodes = parser.get_nodes_from_documents([doc])

            cleaned_nodes = EdgarClient._normalize_html_nodes(raw_nodes)

            splitter = SentenceSplitter(
                chunk_size=512,
                chunk_overlap=64,
            )
            nodes = splitter.get_nodes_from_documents(cleaned_nodes)

            # Final defensive filter
            MAX_NODE_TEXT_LEN, MIN_NODE_TEXT_LEN = 1200, 50
            nodes = [n for n in nodes if MIN_NODE_TEXT_LEN <= len(n.text) <= MAX_NODE_TEXT_LEN]

            if not nodes:
                logger.warning("[upsert_edgar_report] No valid nodes produced")
                return

            # ------------------------------------------------------------------
            # 6. Chroma Cloud vector store
            # ------------------------------------------------------------------
            collection = chroma_client.get_client().get_or_create_collection(
                name="edgar_aapl_10k_2025"
            )

            vector_store = ChromaVectorStore(chroma_collection=collection)

            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            index = VectorStoreIndex(nodes=[], storage_context=storage_context)

            batch_insert(index, nodes, href)
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
    async def upsert_edgar_report(href: str):
        return await _upsert_edgar_report_impl(href)
