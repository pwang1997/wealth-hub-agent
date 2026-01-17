from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from diskcache import Cache

from clients.model_client import ModelClient
from src.agents.analyst.fundamental.fundamental_analyst_agent import FundamentalAnalystAgent
from src.agents.analyst.news.news_analyst_agent import NewsAnalystAgent
from src.agents.analyst.research.research_analyst_agent import ResearchAnalystAgent
from src.agents.manager.investment.investment_manager_agent import InvestmentManagerAgent
from src.agents.retrieval.retrieval_agent import AnalystRetrievalAgent
from src.orchestrator.types import (
    StepName,
    StepStatus,
    StreamEvent,
    WorkflowRequest,
    WorkflowResponse,
    WorkflowStatus,
    WorkflowStepResult,
)

logger = logging.getLogger(__name__)

# Canonical order of steps for validation/sequencing
STEP_ORDER: list[StepName] = [
    StepName.RETRIEVAL,
    StepName.FUNDAMENTAL,
    StepName.NEWS,
    StepName.RESEARCH,
    StepName.INVESTMENT,
]
# Note: 'fundamental' and 'news' are parallel, but strictly after retrieval and before research.
# For 'until' logic, we consider them at the same "level".

DEFAULT_TIMEOUT_SECONDS = 120.0
CACHE_TTL_SECONDS = 86400  # 24 hours

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cache_dir = os.path.join(base_dir, ".workflow_cache")


