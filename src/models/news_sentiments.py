from pydantic import BaseModel


class NewsTopic(BaseModel):
    topic: str
    relevance_score: float | str


class NewsTickerSentiment(BaseModel):
    ticker: str
    relevance_score: float | str
    ticker_sentiment_score: float | str
    ticker_sentiment_label: str


class NewsSentiment(BaseModel):
    title: str
    source: str
    url: str
    summary: str
    topics: list[NewsTopic]
    overall_sentiment_score: float | str
    overall_sentiment_label: str
    ticker_sentiment: list[NewsTickerSentiment]
    time_published: str


class NewsSentimentResponse(BaseModel):
    sentiment_score_definition: str
    relevance_score_definition: str
    feed: list[NewsSentiment]
