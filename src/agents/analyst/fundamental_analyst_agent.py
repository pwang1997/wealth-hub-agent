import json
import logging
import os
from typing import Any, override

from openai import OpenAI

from src.agents.base_agent import BaseAgent
from src.models.fundamental_analyst import FundamentalAnalystOutput
from src.models.fundamentals import FinancialReportLineItem, FundamentalDTO
from src.models.retrieval_agent import RetrievalAgentOutput

from .prompt import format_user_prompt, get_system_prompt

logger = logging.getLogger(__name__)


class FundamentalAnalystAgent(BaseAgent):
    """
    FundamentalAnalystAgent assesses company fundamentals using data from RetrievalAgent.
    """

    def __init__(self) -> None:
        super().__init__(
            agent_name="fundamental_analyst_agent",
            role_description=(
                "FundamentalAnalystAgent is responsible to assess company fundamentals using EDGAR data as the authoritative source."
            ),
        )

    @override
    async def process(self, retrieval_output: RetrievalAgentOutput) -> FundamentalAnalystOutput:  # type: ignore[override]
        """
        Process the retrieval output to perform fundamental analysis.
        """
        logger.info(
            f"Starting fundamental analysis for ticker: {retrieval_output.edgar_filings.ticker}"
        )

        # 1. Calculate metrics from financial reports
        metrics_summary = self._calculate_metrics(retrieval_output.financial_reports)

        # 2. Add extra context from RAG answer (prose from filing)
        if retrieval_output.answer:
            metrics_summary += f"\n\nAdditional Context from Filings:\n{retrieval_output.answer}"

        # 3. Call LLM for structured analysis
        analysis = await self._analyze_with_llm(
            query=retrieval_output.query,
            metrics_summary=metrics_summary,
            ticker=retrieval_output.edgar_filings.ticker,
            company_name=retrieval_output.edgar_filings.cik,  # cik as fallback if name not in filings
        )

        # Add citations from edgar filings
        citations = [f.accession_number for f in retrieval_output.edgar_filings.filings]

        return self.format_output(analysis=analysis, citations=citations)

    @override
    def format_output(
        self, analysis: FundamentalAnalystOutput, citations: list[str]
    ) -> FundamentalAnalystOutput:
        """
        Finalize the FundamentalAnalystOutput with additional data like citations.
        """
        analysis.citations = citations
        return analysis

    def _calculate_metrics(self, reports: FundamentalDTO | None) -> str:
        if not reports or not reports.data:
            return "No structured financial reports available for calculation."

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

        return "\n".join(summary_lines)

    async def _analyze_with_llm(
        self, query: str, metrics_summary: str, ticker: str, company_name: str
    ) -> FundamentalAnalystOutput:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for fundamental analysis")

        client = OpenAI(api_key=openai_api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        system_prompt = get_system_prompt()
        user_prompt = format_user_prompt(query, metrics_summary, company_name, ticker)

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
            # Ensure ticker is set
            parsed["ticker"] = ticker
            return FundamentalAnalystOutput.model_validate(parsed)
        except (json.JSONDecodeError, Exception) as exc:
            logger.error(f"Failed to parse LLM response: {exc}")
            # Fallback output
            return FundamentalAnalystOutput(
                ticker=ticker,
                health_score=0,
                summary="Failed to generate detailed analysis due to LLM response error.",
                citations=[],
            )

    @override
    def get_system_prompt(self) -> str:
        return get_system_prompt()

    @override
    async def call_mcp_tool(self, server_url: str, tool_name: str, tool_input: dict[str, Any]):
        return await super().call_mcp_tool(server_url, tool_name, tool_input)

    @override
    async def get_query_reasoning():
        pass
