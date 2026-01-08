from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from diskcache import Cache
from dotenv import load_dotenv
from fastapi.logger import logger

from clients.finnhub_rest_client import FinnHubRestClient
from src.utils.cache import cache_key
from src.utils.logging_config import configure_logging

load_dotenv()
configure_logging()

cache = Cache("./.finnhub_mcp_cache")


def _get_required_api_key() -> str:
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        raise RuntimeError("FINNHUB_API_KEY is required to use Finnhub MCP tools.")
    return api_key


def _get_client() -> FinnHubRestClient:
    api_key = _get_required_api_key()
    client = FinnHubRestClient(api_key)
    client.init()
    return client


def _validate_iso_date(date_value: str | None, field_name: str) -> str | None:
    if not date_value:
        return None
    try:
        datetime.strptime(date_value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{field_name} must be YYYY-MM-DD") from exc
    return date_value


async def company_news_impl(
    symbol: str,
    from_date: str | None = None,
    to_date: str | None = None,
) -> Any:
    """Return company news for `symbol` from Finnhub."""
    if not symbol:
        raise ValueError("symbol is required")
    from_date = _validate_iso_date(from_date, "from_date")
    to_date = _validate_iso_date(to_date, "to_date")

    key = cache_key(
        "Finnhub",
        "company_news",
        {"symbol": symbol, "from_date": from_date, "to_date": to_date},
    )
    if key in cache:
        logger.info(f"Using cached get_company_news response: {key}")
        return cache[key]

    client = _get_client()
    data = await client.get_company_news_async(symbol, from_date, to_date)
    cache.set(key, data, expire=60 * 10)
    return data


async def company_peer_impl(symbol: str, grouping: str | None = None) -> Any:
    """Return peer companies for `symbol` from Finnhub."""
    if not symbol:
        raise ValueError("symbol is required")

    key = cache_key("Finnhub", "company_peers", {"symbol": symbol, "grouping": grouping})
    if key in cache:
        logger.info(f"Using cached get_company_peer response: {key}")
        return cache[key]

    client = _get_client()
    data = await client.get_company_peer_async(symbol, grouping)
    cache.set(key, data, expire=60 * 60 * 24)
    return data
