from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .news_sentiments import NewsSentiment
from .rag_retrieve import SearchReportsOutput


class RetrievalAgentToolMetadata(BaseModel):
    tool: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_ms: Optional[int] = None
    warnings: list[str] = Field(default_factory=list)


class RetrievalAgentMetadata(BaseModel):
    search: Optional[RetrievalAgentToolMetadata] = None
    upsert: Optional[RetrievalAgentToolMetadata] = None
    retrieve: Optional[RetrievalAgentToolMetadata] = None
    news: Optional[RetrievalAgentToolMetadata] = None
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
