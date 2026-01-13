from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .fundamentals import FundamentalDTO
from .news_sentiments import NewsSentiment
from .rag_retrieve import FinancialStatementOutput, SearchReportsOutput


class RetrievalAgentToolMetadata(BaseModel):
    tool: str
    start_time: str | None = None
    end_time: str | None = None
    duration_ms: int | None = None
    warnings: list[str] = Field(default_factory=list)


class RetrievalAgentMetadata(BaseModel):
    search: RetrievalAgentToolMetadata | None = None
    upsert: RetrievalAgentToolMetadata | None = None
    retrieve: RetrievalAgentToolMetadata | None = None
    news: RetrievalAgentToolMetadata | None = None
    financial_statement: RetrievalAgentToolMetadata | None = None
    financial_reports: RetrievalAgentToolMetadata | None = None
    warnings: list[str] = Field(default_factory=list)


class MarketNewsSource(NewsSentiment):
    related_filings: list[str] = Field(default_factory=list)


class RetrievalAgentOutput(BaseModel):
    query: str
    status: Literal["success", "partial", "failed"]
    answer: str
    edgar_filings: SearchReportsOutput
    market_news: list[MarketNewsSource] = Field(default_factory=list)
    metadata: RetrievalAgentMetadata
    financial_statement: FinancialStatementOutput | None = None
    financial_reports: FundamentalDTO | None = None
