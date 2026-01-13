from __future__ import annotations

import os
from typing import Any, Literal

import httpx
from diskcache import Cache
from dotenv import load_dotenv
from fastapi.logger import logger
from fastmcp import Client as MCPClient
from fastmcp.client.transports import StreamableHttpTransport

from src.models.news_sentiments import NewsSentimentResponse
from src.utils.cache import cache_key
from src.utils.logging_config import configure_logging

load_dotenv()
configure_logging()

cache = Cache("./.alpha_vantage_mcp_cache")

REMOTE_MCP_SERVER_URL = (
    f"https://mcp.alphavantage.co/mcp?apikey={os.getenv('ALPHA_VANTAGE_API_KEY')}"
)


def _create_remote_client(server_url: str) -> MCPClient:
    transport = StreamableHttpTransport(server_url, headers={"accept-encoding": "identity"})
    return MCPClient(transport)


async def _call_remote_tool(
    tool_name: str, tool_input: dict[str, Any], server_url: str = REMOTE_MCP_SERVER_URL
) -> Any:
    logger.info("Calling Alpha Vantage MCP tool %s via %s", tool_name, server_url)
    logger.debug("Tool input: %s", tool_input)
    async with _create_remote_client(server_url) as client:
        response = await client.call_tool(tool_name, tool_input)
    logger.debug("Received response for %s: %s", tool_name, response)
    return response


def _serialize_mcp_tool(tool: Any) -> dict[str, Any]:
    if tool is None:
        return {}
    if isinstance(tool, dict):
        return tool

    model_dump = getattr(tool, "model_dump", None)
    if callable(model_dump):
        return model_dump()

    as_dict = getattr(tool, "dict", None)
    if callable(as_dict):
        return as_dict()

    try:
        return dict(tool)
    except TypeError:
        return vars(tool)


async def discover_remote_tools_impl(
    server_url: str = REMOTE_MCP_SERVER_URL,
) -> list[dict[str, Any]]:
    logger.info("Discovering Alpha Vantage MCP tools from %s", server_url)
    async with _create_remote_client(server_url) as client:
        tools = await client.list_tools()
    logger.info("Discovered %d tools from Alpha Vantage MCP", len(tools) if tools else 0)
    if tools is None:
        return []
    return [_serialize_mcp_tool(tool) for tool in tools]


async def news_sentiment_impl(
    tickers: str,
    limit: int,
    time_from: str,
) -> NewsSentimentResponse:
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        raise ValueError("ALPHA_VANTAGE_API_KEY environment variable is not set")

    params: dict[str, Any] = {
        "function": "NEWS_SENTIMENT",
        "apikey": api_key,
        "tickers": tickers,
        "limit": limit,
        "time_from": time_from,
    }
    logger.debug(
        "Fetching news sentiment via HTTP GET for tickers=%s limit=%s time_from=%s",
        tickers,
        limit,
        time_from,
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("https://www.alphavantage.co/query", params=params)
        response.raise_for_status()
        data = response.json()

    logger.debug("Received news sentiment response: %s", data)
    response = NewsSentimentResponse(
        sentiment_score_definition=data.get("sentiment_score_definition", ""),
        relevance_score_definition=data.get("relevance_score_definition", ""),
        feed=data.get("feed", []),
    )
    return response


async def company_overview_impl(symbol: str) -> Any:
    if not symbol:
        raise ValueError("symbol is required")
    logger.debug("Fetching company overview for symbol=%s", symbol)
    key = cache_key("AlphaVantage", "COMPANY_OVERVIEW", {"symbol": symbol})

    if key in cache:
        logger.info(f"Using cached company_overview response: {cache[key]}")
        return cache[key]

    response = await _call_remote_tool(
        "COMPANY_OVERVIEW", {"symbol": symbol}, server_url=REMOTE_MCP_SERVER_URL
    )
    if response:
        logger.info(f"Caching company_overview response, key: {key}, response: {response}")
        cache.set(key, response, expire=60 * 60 * 24)

    return response


async def fundamentals_impl(
    symbol: str, fundamental_type: Literal["INCOMSE_STATEMENT", "BALANCE_SHEET", "CASH_FLOW"]
) -> Any:
    if not symbol:
        raise ValueError("symbol is required")
    logger.debug("Fetching %s for symbol=%s", fundamental_type, symbol)
    key = cache_key("AlphaVantage", fundamental_type, {"symbol": symbol})

    if key in cache:
        logger.info(f"Using cached {fundamental_type} response: {cache[key]}")
        return cache[key]

    response = await _call_remote_tool(
        fundamental_type, {"symbol": symbol}, server_url=REMOTE_MCP_SERVER_URL
    )
    if response:
        logger.info(f"Caching {fundamental_type} response, key: {key}, response: {response}")
        cache.set(key, response, expire=60 * 60 * 24)

    return response
