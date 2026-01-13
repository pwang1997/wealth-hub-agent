from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from typing import Any

from llama_index.core.embeddings.utils import resolve_embed_model

from clients.chroma_client import ChromaClient
from src.agent_tools.rag.context_builder import build_rag_context, flatten_chroma_query_results
from src.models.rag_retrieve import RAGRetrieveInput

chroma_client = ChromaClient()


def validate_if_domain_edgar(domain: str, filters: dict[str, Any] | None) -> None:
    if domain != "edgar":
        return
    if not isinstance(filters, dict):
        raise ValueError("EDGAR retrieval requires metadata filters as a dict")

    required_keys = {"ticker"}
    missing = required_keys - set(filters.keys())
    if missing:
        raise ValueError(f"EDGAR retrieval requires metadata filters: missing {missing}")


def normalize_edgar_filters(filters: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in filters.items():
        if not isinstance(value, str):
            normalized[key] = value
            continue

        cleaned = value.strip()
        if not cleaned:
            continue

        if key in {"ticker", "form"}:
            normalized[key] = cleaned.upper()
        else:
            normalized[key] = cleaned
    return normalized


async def _retrieve_report(input_data: RAGRetrieveInput) -> dict[str, Any]:
    if not input_data.query or not input_data.query.strip():
        raise ValueError("query is required")

    embed_model_name = os.getenv("RAG_EMBED_MODEL")
    collection_name = input_data.collection or "edgar_filings"

    filters = input_data.filters
    if input_data.domain == "edgar":
        if filters is None:
            raise ValueError("EDGAR retrieval requires metadata filters as a dict")
        filters = normalize_edgar_filters(filters)

    validate_if_domain_edgar(input_data.domain, filters)

    collection = await chroma_client.get_collection_or_raise(
        collection_name=collection_name, cache=None
    )

    embed_model = resolve_embed_model(embed_model_name)
    query_embedding = await asyncio.to_thread(embed_model.get_query_embedding, input_data.query)

    where_document = None
    if input_data.document_contains:
        where_document = {"$contains": input_data.document_contains}

    raw_results = await asyncio.to_thread(
        collection.query,
        query_embeddings=[query_embedding],
        n_results=input_data.top_k,
        where=filters,
        where_document=where_document,
        include=["documents", "metadatas", "distances"],
    )

    matches = flatten_chroma_query_results(raw_results)
    context = build_rag_context(matches, max_chars=input_data.max_context_chars)

    response: dict[str, Any] = {
        "collection": collection_name,
        "query": input_data.query,
        "embed_model": embed_model_name,
        "top_k": input_data.top_k,
        "num_matches": len(matches),
        "filters": filters,
        "document_contains": input_data.document_contains,
        "matches": matches,
        "context": context,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    return response
