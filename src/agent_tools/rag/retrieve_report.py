from __future__ import annotations

from typing import Any

from diskcache import Cache

from src.agent_tools.rag.retrieve_report_impl import _retrieve_report, chroma_client
from src.models.rag_retrieve import RAGRetrieveInput


def register_tools(mcp_server: Any, *, cache: Cache) -> None:
    @mcp_server.tool()
    async def retrieve_report(input: RAGRetrieveInput) -> dict[str, Any]:
        """Retrieve relevant analyst-report chunks from ChromaDB for RAG.

        Agent-friendly output:
        - `matches`: ranked list of chunks with `document`, `metadata`, `distance`
        - `context`: pre-formatted text block suitable to paste into an LLM prompt
        """

        return await _retrieve_report(input)

    @mcp_server.tool()
    async def list_collections() -> list[str]:
        return await chroma_client.list_collection_names(cache=cache)
