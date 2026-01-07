from __future__ import annotations

import asyncio
import json
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.agents.analyst.retrieval_agent import AnalystRetrievalAgent


async def main() -> None:
    agent = AnalystRetrievalAgent()

    result = await agent.process(
        query="what are the core businesses of the company?",
        ticker="NVDA",
        company_name="NVIDIA",
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
