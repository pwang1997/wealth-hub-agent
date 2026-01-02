import os
from typing import Any

import chromadb
from diskcache import Cache
from fastapi.logger import logger

from src.utils.cache import CacheConfig, cache_key


class ChromaClient:
    def __init__(self):
        api_key = os.getenv("CHROMA_API_KEY")
        tenant = os.getenv("CHROMA_TENANT")
        database = os.getenv("CHROMA_DATABASE")

        self.client = None

        if api_key and tenant and database:
            self.client = chromadb.CloudClient(api_key=api_key, tenant=tenant, database=database)
        else:
            host = os.getenv("CHROMA_HOST") or "localhost"
            port = int(os.getenv("CHROMA_PORT") or "8000")
            self.client = chromadb.HttpClient(host=host, port=port)

    async def list_collection_names(self, *, cache: Cache | None) -> list[str]:
        chroma_identity = {
            "chroma_api_key_set": bool(os.getenv("CHROMA_API_KEY")),
            "chroma_tenant": os.getenv("CHROMA_TENANT"),
            "chroma_database": os.getenv("CHROMA_DATABASE"),
        }
        key = cache_key("ChromaDB", "list_collections", chroma_identity)
        if cache is not None:
            cached = cache.get(key)
            if isinstance(cached, list) and all(isinstance(x, str) for x in cached):
                logger.info(f"Using cached list_collections response: {key}")
                return cached

        try:
            collections = self.client.list_collections()
        except Exception:
            return []

        names: list[str] = []
        for c in collections or []:
            name = getattr(c, "name", None)
            if isinstance(name, str) and name:
                names.append(name)
        result = sorted(set(names))

        if cache is not None:
            logger.info(f"Caching list_collections result, key: {key}")
            cache.set(key, result, expire=CacheConfig.LIST_COLLECTIONS_CACHE_TTL_SECONDS)
        return result

    def get_client(self):
        return self.client

    async def get_collection_or_raise(
        self, collection_name: str | None, *, cache: Cache | None
    ) -> Any:
        try:
            return self.client.get_collection(name=collection_name)
        except Exception as exc:
            available = await self.list_collection_names(cache=cache)
            raise ValueError(
                f"Failed to open Chroma collection '{collection_name}'. Available: {available}"
            ) from exc
