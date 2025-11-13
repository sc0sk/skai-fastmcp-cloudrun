# Feature Specification: Fresh PostgreSQL Database Setup & Speech Population

**Feature Branch**: `017-fresh-postgres-population`  
**Created**: 2025-10-26  
**Status**: Draft  
**Input**: User requirement to bypass migration complexity and create fresh database with populated speeches using LangChain 1.0

## User Scenarios & Testing

### User Story 1 - Create Fresh pgvector-Enabled Database (Priority: P1)

System administrator needs to create a clean PostgreSQL database with pgvector extension and langchain-postgres schema tables (`langchain_pg_collection` and `langchain_pg_embedding`).

**Why this priority**: P1 because it's the foundation—without the schema, no data can be loaded.

**Independent Test**: Can be fully tested by: (1) Connecting to Cloud SQL instance, (2) Creating database "hansard_db_fresh", (3) Enabling pgvector extension, (4) Verifying schema tables exist with correct columns and indexes.

**Acceptance Scenarios**:

1. **Given** Cloud SQL instance hansard-db-v2 exists, **When** setup script runs, **Then** database "hansard_db_fresh" is created and pgvector extension is enabled
2. **Given** pgvector is enabled, **When** schema creation runs, **Then** `langchain_pg_collection` table exists with uuid, name, and cmetadata columns
3. **Given** schema exists, **When** schema creation runs, **Then** `langchain_pg_embedding` table exists with id, collection_id, embedding (vector 768d), document, and cmetadata columns
4. **Given** embedding table exists, **When** index creation runs, **Then** HNSW index exists on embedding column with cosine distance

---

### User Story 2 - Bulk Load Speeches from Markdown Files (Priority: P1)

Data engineer needs to bulk load Hansard speeches from markdown files in `data/hansard_converted/` directory using LangChain 1.0 text splitter and Vertex AI embeddings.

**Why this priority**: P1 because population is the second critical step—we need data to test the system.

**Independent Test**: Can be fully tested by: (1) Counting markdown files in source directory, (2) Running bulk loader, (3) Querying langchain_pg_embedding table to verify row count matches expected chunks, (4) Sampling embedding vectors to verify they have correct dimensionality (768).

**Acceptance Scenarios**:

1. **Given** markdown files exist in `data/hansard_converted/`, **When** bulk loader runs, **Then** speeches are split into chunks using RecursiveCharacterTextSplitter
2. **Given** chunks are created, **When** embeddings are generated, **Then** Vertex AI embeddings service creates 768-dimensional vectors for each chunk
3. **Given** embeddings exist, **When** inserts occur, **Then** langchain_pg_embedding table contains rows with: id, collection_id referencing hansard collection, embedding vectors, full document text, and cmetadata JSON
4. **Given** data is loaded, **When** query executes `SELECT COUNT(*) FROM langchain_pg_embedding`, **Then** count matches expected number of chunks

---

### User Story 3 - Store Speech Metadata in cmetadata JSONB (Priority: P1)

Data engineer needs to extract and store speech metadata (speaker, date, hansard_id, speech_type, etc.) in the cmetadata JSONB column for filtering and context.

**Why this priority**: P1 because metadata filtering is essential for search relevance—queries need to filter by speaker, date range, etc.

**Independent Test**: Can be fully tested by: (1) Inspecting cmetadata column contents, (2) Verifying JSONB contains required fields, (3) Running metadata-based queries to confirm filtering works.

**Acceptance Scenarios**:

1. **Given** speeches are loaded, **When** metadata extraction runs, **Then** cmetadata JSONB contains: speaker, date, hansard_id, speech_type, hansard_url
2. **Given** cmetadata exists, **When** query filters `WHERE cmetadata->>'speaker' = 'John Smith'`, **Then** only chunks from that speaker are returned
3. **Given** date metadata exists, **When** query filters by date range, **Then** only chunks within that range are returned

---

### User Story 4 - Verify Data Integrity & Search Functionality (Priority: P2)

QA engineer needs to verify that loaded data is correct and search queries work end-to-end.

**Why this priority**: P2 because it's validation—critical but comes after population.

**Independent Test**: Can be fully tested by: (1) Running smoke tests with sample search queries, (2) Comparing vector similarity results, (3) Verifying metadata filtering produces correct results.

**Acceptance Scenarios**:

1. **Given** data is loaded, **When** similarity search executes with a test query, **Then** results are ranked by cosine distance and top results are relevant
2. **Given** metadata exists, **When** filtering query executes, **Then** results respect metadata constraints
3. **Given** embeddings are loaded, **When** querying with HNSW index, **Then** queries complete in <500ms

