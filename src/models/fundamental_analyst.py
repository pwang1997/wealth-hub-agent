from pydantic import BaseModel, Field


class FundamentalAnalysisSignal(BaseModel):
    name: str
    description: str
    impact: str  # e.g., "positive", "negative", "neutral"


class FundamentalAnalystOutput(BaseModel):
    ticker: str
    health_score: int = Field(..., ge=0, le=100)
    strengths: list[FundamentalAnalysisSignal] = Field(default_factory=list)
    weaknesses: list[FundamentalAnalysisSignal] = Field(default_factory=list)
    red_flags: list[FundamentalAnalysisSignal] = Field(default_factory=list)
    summary: str
    citations: list[str] = Field(
        default_factory=list, description="Accession numbers or links to EDGAR filings"
    )
