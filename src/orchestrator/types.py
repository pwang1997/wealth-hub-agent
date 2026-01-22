from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class StepName(StrEnum):
    RETRIEVAL = "retrieval"
    FUNDAMENTAL = "fundamental"
    NEWS = "news"
    RESEARCH = "research"
    INVESTMENT = "investment"


class WorkflowStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class WorkflowRequest(BaseModel):
    workflow_id: str | None = None
    query: str
    ticker: str
    company_name: str | None = None

    # Execution controls
    only_steps: list[StepName] | None = None
    until_step: StepName | None = None

    # Tuning
    news_limit: int = 5
    search_limit: int = 5
    force_refresh: bool = False  # Ignore cache if True
    temp_workflow: bool = False  # Skip persistence if True


class WorkflowStepResult(BaseModel):
    step_name: StepName
    status: StepStatus
    output: Any | None = None  # Polymorphic based on step
    warnings: list[str] = Field(default_factory=list)
    duration_ms: int = 0
    llm_usage: list[LlmUsageRecord] = Field(default_factory=list)


class WorkflowResponse(BaseModel):
    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    status: WorkflowStatus

    # Step outputs (optional, present if executed)
    retrieval: WorkflowStepResult | None = None
    fundamental: WorkflowStepResult | None = None
    news: WorkflowStepResult | None = None
    research: WorkflowStepResult | None = None
    investment: WorkflowStepResult | None = None

    overall_warnings: list[str] = Field(default_factory=list)


class StreamEvent(BaseModel):
    workflow_id: str
    event: Literal["step_start", "step_complete", "workflow_complete", "error"]
    step: StepName | None = None
    status: StepStatus | WorkflowStatus | None = None
    payload: Any | None = None


class LlmUsageRecord(BaseModel):
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None


class WorkflowRunRecord(BaseModel):
    workflow_id: str
    ticker: str
    started_at: datetime
    completed_at: datetime | None = None
    status: WorkflowStatus
    results: dict[StepName, WorkflowStepResult] = Field(default_factory=dict)


class WorkflowRunSummary(BaseModel):
    workflow_id: str
    ticker: str
    completed_at: datetime | None = None
    status: WorkflowStatus


class WorkflowEventRecord(BaseModel):
    workflow_id: str
    timestamp: datetime
    event: Literal["step_start", "step_complete", "workflow_complete", "error"]
    step: StepName | None = None
    status: StepStatus | WorkflowStatus | None = None
    payload: Any | None = None


class WorkflowRunListResponse(BaseModel):
    runs: list[WorkflowRunSummary]
    next_cursor: str | None = None


class WorkflowRunEventsResponse(BaseModel):
    events: list[WorkflowEventRecord]
