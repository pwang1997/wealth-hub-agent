import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.fundamental_analyst import FundamentalAnalystOutput
from src.models.investment_manager import InvestmentManagerOutput
from src.models.news_analyst import NewsAnalystOutput
from src.models.research_analyst import ResearchAnalystOutput
from src.models.retrieval_agent import RetrievalAgentOutput
from src.orchestrator.orchestrator import WorkflowOrchestrator
from src.orchestrator.types import StepName, StepStatus, WorkflowRequest, WorkflowStatus


class TestWorkflowOrchestrator(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Mock Cache
        self.cache_patcher = patch("src.orchestrator.orchestrator.Cache")
        self.mock_cache_cls = self.cache_patcher.start()
        self.mock_cache = MagicMock()
        self.mock_cache_cls.return_value = self.mock_cache
        self.mock_cache.get.return_value = None  # Default cache miss

        # Mock ModelClient
        self.model_client_patcher = patch("src.orchestrator.orchestrator.ModelClient")
        self.mock_model_client_cls = self.model_client_patcher.start()
        self.mock_model_client = MagicMock()
        self.mock_model_client_cls.return_value = self.mock_model_client

        # Instantiate orchestrator (will use mocked Cache and ModelClient)
        self.orchestrator = WorkflowOrchestrator()

        # Patch Agents
        self.orchestrator.retrieval_agent = AsyncMock()
        self.orchestrator.fundamental_agent = AsyncMock()
        self.orchestrator.news_agent = AsyncMock()
        self.orchestrator.research_agent = AsyncMock()
        self.orchestrator.investment_agent = AsyncMock()

    def tearDown(self):
        self.cache_patcher.stop()
        self.model_client_patcher.stop()

    async def test_full_workflow_success(self):
        # Setup Mocks
        retrieval_out = MagicMock(spec=RetrievalAgentOutput)
        retrieval_out.status = "success"
        self.orchestrator.retrieval_agent.process.return_value = retrieval_out

        fund_out = MagicMock(spec=FundamentalAnalystOutput)
        self.orchestrator.fundamental_agent.process.return_value = fund_out

        news_out = MagicMock(spec=NewsAnalystOutput)
        self.orchestrator.news_agent.process.return_value = news_out

        research_out = MagicMock(spec=ResearchAnalystOutput)
        self.orchestrator.research_agent.process.return_value = research_out

        invest_out = MagicMock(spec=InvestmentManagerOutput)
        self.orchestrator.investment_agent.process.return_value = invest_out

        # Run
        req = WorkflowRequest(query="test", ticker="AAPL")
        res = await self.orchestrator.run_workflow(req)

        # Verify
        self.assertEqual(res.status, WorkflowStatus.COMPLETED)
        self.assertEqual(res.retrieval.status, StepStatus.COMPLETED)
        self.assertEqual(res.fundamental.status, StepStatus.COMPLETED)
        self.assertEqual(res.news.status, StepStatus.COMPLETED)
        self.assertEqual(res.research.status, StepStatus.COMPLETED)
        self.assertEqual(res.investment.status, StepStatus.COMPLETED)

        # Verify calls
        self.orchestrator.retrieval_agent.process.assert_awaited_once()
        self.orchestrator.fundamental_agent.process.assert_awaited_once()
        self.orchestrator.news_agent.process.assert_awaited_once()
        self.orchestrator.research_agent.process.assert_awaited_once()
        self.orchestrator.investment_agent.process.assert_awaited_once()

    async def test_partial_workflow_only(self):
        # Setup Mocks
        retrieval_out = MagicMock(spec=RetrievalAgentOutput)
        retrieval_out.status = "success"
        self.orchestrator.retrieval_agent.process.return_value = retrieval_out

        # Run only retrieval
        req = WorkflowRequest(query="test", ticker="AAPL", only_steps=[StepName.RETRIEVAL])
        res = await self.orchestrator.run_workflow(req)

        # Verify
        self.assertEqual(res.retrieval.status, StepStatus.COMPLETED)
        self.assertEqual(res.fundamental.status, StepStatus.SKIPPED)
        self.assertEqual(res.news.status, StepStatus.SKIPPED)

        self.assertEqual(res.status, WorkflowStatus.PARTIAL)
        self.orchestrator.fundamental_agent.process.assert_not_awaited()

    async def test_parallel_failure_handling(self):
        # Mock Retrieval Success
        retrieval_out = MagicMock(spec=RetrievalAgentOutput)
        retrieval_out.status = "success"
        self.orchestrator.retrieval_agent.process.return_value = retrieval_out

        # Mock Fundamental Success
        fund_out = MagicMock(spec=FundamentalAnalystOutput)
        self.orchestrator.fundamental_agent.process.return_value = fund_out

        # Mock News Failure via Exception
        self.orchestrator.news_agent.process.side_effect = Exception("News API Error")

        # Run
        req = WorkflowRequest(query="test", ticker="AAPL")
        res = await self.orchestrator.run_workflow(req)

        # Verify
        self.assertEqual(res.retrieval.status, StepStatus.COMPLETED)
        self.assertEqual(res.fundamental.status, StepStatus.COMPLETED)
        self.assertEqual(res.news.status, StepStatus.FAILED)
        self.assertIn("News API Error", res.news.warnings[0])

        # Research should be skipped or partially handled depending on logic
        # Current logic checks strictly for success of enabled steps
        self.assertEqual(res.research.status, StepStatus.SKIPPED)
        self.assertEqual(res.status, WorkflowStatus.FAILED)

    async def test_caching(self):
        # Mock Cache Hit for Retrieval
        cached_retrieval = MagicMock()
        cached_retrieval.step_name = StepName.RETRIEVAL
        cached_retrieval.status = StepStatus.COMPLETED
        cached_retrieval.output = MagicMock(spec=RetrievalAgentOutput)

        # Configure cache to return result for retrieval key, None for others
        def side_effect(key):
            print(f"DEBUG: Cache.get called with key='{key}'")
            if "retrieval" in key:
                print("DEBUG: Returning cached_retrieval")
                return cached_retrieval
            print("DEBUG: Returning None")
            return None

        self.mock_cache.get.side_effect = side_effect

        # Mock downstream agents to return proper values
        fund_out = MagicMock(spec=FundamentalAnalystOutput)
        self.orchestrator.fundamental_agent.process.return_value = fund_out

        news_out = MagicMock(spec=NewsAnalystOutput)
        self.orchestrator.news_agent.process.return_value = news_out

        research_out = MagicMock(spec=ResearchAnalystOutput)
        self.orchestrator.research_agent.process.return_value = research_out

        invest_out = MagicMock(spec=InvestmentManagerOutput)
        self.orchestrator.investment_agent.process.return_value = invest_out

        # Run
        req = WorkflowRequest(query="test", ticker="AAPL")
        res = await self.orchestrator.run_workflow(req, workflow_id="cached_wf")

        # Verify Retrieval Agent NOT called (cached)
        print(
            f"DEBUG: retrieval_agent.process.await_count = {self.orchestrator.retrieval_agent.process.await_count}"
        )
        self.orchestrator.retrieval_agent.process.assert_not_awaited()
        self.assertEqual(res.retrieval, cached_retrieval)

    async def test_streaming_generator(self):
        # Setup Mocks
        retrieval_out = MagicMock(spec=RetrievalAgentOutput)
        retrieval_out.status = "success"
        self.orchestrator.retrieval_agent.process.return_value = retrieval_out

        # Stop at retrieval effectively
        req = WorkflowRequest(query="test", ticker="AAPL", only_steps=[StepName.RETRIEVAL])

        events = []
        async for event in self.orchestrator.workflow_generator(req, "stream_id"):
            events.append(event)

        # Should have step_start, step_complete, workflow_complete
        event_types = [e.event for e in events]
        self.assertIn("step_start", event_types)
        self.assertIn("step_complete", event_types)
        self.assertIn("workflow_complete", event_types)
        self.assertEqual(events[-1].status, WorkflowStatus.PARTIAL)

    async def test_full_streaming_events(self):
        # Setup Mocks for all agents
        self.orchestrator.retrieval_agent.process.return_value = MagicMock(
            spec=RetrievalAgentOutput, status="success"
        )
        self.orchestrator.fundamental_agent.process.return_value = MagicMock(
            spec=FundamentalAnalystOutput
        )
        self.orchestrator.news_agent.process.return_value = MagicMock(spec=NewsAnalystOutput)
        self.orchestrator.research_agent.process.return_value = MagicMock(
            spec=ResearchAnalystOutput
        )
        self.orchestrator.investment_agent.process.return_value = MagicMock(
            spec=InvestmentManagerOutput
        )

        req = WorkflowRequest(query="test", ticker="AAPL")
        events = []
        async for event in self.orchestrator.workflow_generator(req, "test_full_stream"):
            events.append(event)
            print(f"DEBUG EVENT: {event.event} for step {event.step}")

        # Check for start and complete for each step
        for step in [
            StepName.RETRIEVAL,
            StepName.FUNDAMENTAL,
            StepName.NEWS,
            StepName.RESEARCH,
            StepName.INVESTMENT,
        ]:
            starts = [e for e in events if e.event == "step_start" and e.step == step]
            completes = [e for e in events if e.event == "step_complete" and e.step == step]
            self.assertTrue(len(starts) > 0, f"Missing step_start for {step}")
            self.assertTrue(len(completes) > 0, f"Missing step_complete for {step}")
