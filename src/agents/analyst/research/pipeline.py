import json
import logging
import re
from dataclasses import dataclass

from clients.model_client import ModelClient
from src.agents.base_agent import BaseAgent
from src.agents.base_pipeline import BasePipeline, BasePipelineNode
from src.models.fundamental_analyst import FundamentalAnalystOutput
from src.models.news_analyst import NewsAnalystOutput
from src.models.research_analyst import ResearchAnalystOutput

from .prompt import format_synthesis_prompt

logger = logging.getLogger(__name__)


@dataclass
class ResearchAnalystPipelineState:
    fundamental_output: FundamentalAnalystOutput
    news_output: NewsAnalystOutput
    internal_thought: str = ""
    objectives: str = ""
    analysis: ResearchAnalystOutput | None = None
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class ResearchAnalystPipelineNode(BasePipelineNode[ResearchAnalystPipelineState]):
    """Base node for research analyst pipeline."""


class ResearchAnalystPipeline(BasePipeline[ResearchAnalystPipelineState]):
    """Orchestrator for research analysis."""

    def __init__(
        self,
        model_client: ModelClient,
        nodes: list[BasePipelineNode[ResearchAnalystPipelineState]] | None = None,
    ):
        super().__init__(nodes)
        self.model_client = model_client


class ReasoningNode(ResearchAnalystPipelineNode):
    async def run(self, agent: BaseAgent, state: ResearchAnalystPipelineState) -> None:
        if not isinstance(agent.pipeline, ResearchAnalystPipeline):
            raise RuntimeError("ReasoningNode must be run within a ResearchAnalystPipeline")

        prompt = (
            f"You are {agent.agent_name}. {agent.role_description}\n"
            f"Ticker: {state.fundamental_output.ticker}\n"
            "Identify the key themes and potential conflicts between the fundamental analysis and market sentiment to prepare a synthesized report.\n"
            "Use the following format:\n"
            "<thought>\n[Your internal chain of thought about the composition strategy]\n</thought>\n"
            "<objectives>\n[Concise objectives for the final synthesized analysis report]\n</objectives>"
        )

        content = agent.pipeline.model_client.generate_completion(prompt=prompt)

        def extract_tag(text: str, tag: str) -> str:
            match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
            return match.group(1).strip() if match else ""

        state.internal_thought = extract_tag(content, "thought")
        state.objectives = extract_tag(content, "objectives")

        if not state.objectives and content:
            state.objectives = content

        logger.info(f"Research ReasoningNode completed. Objectives: {state.objectives[:100]}...")


class SynthesisNode(ResearchAnalystPipelineNode):
    async def run(self, agent: BaseAgent, state: ResearchAnalystPipelineState) -> None:
        if not isinstance(agent.pipeline, ResearchAnalystPipeline):
            raise RuntimeError("SynthesisNode must be run within a ResearchAnalystPipeline")

        prompt = format_synthesis_prompt(
            ticker=state.fundamental_output.ticker,
            fundamental_summary=state.fundamental_output.summary,
            fundamental_score=state.fundamental_output.health_score,
            news_rationale=state.news_output.rationale,
            news_score=state.news_output.overall_sentiment_score,
            objectives=state.objectives,
        )

        content = agent.pipeline.model_client.generate_completion(
            prompt=prompt,
            system_prompt=agent.get_system_prompt(),
            response_format={"type": "json_object"},
        )
        try:
            parsed = json.loads(content)
            parsed["ticker"] = state.fundamental_output.ticker
            # Ensure required fields exist in parsed if LLM missed them
            if "warnings" not in parsed:
                parsed["warnings"] = state.warnings

            state.analysis = ResearchAnalystOutput.model_validate(parsed)
            # Link back the inputs
            state.analysis.fundamental_analysis = state.fundamental_output
            state.analysis.news_analysis = state.news_output

        except Exception as exc:
            logger.error(f"Failed to validate Research LLM response: {exc}")
            state.analysis = ResearchAnalystOutput(
                ticker=state.fundamental_output.ticker,
                composed_analysis=f"Failed to synthesize analysis: {exc}",
                warnings=[*state.warnings, str(exc)],
            )

        logger.info(f"SynthesisNode completed for {state.fundamental_output.ticker}")
