import logging
from typing import override

from src.agents.base_agent import BaseAgent
from src.models.research_analyst import ResearchAnalystOutput
from src.models.fundamental_analyst import FundamentalAnalystOutput
from src.models.news_analyst import NewsAnalystOutput

from .pipeline import (
    ResearchAnalystPipeline,
    ResearchAnalystPipelineState,
    ReasoningNode,
    SynthesisNode,
)
from .prompt import get_system_prompt

logger = logging.getLogger(__name__)


class ResearchAnalystAgent(BaseAgent):
    """
    Agent that composes fundamental and news analysis results into a unified report.
    """

    def __init__(self) -> None:
        super().__init__(
            agent_name="research_analyst_agent",
            role_description=(
                "ResearchAnalystAgent is responsible for synthesizing fundamental "
                "financial health data and market news sentiment into a cohesive "
                "composed analysis report."
            ),
        )

    async def process(
        self, fundamental_output: FundamentalAnalystOutput, news_output: NewsAnalystOutput
    ) -> ResearchAnalystOutput:
        """
        Process fundamental and news outputs to produce a synthesized report.
        """
        logger.info(f"Starting research composition for ticker: {fundamental_output.ticker}")

        state = ResearchAnalystPipelineState(
            fundamental_output=fundamental_output, news_output=news_output
        )

        pipeline = ResearchAnalystPipeline(
            nodes=[
                ReasoningNode(),
                SynthesisNode(),
            ]
        )

        await pipeline.run(self, state)

        if not state.analysis:
            return ResearchAnalystOutput(
                ticker=fundamental_output.ticker,
                composed_analysis="Research pipeline failed to produce a result.",
                warnings=["Pipeline failure"],
            )

        return self.format_output(analysis=state.analysis, reasoning=state.objectives)

    def format_output(
        self, analysis: ResearchAnalystOutput, reasoning: str = ""
    ) -> ResearchAnalystOutput:
        """
        Finalize the ResearchAnalystOutput with additional data.
        """
        # We could add the reasoning/CoT to a field if we extend the model
        return analysis

    @override
    def get_system_prompt(self) -> str:
        return get_system_prompt()
