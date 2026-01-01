from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from diskcache import Cache
from dotenv import load_dotenv
from fastapi.logger import logger

from src.agent_tools.edgar.ingest_primary_document import (
    EdgarIngestionPolicy,
    ingest_edgar_primary_documents,
)
from src.agent_tools.edgar.search_reports import search_reports_direct
from src.agent_tools.rag.context_builder import build_rag_context
from src.agent_tools.rag.retrieve_report import retrieve_report_direct
from src.models.analyst_retrieval import (
    AnalystRetrievalError,
    AnalystRetrievalResult,
    EdgarFilingLink,
    EdgarResult,
    RagMatch,
    RagResult,
)
from src.models.rag_retrieve import RAGRetrieveInput, SearchReportsInput

load_dotenv()


@dataclass(frozen=True)
class AnalystRetrievalConfig:
    domain: str = "finance"
    rag_corpus: str = "analyst_report"
    edgar_corpus: str = "edgar"
    top_k: int = 5
    recency_days: int = 183
    edgar_max_filings_per_query: int = 3
    edgar_max_rps: float = 10.0
    cache_dir: str = "./.analyst_retrieval_cache"


class AnalystRetrievalAgent:
    def __init__(self, *, config: AnalystRetrievalConfig | None = None) -> None:
        self._config = config or AnalystRetrievalConfig()
        self._cache = Cache(self._config.cache_dir)

    async def retrieve(
        self,
        query: str,
        *,
        ticker: str | None = None,
        company_name: str | None = None,
        domain: str | None = None,
        top_k: int | None = None,
        filing_categories: list[str] | None = None,
    ) -> AnalystRetrievalResult:
        errors: list[AnalystRetrievalError] = []
        domain = domain or self._config.domain
        top_k = top_k or self._config.top_k
        ticker = ticker or _infer_ticker(query)

        rag_input = RAGRetrieveInput(
            query=query,
            domain=domain,
            corpus=self._config.rag_corpus,
            company_name=company_name,
            top_k=top_k,
        )

        rag_response: dict[str, Any] | None = None
        try:
            rag_response = await retrieve_report_direct(rag_input, cache=self._cache)
        except Exception as exc:
            errors.append(AnalystRetrievalError(source="rag", message=str(exc)))

        if rag_response and int(rag_response.get("num_matches") or 0) > 0:
            rag = _rag_result_from_single_collection(rag_response)
            return AnalystRetrievalResult(query=query, rag=rag, edgar=None, errors=errors)

        if not ticker:
            rag = _rag_result_from_single_collection(rag_response) if rag_response else None
            return AnalystRetrievalResult(query=query, rag=rag, edgar=None, errors=errors)

        filing_categories = filing_categories or _infer_filing_categories(query)

        edgar_result: EdgarResult | None = None
        try:
            edgar_result, updated_rag = await self._edgar_fallback(
                query=query,
                ticker=ticker,
                company_name=company_name,
                domain=domain,
                top_k=top_k,
                filing_categories=filing_categories,
            )
            if updated_rag is not None:
                return AnalystRetrievalResult(
                    query=query, rag=updated_rag, edgar=edgar_result, errors=errors
                )
            rag = _rag_result_from_single_collection(rag_response) if rag_response else None
            return AnalystRetrievalResult(query=query, rag=rag, edgar=edgar_result, errors=errors)
        except Exception as exc:
            errors.append(AnalystRetrievalError(source="edgar", message=str(exc)))
            rag = _rag_result_from_single_collection(rag_response) if rag_response else None
            return AnalystRetrievalResult(query=query, rag=rag, edgar=None, errors=errors)

    async def _edgar_fallback(
        self,
        *,
        query: str,
        ticker: str,
        company_name: str | None,
        domain: str,
        top_k: int,
        filing_categories: list[str],
    ) -> tuple[EdgarResult, RagResult | None]:
        discovered, cik = _discover_filings(
            ticker=ticker,
            filing_categories=filing_categories,
            limit_per_category=max(1, self._config.edgar_max_filings_per_query),
        )

        selected = _select_recent_filings(
            discovered,
            max_filings=self._config.edgar_max_filings_per_query,
            recency_days=self._config.recency_days,
        )

        edgar_links = [
            EdgarFilingLink(
                form=f.form,
                filing_date=f.filing_date,
                accession_number=f.accession_number,
                href=f.href,
            )
            for f in selected
        ]

        policy = EdgarIngestionPolicy(
            max_rps=self._config.edgar_max_rps,
            max_filings_per_query=self._config.edgar_max_filings_per_query,
        )

        ingest_info = ingest_edgar_primary_documents(
            selected,
            ticker=ticker,
            cik=cik,
            rag_input=RAGRetrieveInput(
                query=query,
                domain=domain,
                corpus=self._config.edgar_corpus,
                company_name=company_name or ticker.upper(),
                top_k=top_k,
            ),
            policy=policy,
        )

        ingested_collections = list(ingest_info.get("collections") or [])

        rag = await _retrieve_across_collections(
            query=query,
            collections=ingested_collections,
            top_k=top_k,
            cache=self._cache,
        )

        edgar_result = EdgarResult(
            ticker=ticker.upper(),
            cik=cik,
            filing_categories=filing_categories,
            filings=edgar_links,
            ingested_collections=ingested_collections,
            ingestion=ingest_info,
        )
        return edgar_result, rag


