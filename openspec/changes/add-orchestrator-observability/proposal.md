# Change: Add observability for workflow orchestrator and pipelines

## Why
- Current logging is inconsistent and there is no structured visibility into each step/node of the orchestrated workflow.
- We need step-level timing/status to monitor, debug, and audit partial or parallel execution across agents.

## What Changes
- Add structured logging/timing for each orchestrated step and pipeline node (including parallel branches), emitting workflow/request ids, start/end, duration, status, and warnings.
- Ensure logging configuration is applied for API execution paths.
- Surface observability data in orchestrator responses where appropriate.

## Impact
- Affected specs: workflow_orchestrator (observability requirements)
- Affected code: orchestration layer instrumentation, pipeline base class, logging configuration utilities, CLI entrypoints (research flow), possibly FastAPI middleware/hooks.
