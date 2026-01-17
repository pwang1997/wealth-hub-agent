from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterable

from src.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class BasePipelineNode[TState](ABC):
    """
    Abstract base class for a single step (node) in an agent's pipeline.
    """

    @abstractmethod
    async def run(self, agent: BaseAgent, state: TState) -> None:
        """
        Execute the logic for this pipeline node.
        """
        ...


class BasePipeline[TState]:
    """
    Orchestrator that executes a sequence of pipeline nodes.
    """

    def __init__(self, nodes: Iterable[BasePipelineNode[TState]]) -> None:
        self._nodes = list(nodes)

    async def run(self, agent: BaseAgent, state: TState) -> TState:
        """
        Execute all nodes in the pipeline sequentially.
        """
        agent.pipeline = self
        for node in self._nodes:
            # We can add global hooks here later (e.g., telemetry, error handling)
            await node.run(agent, state)
        return state
