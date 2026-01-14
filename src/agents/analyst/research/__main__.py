from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

import diskcache
from dotenv import load_dotenv
from openai import OpenAI

# Ensure the project root is in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.agents.analyst.fundamental.fundamental_analyst_agent import FundamentalAnalystAgent
from src.agents.analyst.news.news_analyst_agent import NewsAnalystAgent
from src.agents.analyst.research.research_analyst_agent import ResearchAnalystAgent
from src.agents.retrieval.retrieval_agent import AnalystRetrievalAgent
from src.models.research_analyst import ResearchAnalystOutput

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()


def get_para_from_query(query: str) -> tuple[str, str]:
    """Helper to extract parameters from user query."""
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to parse query parameters")

    client = OpenAI(api_key=openai_api_key)
    prompt = (
        "Extract the company name and ticker symbol from the following user request. "
        "Always respond with valid JSON in the form "
        '{"company_name": "", "ticker": ""}. '
        "If you cannot determine one of the values, return an empty string for it.\n\n"
        f"Query: {query}"
    )

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "You are a structured data extraction assistant."},
            {"role": "user", "content": prompt},
        ],
    )

    payload = response.choices[0].message.content or ""
    payload = payload.strip()

    try:
        parsed = json.loads(payload)
        return parsed.get("company_name", ""), parsed.get("ticker", "")
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON from LLM response. Payload: '{payload}'")
        return "", ""


async def main() -> None:
    # 1. Setup agents
    retrieval_agent = AnalystRetrievalAgent()
    fundamental_analyst = FundamentalAnalystAgent()
    news_analyst = NewsAnalystAgent()
    research_analyst = ResearchAnalystAgent()

    # 2. Define query
    query = "Synthesize a research report for Apple (AAPL) considering its fundamentals and recent news sentiment."
    company_name, ticker = get_para_from_query(query)

    logger.info(
        "Starting research analyst end-to-end validation",
        extra={"query": query, "ticker": ticker, "company_name": company_name},
    )

    # 3. Step 1: Retrieval (with caching)
    cache_dir = os.path.join(REPO_ROOT, ".cache", "research_retrieval")
    with diskcache.Cache(cache_dir) as cache:
        cache_key = f"{ticker}:{company_name}:{query}:research"
        retrieval_result = cache.get(cache_key)

        if retrieval_result:
            logger.info("Retrieval result loaded from cache")
        else:
            try:
                retrieval_result = await retrieval_agent.process(
                    query=query,
                    ticker=ticker,
                    company_name=company_name,
                    news_limit=10,
                )
                cache.set(cache_key, retrieval_result)
                logger.info("Retrieval phase completed and cached successfully")
            except Exception as e:
                logger.error(f"Retrieval phase failed: {e}")
                return

    # 4. Step 2: Parallel Analysis (Fundamental & News)
    logger.info("Starting parallel fundamental and news analysis...")
    try:
        fundamental_task = fundamental_analyst.process(retrieval_result)
        news_task = news_analyst.process(retrieval_result)

        fundamental_output, news_output = await asyncio.gather(fundamental_task, news_task)
        logger.info("Parallel analysis completed successfully")
    except Exception as e:
        logger.error(f"Parallel analysis phase failed: {e}")
        return

    # 5. Step 3: Research Synthesis
    try:
        research_result: ResearchAnalystOutput = await research_analyst.process(
            fundamental_output, news_output
        )
        logger.info("Research Synthesis phase completed successfully")
    except Exception as e:
        logger.error(f"Research Synthesis phase failed: {e}")
        return

    # 6. Output results
    print("\n" + "=" * 60)
    print(f"RESEARCH REPORT: {ticker}")
    print("=" * 60)
    print("\nCOMPOSED ANALYSIS:")
    print("-" * 60)
    print(research_result.composed_analysis)
    print("-" * 60)

    print("\n[INPUT SUMMARY: FUNDAMENTALS]")
    print(f"Health Score: {fundamental_output.health_score}/100")
    print(f"Summary: {fundamental_output.summary[:200]}...")

    print("\n[INPUT SUMMARY: NEWS SENTIMENT]")
    print(
        f"Sentiment: {news_output.overall_sentiment_label.upper()} ({news_output.overall_sentiment_score})"
    )
    print(f"Rationale: {news_output.rationale[:200]}...")

    if research_result.warnings:
        print("\nWARNINGS:")
        for w in research_result.warnings:
            print(f"- {w}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
