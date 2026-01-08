import os

from fastapi.logger import logger

from src.agent_tools.finnhub.finnhub_mcp import mcp_server
from src.factory.mcp_server_factory import McpServerFactory

if __name__ == "__main__":
    logger.info("Running Finnhub Tool as search tool")
    port = int(os.getenv("FINNHUB_MCP_PORT", "8200"))
    McpServerFactory.run_default_mcp_server(mcp_server, port)
