import os
import sys
from dataclasses import dataclass
from typing import Optional

from src.agent_tools.mcp_subprocess_runner import McpServerProcessSpec, McpSubprocessRunner


@dataclass(frozen=True)
class McpLocalServerConfig:
    name: str
    script_path: str
    port_env_var: str
    default_port: int

    def server_url(self) -> str:
        port = int(os.getenv(self.port_env_var, str(self.default_port)))
        return f"http://localhost:{port}/mcp"


class MCPManager:
    def __init__(
        self,
        *,
        llm: Optional[object] = None,
        enabled: Optional[bool] = None,
        autostart: bool = True,
        repo_root: Optional[str] = None,
        servers: Optional[list[McpLocalServerConfig]] = None,
    ):
        self.llm = llm

        if enabled is None:
            enabled = os.getenv("MCP_ENABLED", "false").lower() in {"1", "true", "yes", "y"}
        self._enabled = enabled

        self._repo_root = repo_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        self._servers = servers or [
            McpLocalServerConfig(
                name="alpha_vantage",
                script_path=os.path.join(
                    self._repo_root, "src", "agent_tools", "alpha_vantage_mcp.py"
                ),
                port_env_var="SEARCH_HTTP_PORT",
                default_port=8100,
            ),
            McpLocalServerConfig(
                name="finnhub",
                script_path=os.path.join(self._repo_root, "src", "agent_tools", "finnhub_mcp.py"),
                port_env_var="FINNHUB_MCP_PORT",
                default_port=8200,
            ),
            McpLocalServerConfig(
                name="rag",
                script_path=os.path.join(
                    self._repo_root, "src", "agent_tools", "analyst_report", "server.py"
                ),
                port_env_var="RAG_MCP_PORT",
                default_port=8300,
            ),
        ]

        specs: list[McpServerProcessSpec] = []
        for server in self._servers:
            specs.append(
                McpServerProcessSpec(
                    name=server.name,
                    argv=[sys.executable, "-u", server.script_path],
                    cwd=self._repo_root,
                )
            )
        self._runner = McpSubprocessRunner(specs)

        if autostart and self._enabled:
            self.start_local_servers()

    def is_agent_mcp_enabled(self, agent_name: str) -> bool:
        _ = agent_name
        return self._enabled

    def start_local_servers(self) -> None:
        self._runner.start_all()

    def stop_local_servers(self) -> None:
        self._runner.stop_all()

    def get_server_url(self, name: str) -> str:
        for server in self._servers:
            if server.name == name:
                return server.server_url()
        raise KeyError(f"Unknown MCP server: {name}")
