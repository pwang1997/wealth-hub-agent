import tempfile
import time
import unittest

from src.orchestrator.run_history import WorkflowRunStore
from src.orchestrator.types import (
    StepName,
    StepStatus,
    StreamEvent,
    WorkflowStatus,
    WorkflowStepResult,
)


class TestWorkflowRunStore(unittest.TestCase):
    def test_run_persistence_and_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = WorkflowRunStore(temp_dir)
            workflow_id = "wf_test"

            store.start_run(workflow_id, "AAPL")

            step_result = WorkflowStepResult(
                step_name=StepName.RETRIEVAL,
                status=StepStatus.COMPLETED,
                output={"ok": True},
                duration_ms=10,
            )
            store.record_event(
                StreamEvent(
                    workflow_id=workflow_id,
                    event="step_complete",
                    step=StepName.RETRIEVAL,
                    status=StepStatus.COMPLETED,
                    payload=step_result,
                )
            )
            store.record_event(
                StreamEvent(
                    workflow_id=workflow_id,
                    event="workflow_complete",
                    status=WorkflowStatus.COMPLETED,
                )
            )

            record = store.get_run(workflow_id)
            self.assertIsNotNone(record)
            self.assertEqual(record.workflow_id, workflow_id)
            self.assertEqual(record.ticker, "AAPL")
            self.assertIsNotNone(record.completed_at)
            self.assertEqual(record.status, WorkflowStatus.COMPLETED)
            self.assertIn(StepName.RETRIEVAL, record.results)

            events = store.get_events(workflow_id)
            self.assertIsNotNone(events)
            self.assertEqual(len(events), 2)

            run_list = store.list_runs(limit=10)
            self.assertEqual(len(run_list.runs), 1)
            self.assertEqual(run_list.runs[0].workflow_id, workflow_id)

    def test_list_runs_pagination_and_filter(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = WorkflowRunStore(temp_dir)

            store.start_run("wf1", "AAPL")
            store.record_event(
                StreamEvent(
                    workflow_id="wf1",
                    event="workflow_complete",
                    status=WorkflowStatus.COMPLETED,
                )
            )

            time.sleep(0.001)

            store.start_run("wf2", "MSFT")
            store.record_event(
                StreamEvent(
                    workflow_id="wf2",
                    event="workflow_complete",
                    status=WorkflowStatus.COMPLETED,
                )
            )

            run_list = store.list_runs(limit=1)
            self.assertEqual(len(run_list.runs), 1)
            self.assertEqual(run_list.runs[0].workflow_id, "wf2")
            self.assertIsNotNone(run_list.next_cursor)

            next_page = store.list_runs(limit=1, cursor=run_list.next_cursor)
            self.assertEqual(len(next_page.runs), 1)
            self.assertEqual(next_page.runs[0].workflow_id, "wf1")

            filtered = store.list_runs(limit=10, ticker="AAPL")
            self.assertEqual(len(filtered.runs), 1)
            self.assertEqual(filtered.runs[0].workflow_id, "wf1")
