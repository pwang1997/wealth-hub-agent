## Context
Workflow runs currently return responses to callers and cache per-step results in diskcache for fast retries, but there is no durable run history or log retention. A separate change (add-orchestrator-observability) is adding structured logs, which should be persisted for later inspection.

## Goals / Non-Goals
- Goals:
  - Persist workflow run records (inputs, timestamps, status, per-step outputs/warnings) in a durable store.
  - Persist structured workflow event logs for each run.
  - Provide FastAPI endpoints to list runs and fetch run details/logs.
- Non-Goals:
  - Building a UI or analytics dashboard.
  - Long-term archival or cross-system export (beyond configurable retention).
  - Changing workflow execution semantics.

## Decisions
- Use diskcache directly as the persistence layer in a dedicated directory separate from the step cache.
- Storage layout (all JSON-serializable):
  - `workflow_run:{workflow_id}` -> `WorkflowRunRecord` with minimal metadata (`started_at`, `completed_at`, `status`, `ticker`) and per-agent results (per-step outputs with status/warnings). LLM steps must include model identifiers and usage metrics (input/output tokens, total tokens, latency if available).
  - `workflow_events:{workflow_id}` -> ordered list of `WorkflowEventRecord` entries (step_start/step_complete/workflow_complete/error) with timestamps and payload snapshots.
  - `workflow_runs:index` -> list of `{completed_at, workflow_id}` sorted by `completed_at` descending for pagination; run volume is expected to remain small for local usage.
- Update run record + index within a `cache.transact()` block to keep metadata and pagination consistent.
- Store full step outputs by default; persistence can be skipped via `temp_workflow=true` on `/v1/workflow/run`. Retention and size controls are opt-in via configuration.
- Add API endpoints under `/v1/workflow/runs` for listing runs and `/v1/workflow/runs/{workflow_id}` for details; add `/v1/workflow/runs/{workflow_id}/events` to retrieve logs.

## Risks / Trade-offs
- Diskcache listing may be slower at scale; mitigate with a lightweight index key and optional pruning.
- Persisting full outputs/logs may increase disk usage; mitigate with optional size limits and retention policies.
- Log payloads may include sensitive data; consider optional redaction or truncation.

## Migration Plan
- Default disk-backed storage requires no migration.

## Open Questions
