from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from diskcache import Cache
from fastapi.encoders import jsonable_encoder

from src.orchestrator.types import (
    StreamEvent,
    WorkflowEventRecord,
    WorkflowRunListResponse,
    WorkflowRunRecord,
    WorkflowRunSummary,
    WorkflowStatus,
    WorkflowStepResult,
)

logger = logging.getLogger(__name__)

RUN_KEY_PREFIX = "workflow_run:"
EVENT_KEY_PREFIX = "workflow_events:"
INDEX_KEY = "workflow_runs:index"


class WorkflowRunStore:
    def __init__(self, cache_dir: str):
        self.cache = Cache(cache_dir)

    def start_run(self, workflow_id: str, ticker: str) -> None:
        run_key = self._run_key(workflow_id)
        events_key = self._events_key(workflow_id)
        now = datetime.now(UTC)
        record = WorkflowRunRecord(
            workflow_id=workflow_id,
            ticker=ticker,
            started_at=now,
            status=WorkflowStatus.RUNNING,
        )
        payload = jsonable_encoder(record, exclude_none=True)
        with self.cache.transact():
            if self.cache.get(run_key) is None:
                self.cache.set(run_key, payload)
            if self.cache.get(events_key) is None:
                self.cache.set(events_key, [])

    def record_event(self, event: StreamEvent) -> None:
        run_key = self._run_key(event.workflow_id)
        events_key = self._events_key(event.workflow_id)
        now = datetime.now(UTC)

        payload = self._encode_payload(event.payload)
        event_record = WorkflowEventRecord(
            workflow_id=event.workflow_id,
            timestamp=now,
            event=event.event,
            step=event.step,
            status=event.status,
            payload=payload,
        )
        encoded_event = jsonable_encoder(event_record, exclude_none=True)

        with self.cache.transact():
            record = self.cache.get(run_key)
            if not record:
                return
            events = self.cache.get(events_key) or []
            events.append(encoded_event)
            self.cache.set(events_key, events)

            if event.event == "step_complete" and event.step:
                results = record.get("results") or {}
                results[event.step.value] = payload
                record["results"] = results
                self.cache.set(run_key, record)

            if event.event == "workflow_complete":
                record["status"] = self._status_value(event.status)
                record["completed_at"] = now.isoformat()
                self.cache.set(run_key, record)
                self._update_index(record, now)

    def get_run(self, workflow_id: str) -> WorkflowRunRecord | None:
        record = self.cache.get(self._run_key(workflow_id))
        if not record:
            return None
        return WorkflowRunRecord.model_validate(record)

    def list_runs(
        self, limit: int = 20, cursor: str | None = None, ticker: str | None = None
    ) -> WorkflowRunListResponse:
        limit = max(1, limit)
        index = self.cache.get(INDEX_KEY) or []
        start = 0
        if cursor:
            for idx, item in enumerate(index):
                if self._cursor_for(item) == cursor:
                    start = idx + 1
                    break

        runs: list[WorkflowRunSummary] = []
        next_cursor: str | None = None

        for idx in range(start, len(index)):
            item = index[idx]
            record = self.cache.get(self._run_key(item.get("workflow_id")))
            if not record:
                continue
            if ticker and record.get("ticker") != ticker:
                continue
            summary = WorkflowRunSummary(
                workflow_id=record.get("workflow_id"),
                ticker=record.get("ticker"),
                completed_at=record.get("completed_at"),
                status=record.get("status"),
            )
            runs.append(summary)
            if len(runs) >= limit:
                next_cursor = self._cursor_for(item)
                break

        return WorkflowRunListResponse(runs=runs, next_cursor=next_cursor)

    def get_events(self, workflow_id: str) -> list[WorkflowEventRecord] | None:
        if not self.cache.get(self._run_key(workflow_id)):
            return None
        events = self.cache.get(self._events_key(workflow_id)) or []
        return [WorkflowEventRecord.model_validate(event) for event in events]

    def _update_index(self, record: dict[str, Any], completed_at: datetime) -> None:
        index = self.cache.get(INDEX_KEY) or []
        workflow_id = record.get("workflow_id")
        index = [item for item in index if item.get("workflow_id") != workflow_id]
        index.append(
            {
                "completed_at": completed_at.isoformat(),
                "workflow_id": workflow_id,
            }
        )
        index.sort(key=lambda item: item.get("completed_at", ""), reverse=True)
        self.cache.set(INDEX_KEY, index)

    @staticmethod
    def _encode_payload(payload: Any) -> Any:
        if isinstance(payload, WorkflowStepResult):
            return jsonable_encoder(payload, exclude_none=True)
        return jsonable_encoder(payload, exclude_none=True)

    @staticmethod
    def _status_value(status: Any) -> str:
        if status is None:
            return WorkflowStatus.RUNNING.value
        if isinstance(status, WorkflowStatus):
            return status.value
        return str(status)

    @staticmethod
    def _cursor_for(item: dict[str, Any]) -> str:
        return f"{item.get('completed_at')}|{item.get('workflow_id')}"

    @staticmethod
    def _run_key(workflow_id: str) -> str:
        return f"{RUN_KEY_PREFIX}{workflow_id}"

    @staticmethod
    def _events_key(workflow_id: str) -> str:
        return f"{EVENT_KEY_PREFIX}{workflow_id}"
