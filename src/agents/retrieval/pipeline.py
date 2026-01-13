from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from src.agents.base_agent import BaseAgent
from src.agents.base_pipeline import BasePipeline, BasePipelineNode
from src.models.fundamentals import FundamentalDTO
from src.models.rag_retrieve import (
    FinancialStatementOutput,
    RAGRetrieveInput,
    SearchReportsInput,
    SearchReportsOutput,
)
from src.models.retrieval_agent import MarketNewsSource, RetrievalAgentMetadata
from src.utils.mcp_config import McpConfig

from .exceptions import ToolExecutionError

logger = logging.getLogger(__name__)


@dataclass
class RetrievalPipelineState:
    query: str
    ticker: str
    company_name: str | None
    filing_category: str
    search_limit: int
    top_k: int
    news_limit: int
    collection_name: str
    status: str = "success"
    metadata: RetrievalAgentMetadata = field(default_factory=RetrievalAgentMetadata)
    warnings: list[str] = field(default_factory=list)
    news_items: list[MarketNewsSource] = field(default_factory=list)
    rag_answer: str = ""
    financial_statement: FinancialStatementOutput | None = None
    financial_reports: FundamentalDTO | None = None
    edgar_filings: SearchReportsOutput = field(init=False)

    def __post_init__(self) -> None:
        self.edgar_filings = SearchReportsOutput(
            ticker=self.ticker.upper(),
            cik="",
            filings=[],
            collection_name=self.collection_name,
        )


class RetrievalPipelineNode(BasePipelineNode[RetrievalPipelineState]):
    """Base node for retrieval pipeline."""


class RetrievalQueryPipeline(BasePipeline[RetrievalPipelineState]):
    """Orchestrator for retrieval queries."""


class SearchReportsNode(RetrievalPipelineNode):
    async def run(self, agent: BaseAgent, state: RetrievalPipelineState) -> None:
        logger.info(
            "starting search_reports:",
            extra={
                "ticker": state.ticker,
                "filing_category": state.filing_category,
                "limit": state.search_limit,
            },
        )
        try:
            payload = SearchReportsInput(
                ticker=state.ticker,
                filing_category=state.filing_category,
                limit=state.search_limit,
            ).model_dump()
            raw_search, metadata = await agent._call_tool_with_metadata(
                McpConfig.rag_mcp_url, "search_reports", payload
            )
            state.edgar_filings = SearchReportsOutput.model_validate(raw_search)
            state.metadata.search = metadata
            logger.info(
                "search_reports completed",
                extra={
                    "ticker": state.edgar_filings.ticker,
                    "filings": len(state.edgar_filings.filings),
                    "collection": state.edgar_filings.collection_name,
                },
            )
        except ToolExecutionError as exc:
            state.metadata.search = exc.metadata
            state.warnings.append(f"search_reports failed: {exc}")
            state.status = "partial"
        except ValidationError as exc:
            state.status = "partial"
            state.warnings.append(f"search_reports output invalid: {exc}")


class UpsertFilingsNode(RetrievalPipelineNode):
    async def run(self, agent: BaseAgent, state: RetrievalPipelineState) -> None:
        logger.info("upsert_filings start", extra={"filings": len(state.edgar_filings.filings)})
        state.metadata.upsert = await agent._upsert_filings(state.edgar_filings.filings)
        logger.info(
            "upsert_filings completed",
            extra={"warnings": state.metadata.upsert.warnings},
        )
        if state.metadata.upsert.warnings:
            state.status = "partial"
            state.warnings.extend(state.metadata.upsert.warnings)


class RetrieveReportNode(RetrievalPipelineNode):
    async def run(self, agent: BaseAgent, state: RetrievalPipelineState) -> None:
        retrieve_filters: dict[str, Any] = {"ticker": state.edgar_filings.ticker.upper()}
        logger.info(
            "starting retrieve_report",
            extra={"query": state.query, "filters": retrieve_filters, "top_k": state.top_k},
        )
        try:
            payload = RAGRetrieveInput(
                query=state.query,
                collection=state.collection_name,
                domain="edgar",
                corpus="analyst_report",
                company_name=state.company_name,
                top_k=state.top_k,
                filters=retrieve_filters,
            ).model_dump()
            raw_retrieve, metadata = await agent._call_tool_with_metadata(
                McpConfig.rag_mcp_url, "retrieve_report", payload
            )
            state.metadata.retrieve = metadata
            state.rag_answer = raw_retrieve.get("context", "") or ""
            logger.info(
                "retrieve_report completed",
                extra={
                    "matches": len(raw_retrieve.get("matches") or []),
                    "context_length": len(state.rag_answer),
                },
            )
        except ToolExecutionError as exc:
            state.metadata.retrieve = exc.metadata
            state.warnings.append(f"retrieve_report failed: {exc}")
            state.status = "partial"
        except ValidationError as exc:
            state.status = "partial"
            state.warnings.append(f"retrieve_report output invalid: {exc}")


