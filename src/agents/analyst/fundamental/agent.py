import logging
from typing import override

from src.agents.analyst.fundamental.prompt import get_system_prompt
from src.agents.base_agent import BaseAgent
from src.models.fundamental_analyst import FundamentalAnalystOutput
from src.models.retrieval_agent import RetrievalAgentOutput

from .pipeline import (
    AnalyzeWithLLMNode,
    CalculateMetricsNode,
    FundamentalAnalystPipeline,
    FundamentalAnalystPipelineState,
)

logger = logging.getLogger(__name__)


class FundamentalAnalystAgent(BaseAgent):
    """
    Agent that performs fundamental analysis on a company based on retrieval output.
    """

    def __init__(self) -> None:
        super().__init__(
            agent_name="fundamental_analyst_agent",
            role_description=(
                "FundamentalAnalystAgent is responsible to assess company fundamentals "
                "using EDGAR data as the authoritative source."
            ),
        )

    @override
    async def process(self, retrieval_output: RetrievalAgentOutput) -> FundamentalAnalystOutput:  # type: ignore[override]
        """
        Process the retrieval output to perform fundamental analysis using a pipeline.
        """
        logger.info(
            f"Starting fundamental analysis for ticker: {retrieval_output.edgar_filings.ticker}"
        )

        state = FundamentalAnalystPipelineState(retrieval_output=retrieval_output)
        pipeline = FundamentalAnalystPipeline(
            nodes=[
                CalculateMetricsNode(),
                AnalyzeWithLLMNode(),
            ]
        )

        await pipeline.run(self, state)

        if not state.analysis:
            # Fallback if pipeline failed unexpectedly
            return FundamentalAnalystOutput(
                ticker=retrieval_output.edgar_filings.ticker,
                health_score=0,
                summary="Analysis pipeline failed to produce a result.",
                citations=[],
            )

        return self.format_output(analysis=state.analysis, citations=state.citations)

    @override
    def format_output(
        self, analysis: FundamentalAnalystOutput, citations: list[str]
    ) -> FundamentalAnalystOutput:
        """
        Finalize the FundamentalAnalystOutput with additional data like citations.
        """
        analysis.citations = citations
        return analysis

    @override
    def get_system_prompt(self):
        return get_system_prompt()

    @override
    async def get_query_reasoning(self):
        return ""
