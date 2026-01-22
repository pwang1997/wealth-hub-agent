## ADDED Requirements
### Requirement: Workflow run persistence for history
The system SHALL persist each workflow run's per-agent results (per-step outputs with status/warnings) along with minimal metadata (workflow id, timestamps, overall status, ticker) to a durable store for later retrieval using diskcache. For steps that invoke an LLM, the stored metadata MUST include model identifiers and usage metrics (e.g., input/output tokens, total tokens, latency if available), not just the response content. Persistence MUST be skipped when the caller sets `temp_workflow=true` on `/v1/workflow/run`. Persisted runs MUST be retrievable by workflow id until explicitly deleted or pruned by a configured retention policy.

#### Scenario: Persist and retrieve completed run
- **WHEN** a workflow completes successfully or partially
- **THEN** its run record can be retrieved by workflow id without re-executing the workflow.

### Requirement: Workflow event log retention
The system SHALL capture structured workflow events (step_start, step_complete, workflow_complete, error) with timestamps and persist them with the run record. Event logs MUST be retrievable by workflow id and MAY be paginated or tailed.

#### Scenario: Retrieve event log for a run
- **WHEN** a client requests the event log for a stored workflow id
- **THEN** the API returns the ordered events for that run (or the requested tail).

### Requirement: Workflow run history API
The system SHALL expose API endpoints to list and fetch stored workflow runs, including run metadata and optional step outputs. The list endpoint MUST support pagination and optional filtering by ticker. The detail endpoint MUST return a not-found error for unknown workflow ids.

#### Scenario: List recent runs
- **WHEN** a client requests the run list with a limit and ticker filter
- **THEN** the API returns matching run summaries ordered by completion time (descending).
