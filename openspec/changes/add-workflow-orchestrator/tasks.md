## 1. Implementation
- [ ] 1.1 Define orchestrator contract: required inputs (`query`, `ticker`), optional inputs (`company_name`, limits), validated step selectors as ordered subsequence (`only`/`until`), per-step/overall status model, and response shape (with workflow id, per-step status/output/warnings).
- [ ] 1.2 Implement orchestrator: retrieval → {fundamental, news} in parallel → research → investment with step gating, per-step 60s timeouts, and branch failure rules for downstream.
- [ ] 1.3 Add disk-backed caching (e.g., diskcache) of step inputs/outputs/status with ~24h TTL; reuse cached steps for same workflow id and identical inputs.
- [ ] 1.4 Wire FastAPI endpoints: standard response and streamable (SSE/chunked JSON) emitting step boundary events and terminal status.
- [ ] 1.5 Add tests for full/partial runs, invalid step selector handling, branch failure propagation, timeout behavior, cache reuse, and response/stream event structure.
