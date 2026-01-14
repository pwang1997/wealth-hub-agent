import logging

from src.agents.base_agent import BaseAgent
from src.models.news_analyst import NewsAnalystOutput
from src.models.retrieval_agent import RetrievalAgentOutput

from .pipeline import (
    AggregationNode,
    NewsAnalystPipeline,
    NewsAnalystPipelineState,
    ReasoningNode,
    SynthesisNode,
)
from .prompt import get_system_prompt

logger = logging.getLogger(__name__)


class NewsAnalystAgent(BaseAgent):
    """
    Agent that aggregates and analyzes market news sentiment.
    """

    def __init__(self) -> None:
        super().__init__(
            agent_name="news_analyst_agent",
            role_description=(
                "NewsAnalystAgent is responsible for aggregating market news sentiment "
                "data and synthesizing it into a coherent narrative with per-ticker rollups."
            ),
        )

    async def process(self, retrieval_output: RetrievalAgentOutput) -> NewsAnalystOutput:
        """
        Process the retrieval output to perform news sentiment analysis using a pipeline.
        """
        logger.info(f"Starting news sentiment analysis for query: {retrieval_output.query}")

        state = NewsAnalystPipelineState(retrieval_output=retrieval_output)
        pipeline = NewsAnalystPipeline(
            nodes=[
                ReasoningNode(),
                AggregationNode(),
                SynthesisNode(),
            ]
        )

        await pipeline.run(self, state)

        if not state.analysis:
            # Fallback if pipeline failed unexpectedly
            return NewsAnalystOutput(
                query=retrieval_output.query,
                overall_sentiment_score=0.0,
                overall_sentiment_label="neutral",
                rationale="Analysis pipeline failed to produce a result.",
                news_items=retrieval_output.market_news,
                warnings=["Analysis pipeline failed to produce a result."],
            )

        return self.format_output(analysis=state.analysis, reasoning=state.objectives)

    def format_output(self, analysis: NewsAnalystOutput, reasoning: str = "") -> NewsAnalystOutput:
        """
        Finalize the NewsAnalystOutput with additional data like reasoning.
        """
        # Note: reasoning is the objectives/CoT from ReasoningNode
        # In NewsAnalystOutput we don't have a reasoning field,
        # but we could add it if desired. The rationale field
        # from SynthesisNode is the qualitative part.
        return analysis

    def get_system_prompt(self):
        return get_system_prompt()
