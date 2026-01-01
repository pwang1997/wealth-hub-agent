from __future__ import annotations

import asyncio
import os
from datetime import datetime
from functools import lru_cache
from typing import Any

from diskcache import Cache
from fastapi.logger import logger
from llama_index.core.embeddings import resolve_embed_model

from src.agent_tools.rag.chroma_utils import (
    get_chromadb_client,
    get_collection_or_raise,
    list_collection_names,
)
from src.agent_tools.rag.context_builder import (
    build_rag_context,
    flatten_chroma_query_results,
    jsonable,
    normalize_company_name,
    safe_json_cache_args,
)
from src.models.rag_retrieve import RAGRetrieveInput
from src.utils.cache import CacheConfig, cache_key


@lru_cache(maxsize=4)
def _get_embed_model(model_name: str) -> Any:
    return resolve_embed_model(model_name or "default")


def _resolve_collection_name(client: Any, input_data: RAGRetrieveInput, *, cache: Cache) -> str:
    if input_data.collection:
        return input_data.collection

    domain = input_data.domain
    corpus = input_data.corpus
    company_name = normalize_company_name(input_data.company_name)

    candidates: list[str] = []
    candidates.append(f"{domain}_{corpus}_{company_name}")
    if company_name is None:
        candidates.append(f"{domain}_{corpus}_")
        candidates.append(f"{domain}_{corpus}_None")

    existing = set(list_collection_names(client, cache=cache))
    for candidate in candidates:
        if candidate in existing:
            return candidate

    if existing:
        raise ValueError(
            "No matching Chroma collection found. "
            f"Tried: {candidates}. Available: {sorted(existing)}. "
            "Pass `collection` explicitly or index a PDF first."
        )

    raise ValueError(
        "No Chroma collections found. Index a PDF first (see `/rag/upload_pdf`) or pass `collection`."
    )


async def _retrieve_report_impl(input_data: RAGRetrieveInput, *, cache: Cache) -> dict[str, Any]:
    if not input_data.query or not input_data.query.strip():
        raise ValueError("query is required")

    embed_model_name = os.getenv("RAG_EMBED_MODEL") or "default"
    company_name_for_key = normalize_company_name(input_data.company_name)
    collection_hint = (
        input_data.collection or f"{input_data.domain}_{input_data.corpus}_{company_name_for_key}"
    )
    key = cache_key(
        "ChromaDB",
        "retrieve_report",
        safe_json_cache_args(
            {
                "collection": collection_hint,
                "query": input_data.query,
                "top_k": input_data.top_k,
                "filters": input_data.filters,
                "document_contains": input_data.document_contains,
                "embed_model": embed_model_name,
            }
        ),
    )
    if key in cache:
        logger.info(f"Using cached retrieve_report response: {key}")
        return cache[key]

    client = get_chromadb_client()
    collection_name = _resolve_collection_name(client, input_data, cache=cache)
    collection = get_collection_or_raise(client, collection_name, cache=cache)

    embed_model = _get_embed_model(embed_model_name)
    query_embedding = await asyncio.to_thread(embed_model.get_query_embedding, input_data.query)

    where_document = None
    if input_data.document_contains:
        where_document = {"$contains": input_data.document_contains}

    raw_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=input_data.top_k,
        where=input_data.filters,
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
        "filters": jsonable(input_data.filters),
        "document_contains": input_data.document_contains,
        "matches": matches,
        "context": context,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    cache.set(key, response, expire=CacheConfig.RETRIEVE_REPORT_CACHE_TTL_SECONDS)
    return response


async def _list_collections_impl(*, cache: Cache) -> list[str]:
    client = get_chromadb_client()
    return list_collection_names(client, cache=cache)


async def retrieve_report_direct(input_data: RAGRetrieveInput, *, cache: Cache) -> dict[str, Any]:
    """Direct invocation wrapper (no MCP server required)."""
    return await _retrieve_report_impl(input_data, cache=cache)


def register_tools(mcp_server: Any, *, cache: Cache) -> None:
    @mcp_server.tool()
    async def retrieve_report(input: RAGRetrieveInput) -> dict[str, Any]:
        """Retrieve relevant analyst-report chunks from ChromaDB for RAG.

        Agent-friendly output:
        - `matches`: ranked list of chunks with `document`, `metadata`, `distance`
        - `context`: pre-formatted text block suitable to paste into an LLM prompt
        """

        return await _retrieve_report_impl(input, cache=cache)

    @mcp_server.tool()
    async def list_collections() -> list[str]:
        return await _list_collections_impl(cache=cache)
