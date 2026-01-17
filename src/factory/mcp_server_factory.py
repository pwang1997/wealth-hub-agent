import os

from fastapi.middleware import Middleware
from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware


class McpServerFactory:
    @staticmethod
    def create_mcp_server(mcp_name: str, middleware: list[Middleware] | None = None) -> FastMCP:
        mcp = FastMCP(mcp_name, middleware=middleware)
        return mcp

    def _create_local_mcp_cors_middleware(self) -> Middleware:
        return Middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all origins; use specific origins for security
            allow_methods=["*"],
            allow_headers=[
                "mcp-protocol-version",
                "mcp-session-id",
                "Authorization",
                "Content-Type",
            ],
            expose_headers=["mcp-session-id"],
        )

    @staticmethod
    def run_default_mcp_server(mcp: FastMCP, port: str, transport: str = "streamable-http"):
        host = os.getenv("MCP_HOST", "0.0.0.0")
        mcp.run(transport=transport, port=port, host=host)
