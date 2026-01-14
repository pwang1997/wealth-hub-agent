from typing import Literal

from pydantic import BaseModel


class InvestmentManagerOutput(BaseModel):
    ticker: str
    decision: Literal["strong buy", "buy", "hold", "sell", "strong sell"]
    rationale: str
    confidence: float
    reasoning: str | None = None