---

### User Story 5 - Switch Cloud Run Service to Use New Database (Priority: P2)

Operations engineer needs to update Cloud Run service `hansard-mcp` environment variable `VECTOR_BACKEND=postgres` to point to new database connection string.

**Why this priority**: P2 because it's deployment—happens after all data validation.

**Independent Test**: Can be fully tested by: (1) Updating env var, (2) Redeploying service, (3) Making MCP tool request, (4) Verifying search queries return results from new database.

**Acceptance Scenarios**:

1. **Given** new database is populated, **When** Cloud Run service env var is updated to `VECTOR_BACKEND=postgres`, **Then** service restarts with new config
2. **Given** service is updated, **When** search MCP tool is invoked, **Then** query is executed against postgres backend
3. **Given** postgres backend is active, **When** search request is made, **Then** results include speech chunks from new database

---

### Edge Cases

- What happens if markdown files have missing metadata frontmatter? → Use defaults or skip, log warning
- How are duplicate speeches handled? → Use unique hansard_id + chunk_index as compound key
- What if Vertex AI embeddings service is unavailable? → Retry with exponential backoff, fail gracefully with retry count
- How are very long speeches handled? → Split into chunks respecting token boundaries, link chunks via metadata

## Requirements

### Functional Requirements

- **FR-001**: System MUST create PostgreSQL database "hansard_db_fresh" on Cloud SQL instance hansard-db-v2
- **FR-002**: System MUST enable pgvector extension in new database
- **FR-003**: System MUST create langchain-postgres schema tables (langchain_pg_collection, langchain_pg_embedding)
- **FR-004**: System MUST create HNSW index on embedding column for fast vector similarity search
- **FR-005**: System MUST read markdown files from `data/hansard_converted/` directory using glob patterns
- **FR-006**: System MUST parse frontmatter metadata from markdown files using python-frontmatter
- **FR-007**: System MUST split speeches into chunks using LangChain RecursiveCharacterTextSplitter (chunk_size=1000, overlap=100)
- **FR-008**: System MUST generate embeddings using Vertex AI embeddings API via langchain-google-vertexai
- **FR-009**: System MUST store chunks in langchain_pg_embedding with: id, collection_id, embedding, document, cmetadata
- **FR-010**: System MUST store metadata (speaker, date, hansard_id, speech_type, url) in cmetadata JSONB
- **FR-011**: System MUST handle IAM authentication to Cloud SQL using service account credentials
- **FR-012**: System MUST retry failed embedding requests with exponential backoff
- **FR-013**: System MUST log progress (files processed, chunks created, embeddings generated, rows inserted)
- **FR-014**: System MUST provide smoke test queries to verify data loaded and search works
- **FR-015**: System MUST allow Cloud Run service to connect to new database via environment variable

### Key Entities

- **Speech Chunk**: Document text chunk with embedding vector (768d), metadata, and database row
  - Attributes: id (unique), text, embedding, speaker, date, hansard_id, speech_type, url
  - Relationships: belongs to one Collection, references original Speech
  
- **Collection**: Named group of related embeddings (e.g., "hansard-speeches-2023")
  - Attributes: uuid, name, cmetadata
  - Relationships: contains many Embeddings
  
- **Metadata**: JSONB object stored with chunk containing speaker, date, url, and speech identifiers
  - Attributes: speaker (string), date (ISO string), hansard_id (string), speech_type (string), url (string)
  - Relationships: stored in langchain_pg_embedding.cmetadata

## Success Criteria

### Measurable Outcomes

- **SC-001**: Database creation and schema setup completes in <60 seconds
- **SC-002**: All markdown files in `data/hansard_converted/` are successfully loaded (100% file success rate)
- **SC-003**: Speech chunks are created with correct average token count (~500-1000 tokens per chunk)
- **SC-004**: Embedding vectors are generated with correct dimensionality (768) for all chunks
- **SC-005**: At least 95% of chunks successfully inserted into langchain_pg_embedding table
- **SC-006**: Metadata JSONB contains all required fields for at least 90% of chunks
- **SC-007**: Sample search query completes in <500ms using HNSW index
- **SC-008**: Smoke test queries return relevant results with >80% precision for test queries
- **SC-009**: Cloud Run service successfully connects to new database and executes searches
- **SC-010**: Zero data loss—all chunks have corresponding embedding vectors and metadata
