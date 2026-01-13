import os
import sys
from typing import Any, Literal

from fastapi.logger import logger

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.agent_tools.alpha_vantage.alpha_vantage_mcp_impl import (
    REMOTE_MCP_SERVER_URL,
    company_overview_impl,
    discover_remote_tools_impl,
    fundamentals_impl,
    news_sentiment_impl,
)
from src.factory.mcp_server_factory import McpServerFactory
from src.models.news_sentiments import NewsSentimentResponse
from src.utils.date_utils import since_last_week

mcp_server = McpServerFactory.create_mcp_server("AlphaVantageMcpServer")


@mcp_server.tool()
async def discover_remote_tools(server_url: str = REMOTE_MCP_SERVER_URL) -> list[dict[str, Any]]:
    """Discover and return the tools exposed by a remote MCP server.

    Returns a list of tool descriptors (typically containing `name`, `description`, and `inputSchema`)
    that can be used by planning agents to mirror remote tool signatures.
    """

    return await discover_remote_tools_impl(server_url)


@mcp_server.tool()
async def news_sentiment(
    tickers: str = "",
    limit: int = 10,
    time_from: str = since_last_week(),
) -> NewsSentimentResponse:
    """Proxy to the remote Alpha Vantage `NEWS_SENTIMENT` tool."""

    return await news_sentiment_impl(tickers=tickers, limit=limit, time_from=time_from)


@mcp_server.tool()
async def company_overview(symbol: str) -> Any:
    """Proxy to the remote Alpha Vantage `COMPANY_OVERVIEW` tool."""

    return await company_overview_impl(symbol)


@mcp_server.tool()
async def fundamentals(
    symbol: str, statement_type: Literal["INCOMSE_STATEMENT", "BALANCE_SHEET", "CASH_FLOW"]
) -> Any:
    """Proxy to the remote Alpha Vantage fundamentals tool."""
    return await fundamentals_impl(symbol, statement_type)


if __name__ == "__main__":
    # Run with streamable-http, support configuring host and port through environment variables to avoid conflicts
    logger.info("Running Alpha Vantage Tool as search tool")
    port = int(os.getenv("SEARCH_HTTP_PORT", "8100"))
    McpServerFactory.run_default_mcp_server(mcp_server, port)
