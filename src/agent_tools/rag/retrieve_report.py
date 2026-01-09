from __future__ import annotations

from typing import Any, Literal

from diskcache import Cache
from fastapi.logger import logger

from src.agent_tools.rag.extract_financial_statements_impl import extract_financial_statement_impl
from src.agent_tools.rag.retrieve_report_impl import _retrieve_report
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
    async def extract_financial_statement(
        accession_number: str,
        statement_type: Literal["income_statement", "balance_sheet", "cash_flow_statement"],
    ):
        logger.info(
            "[tool] extract_financial_statements invoked",
            extra={"accession_number": accession_number, "statement_type": statement_type},
        )
        return await extract_financial_statement_impl(accession_number, statement_type)
