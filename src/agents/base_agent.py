

from abc import ABC, abstractmethod


class BaseAgent(ABC):
    
    def __init__(self, agent_name : str, role_description: str):
        self.agent_name = agent_name
        self.role_description = role_description
        
    @abstractmethod
    async def process():
        pass
    
    @abstractmethod
    def get_system_prompt():
        pass
    
    @abstractmethod
    async def call_mcp_tool(self, tools : list[dict]):
        pass
    
    async def get_query_reasoning():
        pass
    
    def format_output(self):
        pass