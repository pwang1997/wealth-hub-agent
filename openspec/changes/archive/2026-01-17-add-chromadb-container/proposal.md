# Change: Add ChromaDB Container to Docker Compose

## Why
Local container workflows need a first-class, reproducible ChromaDB service so the backend and MCP stack can rely on a consistent vector store without manual setup.

## What Changes
- Add a ChromaDB service to `docker-compose.yml` with persistent storage
- Wire backend/MCP configuration to point at the ChromaDB container as the shared local store
- Add an init script that ensures the configured ChromaDB database exists on container startup
- Document required environment variables and defaults in compose

## Impact
- Affected specs: deployment
- Affected code: docker-compose.yml, environment configuration
