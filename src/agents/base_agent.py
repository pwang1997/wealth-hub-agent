from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Any, Callable

from fastmcp import Client as MCPClient
from fastmcp.client.transports import StreamableHttpTransport

MetadataFactory = Callable[..., Any]


def _load_mcp_tool_timeout_seconds() -> float:
    raw_timeout = os.getenv("MCP_TOOL_TIMEOUT_SECONDS")
    if not raw_timeout:
        return 120.0
    try:
        return float(raw_timeout.strip())
    except ValueError:
        return 120.0


DEFAULT_MCP_TOOL_TIMEOUT_SECONDS = _load_mcp_tool_timeout_seconds()


class BaseAgent(ABC):
    def __init__(self, agent_name: str, role_description: str):
        self.agent_name = agent_name
        self.role_description = role_description

    @abstractmethod
    async def process():
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def get_system_prompt():
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    async def call_mcp_tool(self, tools: list[dict]):
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    async def get_query_reasoning():
        raise NotImplementedError("Subclasses must implement this method")

    def format_output(self):
        raise NotImplementedError("Subclasses must implement this method")

    @staticmethod
    async def _call_mcp_tool(
        server_url: str,
        tool_name: str,
        tool_input: dict[str, Any],
        timeout: timedelta | float | int | None = None,
    ) -> Any:
        transport = StreamableHttpTransport(server_url, headers={"accept-encoding": "identity"})
        resolved_timeout = (
            timeout if timeout is not None else DEFAULT_MCP_TOOL_TIMEOUT_SECONDS
        )
        async with MCPClient(transport, timeout=resolved_timeout) as client:
            return await client.call_tool(tool_name, tool_input)

    @staticmethod
    def _build_tool_metadata(
        tool_name: str,
        start_time: str,
        start_monotonic: float,
        metadata_factory: MetadataFactory | None = None,
        warnings: list[str] | None = None,
    ) -> Any:
        end_time = datetime.now(timezone.utc).isoformat()
        duration_ms = int((time.monotonic() - start_monotonic) * 1000)
        builder = metadata_factory if metadata_factory is not None else lambda **kwargs: kwargs
        return builder(
            tool=tool_name,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            warnings=warnings or [],
        )

    @staticmethod
    def _normalize_news_response(response: Any) -> list[dict[str, Any]]:
        if isinstance(response, list):
            return [entry for entry in response if isinstance(entry, dict)]
        if not isinstance(response, dict):
            return []
        for candidate in ("news", "items", "feed", "data"):
            block = response.get(candidate)
            if isinstance(block, list):
                return [entry for entry in block if isinstance(entry, dict)]
        return []
