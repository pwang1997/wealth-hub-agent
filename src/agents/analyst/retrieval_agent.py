from __future__ import annotations

from dataclasses import dataclass

from diskcache import Cache
from dotenv import load_dotenv

from src.models.analyst_retrieval import AnalystRetrievalResult

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
        pass
        # errors: list[AnalystRetrievalError] = []
        # domain = domain or self._config.domain
        # top_k = top_k or self._config.top_k
        # ticker = ticker or _infer_ticker(query)

        # rag_input = RAGRetrieveInput(
        #     query=query,
        #     domain=domain,
        #     corpus=self._config.rag_corpus,
        #     company_name=company_name,
        #     top_k=top_k,
        # )

        # rag_response: dict[str, Any] | None = None
        # try:
        #     rag_response = await retrieve_report_direct(rag_input, cache=self._cache)
        # except Exception as exc:
        #     errors.append(AnalystRetrievalError(source="rag", message=str(exc)))

        # if rag_response and int(rag_response.get("num_matches") or 0) > 0:
        #     rag = _rag_result_from_single_collection(rag_response)
        #     return AnalystRetrievalResult(query=query, rag=rag, edgar=None, errors=errors)

        # if not ticker:
        #     rag = _rag_result_from_single_collection(rag_response) if rag_response else None
        #     return AnalystRetrievalResult(query=query, rag=rag, edgar=None, errors=errors)

        # filing_categories = filing_categories or _infer_filing_categories(query)

        # edgar_result: EdgarResult | None = None
        # try:
        #     edgar_result, updated_rag = await self._edgar_fallback(
        #         query=query,
        #         ticker=ticker,
        #         company_name=company_name,
        #         domain=domain,
        #         top_k=top_k,
        #         filing_categories=filing_categories,
        #     )
        #     if updated_rag is not None:
        #         return AnalystRetrievalResult(
        #             query=query, rag=updated_rag, edgar=edgar_result, errors=errors
        #         )
        #     rag = _rag_result_from_single_collection(rag_response) if rag_response else None
        #     return AnalystRetrievalResult(query=query, rag=rag, edgar=edgar_result, errors=errors)
        # except Exception as exc:
        #     errors.append(AnalystRetrievalError(source="edgar", message=str(exc)))
        #     rag = _rag_result_from_single_collection(rag_response) if rag_response else None
        #     return AnalystRetrievalResult(query=query, rag=rag, edgar=None, errors=errors)

    async def process(
        self,
        query: str,
        *,
        ticker: str | None = None,
        company_name: str | None = None,
        domain: str | None = None,
        top_k: int | None = None,
        filing_categories: list[str] | None = None,
    ) -> AnalystRetrievalResult:
        """Backward-compatible alias for `retrieve`."""
        return await self.retrieve(
            query,
            ticker=ticker,
            company_name=company_name,
            domain=domain,
            top_k=top_k,
            filing_categories=filing_categories,
        )


# TODO:
def get_query_reasoning():
    """
    Apply Agent reasoning to create user intent frame from user query. Discover available function tools to assist the downstream agent.
    Return message to the downstream agent and chain of actions/tools need to be invoked.
    """
    pass


def discover_collections():
    """
    Discover collections from chromadb, if none, invoke discover_filling()
    """
    pass


def discover_fillings():
    """
    Use EdgarClient to retrieve fillings.
    """
    pass


def upsert_fillings():
    """
    Upsert edgar filling to chromadb
    """
    pass


def retrieve():
    """
    Retrieve document from crhomadb ---  RAG
    """
