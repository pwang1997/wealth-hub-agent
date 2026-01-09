from __future__ import annotations

import asyncio

from src.agent_tools.rag import extract_financial_statements_impl


def test_extract_financial_statement_preserves_chunk_index_order(monkeypatch):
    async def run():
        class DummyCollection:
            def __init__(self) -> None:
                self.query_calls: list[dict[str, object]] = []

            def query(self, *, where, include, n_results, **kwargs) -> dict:
                self.query_calls.append({"where": where, **kwargs})
                return {}

        class DummyChromaClient:
            async def get_collection_or_raise(self, *, collection_name: str, cache=None):
                return dummy_collection

        dummy_collection = DummyCollection()
        monkeypatch.setattr(
            extract_financial_statements_impl,
            "chroma_client",
            DummyChromaClient(),
        )

        def fake_flatten(_results: dict[str, object]) -> list[dict[str, object]]:
            return [
                {"document": "second chunk", "metadata": {"chunk_index": 2}},
                {"document": "first chunk", "metadata": {"chunk_index": 1}},
            ]

        monkeypatch.setattr(
            extract_financial_statements_impl,
            "flatten_chroma_query_results",
            fake_flatten,
        )
        monkeypatch.delenv("RAG_EMBED_MODEL", raising=False)

        result = await extract_financial_statements_impl.extract_financial_statement_impl(
            accession_number="ACC-123",
            statement_type="income_statement",
        )

        assert result["chunks_returned"] == 2
        assert result["statement_text"] == "first chunk\nsecond chunk"

    asyncio.run(run())
