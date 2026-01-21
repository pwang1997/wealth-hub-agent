# Change: Add workflow run history persistence and retrieval

## Why
- Workflow runs are not durable beyond in-memory responses, making it impossible for users to revisit prior runs.
- Step outputs are cached per workflow id, but there is no run-level record or API to list and inspect historical workflows.

## What Changes
- Persist workflow run records focused on per-agent results (per-step outputs with status/warnings) plus minimal metadata (workflow id, timestamps, ticker) in a disk-backed diskcache store, with an opt-out flag on `/v1/workflow/run` (`temp_workflow`) to skip persistence.
- Persist structured workflow event logs (step start/complete, workflow complete, errors) alongside run records.
- Add FastAPI endpoints to list workflow runs and fetch details/logs by workflow id.

## Impact
- Affected specs: workflow_orchestrator
- Affected code: orchestrator persistence hooks, workflow routes, storage/config modules, tests
