from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any

from diskcache import Cache

from src.agents.analyst.fundamental.fundamental_analyst_agent import FundamentalAnalystAgent
from src.agents.analyst.news.news_analyst_agent import NewsAnalystAgent
from src.agents.analyst.research.research_analyst_agent import ResearchAnalystAgent
from src.agents.manager.investment.investment_manager_agent import InvestmentManagerAgent
from src.agents.retrieval.retrieval_agent import AnalystRetrievalAgent
from src.orchestrator.types import (
    StepName,
    StreamEvent,
    WorkflowRequest,
    WorkflowResponse,
    WorkflowStepResult,
)

logger = logging.getLogger(__name__)

# Canonical order of steps for validation/sequencing
STEP_ORDER: list[StepName] = ["retrieval", "fundamental", "news", "research", "investment"]
# Note: 'fundamental' and 'news' are parallel, but strictly after retrieval and before research.
# For 'until' logic, we consider them at the same "level".

DEFAULT_TIMEOUT_SECONDS = 60.0
CACHE_TTL_SECONDS = 86400  # 24 hours


class WorkflowOrchestrator:
    def __init__(self, cache_dir: str = "/tmp/wealth_hub_workflow_cache"):
        self.cache = Cache(cache_dir)
        
        # Initialize agents
        self.retrieval_agent = AnalystRetrievalAgent()
        self.fundamental_agent = FundamentalAnalystAgent()
        self.news_agent = NewsAnalystAgent()
        self.research_agent = ResearchAnalystAgent()
        self.investment_agent = InvestmentManagerAgent()

    def _should_run_step(
        self, 
        step: StepName, 
        only_steps: list[StepName] | None, 
        until_step: StepName | None
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
            workflow_id=workflow_id or request.workflow_id or f"wf_{time.time()}", 
            status="running"
        )
        
        async for event in self.workflow_generator(request, final_response.workflow_id):
            if event.event == "step_complete":
                if event.step == "retrieval":
                    final_response.retrieval = event.payload
                elif event.step == "fundamental":
                    final_response.fundamental = event.payload
                elif event.step == "news":
                    final_response.news = event.payload
                elif event.step == "research":
                    final_response.research = event.payload
                elif event.step == "investment":
                    final_response.investment = event.payload
            elif event.event == "workflow_complete":
                final_response.status = event.status  # type: ignore
        
        return final_response

    async def workflow_generator(self, request: WorkflowRequest, workflow_id: str):
        """
        Yields StreamEvents as the workflow progresses.
        """
        yield StreamEvent(workflow_id=workflow_id, event="step_start", step="retrieval")
        
        # 1. Retrieval
        retrieval_res = await self._execute_step(
            workflow_id=workflow_id,
            step_name="retrieval",
            request=request,
            func=lambda: self.retrieval_agent.process(
                query=request.query, 
                ticker=request.ticker,
                company_name=request.company_name,
                news_limit=request.news_limit,
                search_limit=request.search_limit
            )
        )
        yield StreamEvent(
            workflow_id=workflow_id, 
            event="step_complete", 
            step="retrieval", 
            status=retrieval_res.status, 
            payload=retrieval_res
        )

        if retrieval_res.status != "completed":
            final_status = "failed" if retrieval_res.status == "failed" else "partial"
            yield StreamEvent(workflow_id=workflow_id, event="workflow_complete", status=final_status)
            return

        # 2. Parallel Extraction (Fundamental & News)
        run_fundamental = self._should_run_step("fundamental", request.only_steps, request.until_step)
        run_news = self._should_run_step("news", request.only_steps, request.until_step)
        
        yield StreamEvent(workflow_id=workflow_id, event="step_start", step="fundamental")
        yield StreamEvent(workflow_id=workflow_id, event="step_start", step="news")

        fundamental_task = None
        news_task = None
        
        if run_fundamental:
            fundamental_task = asyncio.create_task(
                 self._execute_step(
                    workflow_id=workflow_id,
                    step_name="fundamental",
                    request=request,
                    func=lambda: self.fundamental_agent.process(retrieval_output=retrieval_res.output)
                )
            )
        
        if run_news:
             news_task = asyncio.create_task(
                 self._execute_step(
                    workflow_id=workflow_id,
                    step_name="news",
                    request=request,
                    func=lambda: self.news_agent.process(retrieval_output=retrieval_res.output)
                )
            )

        # Await parallel results
        fundamental_res = None
        news_res = None
        
        if fundamental_task:
            fundamental_res = await fundamental_task
            yield StreamEvent(
                workflow_id=workflow_id, 
                event="step_complete", 
                step="fundamental", 
                status=fundamental_res.status, 
                payload=fundamental_res
            )
        elif run_fundamental is False: # Skipped
             fundamental_res = WorkflowStepResult(step_name="fundamental", status="skipped")
             yield StreamEvent(workflow_id=workflow_id, event="step_complete", step="fundamental", status="skipped", payload=fundamental_res)

        if news_task:
            news_res = await news_task
            yield StreamEvent(
                workflow_id=workflow_id, 
                event="step_complete", 
                step="news", 
                status=news_res.status, 
                payload=news_res
            )
        elif run_news is False: # Skipped
            news_res = WorkflowStepResult(step_name="news", status="skipped")
            yield StreamEvent(workflow_id=workflow_id, event="step_complete", step="news", status="skipped", payload=news_res)

        # 3. Research
        can_run_research = True
        if run_fundamental and fundamental_res.status != "completed":
            can_run_research = False
        if run_news and news_res.status != "completed":
            can_run_research = False
            
        research_res = None
        if can_run_research and self._should_run_step("research", request.only_steps, request.until_step):
            yield StreamEvent(workflow_id=workflow_id, event="step_start", step="research")
            research_res = await self._execute_step(
                workflow_id=workflow_id,
                step_name="research",
                request=request,
                func=lambda: self.research_agent.process(
                    fundamental_output=fundamental_res.output,
                    news_output=news_res.output
                )
            )
            yield StreamEvent(
                workflow_id=workflow_id, 
                event="step_complete", 
                step="research", 
                status=research_res.status, 
                payload=research_res
            )
        else:
             status = "skipped" if not can_run_research else "skipped"
             warnings = ["Upstream dependencies failed"] if not can_run_research else []
             research_res = WorkflowStepResult(step_name="research", status=status, warnings=warnings)
             # emit skipped event if strictly needed, or just omit. Let's emit for completeness
             yield StreamEvent(workflow_id=workflow_id, event="step_complete", step="research", status=status, payload=research_res)

        if research_res.status != "completed":
             steps_so_far = [retrieval_res, fundamental_res, news_res, research_res]
             if any(s and s.status == "failed" for s in steps_so_far):
                 final_status = "failed"
             else:
                 final_status = "partial"
             yield StreamEvent(workflow_id=workflow_id, event="workflow_complete", status=final_status)
             return

        # 4. Investment
        investment_res = None
        if self._should_run_step("investment", request.only_steps, request.until_step):
             yield StreamEvent(workflow_id=workflow_id, event="step_start", step="investment")
             investment_res = await self._execute_step(
                workflow_id=workflow_id,
                step_name="investment",
                request=request,
                func=lambda: self.investment_agent.process(research_output=research_res.output)
             )
             yield StreamEvent(
                workflow_id=workflow_id, 
                event="step_complete", 
                step="investment", 
                status=investment_res.status, 
                payload=investment_res
             )
        else:
             investment_res = WorkflowStepResult(step_name="investment", status="skipped")
             yield StreamEvent(workflow_id=workflow_id, event="step_complete", step="investment", status="skipped", payload=investment_res)

        # Overall Status
        steps = [
            retrieval_res, 
            fundamental_res, 
            news_res, 
            research_res, 
            investment_res
        ]
        if any(s and s.status == "failed" for s in steps):
            final_status = "failed"
        elif investment_res.status == "completed":
            final_status = "completed"
        else:
            final_status = "partial"
            
        yield StreamEvent(workflow_id=workflow_id, event="workflow_complete", status=final_status)

    async def _execute_step(
        self, 
        workflow_id: str, 
        step_name: StepName, 
        request: WorkflowRequest, 
        func: callable
    ) -> WorkflowStepResult:
        # Check cache
        if not request.force_refresh:
            cached = self._get_cached_result(workflow_id, step_name)
            if cached:
                logger.info(f"Cache hit for {step_name} in workflow {workflow_id}")
                return cached

        # Run
        start_mono = time.monotonic()
        try:
            # We enforce a timeout
            output = await asyncio.wait_for(func(), timeout=DEFAULT_TIMEOUT_SECONDS)
            duration = int((time.monotonic() - start_mono) * 1000)
            
            result = WorkflowStepResult(
                step_name=step_name,
                status="completed",
                output=output,
                duration_ms=duration
            )
            self._cache_result(workflow_id, result)
            return result
            
        except asyncio.TimeoutError:
            duration = int((time.monotonic() - start_mono) * 1000)
            logger.error(f"Step {step_name} timed out after {DEFAULT_TIMEOUT_SECONDS}s")
            return WorkflowStepResult(step_name=step_name, status="failed", warnings=["Timeout"], duration_ms=duration)
        except Exception as e:
            duration = int((time.monotonic() - start_mono) * 1000)
            logger.exception(f"Step {step_name} failed: {e}")
            return WorkflowStepResult(step_name=step_name, status="failed", warnings=[str(e)], duration_ms=duration)
