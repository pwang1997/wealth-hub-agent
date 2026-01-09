from __future__ import annotations

import asyncio
import os
from collections.abc import Iterable
from typing import Literal

from chromadb import Collection
from dotenv import load_dotenv
from fastapi.logger import logger
from llama_index.core.embeddings import resolve_embed_model

from clients.chroma_client import ChromaClient
from src.agent_tools.rag.context_builder import flatten_chroma_query_results

chroma_client = ChromaClient()

STATEMENT_KEYWORDS: dict[str, list[str]] = {
    "income_statement": [
        "income statement",
        "statement of operations",
        "statement of earnings",
        "statement of comprehensive income",
    ],
    "balance_sheet": [
        "balance sheet",
        "statement of financial position",
        "statement of assets and liabilities",
    ],
    "cash_flow_statement": [
        "cash flow statement",
        "statement of cash flows",
        "statement of cash flow",
    ],
}

load_dotenv()


def _match_keywords(text: str, keywords: Iterable[str]) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in keywords)


def _sort_key(match: dict[str, object | None]) -> object:
    metadata = match.get("metadata") or {}
    chunk_index = metadata.get("chunk_index")
    if isinstance(chunk_index, int):
        return chunk_index
    return match.get("rank", 0)


async def extract_financial_statement_impl(
    accession_number: str,
    statement_type: Literal["income_statement", "balance_sheet", "cash_flow_statement"],
) -> dict[str, object | str]:
    """
    Extract fundamental financial statements from "edgar_filings" vector database.

    Args:
        accession_number (str)
        statement_type (Literal["income_statement", "balance_sheet", "cash_flow_statement"])
    """
    logger.info(
        "[extract_financial_statement] start for accession %s statement %s",
        accession_number,
        statement_type,
        extra={"accession_number": accession_number, "statement_type": statement_type},
    )

    collection: Collection = await chroma_client.get_collection_or_raise(
        collection_name="edgar_filings", cache=None
    )

    query_text = (
        f"{' or '.join(STATEMENT_KEYWORDS[statement_type])} for accession {accession_number}"
    )
    query_kwargs: dict[str, list[list[float]] | list[str]] = {}
    embed_model_name = os.getenv("RAG_EMBED_MODEL")
    if embed_model_name:
        embed_model = resolve_embed_model(embed_model_name)
        query_embedding = await asyncio.to_thread(
            embed_model.get_query_embedding,
            query_text,
        )
        query_kwargs["query_embeddings"] = [query_embedding]
        logger.info("[extract_financial_statement] using embed model %s", embed_model_name)
    else:
        query_kwargs["query_texts"] = [query_text]
        logger.info("[extract_financial_statement] falling back to query_texts for %r", query_text)

    raw_results = await asyncio.to_thread(
        collection.query,
        where={"accession_number": accession_number},
        include=["documents", "metadatas", "distances"],
        n_results=100,
        **query_kwargs,
    )

    matches = flatten_chroma_query_results(raw_results)
    logger.info(
        "[extract_financial_statement] retrieved %d matches for accession %s",
        len(matches),
        accession_number,
        extra={"accession_number": accession_number, "matches": len(matches)},
    )

    logger.info(
        "[extract_financial_statement] selected %d chunks for %s",
        len(matches),
        statement_type,
        extra={
            "accession_number": accession_number,
            "statement_type": statement_type,
            "selected": len(matches),
        },
    )
    document_parts = [match["document"] for match in matches if match.get("document")]
    statement_text = "\n".join(document_parts)

    logger.info(
        "[extract_financial_statement] complete for accession %s (%s) returning %d chunks",
        accession_number,
        statement_type,
        len(matches),
        extra={
            "accession_number": accession_number,
            "statement_type": statement_type,
            "chunks_returned": len(matches),
        },
    )

    return {
        "accession_number": accession_number,
        "statement_type": statement_type,
        "statement_text": statement_text.strip(),
        "chunks_returned": len(matches),
        "matches_examined": len(matches),
    }
