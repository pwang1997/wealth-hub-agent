from typing import Any, Optional

from openai import BaseModel
from pydantic import Field


class RAGRetrieveInput(BaseModel):
    query: str = Field(..., description="Natural-language query to search for.")
    collection: Optional[str] = Field(
        None,
        description=(
            "Chroma collection name. If omitted, the tool attempts to build one from "
            "`domain`, `corpus`, and `company_name`."
        ),
    )
    domain: str = Field(
        "finance", description="Used to build collection name if `collection` is omitted."
    )
    corpus: str = Field(
        "analyst_report", description="Used to build collection name if `collection` is omitted."
    )
    company_name: Optional[str] = Field(
        None,
        description=(
            "Used to build collection name if `collection` is omitted. This should match the value used "
            "during indexing (see `/rag/upload_pdf`)."
        ),
    )
    top_k: int = Field(5, ge=1, le=50, description="Number of chunks to retrieve (1-50).")
    filters: Optional[dict[str, Any]] = Field(
        None, description="Chroma `where` filter (metadata constraints). expected one of the filters [ticker, form]"
    )
    document_contains: Optional[str] = Field(
        None,
        description=(
            "Optional substring filter applied to document text via Chroma `where_document`."
        ),
    )
    max_context_chars: int = Field(
        8000, ge=0, le=50000, description="Maximum characters to include in `context`."
    )


class SearchReportsInput(BaseModel):
    ticker: str = Field(..., description="Company ticker symbol, e.g. AAPL")
    filing_category: str = Field(..., description="SEC form type, e.g. 10-K, 10-Q, 8-K")
    limit: int = Field(10, ge=1, le=50, description="Max number of filings to return")


class EdgarSearchMetaData(BaseModel):
    cik: str
    ticker: str
    company_name: str
    form: str
    filing_date: str
    report_date: str
    accession_number: str
    collection_name: str


class FilingResult(BaseModel):
    form: str
    filing_date: str
    accession_number: str
    href: str
    metadata: EdgarSearchMetaData


class SearchReportsOutput(BaseModel):
    ticker: str
    cik: str
    filings: list[FilingResult]
    collection_name: str
