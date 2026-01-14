# Change: Add workflow orchestrator entrypoint

## Why
- Callers need a single entrypoint to run the end-to-end investment workflow without duplicating orchestration logic across the API surface.
- The system must allow partial execution (e.g., only news sentiment or stop at research) while reusing the same pipeline sequencing.
- Streamed progress and cached step results reduce latency for status checks and avoid rerunning completed work.

## What Changes
- Introduce a workflow orchestrator that sequences retrieval → fundamental analysis → news sentiment analysis (in parallel) → research synthesis → investment decision.
- Add controls to run full or partial workflows (`only`/`until`) and return per-step outputs/status so clients can stop early.
- Expose the orchestrator via the API with both standard and streaming (SSE/chunked JSON) endpoints.
- Enforce per-step timeouts (default 60s) and persist step inputs/outputs/status with disk-backed caching (e.g., 24h TTL) to prevent zombie runs and enable fast reuse/status checks.

## Impact
- Affected specs: workflow_orchestrator (new capability)
- Affected code: orchestration layer (new module), FastAPI route/handler (standard + streaming), state/response models shared with agents, caching configuration.
