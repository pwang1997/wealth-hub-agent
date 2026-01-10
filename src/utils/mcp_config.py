import os


class McpConfig:
    rag_mcp_url = os.getenv("RAG_MCP_URL", "http://localhost:8300/mcp")
    alpha_vantage_url = os.getenv("ALPHA_VANTAGE_MCP_URL", "http://localhost:8100/mcp")
    finnhub_mcp_url = os.getenv("FINNHUB_MCP_URL", "http://localhost:8200/mcp")
