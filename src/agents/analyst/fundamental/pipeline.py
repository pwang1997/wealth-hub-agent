from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from clients.model_client import ModelClient
from src.agents.base_agent import BaseAgent
from src.agents.base_pipeline import BasePipeline, BasePipelineNode
from src.models.fundamental_analyst import FundamentalAnalystOutput
from src.models.fundamentals import FinancialReportLineItem
from src.models.retrieval_agent import RetrievalAgentOutput

from .prompt import format_user_prompt, get_system_prompt

logger = logging.getLogger(__name__)


@dataclass
class FundamentalAnalystPipelineState:
    retrieval_output: RetrievalAgentOutput
    metrics_summary: str = ""
    analysis: FundamentalAnalystOutput | None = None
    citations: list[str] = field(default_factory=list)
    internal_thought: str = ""
    objectives: str = ""


class FundamentalAnalystPipelineNode(BasePipelineNode[FundamentalAnalystPipelineState]):
    """Base node for fundamental analyst pipeline."""


class FundamentalAnalystPipeline(BasePipeline[FundamentalAnalystPipelineState]):
    """Orchestrator for fundamental analysis."""

    def __init__(
        self,
        model_client: ModelClient,
        nodes: list[BasePipelineNode[FundamentalAnalystPipelineState]] | None = None,
    ):
        super().__init__(nodes)
        self.model_client = model_client


class ReasoningNode(FundamentalAnalystPipelineNode):
    async def run(self, agent: BaseAgent, state: FundamentalAnalystPipelineState) -> None:
        if not isinstance(agent.pipeline, FundamentalAnalystPipeline):
            raise RuntimeError("ReasoningNode must be run within a FundamentalAnalystPipeline")

        prompt = (
            f"You are {agent.agent_name}. {agent.role_description}\n"
            f"User Query: {state.retrieval_output.query}\n"
            "Identify your specific responsibilities and extract the key objectives for this analysis.\n"
            "Use the following format:\n"
            "<thought>\n[Your internal chain of thought about the query and the agent's role]\n</thought>\n"
            "<objectives>\n[Concise objectives for the rest of the pipeline]\n</objectives>"
        )

        content = agent.pipeline.model_client.generate_completion(prompt=prompt)

        def extract_tag(text: str, tag: str) -> str:
            # Use a non-greedy match to find content between the first pair of tags
            match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
            return match.group(1).strip() if match else ""

        state.internal_thought = extract_tag(content, "thought")
        state.objectives = extract_tag(content, "objectives")

        # Fallback if tags are missing
        if not state.objectives and content:
            state.objectives = content

        logger.info(f"ReasoningNode completed. Objectives: {state.objectives[:100]}...")


class CalculateMetricsNode(FundamentalAnalystPipelineNode):
    async def run(self, agent: BaseAgent, state: FundamentalAnalystPipelineState) -> None:
        reports = state.retrieval_output.financial_reports
        if not reports or not reports.data:
            state.metrics_summary = "No structured financial reports available for calculation."
            return

        summary_lines = []
        # Sort data by year and quarter to show trends
        sorted_entries = sorted(reports.data, key=lambda x: (x.year, x.quarter))

        for entry in sorted_entries:
            period = f"FY{entry.year}Q{entry.quarter}"
            summary_lines.append(
                f"--- Period: {period} (Form {entry.form}, Filed {entry.filed_date}) ---"
            )

            # Helper to find value by common labels/concepts
            def get_val(items: list[FinancialReportLineItem], *concepts: str) -> float | None:
                for concept in concepts:
                    for item in items:
                        if (
                            item.concept.lower() == concept.lower()
                            or item.label.lower() == concept.lower()
                        ):
                            return item.value
                return None

            # Revenue
            revenue = get_val(
                entry.income_statement,
                "Revenues",
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet",
                "SalesRevenueGoodsNet",
            )
            # Net Income
            net_income = get_val(
                entry.income_statement,
                "NetIncomeLoss",
                "NetIncomeLossAvailableToCommonStockholdersBasic",
            )
            # Operating Income
            op_income = get_val(entry.income_statement, "OperatingIncomeLoss")
            # Operating Cash Flow
            ocf = get_val(entry.cash_flow, "NetCashProvidedByUsedInOperatingActivities")

            # Calculate Margins
            if revenue and revenue != 0:
                if op_income is not None:
                    summary_lines.append(f"Operating Margin: {(op_income / revenue) * 100:.2f}%")
                if net_income is not None:
                    summary_lines.append(f"Net Margin: {(net_income / revenue) * 100:.2f}%")

            summary_lines.append(f"Revenue: {revenue}")
            summary_lines.append(f"Net Income: {net_income}")
            summary_lines.append(f"Operating Cash Flow: {ocf}")

            # Cash Flow Quality
            if net_income and net_income != 0 and ocf is not None:
                summary_lines.append(f"OCF / Net Income Ratio: {ocf / net_income:.2f}")

        state.metrics_summary = "\n".join(summary_lines)

        # Add extra context from RAG answer (prose from filing)
        if state.retrieval_output.answer:
            summary_lines.append("\n### Filings Context")
            summary_lines.append(state.retrieval_output.answer)

        # Add news sentiment context
        if state.retrieval_output.market_news:
            summary_lines.append("\n### Recent Market News")
            for item in state.retrieval_output.market_news:
                summary_lines.append(
                    f"- {item.title} ({item.source}) - Sentiment: {item.overall_sentiment_label}"
                )

        state.metrics_summary = "\n".join(summary_lines)

        logger.info(
            f"CalculateMetricsNode completed for {state.retrieval_output.edgar_filings.ticker}"
        )


class AnalyzeWithLLMNode(FundamentalAnalystPipelineNode):
    async def run(self, agent: BaseAgent, state: FundamentalAnalystPipelineState) -> None:
        if not isinstance(agent.pipeline, FundamentalAnalystPipeline):
            raise RuntimeError("AnalyzeWithLLMNode must be run within a FundamentalAnalystPipeline")

        ticker = state.retrieval_output.edgar_filings.ticker
        company_name = state.retrieval_output.edgar_filings.cik  # cik as fallback

        system_prompt = get_system_prompt()
        user_prompt = format_user_prompt(
            state.retrieval_output.query,
            state.metrics_summary,
            company_name,
            ticker,
            state.objectives,
        )

        content = agent.pipeline.model_client.generate_completion(
            prompt=user_prompt,
            system_prompt=system_prompt,
            response_format={"type": "json_object"},
        )
        try:
            parsed = json.loads(content)
            parsed["ticker"] = ticker
            state.analysis = FundamentalAnalystOutput.model_validate(parsed)
            # Add citations from edgar filings
            state.citations = [
                f.accession_number for f in state.retrieval_output.edgar_filings.filings
            ]
        except Exception as exc:
            logger.error(f"Failed to validate LLM response against model: {exc}")
            state.analysis = FundamentalAnalystOutput(
                ticker=ticker,
                health_score=0,
                summary=f"Failed to generate valid analysis: {exc}",
                citations=[],
            )

        logger.info(f"AnalyzeWithLLMNode completed for {ticker}")
