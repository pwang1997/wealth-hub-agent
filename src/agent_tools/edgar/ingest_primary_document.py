from __future__ import annotations

import re
import time
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Any, Iterable, Optional

import os
import requests
from fastapi.logger import logger
from llama_index.core.embeddings import resolve_embed_model
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document

from src.agent_tools.rag.chroma_utils import get_chromadb_client, list_collection_names
from src.agent_tools.rag.context_builder import normalize_company_name
from src.models.rag_retrieve import FilingResult, RAGRetrieveInput
from src.utils.edgar_config import EdgarConfig


@dataclass(frozen=True)
class EdgarIngestionPolicy:
    max_rps: float = 10.0
    max_filings_per_query: int = 3
    chunk_size: int = 256


class _HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if tag in {"p", "br", "div", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if tag in {"p", "div", "li", "tr"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        text = data.strip()
        if not text:
            return
        self._parts.append(text)
        self._parts.append(" ")

    def text(self) -> str:
        raw = unescape("".join(self._parts))
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def html_to_text(html: str) -> str:
    parser = _HtmlTextExtractor()
    parser.feed(html)
    return parser.text()


def _sanitize_collection_part(value: str) -> str:
    value = value.strip()
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^a-zA-Z0-9._-]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_") or "unknown"


def _resolve_collection_name(client: Any, input_data: RAGRetrieveInput) -> str:
    if input_data.collection:
        return input_data.collection

    domain = input_data.domain
    corpus = input_data.corpus
    company_name = normalize_company_name(input_data.company_name)

    candidates: list[str] = []
    candidates.append(f"{domain}_{corpus}_{company_name}")
    if company_name is None:
        candidates.append(f"{domain}_{corpus}_")
        candidates.append(f"{domain}_{corpus}_None")

    existing = set(list_collection_names(client, cache=None))
    for candidate in candidates:
        if candidate in existing:
            return candidate

    return candidates[0]


def _sleep_for_rate_limit(*, last_request_at: float | None, max_rps: float) -> float:
    if max_rps <= 0:
        return time.monotonic()
    min_interval = 1.0 / max_rps
    now = time.monotonic()
    if last_request_at is not None:
        elapsed = now - last_request_at
        remaining = min_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
    return time.monotonic()


def _safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in (metadata or {}).items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        else:
            safe[key] = str(value)
    return safe


def _filing_already_indexed(collection: Any, accession_number: str) -> bool:
    try:
        existing = collection.get(
            where={"source": "edgar", "accession_number": accession_number},
            include=[],
        )
    except Exception:
        return False

    ids = (existing or {}).get("ids") or []
    return bool(ids)


def _iter_limited_filings(
    filings: Iterable[FilingResult], *, max_filings: int
) -> list[FilingResult]:
    result: list[FilingResult] = []
    for filing in filings:
        result.append(filing)
        if len(result) >= max_filings:
            break
    return result


def ingest_edgar_primary_documents(
    filings: list[FilingResult],
    *,
    ticker: str,
    cik: str,
    rag_input: RAGRetrieveInput,
    policy: EdgarIngestionPolicy = EdgarIngestionPolicy(),
    embed_model_name: str | None = None,
    request_timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    """Fetch EDGAR primary filing documents (HTML), chunk/embed with LlamaIndex, and upsert into Chroma.

    This helper is designed to be called by agents so they can avoid re-fetching the same filing
    across queries. It is single-threaded and rate-limited to comply with EDGAR guidance.
    """

    if not filings:
        return {"collections": [], "attempted": 0, "ingested": 0, "skipped_existing": 0}

    base_company_name = normalize_company_name(rag_input.company_name) or ticker.upper()
    base_company_key = _sanitize_collection_part(base_company_name)
    client = get_chromadb_client()

    selected = _iter_limited_filings(filings, max_filings=policy.max_filings_per_query)
    last_request_at: float | None = None

    attempted = 0
    ingested = 0
    skipped_existing = 0
    collections_touched: list[str] = []

    embed_model_name = embed_model_name or os.getenv("RAG_EMBED_MODEL") or "default"
    embed_model = resolve_embed_model(embed_model_name)
    splitter = SentenceSplitter(chunk_size=policy.chunk_size)

    for filing in selected:
        attempted += 1
        form_key = _sanitize_collection_part(filing.form)
        filing_rag_input = RAGRetrieveInput(
            query=rag_input.query,
            collection=None,
            domain=rag_input.domain,
            corpus="edgar",
            company_name=f"{base_company_key}_{form_key}",
            top_k=rag_input.top_k,
            filters=rag_input.filters,
            document_contains=rag_input.document_contains,
            max_context_chars=rag_input.max_context_chars,
        )
        collection_name = _resolve_collection_name(client, filing_rag_input)
        collection = client.get_or_create_collection(name=collection_name)
        collections_touched.append(collection_name)

        if _filing_already_indexed(collection, filing.accession_number):
            skipped_existing += 1
            continue

        last_request_at = _sleep_for_rate_limit(last_request_at=last_request_at, max_rps=policy.max_rps)
        resp = requests.get(filing.href, headers=EdgarConfig.HEADERS, timeout=request_timeout_seconds)
        resp.raise_for_status()
        text = html_to_text(resp.text)
        if not text:
            logger.info(
                "edgar_primary_document_empty",
                extra={"ticker": ticker, "cik": cik, "accession": filing.accession_number},
            )
            continue

        doc = Document(
            text=text,
            metadata=_safe_metadata(
                {
                    "source": "edgar",
                    "ticker": ticker.upper(),
                    "cik": cik,
                    "form": filing.form,
                    "filing_date": filing.filing_date,
                    "accession_number": filing.accession_number,
                    "href": filing.href,
                    "domain": filing_rag_input.domain,
                    "corpus": filing_rag_input.corpus,
                    "company_name": filing_rag_input.company_name,
                }
            ),
        )
        nodes = splitter.get_nodes_from_documents([doc])

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []
        for idx, node in enumerate(nodes):
            ids.append(f"edgar:{cik}:{filing.accession_number}:{idx}")
            documents.append(node.get_content(metadata_mode="none"))
            metadatas.append(_safe_metadata({**doc.metadata, "chunk_index": idx}))

        embeddings = embed_model.get_text_embedding_batch(documents)
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        ingested += 1

    collections_used = sorted(set(collections_touched))
    logger.info(
        "edgar_ingest_primary_documents",
        extra={
            "ticker": ticker,
            "cik": cik,
            "collections": collections_used,
            "attempted": attempted,
            "ingested": ingested,
            "skipped_existing": skipped_existing,
            "max_filings_per_query": policy.max_filings_per_query,
            "max_rps": policy.max_rps,
            "chunk_size": policy.chunk_size,
        },
    )
    return {
        "collections": collections_used,
        "attempted": attempted,
        "ingested": ingested,
        "skipped_existing": skipped_existing,
    }
