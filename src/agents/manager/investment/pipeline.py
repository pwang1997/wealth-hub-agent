import json
import logging
import os
import re
from dataclasses import dataclass

from openai import OpenAI

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


class ReasoningNode(InvestmentManagerPipelineNode):
    async def run(self, agent: BaseAgent, state: InvestmentManagerPipelineState) -> None:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for investment decision")

        client = OpenAI(api_key=openai_api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        prompt = (
            f"You are {agent.agent_name}. {agent.role_description}\n"
            f"Ticker: {state.ticker}\n"
            "Identify the key factors from the research report that will drive the final investment decision.\n"
            "Use the following format:\n"
            "<thought>\n[Your internal chain of thought about the decision strategy]\n</thought>\n"
            "<objectives>\n[Concise objectives for the final investment decision and rationale]\n</objectives>"
        )

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content or ""

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
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for investment decision")

        client = OpenAI(api_key=openai_api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        user_prompt = (
            f"Ticker: {state.ticker}\n"
            "Research Report:\n"
            f"{state.research_output.composed_analysis}\n\n"
            "Decision Objectives:\n"
            f"{state.objectives}\n\n"
            "Provide the final investment decision in JSON format."
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": agent.get_system_prompt()},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
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
