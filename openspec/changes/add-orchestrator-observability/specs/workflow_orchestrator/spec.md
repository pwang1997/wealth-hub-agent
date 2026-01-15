## ADDED Requirements
### Requirement: Structured observability across orchestrated steps
The system SHALL emit structured logs for each orchestrated step and each pipeline node, including workflow/request id, agent name, step/node name, start/end timestamps, duration, and status (started/completed/failed/skipped). Logging MUST be visible for API-triggered workflows.

#### Scenario: API execution shows node logs
- **WHEN** the workflow is invoked via the API endpoint
- **THEN** INFO-level logs display node start/end/duration with a workflow id, without being suppressed by prior logging configuration.

#### Scenario: Parallel branch visibility
- **WHEN** fundamental and news analysis run in parallel
- **THEN** each branch emits start/completion/exception logs with the shared workflow id so failures in one branch are observable without masking the other branch.
