import json
import logging
import re
from dataclasses import dataclass

from clients.model_client import ModelClient
from src.agents.base_agent import BaseAgent
from src.agents.base_pipeline import BasePipeline, BasePipelineNode
from src.models.investment_manager import InvestmentManagerOutput
from src.models.research_analyst import ResearchAnalystOutput

logger = logging.getLogger(__name__)


@dataclass
class InvestmentManagerPipelineState:
    ticker: str
    research_output: ResearchAnalystOutput
    internal_thought: str = ""
    objectives: str = ""
    decision_output: InvestmentManagerOutput | None = None
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class InvestmentManagerPipelineNode(BasePipelineNode[InvestmentManagerPipelineState]):
    """Base node for investment manager pipeline."""


class InvestmentManagerPipeline(BasePipeline[InvestmentManagerPipelineState]):
    """Orchestrator for investment decision making."""

    def __init__(
        self,
        model_client: ModelClient,
        nodes: list[BasePipelineNode[InvestmentManagerPipelineState]] | None = None,
    ):
        super().__init__(nodes)
        self.model_client = model_client


class ReasoningNode(InvestmentManagerPipelineNode):
    async def run(self, agent: BaseAgent, state: InvestmentManagerPipelineState) -> None:
        if not isinstance(agent.pipeline, InvestmentManagerPipeline):
            raise RuntimeError("ReasoningNode must be run within an InvestmentManagerPipeline")

        prompt = (
            f"You are {agent.agent_name}. {agent.role_description}\n"
            f"Ticker: {state.ticker}\n"
            "Identify the key factors from the research report that will drive the final investment decision.\n"
            "Use the following format:\n"
            "<thought>\n[Your internal chain of thought about the decision strategy]\n</thought>\n"
            "<objectives>\n[Concise objectives for the final investment decision and rationale]\n</objectives>"
        )

        content = agent.pipeline.model_client.generate_completion(prompt=prompt)

        def extract_tag(text: str, tag: str) -> str:
            match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
            return match.group(1).strip() if match else ""

        state.internal_thought = extract_tag(content, "thought")
        state.objectives = extract_tag(content, "objectives")

        if not state.objectives and content:
            state.objectives = content

        logger.info(f"Investment Manager ReasoningNode completed for {state.ticker}")


class DecisionNode(InvestmentManagerPipelineNode):
    async def run(self, agent: BaseAgent, state: InvestmentManagerPipelineState) -> None:
        if not isinstance(agent.pipeline, InvestmentManagerPipeline):
            raise RuntimeError("DecisionNode must be run within an InvestmentManagerPipeline")

        user_prompt = (
            f"Ticker: {state.ticker}\n"
            "Research Report:\n"
            f"{state.research_output.composed_analysis}\n\n"
            "Decision Objectives:\n"
            f"{state.objectives}\n\n"
            "Provide the final investment decision in JSON format."
        )

        content = agent.pipeline.model_client.generate_completion(
            prompt=user_prompt,
            system_prompt=agent.get_system_prompt(),
            response_format={"type": "json_object"},
        )
        try:
            parsed = json.loads(content)
            parsed["ticker"] = state.ticker
            parsed["reasoning"] = state.objectives

            state.decision_output = InvestmentManagerOutput.model_validate(parsed)

        except Exception as exc:
            logger.error(f"Failed to validate Investment Manager LLM response: {exc}")
            state.decision_output = InvestmentManagerOutput(
                ticker=state.ticker,
                decision="hold",
                rationale=f"Failed to reach a decision: {exc}",
                confidence=0.0,
                reasoning=state.objectives,
            )

        logger.info(f"DecisionNode completed for {state.ticker}")
