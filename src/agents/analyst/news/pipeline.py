from __future__ import annotations

import logging
import math
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

from openai import OpenAI

from src.agents.base_agent import BaseAgent
from src.agents.base_pipeline import BasePipeline, BasePipelineNode
from src.models.news_analyst import NewsAnalystOutput, NewsTickerRollup
from src.models.retrieval_agent import RetrievalAgentOutput

from .prompt import format_synthesis_prompt

logger = logging.getLogger(__name__)

RELEVANCE_THRESHOLD = 0.8
BULLISH_THRESHOLD = 0.25
BEARISH_THRESHOLD = -0.25


@dataclass
class NewsAnalystPipelineState:
    retrieval_output: RetrievalAgentOutput
    analysis: NewsAnalystOutput | None = None
    internal_thought: str = ""
    objectives: str = ""
    ticker_rollups: dict[str, NewsTickerRollup] = field(default_factory=dict)
    overall_score: float = 0.0
    overall_label: str = "neutral"
    warnings: list[str] = field(default_factory=list)


class NewsAnalystPipelineNode(BasePipelineNode[NewsAnalystPipelineState]):
    """Base node for news analyst pipeline."""


class NewsAnalystPipeline(BasePipeline[NewsAnalystPipelineState]):
    """Orchestrator for news analysis."""


