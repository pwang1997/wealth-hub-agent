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
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.agents.analyst.fundamental_analyst_agent import FundamentalAnalystAgent
from src.agents.retrieval.retrieval_agent import AnalystRetrievalAgent
from src.models.fundamental_analyst import FundamentalAnalystOutput

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()


def get_para_from_query(query: str) -> tuple[str, str]:
    """Extracted from retrieval agent for standalone validation."""
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
        return "", ""


async def main() -> None:
    # 1. Setup agents
    retrieval_agent = AnalystRetrievalAgent()
    analyst_agent = FundamentalAnalystAgent()

    # 2. Define query
    query = "Analyze NVDA's fundamental health and check for any red flags."
    company_name, ticker = get_para_from_query(query)

    logger.info(
        "Starting end-to-end validation",
        extra={"query": query, "ticker": ticker, "company_name": company_name},
    )

    # 3. Step 1: Retrieval (with caching)
    cache_dir = os.path.join(REPO_ROOT, ".cache", "retrieval_agent")
    with diskcache.Cache(cache_dir) as cache:
        cache_key = f"{ticker}:{company_name}:{query}"
        retrieval_result = cache.get(cache_key)

        if retrieval_result:
            logger.info("Retrieval result loaded from cache")
        else:
            try:
                retrieval_result = await retrieval_agent.process(
                    query=query,
                    ticker=ticker,
                    company_name=company_name,
                    top_k=5,
                )
                cache.set(cache_key, retrieval_result)
                logger.info("Retrieval phase completed and cached successfully")
            except Exception as e:
                logger.error(f"Retrieval phase failed: {e}")
                return

    # 4. Step 2: Fundamental Analysis
    try:
        analyst_result: FundamentalAnalystOutput = await analyst_agent.process(retrieval_result)
        logger.info("Fundamental Analysis phase completed successfully")
    except Exception as e:
        logger.error(f"Fundamental Analysis phase failed: {e}")
        return

    # 5. Output results
    print("\n" + "=" * 50)
    print(f"FUNDAMENTAL ANALYSIS FOR {analyst_result.ticker}")
    print("=" * 50)
    print(f"HEALTH SCORE: {analyst_result.health_score}/100")
    print("-" * 50)
    print("SUMMARY:")
    print(analyst_result.summary)
    print("-" * 50)
    print("STRENGTHS:")
    for s in analyst_result.strengths:
        print(f"- [{s.impact.upper()}] {s.name}: {s.description}")
    print("-" * 50)
    print("WEAKNESSES:")
    for w in analyst_result.weaknesses:
        print(f"- [{w.impact.upper()}] {w.name}: {w.description}")
    print("-" * 50)
    print("RED FLAGS:")
    for rf in analyst_result.red_flags:
        print(f"- [CRITICAL] {rf.name}: {rf.description}")
    print("-" * 50)
    print("CITATIONS:")
    for c in analyst_result.citations:
        print(f"- {c}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
