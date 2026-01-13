from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass, field

from openai import OpenAI

from src.agents.analyst.prompt import format_user_prompt, get_system_prompt
from src.agents.base_agent import BaseAgent
from src.agents.base_pipeline import BasePipeline, BasePipelineNode
from src.models.fundamental_analyst import FundamentalAnalystOutput
from src.models.fundamentals import FinancialReportLineItem, FundamentalDTO
from src.models.retrieval_agent import RetrievalAgentOutput

logger = logging.getLogger(__name__)


@dataclass
class FundamentalAnalystPipelineState:
    retrieval_output: RetrievalAgentOutput
    metrics_summary: str = ""
    analysis: FundamentalAnalystOutput | None = None
    citations: list[str] = field(default_factory=list)


class FundamentalAnalystPipelineNode(BasePipelineNode[FundamentalAnalystPipelineState]):
    """Base node for fundamental analyst pipeline."""


class FundamentalAnalystPipeline(BasePipeline[FundamentalAnalystPipelineState]):
    """Orchestrator for fundamental analysis."""


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
            state.metrics_summary += (
                f"\n\nAdditional Context from Filings:\n{state.retrieval_output.answer}"
            )

        logger.info(
            f"CalculateMetricsNode completed for {state.retrieval_output.edgar_filings.ticker}"
        )


class AnalyzeWithLLMNode(FundamentalAnalystPipelineNode):
    async def run(self, agent: BaseAgent, state: FundamentalAnalystPipelineState) -> None:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for fundamental analysis")

        client = OpenAI(api_key=openai_api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        ticker = state.retrieval_output.edgar_filings.ticker
        company_name = state.retrieval_output.edgar_filings.cik  # cik as fallback

        system_prompt = get_system_prompt()
        user_prompt = format_user_prompt(
            state.retrieval_output.query, state.metrics_summary, company_name, ticker
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
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
