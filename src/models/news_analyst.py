from __future__ import annotations

from pydantic import BaseModel, Field

from .news_sentiments import NewsSentiment


class NewsTickerRollup(BaseModel):
    ticker: str
    sentiment_score: float
    sentiment_label: str
    relevance_score: float
    top_headlines: list[str] = Field(default_factory=list)


class NewsAnalystOutput(BaseModel):
    query: str
    overall_sentiment_score: float
    overall_sentiment_label: str
    rationale: str
    ticker_rollups: list[NewsTickerRollup] = Field(default_factory=list)
    news_items: list[NewsSentiment] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
