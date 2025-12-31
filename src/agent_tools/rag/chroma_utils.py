from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import chromadb
from diskcache import Cache
from fastapi.logger import logger

from src.agent_tools.rag.context_builder import safe_json_cache_args
from src.utils.cache import CacheConfig, cache_key


@lru_cache(maxsize=1)
def get_chromadb_client() -> Any:
    api_key = os.getenv("CHROMA_API_KEY")
    tenant = os.getenv("CHROMA_TENANT")
    database = os.getenv("CHROMA_DATABASE")
    if api_key and tenant and database:
        return chromadb.CloudClient(api_key=api_key, tenant=tenant, database=database)

    persist_dir = os.getenv("CHROMA_PERSIST_DIR") or os.path.join("storage", "chroma")
    os.makedirs(persist_dir, exist_ok=True)
    return chromadb.PersistentClient(path=persist_dir)


def list_collection_names(client: Any, *, cache: Cache) -> list[str]:
    chroma_identity = {
        "chroma_api_key_set": bool(os.getenv("CHROMA_API_KEY")),
        "chroma_tenant": os.getenv("CHROMA_TENANT"),
        "chroma_database": os.getenv("CHROMA_DATABASE"),
    }
    key = cache_key("ChromaDB", "list_collections", safe_json_cache_args(chroma_identity))
    cached = cache.get(key)
    if isinstance(cached, list) and all(isinstance(x, str) for x in cached):
        logger.info(f"Using cached list_collections response: {key}")
        return cached

    try:
        collections = client.list_collections()
    except Exception:
        return []

    names: list[str] = []
    for c in collections or []:
        name = getattr(c, "name", None)
        if isinstance(name, str) and name:
            names.append(name)
    result = sorted(set(names))

    logger.info(f"Caching list_collections result, key: {key}")
    cache.set(key, result, expire=CacheConfig.LIST_COLLECTIONS_CACHE_TTL_SECONDS)
    return result


def get_collection_or_raise(client: Any, collection_name: str, *, cache: Cache) -> Any:
    try:
        return client.get_collection(name=collection_name)
    except Exception as exc:
        available = list_collection_names(client, cache=cache)
        raise ValueError(
            f"Failed to open Chroma collection '{collection_name}'. Available: {available}"
        ) from exc
