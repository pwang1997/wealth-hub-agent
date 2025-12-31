from __future__ import annotations

import os
import sys

from diskcache import Cache
from dotenv import load_dotenv


def _ensure_repo_root_on_path() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


_ensure_repo_root_on_path()

from src.agent_tools.edgar.search_reports import register_tools as register_edgar_tools  # noqa: E402
from src.agent_tools.rag.retrieve_report import register_tools as register_rag_tools  # noqa: E402
from src.factory.mcp_server_factory import McpServerFactory  # noqa: E402
from src.utils.logging_config import configure_logging  # noqa: E402

load_dotenv()
configure_logging()

mcp_server = McpServerFactory.create_mcp_server("AnalystReportMcpServer")
cache = Cache("./.rag_mcp_cache")

register_rag_tools(mcp_server, cache=cache)
register_edgar_tools(mcp_server)

