import asyncio
import json
import os
import sys
from typing import Any

import openai
from dotenv import load_dotenv
from fastmcp import Client as MCPClient

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.models.news_sentiments import NewsSentiment

load_dotenv()

OPENAI_MODEL = "gpt-5-mini-2025-08-07"
MCP_SERVER_URL = os.getenv("ALPHA_VANTAGE_NEWS_MCP_URL", "http://localhost:8001/mcp")


def _ensure_openai_api_key() -> str:
    """Ensure we can call OpenAI before issuing any requests."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required to drive the GPT-5 planning flow.")
    openai.api_key = api_key
    return api_key


def _build_news_function_schema() -> dict[str, Any]:
    """Mirror the MCP tool signature so GPT can plan correct arguments."""
    return {
        "name": "get_market_news",
        "description": "Retrieve Alpha Vantage news articles for a list of symbols.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbols": {"type": "string", "description": "Comma-separated tickers to search."},
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of articles to return.",
                    "minimum": 1,
                    "maximum": 20,
                },
            },
            "required": ["symbols"],
        },
    }


def _build_message(symbols: str, limit: int) -> list[dict[str, str]]:
    """Provide GPT with a short system directive and the user goal."""
    system_content = (
        "You are a planning agent that always calls the get_market_news MCP tool. "
        "Inspect the user request, emit a single function call with valid JSON arguments, "
        "and do not try to summarize anything yourself."
    )
    user_content = (
        f"Gather the latest {limit} Alpha Vantage news articles for {symbols}. "
        "Only call the tool; do not produce freeform text."
    )
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def fetch_news_with_gpt(symbols: str, limit: int = 5) -> list[NewsSentiment]:
    """Demonstrate invoking the get_market_news MCP tool through GPT-5 mini."""
    _ensure_openai_api_key()
    messages = _build_message(symbols, limit)
    response = openai.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        functions=[_build_news_function_schema()],
        function_call={"name": "get_market_news"},
        temperature=1.0,
    )

    choice = response.choices[0]
    message = getattr(choice, "message", None)
    if message is None:
        raise RuntimeError("GPT-5.1 mini returned no assistant message.")

    function_call = getattr(message, "function_call", None)
    if not function_call:
        raise RuntimeError("GPT-5.1 mini did not emit a function call.")

    arguments = getattr(function_call, "arguments", None)
    if not arguments:
        raise RuntimeError("Function call payload missing arguments.")

    parsed_args = json.loads(arguments)
    final_symbols = parsed_args.get("symbols", symbols)
    final_limit = parsed_args.get("limit", limit)

    return asyncio.run(_get_market_news_via_mcp(symbols=final_symbols, limit=final_limit))


async def _get_market_news_via_mcp(symbols: str, limit: int) -> list[NewsSentiment]:
    async with MCPClient(MCP_SERVER_URL) as client:
        result = await client.call_tool(
            "get_market_news",
            {"symbols": symbols, "limit": limit},
        )

    data = result.data
    if isinstance(data, list) and all(isinstance(item, NewsSentiment) for item in data):
        return data
    if isinstance(data, list):
        return [NewsSentiment.model_validate(item) for item in data]
    raise RuntimeError(f"Unexpected tool result type: {type(data).__name__}")


def sample_usage() -> None:
    """A quick script that verifies the GPT planning flow locally."""
    try:
        articles = fetch_news_with_gpt("AAPL,MSFT", limit=3)
    except Exception as exc:
        print(f"Unable to fetch news: {exc}")
        return

    print(f"Retrieved {len(articles)} articles via GPT-planned MCP call:")
    for article in articles:
        print(f"- {article.time_published} | {article.title} ({article.source})")


if __name__ == "__main__":
    sample_usage()
