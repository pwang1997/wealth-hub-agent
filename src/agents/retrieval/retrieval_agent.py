from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any, override

from src.agents.base_agent import BaseAgent
from src.agents.retrieval.exceptions import ToolExecutionError
from src.agents.retrieval.pipeline import (
    ExtractFinancialStatementNode,
    GetFinancialReportsNode,
    NewsSentimentNode,
    RetrievalPipelineState,
    RetrievalQueryPipeline,
    RetrieveReportNode,
    SearchReportsNode,
    UpsertFilingsNode,
)
from src.models.fundamentals import FundamentalDTO
from src.models.rag_retrieve import FilingResult, FinancialStatementOutput, SearchReportsOutput
from src.models.retrieval_agent import (
    MarketNewsSource,
    RetrievalAgentMetadata,
    RetrievalAgentOutput,
    RetrievalAgentToolMetadata,
)
from src.utils.mcp_config import McpConfig

logger = logging.getLogger(__name__)

DEFAULT_FILING_CATEGORY = "10-K"
DEFAULT_SEARCH_LIMIT = 5
DEFAULT_TOP_K = 5
DEFAULT_NEWS_LIMIT = 5
DEFAULT_COLLECTION = "edgar_filings"


class AnalystRetrievalAgent(BaseAgent):
    """
    AnalystRetrievalAgent collects Edgar filings, upserts them to ChromaDB, retrieves RAG context,
    and supplements the response with Alpha Vantage news/sentiment before emitting a structured payload.
    """

    def __init__(self) -> None:
        super().__init__(
            agent_name="analyst_retrieval_agent",
            role_description=(
                "AnalystRetrievalAgent is responsible for collecting filings and market news for user-queried companies."
            ),
        )

    @override
    async def process(
        self,
        *,
        query: str,
        ticker: str,
        company_name: str | None = None,
        filing_category: str | None = None,
        search_limit: int = DEFAULT_SEARCH_LIMIT,
        top_k: int = DEFAULT_TOP_K,
        news_limit: int = DEFAULT_NEWS_LIMIT,
    ) -> RetrievalAgentOutput:
        normalized_category = (filing_category or DEFAULT_FILING_CATEGORY).upper()
        state = RetrievalPipelineState(
            query=query,
            ticker=ticker,
            company_name=company_name,
            filing_category=normalized_category,
            search_limit=search_limit,
            top_k=top_k,
            news_limit=news_limit,
            collection_name=DEFAULT_COLLECTION,
        )
        pipeline = RetrievalQueryPipeline(
            nodes=[
                SearchReportsNode(),
                UpsertFilingsNode(),
                RetrieveReportNode(),
                NewsSentimentNode(),
                ExtractFinancialStatementNode(),
                GetFinancialReportsNode(),
            ]
        )
        await pipeline.run(self, state)

        if state.status == "success" and not state.edgar_filings.filings and not state.rag_answer:
            state.status = "partial"
            state.warnings.append("No filings or RAG context could be gathered.")

        return self.format_output(
            query=query,
            status=state.status,
            answer=state.rag_answer,
            edgar_filings=state.edgar_filings,
            market_news=state.news_items,
            metadata=state.metadata,
            warnings=state.warnings,
            financial_statement=state.financial_statement,
            financial_reports=state.financial_reports,
        )

    @override
    def get_system_prompt(self) -> str:  # type: ignore[override]
        from .prompt import get_system_prompt as _get_prompt

        return _get_prompt()

    async def _call_tool_with_metadata(
        self, server_url: str, tool_name: str, tool_input: dict[str, Any]
    ) -> tuple[Any, RetrievalAgentToolMetadata]:
        start_time = datetime.now(UTC).isoformat()
        start_monotonic = time.monotonic()
        try:
            payload = self._prepare_tool_payload(tool_name, tool_input)
            result = await self.call_mcp_tool(server_url, tool_name, payload)
            metadata = self._build_tool_metadata(
                tool_name,
                start_time,
                start_monotonic,
                metadata_factory=RetrievalAgentToolMetadata,
            )
            return self._extract_tool_result(result), metadata
        except Exception as exc:
            metadata = self._build_tool_metadata(
                tool_name,
                start_time,
                start_monotonic,
                metadata_factory=RetrievalAgentToolMetadata,
                warnings=[str(exc)],
            )
            raise ToolExecutionError(str(exc), metadata) from exc

    @staticmethod
    def _prepare_tool_payload(tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        if tool_name in {"search_reports", "retrieve_report"}:
            return {"input": tool_input}
        return tool_input

    @staticmethod
    def _extract_tool_result(result: Any) -> Any:
        structured = getattr(result, "structured_content", None)
        if structured:
            return structured
        data = getattr(result, "data", None)
        if data is not None:
            return data
        content = getattr(result, "content", None)
        if isinstance(content, list) and len(content) == 1:
            return content[0]
        return result

    async def _upsert_filings(self, filings: list[FilingResult]) -> RetrievalAgentToolMetadata:
        start_time = datetime.now(UTC).isoformat()
        start_monotonic = time.monotonic()
        warnings: list[str] = []
        for filing in filings:
            metadata_dict = filing.metadata.model_dump()
            try:
                await self.call_mcp_tool(
                    McpConfig.rag_mcp_url,
                    "upsert_edgar_report",
                    {"href": filing.href, "metadata": metadata_dict},
                )
            except Exception as exc:
                warnings.append(f"upsert failed for {metadata_dict.get('accession_number')}: {exc}")
        end_time = datetime.now(UTC).isoformat()
        duration_ms = int((time.monotonic() - start_monotonic) * 1000)
        return RetrievalAgentToolMetadata(
            tool="upsert_edgar_report",
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            warnings=warnings,
        )

    @override
    def format_output(
        self,
        query: str,
        status: str,
        answer: str,
        edgar_filings: SearchReportsOutput,
        market_news: list[MarketNewsSource],
        metadata: RetrievalAgentMetadata,
        warnings: list[str],
        financial_statement: FinancialStatementOutput | None,
        financial_reports: FundamentalDTO | None,
    ) -> RetrievalAgentOutput:
        metadata.warnings = warnings
        return RetrievalAgentOutput(
            query=query,
            status=status,
            answer=answer,
            edgar_filings=edgar_filings,
            market_news=market_news,
            metadata=metadata,
            financial_statement=financial_statement,
            financial_reports=financial_reports,
        )
