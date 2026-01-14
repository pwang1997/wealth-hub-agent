from pydantic import BaseModel, Field

from src.models.fundamental_analyst import FundamentalAnalystOutput
from src.models.news_analyst import NewsAnalystOutput


class ResearchAnalystOutput(BaseModel):
    ticker: str
    composed_analysis: str
    fundamental_analysis: FundamentalAnalystOutput | None = None
    news_analysis: NewsAnalystOutput | None = None
    warnings: list[str] = Field(default_factory=list)
