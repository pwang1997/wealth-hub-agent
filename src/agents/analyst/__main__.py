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


def _build_answer_with_context(query: str, context: str) -> str:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to generate the final answer")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=openai_api_key)
    user_prompt = f"""Context:
{context or "No retrieval context was returned."}

Question:
{query}

Instructions:
- Answer based ONLY on the provided context.
- If the context lacks relevant information, explain that additional data is needed.
- Keep the response concise and factual.

Answer:"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a retrieval pipeline assistant. Use only the context provided to answer the user's question.",
            },
            {"role": "user", "content": user_prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()


async def main() -> None:
    agent = AnalystRetrievalAgent()
    query = "what are the core businesses of Nvidia?"
    company_name, ticker = get_para_from_query(query)
    logging.getLogger(__name__).info(
        "Running retrieval agent workflow",
        extra={"query": query, "ticker": ticker, "company_name": company_name},
    )

    result = await agent.process(
        query=query,
        ticker=ticker,
        company_name=company_name,
        top_k=3,
    )

    payload = result.model_dump()

    context_str = str(payload.get("answer") or "")
    final_answer = _build_answer_with_context(query, context_str)

    logging.getLogger(__name__).info(
        "Final answer generated from context",
        extra={"query": query, "answer": final_answer},
    )

    print(f"Final answer:\n{final_answer}")


if __name__ == "__main__":
    asyncio.run(main())
