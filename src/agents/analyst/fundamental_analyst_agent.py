


from typing import override
from agents.base_agent import BaseAgent


class FundamentalAnalystAgent(BaseAgent):
    """
    Design note:
    This agent should be numerically constrained:
	- Prefer tool-verified calculations over free-form LLM math
	- Emit structured metrics, not prose
    
    Responsiblities:
    - Revenue growth analysis
	- Margin trends
	- Cash flow quality
	- Balance sheet strength
	- Valuation metrics (P/E, EV/EBITDA, FCF yield)
 
    Outputs:
    - Fundamental health score
	- Key strengths / weaknesses
	- Red flags (e.g., declining margins, leverage spikes)
    """
    def __init__(self) -> None:
        super().__init__(
            agent_name="fundamental_analyst_agent",
            role_description=(
                "FundamentalAnalystAgent is responsible to assess company fundamentals using EDGAR data as the authoritative source."
            ),
        )
        
    @override
    async def process():
        raise NotImplementedError("Subclasses must implement this method")

    @override
    def get_system_prompt():
        raise NotImplementedError("Subclasses must implement this method")

    @override
    async def call_mcp_tool(self, tools: list[dict]):
        raise NotImplementedError("Subclasses must implement this method")

    @override
    async def get_query_reasoning():
        raise NotImplementedError("Subclasses must implement this method")