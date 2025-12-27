import os
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv
from fastapi.logger import logger
from fastmcp import Client as MCPClient
from fastmcp.client.transports import StreamableHttpTransport

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from src.factory.mcp_server_factory import McpServerFactory

load_dotenv()

REMOTE_MCP_SERVER_URL = (
    f"https://mcp.alphavantage.co/mcp?apikey={os.getenv('ALPHA_VANTAGE_API_KEY', 'demo')}"
)

mcp_server = McpServerFactory.create_mcp_server("AlphaVantageMcpServer")


def _create_remote_client(server_url: str) -> MCPClient:
    # Some MCP servers respond with compressed bodies that the underlying client may not
    # be able to decode (e.g., `Content-Encoding: br`). Force an identity encoding so the
    # response body is plain JSON.
    transport = StreamableHttpTransport(server_url, headers={"accept-encoding": "identity"})
    return MCPClient(transport)


async def _call_remote_tool(
    tool_name: str, tool_input: Dict[str, Any], server_url: str = REMOTE_MCP_SERVER_URL
) -> Any:
    async with _create_remote_client(server_url) as client:
        return await client.call_tool(tool_name, tool_input)


def _serialize_mcp_tool(tool: Any) -> Dict[str, Any]:
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


@mcp_server.tool()
async def discover_remote_tools(server_url: str = REMOTE_MCP_SERVER_URL) -> List[Dict[str, Any]]:
    """Discover and return the tools exposed by a remote MCP server.

    Returns a list of tool descriptors (typically containing `name`, `description`, and `inputSchema`)
    that can be used by planning agents to mirror remote tool signatures.
    """
    async with _create_remote_client(server_url) as client:
        tools = await client.list_tools()
    if tools is None:
        return []
    return [_serialize_mcp_tool(tool) for tool in tools]


@mcp_server.tool()
async def news_sentiment(
    tickers: str = "",
    limit: int = 0,
) -> Any:
    """Proxy to the remote Alpha Vantage `NEWS_SENTIMENT` tool."""
    tool_input: Dict[str, Any] = {}
    if tickers:
        tool_input["tickers"] = tickers
    if limit:
        tool_input["limit"] = limit

    return await _call_remote_tool("NEWS_SENTIMENT", tool_input, server_url=REMOTE_MCP_SERVER_URL)


@mcp_server.tool()
async def company_overview(symbol: str) -> Any:
    """Proxy to the remote Alpha Vantage `COMPANY_OVERVIEW` tool."""
    if not symbol:
        raise ValueError("symbol is required")
    return await _call_remote_tool("COMPANY_OVERVIEW", {"symbol": symbol}, server_url=REMOTE_MCP_SERVER_URL)

if __name__ == "__main__":
    # Run with streamable-http, support configuring host and port through environment variables to avoid conflicts
    logger.info("Running Alpha Vantage Tool as search tool")
    port = int(os.getenv("SEARCH_HTTP_PORT", "8001"))
    McpServerFactory.run_default_mcp_server(mcp_server, port)