class WorkflowOrchestrator:
    def __init__(self, cache_dir: str = cache_dir):
        self.cache = Cache(cache_dir)
        self.model_client = ModelClient()

        # Initialize agents
        self.retrieval_agent = AnalystRetrievalAgent()
        self.fundamental_agent = FundamentalAnalystAgent(model_client=self.model_client)
        self.news_agent = NewsAnalystAgent(model_client=self.model_client)
        self.research_agent = ResearchAnalystAgent(model_client=self.model_client)
        self.investment_agent = InvestmentManagerAgent(model_client=self.model_client)

    def _should_run_step(
        self, step: StepName, only_steps: list[StepName] | None, until_step: StepName | None
    ) -> bool:
        if only_steps:
            return step in only_steps

        if until_step:
            try:
                stop_index = STEP_ORDER.index(until_step)
                current_index = STEP_ORDER.index(step)
                return current_index <= stop_index
            except ValueError:
                # Fallback if step names strictly don't align perfectly (e.g. parallel steps)
                # But here we handle strict list logic.
                pass

        return True

    def _get_cached_result(self, workflow_id: str, step: StepName) -> WorkflowStepResult | None:
        key = f"{workflow_id}:{step}"
        return self.cache.get(key)

    def _cache_result(self, workflow_id: str, result: WorkflowStepResult):
        key = f"{workflow_id}:{result.step_name}"
        self.cache.set(key, result, expire=CACHE_TTL_SECONDS)

    async def run_workflow(
        self, request: WorkflowRequest, workflow_id: str | None = None
    ) -> WorkflowResponse:
        """
        Executes the workflow and returns the final response object.
        """
        final_response = WorkflowResponse(
            workflow_id=workflow_id or request.workflow_id or f"wf_{uuid.uuid4()!s}",
            status=WorkflowStatus.RUNNING,
        )

        async for event in self.workflow_generator(request, final_response.workflow_id):
            if event.event == "step_complete":
                if event.step:
                    setattr(final_response, event.step, event.payload)
                else:
                    raise ValueError(f"Step complete event without step: {event}")
            elif event.event == "workflow_complete":
                final_response.status = event.status  # type: ignore

        return final_response

    async def workflow_generator(self, request: WorkflowRequest, workflow_id: str):
        """
        Yields StreamEvents as the workflow progresses.
        """
        # Validate steps
        if request.until_step and request.until_step not in STEP_ORDER:
            raise ValueError(
                f"Invalid until_step: {request.until_step}. Must be one of {STEP_ORDER}"
            )

        if request.only_steps:
            for step in request.only_steps:
                if step not in STEP_ORDER:
                    raise ValueError(
                        f"Invalid step in only_steps: {step}. Must be one of {STEP_ORDER}"
                    )

            # check order
            indices = [STEP_ORDER.index(s) for s in request.only_steps]
            if indices != sorted(indices):
                raise ValueError(f"Steps in only_steps must be in canonical order: {STEP_ORDER}")

        # 1. Retrieval
        retrieval_res: WorkflowStepResult | None = None
        async for event in self._run_step_helper(
            workflow_id=workflow_id,
            step_name=StepName.RETRIEVAL,
            request=request,
            should_run=self._should_run_step(
                StepName.RETRIEVAL, request.only_steps, request.until_step
            ),
            func=lambda: self.retrieval_agent.process(
                query=request.query,
                ticker=request.ticker,
                company_name=request.company_name,
                news_limit=request.news_limit,
                search_limit=request.search_limit,
            ),
        ):
            yield event
            if event.event == "step_complete":
                retrieval_res = event.payload  # type: ignore

        if not retrieval_res or retrieval_res.status != StepStatus.COMPLETED:
            final_status = (
                WorkflowStatus.FAILED
                if retrieval_res and retrieval_res.status == StepStatus.FAILED
                else WorkflowStatus.PARTIAL
            )
            yield StreamEvent(
                workflow_id=workflow_id, event="workflow_complete", status=final_status
            )
            return

        # 2. Parallel Extraction (Fundamental & News)
        run_fundamental = self._should_run_step(
            StepName.FUNDAMENTAL, request.only_steps, request.until_step
        )
        run_news = self._should_run_step(StepName.NEWS, request.only_steps, request.until_step)

        if run_fundamental:
            yield StreamEvent(
                workflow_id=workflow_id, event="step_start", step=StepName.FUNDAMENTAL
            )
        if run_news:
            yield StreamEvent(workflow_id=workflow_id, event="step_start", step=StepName.NEWS)

        fundamental_task = None
        news_task = None

        if run_fundamental:
            fundamental_task = asyncio.create_task(
                self._execute_step(
                    workflow_id=workflow_id,
                    step_name=StepName.FUNDAMENTAL,
                    request=request,
                    func=lambda: self.fundamental_agent.process(
                        retrieval_output=retrieval_res.output
                    ),
                )
            )

        if run_news:
            news_task = asyncio.create_task(
                self._execute_step(
                    workflow_id=workflow_id,
                    step_name=StepName.NEWS,
                    request=request,
                    func=lambda: self.news_agent.process(retrieval_output=retrieval_res.output),
                )
            )

        # Await parallel results as they complete
        fundamental_res = None
        news_res = None
        parallel_tasks = []
        if fundamental_task:
            parallel_tasks.append(fundamental_task)
        if news_task:
            parallel_tasks.append(news_task)

        if parallel_tasks:
            for completed_task in asyncio.as_completed(parallel_tasks):
                res = await completed_task
                if res.step_name == StepName.FUNDAMENTAL:
                    fundamental_res = res
                else:
                    news_res = res

                yield StreamEvent(
                    workflow_id=workflow_id,
                    event="step_complete",
                    step=res.step_name,
                    status=res.status,
                    payload=res,
                )

        # Handle skipped branches
        if run_fundamental is False:
            fundamental_res = WorkflowStepResult(
                step_name=StepName.FUNDAMENTAL, status=StepStatus.SKIPPED
            )
            yield StreamEvent(
                workflow_id=workflow_id,
                event="step_complete",
                step=StepName.FUNDAMENTAL,
                status=StepStatus.SKIPPED,
                payload=fundamental_res,
            )

        if run_news is False:
            news_res = WorkflowStepResult(step_name=StepName.NEWS, status=StepStatus.SKIPPED)
            yield StreamEvent(
                workflow_id=workflow_id,
                event="step_complete",
                step=StepName.NEWS,
                status=StepStatus.SKIPPED,
                payload=news_res,
            )

        # 3. Research
        can_run_research = True
        if run_fundamental and (
            not fundamental_res or fundamental_res.status != StepStatus.COMPLETED
        ):
            logger.warning(
                f"Research dependence failed: Fundamental status={fundamental_res.status if fundamental_res else 'None'}"
            )
            can_run_research = False
        if run_news and (not news_res or news_res.status != StepStatus.COMPLETED):
            logger.warning(
                f"Research dependence failed: News status={news_res.status if news_res else 'None'}"
            )
            can_run_research = False

        research_res: WorkflowStepResult | None = None
        async for event in self._run_step_helper(
            workflow_id=workflow_id,
            step_name=StepName.RESEARCH,
            request=request,
            should_run=self._should_run_step(
                StepName.RESEARCH, request.only_steps, request.until_step
            ),
            dependencies_ok=can_run_research,
            func=lambda: self.research_agent.process(
                fundamental_output=fundamental_res.output if fundamental_res else None,
                news_output=news_res.output if news_res else None,
            ),
        ):
            yield event
            if event.event == "step_complete":
                research_res = event.payload  # type: ignore

        if not research_res or research_res.status != StepStatus.COMPLETED:
            steps_so_far = [retrieval_res, fundamental_res, news_res, research_res]
            if any(s and s.status == StepStatus.FAILED for s in steps_so_far if s):
                final_status = WorkflowStatus.FAILED
            else:
                final_status = WorkflowStatus.PARTIAL
            yield StreamEvent(
                workflow_id=workflow_id, event="workflow_complete", status=final_status
            )
            return

        # 4. Investment
        investment_res: WorkflowStepResult | None = None
        async for event in self._run_step_helper(
            workflow_id=workflow_id,
            step_name=StepName.INVESTMENT,
            request=request,
            should_run=self._should_run_step(
                StepName.INVESTMENT, request.only_steps, request.until_step
            ),
            func=lambda: self.investment_agent.process(research_output=research_res.output),
        ):
            yield event
            if event.event == "step_complete":
                investment_res = event.payload  # type: ignore

        # Overall Status
        steps = [retrieval_res, fundamental_res, news_res, research_res, investment_res]
        if any(s and s.status == StepStatus.FAILED for s in steps):
            final_status = WorkflowStatus.FAILED
        elif investment_res and investment_res.status == StepStatus.COMPLETED:
            final_status = WorkflowStatus.COMPLETED
        else:
            final_status = WorkflowStatus.PARTIAL

        yield StreamEvent(workflow_id=workflow_id, event="workflow_complete", status=final_status)

    async def _run_step_helper(
        self,
        workflow_id: str,
        step_name: StepName,
        request: WorkflowRequest,
        should_run: bool,
        func: Callable[[], Awaitable[Any]] | None = None,
        dependencies_ok: bool = True,
    ):
        """
        Helper to run a standard sequential step, emitting start/complete events.
        """
        if should_run and dependencies_ok and func:
            yield StreamEvent(workflow_id=workflow_id, event="step_start", step=step_name)
            # Give the event loop a chance to flush the start event to the client
            await asyncio.sleep(0.01)

            result = await self._execute_step(workflow_id, step_name, request, func)
            yield StreamEvent(
                workflow_id=workflow_id,
                event="step_complete",
                step=step_name,
                status=result.status,
                payload=result,
            )
        else:
            status = StepStatus.SKIPPED
            warnings = ["Upstream dependencies failed"] if not dependencies_ok else []
            result = WorkflowStepResult(step_name=step_name, status=status, warnings=warnings)
            yield StreamEvent(
                workflow_id=workflow_id,
                event="step_complete",
                step=step_name,
                status=result.status,
                payload=result,
            )

    async def _execute_step(
        self, workflow_id: str, step_name: StepName, request: WorkflowRequest, func: callable
    ) -> WorkflowStepResult:
        # Check cache
        if not request.force_refresh:
            cached = self._get_cached_result(workflow_id, step_name)
            if cached:
                logger.info(f"Cache hit for {step_name} in workflow {workflow_id}")
                return cached

        # Run
        start_mono = time.monotonic()
        output: Any | None = None
        warnings: list[str] = []
        status: StepStatus = StepStatus.FAILED

        try:
            # We enforce a timeout
            output = await asyncio.wait_for(func(), timeout=DEFAULT_TIMEOUT_SECONDS)
            status = StepStatus.COMPLETED
        except TimeoutError:
            logger.error(f"Step {step_name} timed out after {DEFAULT_TIMEOUT_SECONDS}s")
            warnings = ["Timeout"]
        except Exception as e:
            logger.exception(f"Step {step_name} failed: {e}")
            warnings = [str(e)]

        duration = int((time.monotonic() - start_mono) * 1000)
        result = WorkflowStepResult(
            step_name=step_name,
            status=status,
            output=output,
            warnings=warnings,
            duration_ms=duration,
        )
        if status == StepStatus.COMPLETED:
            self._cache_result(workflow_id, result)
        return result
