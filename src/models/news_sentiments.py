from decimal import Decimal

from pydantic import BaseModel


class NewsSentiment(BaseModel):
    title: str
    source: str
    url: str
    summary: str
    topics: str
    overall_sentiment: Decimal | str
    sentiment_label: str
    ticker_sentiment: list[str]
    time_published: str
