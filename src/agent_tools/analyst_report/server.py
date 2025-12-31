from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.agent_tools.analyst_report import mcp_server
from src.factory.mcp_server_factory import McpServerFactory


def main() -> None:
    port = int(os.getenv("RAG_MCP_PORT", "8300"))
    McpServerFactory.run_default_mcp_server(mcp_server, port)


if __name__ == "__main__":
    main()
