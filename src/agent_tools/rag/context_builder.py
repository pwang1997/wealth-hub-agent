from __future__ import annotations

import json
from typing import Any, Optional


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    return str(value)


def normalize_company_name(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def flatten_chroma_query_results(results: dict[str, Any]) -> list[dict[str, Any]]:
    ids = (results or {}).get("ids") or []
    documents = (results or {}).get("documents") or []
    metadatas = (results or {}).get("metadatas") or []
    distances = (results or {}).get("distances") or []

    doc_ids = ids[0] if ids else []
    docs = documents[0] if documents else []
    metas = metadatas[0] if metadatas else []
    dists = distances[0] if distances else []

    matches: list[dict[str, Any]] = []
    for idx in range(max(len(doc_ids), len(docs), len(metas), len(dists))):
        match = {
            "rank": idx + 1,
            "id": doc_ids[idx] if idx < len(doc_ids) else None,
            "distance": dists[idx] if idx < len(dists) else None,
            "document": docs[idx] if idx < len(docs) else None,
            "metadata": jsonable(metas[idx]) if idx < len(metas) else None,
        }
        matches.append(match)
    return matches


def build_rag_context(matches: list[dict[str, Any]], *, max_chars: int = 8000) -> str:
    parts: list[str] = []
    total_chars = 0
    for match in matches:
        chunk = (
            f"[{match.get('rank')}] id={match.get('id')} distance={match.get('distance')} "
            f"meta={match.get('metadata')}\n{match.get('document') or ''}"
        )
        parts.append(chunk)
        total_chars += len(chunk)
        if total_chars >= max_chars:
            break
    context = "\n\n---\n\n".join(parts)
    return context[:max_chars]


def safe_json_cache_args(args: dict[str, Any]) -> dict[str, Any]:
    safe_args = jsonable(args)
    try:
        json.dumps(safe_args, sort_keys=True, separators=(",", ":"))
    except TypeError:
        safe_args = {"_non_jsonable_args": str(safe_args)}
    return safe_args

