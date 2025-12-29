from abc import ABC, abstractmethod
from typing import Any

from src.agent_tools.mcp_manager import MCPManager


class BaseAgent(ABC):
    def __init__(self, agent_name: str, mcp_manager: MCPManager, role_description: str = ""):
        self.agent_name = agent_name
        self.mcp_manager = mcp_manager
        self.role_description = role_description

        self.llm = mcp_manager.llm

        self.mcp_enabled = mcp_manager.is_agent_mcp_enabled(agent_name)

        self.available_tools = []

        self.agent = None

    @abstractmethod
    def call_mcp_tool(self, tool_name: str, tool_input: dict) -> Any:
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    @abstractmethod
    async def process(self, state) -> Any:
        pass
