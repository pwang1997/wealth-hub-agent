# Capability: Analyst Retrieval Agent

## ADDED Requirements

### Requirement: Retrieve analyst-report context from ChromaDB
The system SHALL provide an analyst/report retrieval agent that retrieves relevant document chunks from the vector database by calling the logic in `src/agent_tools/rag/retrieve_report.py`.

#### Scenario: RAG retrieval returns ranked matches
- **GIVEN** a user query
- **WHEN** the agent performs retrieval
- **THEN** the agent returns the top 5 matches in `rag.matches` and a prompt-ready `rag.context`

#### Scenario: No Chroma collections exist yet
- **GIVEN** no Chroma collections are available for the requested domain/corpus/company
- **WHEN** the agent performs retrieval
- **THEN** the agent returns a structured error indicating that PDFs must be indexed first

### Requirement: Discover relevant EDGAR filings for research
The system SHALL support financial report research by discovering relevant SEC EDGAR filings using `src/agent_tools/edgar/search_reports.py`.

#### Scenario: Query requests a specific SEC form
- **GIVEN** a user query that mentions an SEC form (e.g., “10-K”)
- **WHEN** the agent processes the query with a company ticker
- **THEN** the agent returns EDGAR filing links including form, filing date, accession number, and href

#### Scenario: Ticker does not map to a CIK
- **GIVEN** a user query with a ticker that is not recognized by EDGAR
- **WHEN** the agent calls EDGAR discovery
- **THEN** the agent returns a structured error indicating the ticker/CIK lookup failed

### Requirement: Prefer recent EDGAR filings
When EDGAR is used, the system SHALL prefer filings that are relatively new (within approximately 6 months).

#### Scenario: EDGAR discovery filters to recent filings
- **GIVEN** the agent uses EDGAR discovery
- **WHEN** the agent selects filings to fetch/index
- **THEN** the selected filings are within the last ~6 months when such filings are available

### Requirement: EDGAR ingestion complies with SEC rate limits
When fetching and ingesting EDGAR content, the system SHALL comply with SEC EDGAR API guidance by rate-limiting EDGAR requests to a maximum of 10 requests/second and avoiding multi-threading for EDGAR ingestion requests.

#### Scenario: EDGAR ingestion is rate-limited and single-threaded
- **GIVEN** the agent is ingesting EDGAR filings as part of fallback behavior
- **WHEN** multiple EDGAR HTTP requests are required to fetch filing content
- **THEN** the agent issues requests sequentially and enforces a maximum rate of 10 requests/second

### Requirement: EDGAR ingestion is limited per query
When ingesting EDGAR filings as fallback behavior, the system SHALL ingest at most 3 filings per query.

#### Scenario: EDGAR ingestion caps filings per query
- **GIVEN** EDGAR discovery returns more than 3 candidate filings
- **WHEN** the agent selects filings to fetch/index
- **THEN** the agent selects and ingests no more than 3 filings for that query

### Requirement: EDGAR documents are indexed into form-specific collections
When indexing EDGAR-derived content into ChromaDB, the system SHALL index into `corpus=edgar` and the chosen collection name SHALL include the SEC form so downstream agents can reliably target the appropriate filing type.

#### Scenario: EDGAR ingest chooses a form-specific collection
- **GIVEN** the agent ingests an EDGAR 10-K primary document for a company
- **WHEN** the agent writes chunks to ChromaDB
- **THEN** the collection name includes `edgar` and the form (e.g., `..._edgar_..._10-K`)

### Requirement: Fallback ingestion when no RAG matches
If the vector database contains no relevant matches for a query, the system SHALL use EDGAR to discover and ingest relevant filings into ChromaDB, and then rerun retrieval.

#### Scenario: No RAG matches triggers EDGAR ingest and retry
- **GIVEN** a user query and a target company
- **AND** initial vector retrieval returns no relevant matches
- **WHEN** the agent completes its workflow
- **THEN** the agent discovers recent EDGAR filings, upserts content into ChromaDB, reruns retrieval, and returns the top 5 matches

### Requirement: Tool routing and partial success
The system SHALL allow partial success: failure in one retrieval source SHALL NOT prevent returning results from the other source.

#### Scenario: RAG succeeds but EDGAR fails
- **GIVEN** RAG retrieval returns matches
- **AND** EDGAR discovery fails due to an upstream error
- **WHEN** the agent completes the request
- **THEN** the response includes `rag` results and an `errors` entry for the EDGAR failure

### Requirement: Stable, JSON-serializable response
The system SHALL return a structured “final answer” suitable for downstream agent use, preferably represented as a Pydantic model and serialized to JSON with stable top-level keys.

#### Scenario: Successful retrieval bundle
- **GIVEN** a valid user query
- **WHEN** the agent completes its retrieval workflow
- **THEN** the response includes `query`, `rag`, `edgar` (or `null`), and `errors`

#### Scenario: Downstream agent consumes the result
- **GIVEN** the analyst retrieval agent returns a result
- **WHEN** a downstream agent receives the result for further reasoning/workflow steps
- **THEN** the downstream agent can parse the result deterministically via the Pydantic schema (or the equivalent JSON schema)
