import os

from fastapi.logger import logger

from src.agent_tools.alpha_vantage.alpha_vantage_mcp import (
    mcp_server,
)
from src.factory.mcp_server_factory import McpServerFactory

if __name__ == "__main__":
    logger.info("Running Alpha Vantage Tool as search tool")
    port = int(os.getenv("SEARCH_HTTP_PORT", "8100"))
    McpServerFactory.run_default_mcp_server(mcp_server, port)
