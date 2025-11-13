# Feature Specification: Update LangChain to 1.0

**Feature Branch**: `014-update-langchain-1-0`  
**Created**: 2025-10-25  
**Status**: Draft  
**Type**: Dependency Upgrade  
**Input**: User description: "Update LangChain to 1.0"  
**Constitution**: Not applicable (project constitution is template-only; no formal principles enforced)

## Problem Statement

The project currently uses LangChain 0.x without version pinning in `pyproject.toml`. LangChain 1.0 introduced significant breaking changes, including:

1. **Import path changes**: Many modules moved (e.g., `langchain.text_splitter` → `langchain_text_splitters`)
2. **API updates**: Method signatures and class interfaces changed
3. **Deprecations**: Several classes and functions removed or renamed
4. **New features**: Improved async support, better type hints, performance improvements

**Current LangChain Usage** in this project:
- `langchain_google_cloud_sql_pg` - PostgreSQL vector store with pgvector
- `langchain_google_vertexai` - Vertex AI embeddings
- `langchain.text_splitter.RecursiveCharacterTextSplitter` - Document chunking
- Integration in `src/storage/vector_store.py`, `src/tools/ingest.py`, `src/tools/ingest_markdown_file.py`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Seamless Upgrade (Priority: P1)

**As a** developer maintaining the Hansard MCP server  
**I want to** upgrade to LangChain 1.0 without breaking existing functionality  
**So that** the project stays current with security patches and new features

**Why this priority**: Critical for security updates, bug fixes, and long-term maintainability. LangChain 0.x will eventually become unsupported.

**Independent Test**: Can be fully tested by running existing test suite (`test_tools.py`, unit tests) and verifying all vector operations (search, ingest, embedding generation) work identically to before.

**Acceptance Scenarios**:

1. **Given** LangChain 1.0 is installed, **When** vector store initializes, **Then** connection succeeds and table schema remains compatible
2. **Given** LangChain 1.0 is installed, **When** text splitter chunks a document, **Then** chunk sizes and overlap behavior match 0.x exactly
3. **Given** LangChain 1.0 is installed, **When** embeddings are generated, **Then** vector dimensions and values match 0.x format

---

### User Story 2 - Backward Compatible Data (Priority: P1)

**As a** system operator  
**I want** existing database vectors and metadata to remain valid after upgrade  
**So that** I don't need to reindex the entire database (expensive operation)

**Why this priority**: Re-embedding 64+ speeches with Vertex AI is time-consuming and costly. Backward compatibility is essential.

**Independent Test**: Query existing speeches in database using LangChain 1.0 and verify search results match pre-upgrade behavior.

**Acceptance Scenarios**:

1. **Given** database contains speeches indexed with LangChain 0.x, **When** similarity search runs with 1.0, **Then** results are identical
2. **Given** database table schema from 0.x, **When** LangChain 1.0 connects, **Then** no schema migrations are triggered
3. **Given** existing vector dimensions (e.g., 768 for VertexAI), **When** new embeddings generate, **Then** dimensions remain unchanged

---

### User Story 3 - Updated Documentation (Priority: P2)

**As a** new contributor  
**I want** documentation reflecting LangChain 1.0 patterns  
**So that** examples and code comments match the installed version

**Why this priority**: Medium priority - functional correctness comes first, but good docs prevent confusion.

**Independent Test**: Review inline comments and ensure import paths, class names, and API calls match LangChain 1.0 official docs.

**Acceptance Scenarios**:

1. **Given** code comments reference LangChain classes, **When** developer reads them, **Then** class names match 1.0 API
2. **Given** README or DATABASE_SETUP.md mention LangChain, **When** developer follows examples, **Then** code samples work with 1.0
3. **Given** error messages reference LangChain features, **When** errors occur, **Then** stack traces show correct 1.0 module paths

---

### Edge Cases

- What if `langchain-google-cloud-sql-pg` or `langchain-google-vertexai` don't support 1.0 yet?
- How to handle deprecation warnings during transition period?
- What if LangChain 1.0 changes pgvector table structure?
- How to validate embedding compatibility without re-indexing everything?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST upgrade to `langchain>=1.0.0` in `pyproject.toml`
- **FR-002**: All import statements MUST use LangChain 1.0 module paths (e.g., `langchain_text_splitters` instead of `langchain.text_splitter`)
- **FR-003**: Text splitting behavior MUST remain byte-for-byte identical to 0.x for existing chunk configurations
- **FR-004**: Vector store connections MUST work with existing database schema (no forced migrations)
- **FR-005**: Embedding generation MUST produce same dimensions and compatible vectors as 0.x
- **FR-006**: All existing tests MUST pass without modification (except import path updates)
- **FR-007**: System MUST upgrade `langchain-google-vertexai` and `langchain-google-cloud-sql-pg` to compatible versions

### Non-Functional Requirements

- **NFR-001**: Upgrade process SHOULD complete in < 2 hours (research + implementation + testing)
- **NFR-002**: No database downtime or re-indexing required
- **NFR-003**: Performance SHOULD remain same or improve (LangChain 1.0 has optimizations)

### Key Entities *(include if feature involves data)*

- **Vector Store**: `PostgresVectorStore` - may have API changes in 1.0
- **Text Splitter**: `RecursiveCharacterTextSplitter` - import path definitely changed
- **Embeddings**: `VertexAIEmbeddings` - interface may have updates
- **Database Schema**: `langchain_pg_collection`, `langchain_pg_embedding` tables - must remain compatible

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All existing unit and integration tests pass with LangChain 1.0 installed
- **SC-002**: Vector similarity search returns identical results for test queries before and after upgrade
- **SC-003**: Text splitter produces identical chunk count and sizes for sample documents
- **SC-004**: Zero deprecation warnings appear in server logs
- **SC-005**: `pip install` succeeds without dependency conflicts
- **SC-006**: Production deployment to Cloud Run succeeds with new dependencies

### Testing Checklist

- [ ] Run `test_tools.py` - all searches return results
- [ ] Run `test_mcp_tools.py` - MCP tool calls work end-to-end
- [ ] Test ingestion with `ingest_markdown_file` tool - chunking works
- [ ] Query existing speeches - results match pre-upgrade
- [ ] Generate new embeddings - dimensions match (768 for VertexAI)
- [ ] Check for deprecation warnings in logs
- [ ] Deploy to Cloud Run - health check passes
