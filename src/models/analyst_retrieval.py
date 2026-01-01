from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnalystRetrievalError(BaseModel):
    source: str
    message: str


class RagMatch(BaseModel):
    rank: int | None = None
    id: str | None = None
    distance: float | None = None
    document: str | None = None
    metadata: Any | None = None


class RagResult(BaseModel):
    collections: list[str] = Field(default_factory=list)
    query: str
    top_k: int
    num_matches: int
    matches: list[RagMatch] = Field(default_factory=list)
    context: str


class EdgarFilingLink(BaseModel):
    form: str
    filing_date: str
    accession_number: str
    href: str


class EdgarResult(BaseModel):
    ticker: str
    cik: str
    filing_categories: list[str] = Field(default_factory=list)
    filings: list[EdgarFilingLink] = Field(default_factory=list)
    ingested_collections: list[str] = Field(default_factory=list)
    ingestion: dict[str, Any] = Field(default_factory=dict)


class AnalystRetrievalResult(BaseModel):
    query: str
    rag: RagResult | None = None
    edgar: EdgarResult | None = None
    errors: list[AnalystRetrievalError] = Field(default_factory=list)
