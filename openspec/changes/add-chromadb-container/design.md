## Context
Local container workflows currently run MCP servers and the backend without a containerized ChromaDB dependency, which makes local setup inconsistent.

## Goals / Non-Goals
- Goals: Provide a ChromaDB service in docker-compose with persistent storage and predictable connectivity for the backend and MCP servers.
- Non-Goals: Redesign ChromaDB usage, change vector schema, or migrate existing local data.

## Decisions
- Decision: Add a ChromaDB container service in compose and wire environment variables for service discovery.
- Decision: Run a lightweight init script on container startup to ensure the target database exists.
- Decision: All local services (backend and MCP) use the same ChromaDB container via `clients/chroma_client.py`.
- Alternatives considered: Manual local ChromaDB install (inconsistent), embedding ChromaDB in the backend container (larger image, coupled lifecycle).

## Risks / Trade-offs
- Risk: Data persistence could be lost if volumes are misconfigured -> Mitigation: Named volume and documented path.

## Migration Plan
- Add service and env wiring in compose.
- Update docs/examples for local env variables if needed.

## Open Questions
- None.
