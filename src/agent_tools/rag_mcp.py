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

from src.factory.mcp_server_factory import McpServerFactory
from src.utils.cache import cache_key
from src.utils.logging_config import configure_logging

load_dotenv()
configure_logging()

from factory.mcp_server_factory import McpServerFactory

mcp_server = McpServerFactory.create_mcp_server("AnalystReportMcpServer")

# TODO: Implement tool to retrieve analyst report on chromadb with fuzzy search

@mcp_server.tool(
    name="RetrieveAnalystReport",
    description="Retrieve analyst report for a given company using fuzzy search on ChromaDB.",
)
async def retrieve_analyst_report(company_name: str) -> Optional[str]:
    pass


if __name__ == "__main__":
    port = int(os.getenv("RAG_MCP_PORT", "8003"))
    McpServerFactory.run_default_mcp_server(mcp_server, port)