class ReasoningNode(NewsAnalystPipelineNode):
    async def run(self, agent: BaseAgent, state: NewsAnalystPipelineState) -> None:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for news analysis")

        client = OpenAI(api_key=openai_api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        prompt = (
            f"You are {agent.agent_name}. {agent.role_description}\n"
            f"User Query: {state.retrieval_output.query}\n"
            "Identify your specific responsibilities and extract the key objectives for this news sentiment analysis.\n"
            "Use the following format:\n"
            "<thought>\n[Your internal chain of thought about the query and the agent's role]\n</thought>\n"
            "<objectives>\n[Concise objectives for the rest of the pipeline]\n</objectives>"
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

        logger.info(f"News ReasoningNode completed. Objectives: {state.objectives[:100]}...")


class AggregationNode(NewsAnalystPipelineNode):
    async def run(self, agent: BaseAgent, state: NewsAnalystPipelineState) -> None:
        news_items = state.retrieval_output.market_news
        if not news_items:
            state.warnings.append("No market news items available for analysis.")
            return

        # 1. Deduplication (by normalized title)
        seen_titles = set()
        unique_news = []
        for item in news_items:
            norm_title = re.sub(r"\W+", "", item.title.lower())
            if norm_title in seen_titles:
                continue
            seen_titles.add(norm_title)
            unique_news.append(item)

        if len(unique_news) < len(news_items):
            state.warnings.append(f"Deduplicated {len(news_items) - len(unique_news)} articles.")

        # 2. Score Calculation with Exponential Decay
        target_ticker = state.retrieval_output.edgar_filings.ticker
        now = datetime.now(UTC)
        total_weighted_score = 0.0
        total_weight = 0.0

        ticker_data = {}  # ticker -> list of (weighted_score, weight, headline)

        for item in unique_news:
            try:
                # Alpha Vantage format: 20240124T123205
                pub_date = datetime.strptime(item.time_published, "%Y%m%dT%H%M%S").replace(
                    tzinfo=UTC
                )
            except ValueError:
                try:
                    pub_date = datetime.fromisoformat(item.time_published).replace(tzinfo=UTC)
                except Exception:
                    state.warnings.append(f"Invalid timestamp for article: {item.title}")
                    pub_date = now

            delta_hours = (now - pub_date).total_seconds() / 3600.0
            decay_lambda = math.log(2) / 24.0
            recency_weight = math.exp(-decay_lambda * delta_hours)

            # Ticker rollups - only care about the target ticker if highly relevant (> 0.8)
            item_is_relevant_to_target = False
            for ts in item.ticker_sentiment:
                ticker = ts.ticker
                if ticker != target_ticker:
                    continue

                try:
                    rel_score = float(ts.relevance_score)
                    ts_score = float(ts.ticker_sentiment_score)
                except (ValueError, TypeError):
                    rel_score = 0.0
                    ts_score = 0.0
                if rel_score > RELEVANCE_THRESHOLD:
                    item_is_relevant_to_target = True
                    if ticker not in ticker_data:
                        ticker_data[ticker] = []

                    # Weight by ticker-specific relevance AND recency
                    t_weight = rel_score * recency_weight
                    ticker_data[ticker].append((ts_score * t_weight, t_weight, item.title))

            # Only contribute to overall score if the article is highly relevant to the target ticker
            if item_is_relevant_to_target:
                try:
                    score = float(item.overall_sentiment_score)
                except (ValueError, TypeError):
                    score = 0.0

                weighted_score = score * recency_weight
                total_weighted_score += weighted_score
                total_weight += recency_weight

        # Final overall calculation
        if total_weight > 0:
            state.overall_score = total_weighted_score / total_weight
        else:
            state.overall_score = 0.0

        # Mapping thresholds
        if state.overall_score >= BULLISH_THRESHOLD:
            state.overall_label = "bullish"
        elif state.overall_score <= BEARISH_THRESHOLD:
            state.overall_label = "bearish"
        else:
            state.overall_label = "neutral"

        # Ticker rollups finalization
        for ticker, signals in ticker_data.items():
            t_weighted_sum = sum(s[0] for s in signals)
            t_weight_sum = sum(s[1] for s in signals)
            t_score = t_weighted_sum / t_weight_sum if t_weight_sum > 0 else 0.0

            if t_score >= BULLISH_THRESHOLD:
                t_label = "bullish"
            elif t_score <= BEARISH_THRESHOLD:
                t_label = "bearish"
            else:
                t_label = "neutral"

            # Get top headlines for this ticker (weighted by relevance * recency)
            sorted_signals = sorted(signals, key=lambda x: x[1], reverse=True)
            top_h = [s[2] for s in sorted_signals[:3]]

            t_avg_weight = t_weight_sum / len(signals) if signals else 0.0

            state.ticker_rollups[ticker] = NewsTickerRollup(
                ticker=ticker,
                sentiment_score=round(t_score, 4),
                sentiment_label=t_label,
                relevance_score=round(t_avg_weight, 4),
                top_headlines=top_h,
            )

        logger.info(f"AggregationNode completed. Overall score: {state.overall_score:.4f}")


class SynthesisNode(NewsAnalystPipelineNode):
    async def run(self, agent: BaseAgent, state: NewsAnalystPipelineState) -> None:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for news analysis")

        client = OpenAI(api_key=openai_api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Top 5 headlines overall (by recency weight)
        # We didn't store overall weights in state, so we just pick from unique_news if we had them or just use ticker data
        # Let's just use ticker rollups for the prompt context
        ticker_summaries = "\n".join(
            [
                f"- {t}: {r.sentiment_label} (score: {r.sentiment_score})"
                for t, r in state.ticker_rollups.items()
            ]
        )

        # Collect top headlines from all rollups for synthesis
        all_top_headlines = set()
        for r in state.ticker_rollups.values():
            all_top_headlines.update(r.top_headlines)

        prompt = format_synthesis_prompt(
            state.retrieval_output.query,
            state.overall_score,
            state.overall_label,
            list(all_top_headlines)[:5],
            ticker_summaries,
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": agent.get_system_prompt()},
                {"role": "user", "content": prompt},
            ],
        )
        rationale = response.choices[0].message.content or "No rationale provided."

        state.analysis = NewsAnalystOutput(
            query=state.retrieval_output.query,
            overall_sentiment_score=round(state.overall_score, 4),
            overall_sentiment_label=state.overall_label,
            rationale=rationale,
            ticker_rollups=list(state.ticker_rollups.values()),
            news_items=state.retrieval_output.market_news,
            warnings=state.warnings,
        )
        logger.info("SynthesisNode completed.")
