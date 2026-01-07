from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from src.models.rag_retrieve import (FilingResult, RAGRetrieveInput,
                                     SearchReportsInput, SearchReportsOutput)
from src.models.retrieval_agent import (MarketNewsSource,
                                        RetrievalAgentMetadata,
                                        RetrievalAgentOutput,
                                        RetrievalAgentToolMetadata)

from ..base_agent import BaseAgent

DEFAULT_FILING_CATEGORY = "10-K"
DEFAULT_SEARCH_LIMIT = 5
DEFAULT_TOP_K = 5
DEFAULT_NEWS_LIMIT = 5
DEFAULT_COLLECTION = "edgar_filings"


class ToolExecutionError(Exception):
    def __init__(self, message: str, metadata: RetrievalAgentToolMetadata) -> None:
        super().__init__(message)
        self.metadata = metadata


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
        self._rag_mcp_url = os.getenv("RAG_MCP_URL", "http://localhost:8300/mcp")
        self._alpha_vantage_url = os.getenv("ALPHA_VANTAGE_MCP_URL", "http://localhost:8100/mcp")

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
        status = "success"
        metadata = RetrievalAgentMetadata()
        warnings = metadata.warnings
        normalized_category = (filing_category or DEFAULT_FILING_CATEGORY).upper()
        edgar_filings = self._default_search_output(ticker)
        news_items: list[MarketNewsSource] = []
        rag_answer = ""

        try:
            search_payload = SearchReportsInput(
                ticker=ticker,
                filing_category=normalized_category,
                limit=search_limit,
            ).model_dump()
            raw_search, metadata.search = await self._call_tool_with_metadata(
                self._rag_mcp_url, "search_reports", search_payload
            )
            edgar_filings = SearchReportsOutput.model_validate(raw_search)
        except ToolExecutionError as exc:
            metadata.search = exc.metadata
            warnings.append(f"search_reports failed: {exc}")
            status = "partial"
        except ValidationError as exc:
            status = "partial"
            warnings.append(f"search_reports output invalid: {exc}")

        metadata.upsert = await self._upsert_filings(edgar_filings.filings)
        if metadata.upsert.warnings:
            status = "partial"
            warnings.extend(metadata.upsert.warnings)

        retrieve_filters: dict[str, Any] = {
            "ticker": edgar_filings.ticker.upper(),
            "form": normalized_category,
        }
        rag_answer = ""
        raw_retrieve: dict[str, Any] = {}
        try:
            retrieve_payload = RAGRetrieveInput(
                query=query,
                collection=edgar_filings.collection_name or DEFAULT_COLLECTION,
                domain="edgar",
                corpus="analyst_report",
                company_name=company_name,
                top_k=top_k,
                filters=retrieve_filters,
            ).model_dump()
            raw_retrieve, metadata.retrieve = await self._call_tool_with_metadata(
                self._rag_mcp_url, "retrieve_report", retrieve_payload
            )
            rag_answer = raw_retrieve.get("context", "") or ""
        except ToolExecutionError as exc:
            metadata.retrieve = exc.metadata
            warnings.append(f"retrieve_report failed: {exc}")
            status = "partial"
        except ValidationError as exc:
            status = "partial"
            warnings.append(f"retrieve_report output invalid: {exc}")

        try:
            news_payload: dict[str, Any] = {}
            if ticker:
                news_payload["tickers"] = ticker.upper()
            if news_limit:
                news_payload["limit"] = news_limit
            raw_news, metadata.news = await self._call_tool_with_metadata(
                self._alpha_vantage_url, "news_sentiment", news_payload
            )
            normalized_news = self._normalize_news_response(raw_news)
            for index, entry in enumerate(normalized_news):
                try:
                    news_items.append(MarketNewsSource.model_validate(entry))
                except ValidationError as exc:
                    metadata.news.warnings.append(f"news entry {index} invalid: {exc}")
            if metadata.news.warnings:
                warnings.extend(metadata.news.warnings)
        except ToolExecutionError as exc:
            metadata.news = exc.metadata
            warnings.append(f"news_sentiment failed: {exc}")
            status = "partial"
        except ValidationError as exc:
            status = "partial"
            warnings.append(f"news_sentiment output invalid: {exc}")

        if status == "success" and not edgar_filings.filings and not rag_answer:
            status = "partial"
            warnings.append("No filings or RAG context could be gathered.")

        return self._build_output(
            query=query,
            status=status,
            answer=rag_answer,
            edgar_filings=edgar_filings,
            market_news=news_items,
            metadata=metadata,
            warnings=warnings,
        )

    async def call_mcp_tool(self, tools: list[dict[str, Any]]) -> Any:  # type: ignore[override]
        raise NotImplementedError("call_mcp_tool is not used by the retrieval agent.")

    def get_system_prompt(self) -> str:  # type: ignore[override]
        from .prompt import get_system_prompt as _get_prompt

        return _get_prompt()

    async def _call_tool_with_metadata(
        self, server_url: str, tool_name: str, tool_input: dict[str, Any]
    ) -> tuple[Any, RetrievalAgentToolMetadata]:
        start_time = datetime.now(timezone.utc).isoformat()
        start_monotonic = time.monotonic()
        try:
            result = await self._call_mcp_tool(server_url, tool_name, tool_input)
            metadata = self._build_tool_metadata(
                tool_name,
                start_time,
                start_monotonic,
                metadata_factory=RetrievalAgentToolMetadata,
            )
            return result, metadata
        except Exception as exc:
            metadata = self._build_tool_metadata(
                tool_name,
                start_time,
                start_monotonic,
                metadata_factory=RetrievalAgentToolMetadata,
                warnings=[str(exc)],
            )
            raise ToolExecutionError(str(exc), metadata) from exc

    async def _upsert_filings(self, filings: list[FilingResult]) -> RetrievalAgentToolMetadata:
        start_time = datetime.now(timezone.utc).isoformat()
        start_monotonic = time.monotonic()
        warnings: list[str] = []
        for filing in filings:
            try:
                await self._call_mcp_tool(
                    self._rag_mcp_url,
                    "upsert_edgar_report",
                    {"href": filing.href, "metadata": filing.metadata},
                )
            except Exception as exc:
                warnings.append(f"upsert failed for {filing.metadata.get('accession_number')}: {exc}")
        end_time = datetime.now(timezone.utc).isoformat()
        duration_ms = int((time.monotonic() - start_monotonic) * 1000)
        return RetrievalAgentToolMetadata(
            tool="upsert_edgar_report",
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            warnings=warnings,
        )

    def _build_output(
        self,
        *,
        query: str,
        status: str,
        answer: str,
        edgar_filings: SearchReportsOutput,
        market_news: list[MarketNewsSource],
        metadata: RetrievalAgentMetadata,
        warnings: list[str],
    ) -> RetrievalAgentOutput:
        metadata.warnings = warnings
        return RetrievalAgentOutput(
            query=query,
            status=status,
            answer=answer,
            edgar_filings=edgar_filings,
            market_news=market_news,
            metadata=metadata,
        )

    @staticmethod
    def _default_search_output(ticker: str) -> SearchReportsOutput:
        return SearchReportsOutput(
            ticker=ticker.upper(),
            cik="",
            filings=[],
            collection_name=DEFAULT_COLLECTION,
        )
