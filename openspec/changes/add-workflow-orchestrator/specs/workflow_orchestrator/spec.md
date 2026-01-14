## ADDED Requirements
### Requirement: Workflow orchestration entrypoint
The system SHALL expose a workflow orchestrator that sequences the existing agents in the order: retrieval → fundamental analysis → news sentiment analysis → research synthesis → investment decision. It MUST accept controls to run the full pipeline or a caller-selected subset (e.g., `only`/`until`), and MUST return a structured response with per-step status and outputs. Inputs MUST include `query`, `ticker`, and may include `company_name`, `news_limit`, and other retrieval parameters. Step selectors MUST be validated as an ordered subsequence of the canonical pipeline; invalid combinations SHALL return an error without executing.

#### Scenario: Run full workflow
- **WHEN** the caller invokes the orchestrator without limiting steps
- **THEN** it executes all steps in order and returns each step's output with status `completed`.

#### Scenario: Run subset of steps
- **WHEN** the caller specifies a subset (e.g., only news sentiment or stop `until` research)
- **THEN** the orchestrator executes only those steps, marks unrun steps as `skipped` or omits them, and returns the executed steps with status `partial` overall.

### Requirement: Parallel analysis branch handling
The orchestrator SHALL execute fundamental analysis and news sentiment analysis in parallel using the shared retrieval result. It MUST capture each branch's status/output independently and handle failures without losing the other branch's result.

#### Scenario: One branch fails
- **WHEN** news analysis fails but fundamentals succeed
- **THEN** the orchestrator returns the fundamental output, marks the news branch as `failed` with warnings, and flags downstream synthesis/decision as `skipped` or `partial` due to missing inputs.

### Requirement: Response shape with per-step status and warnings
The orchestrator SHALL return a response object that includes per-step status, output payload, and propagated warnings/errors so callers can audit or retry specific steps. Overall status SHALL reflect completion vs partial. Allowed per-step statuses are `completed`, `skipped`, `failed`, and `partial`. Overall status SHALL be `completed` only if all required steps complete; otherwise `partial` if steps were intentionally skipped; `failed` if any executed step fails.

#### Scenario: Partial response when stopping early
- **WHEN** the caller stops at `until=research`
- **THEN** the response includes retrieval, fundamental, news, and research steps with `status` fields and any warnings, and the overall workflow status is `partial` because investment was not executed.

### Requirement: Streamable workflow responses
The orchestrator SHALL expose a streamable HTTP response mode (e.g., SSE or chunked JSON) that emits step boundary events containing workflow id, step name, status, and any available payload snippets as the workflow progresses.

#### Scenario: Streaming step events
- **WHEN** the caller uses the streamable endpoint
- **THEN** the orchestrator emits events at each step start/completion with workflow id, step name, status, and partial/final payload, followed by a terminal event carrying the overall status.

### Requirement: Persist step inputs/outputs for fast retrieval
The orchestrator SHALL persist each step's inputs and outputs using disk-backed caching (e.g., `diskcache`) keyed by workflow id so that clients or internal retries can rapidly retrieve prior results without re-executing completed steps. Cached entries SHALL include step status and warnings. Cached data MUST be reused for subsequent status checks of the same workflow id and MAY be reused across requests when identical inputs are provided, subject to eviction policy configured for a reasonable retention window (e.g., TTL of 24 hours) to prevent unbounded disk usage.

#### Scenario: Retrieve cached step data
- **WHEN** a caller requests status for an in-flight or recently completed workflow
- **THEN** the orchestrator can serve the request/response data for any completed step from the cache without recomputing, and only executes missing steps.

### Requirement: Per-step timeout guards
Each orchestrated step SHALL enforce an explicit timeout (default 60 seconds per stage) to prevent zombie workflows. On timeout, the step status SHALL be `failed`, the overall workflow SHALL be marked `failed` unless downstream is intentionally skipped, and downstream dependent steps SHALL be marked `skipped` or `partial` accordingly.

#### Scenario: Timeout during news analysis
- **WHEN** the news sentiment stage exceeds 60 seconds
- **THEN** the orchestrator marks the news step as `failed` with a timeout warning, does not reuse the hung task, and marks downstream synthesis/manager steps as `skipped` or `partial` because required inputs are missing.
