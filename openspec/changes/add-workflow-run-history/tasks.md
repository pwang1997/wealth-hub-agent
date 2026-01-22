## 1. Implementation
- [x] 1.1 Define workflow run persistence models and store interface (per-agent results + minimal metadata)
- [x] 1.2 Capture and persist LLM usage metadata (model id, token counts, latency) for LLM-invoking steps
- [x] 1.3 Implement diskcache-backed run store with optional retention controls
- [x] 1.4 Persist run records and structured event logs during workflow execution (skip when `temp_workflow=true`)
- [x] 1.5 Add FastAPI endpoints for run listing (pagination + ticker filter + completion-time ordering), run detail (optional step outputs, 404 on unknown id), and event log retrieval
- [x] 1.6 Add tests for persistence and API behaviors
- [x] 1.7 Document configuration and optional retention controls
