import os
import sys
from datetime import datetime
from typing import Any, Optional

from diskcache import Cache
from dotenv import load_dotenv
from fastapi.logger import logger

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from clients.finnhub_rest_client import FinnHubRestClient
from src.factory.mcp_server_factory import McpServerFactory
from src.utils.cache import cache_key

load_dotenv()

cache = Cache("./.finnhub_mcp_cache")
mcp_server = McpServerFactory.create_mcp_server("FinnhubMcpServer")


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


def _validate_iso_date(date_value: Optional[str], field_name: str) -> Optional[str]:
    if not date_value:
        return None
    try:
        datetime.strptime(date_value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{field_name} must be YYYY-MM-DD") from exc
    return date_value


@mcp_server.tool()
async def get_company_news(
    symbol: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
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


@mcp_server.tool()
async def get_company_peer(symbol: str, grouping: Optional[str] = None) -> Any:
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


if __name__ == "__main__":
    logger.info("Running Finnhub MCP server")
    port = int(os.getenv("FINNHUB_MCP_PORT", "8002"))
    McpServerFactory.run_default_mcp_server(mcp_server, port)