class NewsSentimentNode(RetrievalPipelineNode):
    async def run(self, agent: BaseAgent, state: RetrievalPipelineState) -> None:
        news_payload: dict[str, Any] = {}
        if state.ticker:
            news_payload["tickers"] = state.ticker.upper()
        if state.news_limit:
            news_payload["limit"] = state.news_limit
        logger.info(
            "starting news_sentiment",
            extra={"tickers": news_payload.get("tickers"), "limit": state.news_limit},
        )
        try:
            raw_news, metadata = await agent._call_tool_with_metadata(
                McpConfig.alpha_vantage_url, "news_sentiment", news_payload
            )
            state.metadata.news = metadata
            normalized_news = agent._normalize_news_response(raw_news)
            for index, entry in enumerate(normalized_news):
                try:
                    state.news_items.append(MarketNewsSource.model_validate(entry))
                except ValidationError as exc:
                    metadata.warnings.append(f"news entry {index} invalid: {exc}")
            if metadata.warnings:
                state.status = "partial"
                state.warnings.extend(metadata.warnings)
        except ToolExecutionError as exc:
            state.metadata.news = exc.metadata
            state.warnings.append(f"news_sentiment failed: {exc}")
            state.status = "partial"
        except ValidationError as exc:
            state.status = "partial"
            state.warnings.append(f"news_sentiment output invalid: {exc}")


class ExtractFinancialStatementNode(RetrievalPipelineNode):
    async def run(self, agent: BaseAgent, state: RetrievalPipelineState) -> None:
        if not state.edgar_filings.filings:
            return
        statement_payload = {
            "accession_number": state.edgar_filings.filings[0].accession_number,
            "statement_type": "income_statement",
        }
        try:
            raw_statement, metadata = await agent._call_tool_with_metadata(
                McpConfig.rag_mcp_url,
                "extract_financial_statement",
                statement_payload,
            )
            state.metadata.financial_statement = metadata
            state.financial_statement = FinancialStatementOutput.model_validate(raw_statement)
            logger.info(
                "extract_financial_statement completed",
                extra={
                    "accession_number": statement_payload["accession_number"],
                    "statement_type": statement_payload["statement_type"],
                },
            )
        except ToolExecutionError as exc:
            state.metadata.financial_statement = exc.metadata
            state.warnings.append(f"extract_financial_statement failed: {exc}")
            state.status = "partial"
        except ValidationError as exc:
            state.status = "partial"
            state.warnings.append(f"extract_financial_statement output invalid: {exc}")


class GetFinancialReportsNode(RetrievalPipelineNode):
    async def run(self, agent: BaseAgent, state: RetrievalPipelineState) -> None:
        reports_payload = {
            "symbol": state.ticker.upper(),
            "access_number": (
                state.edgar_filings.filings[0].accession_number
                if state.edgar_filings.filings
                else None
            ),
            "from_date": None,
            "freq": "annual",
        }
        try:
            raw_reports, metadata = await agent._call_tool_with_metadata(
                McpConfig.finnhub_mcp_url,
                "get_financial_reports",
                reports_payload,
            )
            state.metadata.financial_reports = metadata
            state.financial_reports = FundamentalDTO.model_validate(raw_reports)
            logger.info(
                "get_financial_reports completed",
                extra={
                    "symbol": reports_payload["symbol"],
                    "access_number": reports_payload["access_number"],
                },
            )
        except ToolExecutionError as exc:
            state.metadata.financial_reports = exc.metadata
            state.warnings.append(f"get_financial_reports failed: {exc}")
            state.status = "partial"
        except ValidationError as exc:
            state.status = "partial"
            state.warnings.append(f"get_financial_reports output invalid: {exc}")