def _infer_filing_categories(query: str) -> list[str]:
    q = (query or "").lower()
    forms: list[str] = []

    if re.search(r"\b10[\s-]?k\b", q):
        forms.append("10-K")
    if re.search(r"\b10[\s-]?q\b", q):
        forms.append("10-Q")
    if re.search(r"\b8[\s-]?k\b", q):
        forms.append("8-K")

    if not forms:
        return ["10-K", "10-Q", "8-K"]
    return forms


def _infer_ticker(query: str) -> str | None:
    q = (query or "").strip()
    if not q:
        return None

    m = re.search(r"\$([A-Za-z]{1,5})\b", q)
    if m:
        return m.group(1).upper()

    m = re.search(r"\(([A-Za-z]{1,5})\)", q)
    if m:
        return m.group(1).upper()

    return None


def _discover_filings(
    *,
    ticker: str,
    filing_categories: list[str],
    limit_per_category: int,
) -> tuple[list[Any], str]:
    all_filings: list[Any] = []
    cik: str | None = None

    for category in filing_categories:
        out = search_reports_direct(
            SearchReportsInput(
                ticker=ticker,
                filing_category=category,
                limit=limit_per_category,
            )
        )
        cik = cik or out.cik
        all_filings.extend(list(out.filings))

    if cik is None:
        raise ValueError("EDGAR discovery did not return a CIK")

    unique: dict[str, Any] = {}
    for filing in all_filings:
        unique[filing.accession_number] = filing
    return list(unique.values()), cik


def _parse_filing_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def _select_recent_filings(
    filings: Iterable[Any],
    *,
    max_filings: int,
    recency_days: int,
) -> list[Any]:
    filings = list(filings)
    if not filings:
        return []

    cutoff = date.today() - timedelta(days=recency_days)

    recent: list[Any] = []
    for filing in filings:
        filing_date = _parse_filing_date(getattr(filing, "filing_date", ""))
        if filing_date and filing_date >= cutoff:
            recent.append(filing)

    chosen = recent if recent else filings
    return chosen[:max_filings]


async def _retrieve_across_collections(
    *,
    query: str,
    collections: list[str],
    top_k: int,
    cache: Cache,
) -> RagResult | None:
    if not collections:
        return None

    per_collection: list[dict[str, Any]] = []
    for collection in collections:
        try:
            resp = await retrieve_report_direct(
                RAGRetrieveInput(query=query, collection=collection, top_k=top_k),
                cache=cache,
            )
            per_collection.append(resp)
        except Exception as exc:
            logger.info(
                "edgar_rag_retrieve_failed",
                extra={"collection": collection, "error": str(exc)},
            )

    all_matches: list[dict[str, Any]] = []
    for resp in per_collection:
        matches = list(resp.get("matches") or [])
        all_matches.extend(matches)

    def sort_key(match: dict[str, Any]) -> tuple[int, float]:
        dist = match.get("distance")
        if dist is None:
            return (1, float("inf"))
        try:
            return (0, float(dist))
        except Exception:
            return (1, float("inf"))

    all_matches_sorted = sorted(all_matches, key=sort_key)[:top_k]
    context = build_rag_context(all_matches_sorted, max_chars=8000)

    return RagResult(
        collections=collections,
        query=query,
        top_k=top_k,
        num_matches=len(all_matches_sorted),
        matches=[RagMatch(**m) for m in all_matches_sorted],
        context=context,
    )


def _rag_result_from_single_collection(rag_response: dict[str, Any]) -> RagResult:
    collection = rag_response.get("collection")
    matches = list(rag_response.get("matches") or [])
    return RagResult(
        collections=[collection] if collection else [],
        query=str(rag_response.get("query") or ""),
        top_k=int(rag_response.get("top_k") or 0),
        num_matches=int(rag_response.get("num_matches") or 0),
        matches=[RagMatch(**m) for m in matches],
        context=str(rag_response.get("context") or ""),
    )
