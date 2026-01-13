from __future__ import annotations

from src.models.retrieval_agent import RetrievalAgentToolMetadata


class ToolExecutionError(Exception):
    def __init__(self, message: str, metadata: RetrievalAgentToolMetadata) -> None:
        super().__init__(message)
        self.metadata = metadata
