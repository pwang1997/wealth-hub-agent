from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from src.models.fundamental_analyst import FundamentalAnalystOutput
from src.models.investment_manager import InvestmentManagerOutput
from src.models.news_analyst import NewsAnalystOutput
from src.models.research_analyst import ResearchAnalystOutput
from src.models.retrieval_agent import RetrievalAgentOutput

StepName = Literal["retrieval", "fundamental", "news", "research", "investment"]
WorkflowStatus = Literal["running", "completed", "failed", "partial"]
StepStatus = Literal["pending", "running", "completed", "skipped", "failed"]


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


class WorkflowStepResult(BaseModel):
    step_name: StepName
    status: StepStatus
    output: Any | None = None # Polymorphic based on step
    warnings: list[str] = Field(default_factory=list)
    duration_ms: int = 0


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
