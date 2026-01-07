from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.agents.analyst.retrieval_agent import AnalystRetrievalAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

load_dotenv()

def get_para_from_query(query: str) -> tuple[str, str]:
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
    agent = AnalystRetrievalAgent()
    query = "what are the core businesses of the company?"
    company_name, ticker = get_para_from_query(query)
    logging.getLogger(__name__).info(
        "Running retrieval agent workflow",
        extra={"query": query, "ticker": ticker, "company_name": company_name},
    )

    result = await agent.process(
        query=query,
        ticker=ticker or "NVDA",
        company_name=company_name or None,
        top_k=3,
    )

    payload = result.model_dump()
    print(json.dumps(payload, indent=2, sort_keys=True))

    edgar = payload.get("edgar") or {}
    collections = edgar.get("ingested_collections") or []
    if collections:
        print("\nEDGAR collections created/used:")
        for name in collections:
            print(f"- {name}")


if __name__ == "__main__":
    asyncio.run(main())
