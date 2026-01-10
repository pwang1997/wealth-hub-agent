import os
import sys
from typing import Any, Literal

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.agent_tools.finnhub.finnhub_mcp_impl import (
    company_news_impl,
    company_peer_impl,
    get_financial_reports_impl,
)
from src.factory.mcp_server_factory import McpServerFactory
from src.models.fundamentals import FundamentalDTO

mcp_server = McpServerFactory.create_mcp_server("FinnhubMcpServer")


@mcp_server.tool()
async def get_company_news(
    symbol: str,
    from_date: str | None = None,
    to_date: str | None = None,
) -> Any:
    return await company_news_impl(symbol, from_date, to_date)


@mcp_server.tool()
async def get_company_peer(symbol: str, grouping: str | None = None) -> Any:
    return await company_peer_impl(symbol, grouping)


@mcp_server.tool()
async def get_financial_reports(
    symbol: str,
    access_number: str | None,
    from_date: str | None,
    freq: Literal["annual", "quarterly"] = "annual",
) -> FundamentalDTO:
    return await get_financial_reports_impl(symbol, access_number, from_date, freq)


if __name__ == "__main__":
    port = int(os.getenv("FINNHUB_MCP_PORT", "8200"))
    McpServerFactory.run_default_mcp_server(mcp_server, port)
