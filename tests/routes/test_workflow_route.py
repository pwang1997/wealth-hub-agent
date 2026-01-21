import os
import unittest
from unittest.mock import MagicMock

from fastapi import HTTPException

os.environ.setdefault("LLM_API_KEY", "test-key")

from src.orchestrator.types import WorkflowRunListResponse, WorkflowRunRecord
from src.routes import workflow_route


class TestWorkflowRoute(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original_orchestrator = workflow_route.orchestrator
        self.mock_orchestrator = MagicMock()
        workflow_route.orchestrator = self.mock_orchestrator

    def tearDown(self):
        workflow_route.orchestrator = self.original_orchestrator

    async def test_list_workflow_runs(self):
        response = WorkflowRunListResponse(runs=[], next_cursor=None)
        self.mock_orchestrator.run_store.list_runs.return_value = response

        result = await workflow_route.list_workflow_runs(limit=5)
        self.assertEqual(result, response)
        self.mock_orchestrator.run_store.list_runs.assert_called_once_with(
            limit=5, cursor=None, ticker=None
        )

    async def test_get_workflow_run_not_found(self):
        self.mock_orchestrator.run_store.get_run.return_value = None
        with self.assertRaises(HTTPException):
            await workflow_route.get_workflow_run("missing")

    async def test_get_workflow_run_found(self):
        record = WorkflowRunRecord(
            workflow_id="wf1",
            ticker="AAPL",
            started_at="2025-01-01T00:00:00Z",
            completed_at="2025-01-01T00:01:00Z",
            status="completed",
        )
        self.mock_orchestrator.run_store.get_run.return_value = record
        result = await workflow_route.get_workflow_run("wf1")
        self.assertEqual(result, record)

    async def test_get_workflow_events_not_found(self):
        self.mock_orchestrator.run_store.get_events.return_value = None
        with self.assertRaises(HTTPException):
            await workflow_route.get_workflow_events("missing")

    async def test_get_workflow_events_found(self):
        self.mock_orchestrator.run_store.get_events.return_value = []
        result = await workflow_route.get_workflow_events("wf1")
        self.assertEqual(result.events, [])
