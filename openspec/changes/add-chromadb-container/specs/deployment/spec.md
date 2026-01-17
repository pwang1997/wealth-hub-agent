## ADDED Requirements
### Requirement: Local ChromaDB Service
The system SHALL provide a ChromaDB container in local docker-compose workflows with persistent storage and a stable network address for dependent services. The local container SHALL be a first-class option for `clients/chroma_client.py` to connect without requiring Chroma Cloud credentials.

#### Scenario: Backend connects to ChromaDB container
- **WHEN** docker-compose is started
- **THEN** the backend can reach ChromaDB via a service hostname and configured port

#### Scenario: MCP servers use the shared ChromaDB container
- **WHEN** MCP servers start under docker-compose
- **THEN** they connect to the same ChromaDB service via `clients/chroma_client.py`

### Requirement: ChromaDB Database Initialization
The system SHALL ensure the configured ChromaDB database exists on container startup for local workflows.

#### Scenario: Database is created when missing
- **WHEN** the ChromaDB service starts with a configured database name
- **THEN** the service ensures the database exists before dependent services connect
