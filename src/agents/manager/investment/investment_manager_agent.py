import logging
from typing import override

from src.agents.base_agent import BaseAgent
from src.models.investment_manager import InvestmentManagerOutput
from src.models.research_analyst import ResearchAnalystOutput

from .pipeline import (
    DecisionNode,
    InvestmentManagerPipeline,
    InvestmentManagerPipelineState,
    ReasoningNode,
)
from .prompt import get_system_prompt

logger = logging.getLogger(__name__)


class InvestmentManagerAgent(BaseAgent):
    """
    Agent that makes the final investment decision based on synthesized research.
    """

    def __init__(self) -> None:
        super().__init__(
            agent_name="investment_manager_agent",
            role_description=(
                "InvestmentManagerAgent is responsible for making the final investment "
                "decision by weighing fundamental health and market news sentiment "
                "contextualized in a synthesized research report."
            ),
        )

    async def process(self, research_output: ResearchAnalystOutput) -> InvestmentManagerOutput:
        """
        Process research output to produce an investment decision.
        """
        logger.info(f"Starting investment decision for ticker: {research_output.ticker}")

        state = InvestmentManagerPipelineState(
            ticker=research_output.ticker, research_output=research_output
        )

        pipeline = InvestmentManagerPipeline(
            nodes=[
                ReasoningNode(),
                DecisionNode(),
            ]
        )

        await pipeline.run(self, state)

        if not state.decision_output:
            decision_output = InvestmentManagerOutput(
                ticker=research_output.ticker,
                decision="hold",
                rationale="Investment pipeline failed to produce a decision.",
                confidence=0.0,
                reasoning=state.objectives,
            )
        else:
            decision_output = state.decision_output

        return self.format_output(decision_output=decision_output)

    @override
    def format_output(self, decision_output: InvestmentManagerOutput) -> InvestmentManagerOutput:
        """
        Finalize the InvestmentManagerOutput.
        """
        return decision_output

    @override
    def get_system_prompt(self) -> str:
        return get_system_prompt()
