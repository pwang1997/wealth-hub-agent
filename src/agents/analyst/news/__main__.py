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

from src.agents.analyst.news.news_analyst_agent import NewsAnalystAgent
from src.agents.retrieval.retrieval_agent import AnalystRetrievalAgent
from src.models.news_analyst import NewsAnalystOutput

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
    news_analyst = NewsAnalystAgent()

    # 2. Define query
    query = "What is the current market sentiment for Nvidia (NVDA)?"
    company_name, ticker = get_para_from_query(query)

    logger.info(
        "Starting news analyst validation",
        extra={"query": query, "ticker": ticker, "company_name": company_name},
    )

    # 3. Step 1: Retrieval (with caching)
    cache_dir = os.path.join(REPO_ROOT, ".cache", "retrieval_agent")
    with diskcache.Cache(cache_dir) as cache:
        cache_key = f"{ticker}:{company_name}:{query}:news"
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

    # 4. Step 2: News Sentiment Analysis
    try:
        news_result: NewsAnalystOutput = await news_analyst.process(retrieval_result)
        logger.info("News Analysis phase completed successfully")
    except Exception as e:
        logger.error(f"News Analysis phase failed: {e}")
        return

    # 5. Output results
    print("\n" + "=" * 50)
    print(f"NEWS SENTIMENT ANALYSIS FOR '{query}'")
    print("=" * 50)
    print(f"OVERALL SENTIMENT: {news_result.overall_sentiment_label.upper()}")
    print(f"OVERALL SCORE: {news_result.overall_sentiment_score}")
    print("-" * 50)
    print("RATIONALE:")
    print(news_result.rationale)
    print("-" * 50)
    print("TICKER SUMMARIES:")
    for rollup in news_result.ticker_rollups:
        print(f"\n[{rollup.ticker}]")
        print(f"  Sentiment: {rollup.sentiment_label} ({rollup.sentiment_score})")
        print(f"  Relevance: {rollup.relevance_score}")
        print("  Top Headlines:")
        for h in rollup.top_headlines:
            print(f"    - {h}")
    print("-" * 50)
    if news_result.warnings:
        print("WARNINGS:")
        for w in news_result.warnings:
            print(f"- {w}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
