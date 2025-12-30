import asyncio
import os
import sys
from datetime import datetime
from typing import Any, Optional

import chromadb
from diskcache import Cache
from dotenv import load_dotenv
from fastapi.logger import logger
from llama_index.core.embeddings import resolve_embed_model
from pydantic import BaseModel, Field

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.factory.mcp_server_factory import McpServerFactory
from src.utils.cache import cache_key
from src.utils.logging_config import configure_logging

load_dotenv()
configure_logging()

mcp_server = McpServerFactory.create_mcp_server("AnalystReportMcpServer")
cache = Cache("./.rag_mcp_cache")


def _get_chromadb_client():
    api_key = os.getenv("CHROMA_API_KEY")
    tenant = os.getenv("CHROMA_TENANT")
    database = os.getenv("CHROMA_DATABASE")
    if api_key and tenant and database:
        return chromadb.CloudClient(api_key=api_key, tenant=tenant, database=database)

    persist_dir = os.getenv("CHROMA_PERSIST_DIR") or os.path.join("storage", "chroma")
    os.makedirs(persist_dir, exist_ok=True)
    return chromadb.PersistentClient(path=persist_dir)


def _flatten_chroma_query_results(results: dict[str, Any]) -> list[dict[str, Any]]:
    ids = (results or {}).get("ids") or []
    documents = (results or {}).get("documents") or []
    metadatas = (results or {}).get("metadatas") or []
    distances = (results or {}).get("distances") or []

    doc_ids = ids[0] if ids else []
    docs = documents[0] if documents else []
    metas = metadatas[0] if metadatas else []
    dists = distances[0] if distances else []

    matches: list[dict[str, Any]] = []
    for idx in range(max(len(doc_ids), len(docs), len(metas), len(dists))):
        match = {
            "rank": idx + 1,
            "id": doc_ids[idx] if idx < len(doc_ids) else None,
            "distance": dists[idx] if idx < len(dists) else None,
            "document": docs[idx] if idx < len(docs) else None,
            "metadata": metas[idx] if idx < len(metas) else None,
        }
        matches.append(match)
    return matches


def _build_rag_context(matches: list[dict[str, Any]], max_chars: int = 8000) -> str:
    parts: list[str] = []
    total_chars = 0
    for match in matches:
        chunk = (
            f"[{match.get('rank')}] id={match.get('id')} distance={match.get('distance')} "
            f"meta={match.get('metadata')}\n{match.get('document') or ''}"
        )
        parts.append(chunk)
        total_chars += len(chunk)
        if total_chars >= max_chars:
            break
    context = "\n\n---\n\n".join(parts)
    return context[:max_chars]


def _list_collection_names(client: Any) -> list[str]:
    try:
        collections = client.list_collections()
    except Exception:
        return []
    names: list[str] = []
    for c in collections or []:
        name = getattr(c, "name", None)
        if isinstance(name, str) and name:
            names.append(name)
    return sorted(set(names))


def _resolve_collection_name(client: Any, input_data: "RAGRetrieveInput") -> str:
    if input_data.collection:
        return input_data.collection

    domain = input_data.domain
    corpus = input_data.corpus
    company_name = input_data.company_name
    if company_name is not None and not company_name.strip():
        company_name = None

    candidates: list[str] = []
    candidates.append(f"{domain}_{corpus}_{company_name}")
    if company_name is None:
        candidates.append(f"{domain}_{corpus}_")
        candidates.append(f"{domain}_{corpus}_None")

    existing = set(_list_collection_names(client))
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


class RAGRetrieveInput(BaseModel):
    query: str = Field(..., description="Natural-language query to search for.")
    collection: Optional[str] = Field(
        None,
        description=(
            "Chroma collection name. If omitted, the tool attempts to build one from "
            "`domain`, `corpus`, and `company_name`."
        ),
    )
    domain: str = Field(
        "finance", description="Used to build collection name if `collection` is omitted."
    )
    corpus: str = Field(
        "analyst_report", description="Used to build collection name if `collection` is omitted."
    )
    company_name: Optional[str] = Field(
        None,
        description=(
            "Used to build collection name if `collection` is omitted. This should match the value used "
            "during indexing (see `/rag/upload_pdf`)."
        ),
    )
    top_k: int = Field(5, ge=1, le=50, description="Number of chunks to retrieve (1-50).")
    filters: Optional[dict[str, Any]] = Field(
        None, description="Chroma `where` filter (metadata constraints)."
    )
    document_contains: Optional[str] = Field(
        None,
        description=(
            "Optional substring filter applied to document text via Chroma `where_document`."
        ),
    )
    max_context_chars: int = Field(
        8000, ge=0, le=50000, description="Maximum characters to include in `context`."
    )


@mcp_server.tool()
async def retrieve_report(input: RAGRetrieveInput) -> dict[str, Any]:
    """Retrieve relevant analyst-report chunks from ChromaDB for RAG.

    Agent-friendly output:
    - `matches`: ranked list of chunks with `document`, `metadata`, `distance`
    - `context`: pre-formatted text block suitable to paste into an LLM prompt
    """
    if not input.query or not input.query.strip():
        raise ValueError("query is required")

    embed_model_name = os.getenv("RAG_EMBED_MODEL") or "default"
    company_name_for_key = input.company_name.strip() if input.company_name else None
    collection_hint = input.collection or f"{input.domain}_{input.corpus}_{company_name_for_key}"
    key = cache_key(
        "ChromaDB",
        "retrieve_report",
        {
            "collection": collection_hint,
            "query": input.query,
            "top_k": input.top_k,
            "filters": input.filters,
            "document_contains": input.document_contains,
            "embed_model": embed_model_name,
        },
    )
    if key in cache:
        logger.info(f"Using cached retrieve_report response: {key}")
        return cache[key]

    client = _get_chromadb_client()
    collection_name = _resolve_collection_name(client, input)

    try:
        collection = client.get_collection(name=collection_name)
    except Exception as exc:
        available = _list_collection_names(client)
        raise ValueError(
            f"Failed to open Chroma collection '{collection_name}'. Available: {available}"
        ) from exc

    embed_model = resolve_embed_model(embed_model_name)
    query_embedding = await asyncio.to_thread(embed_model.get_query_embedding, input.query)

    where_document = None
    if input.document_contains:
        where_document = {"$contains": input.document_contains}

    raw_results = collection.query(
        query_embeddings=[query_embedding],
        n_results=input.top_k,
        where=input.filters,
        where_document=where_document,
        include=["documents", "metadatas", "distances"],
    )

    matches = _flatten_chroma_query_results(raw_results)
    context = _build_rag_context(matches, max_chars=input.max_context_chars)

    response: dict[str, Any] = {
        "collection": collection_name,
        "query": input.query,
        "top_k": input.top_k,
        "num_matches": len(matches),
        "filters": input.filters,
        "document_contains": input.document_contains,
        "matches": matches,
        "context": context,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    cache.set(key, response, expire=60 * 5)
    return response


if __name__ == "__main__":
    port = int(os.getenv("RAG_MCP_PORT", "8300"))
    McpServerFactory.run_default_mcp_server(mcp_server, port)
