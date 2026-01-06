from __future__ import annotations

import asyncio

from src.agent_tools.rag import retrieve_report
from src.models.rag_retrieve import RAGRetrieveInput


class DummyCollection:
    def __init__(self) -> None:
        self.query_calls: list[dict[str, object]] = []

    def query(
        self,
        *,
        query_embeddings: list[object],
        n_results: int,
        where: dict[str, object] | None,
        where_document: dict[str, object] | None,
        include: list[str],
    ) -> dict[str, list[list[object]]]:
        self.query_calls.append(where or {})
        return {
            "ids": [["chunk-1"]],
            "documents": [["sample document"]],
            "metadatas": [[{"ticker": "AAPL", "form": "10-K"}]],
            "distances": [[0.12]],
        }


class DummyEmbedModel:
    def get_query_embedding(self, query: str) -> list[float]:
        return [0.1, 0.2]


def test_retrieve_report_normalizes_edgar_filters(monkeypatch):
    async def run():
        dummy_collection = DummyCollection()

        async def fake_get_collection_or_raise(collection_name: str, *, cache=None):
            return dummy_collection

        monkeypatch.setattr(
            retrieve_report.chroma_client,
            "get_collection_or_raise",
            fake_get_collection_or_raise,
        )
        monkeypatch.setattr(retrieve_report, "resolve_embed_model", lambda name: DummyEmbedModel())

        input_data = RAGRetrieveInput(
            query="earnings summary",
            domain="edgar",
            filters={"ticker": "aapl", "form": "10-k"},
        )

        result = await retrieve_report._retrieve_report(input_data)

        assert dummy_collection.query_calls == [{"ticker": "AAPL", "form": "10-K"}]
        assert result["filters"] == {"ticker": "AAPL", "form": "10-K"}

    asyncio.run(run())
