# Implementation Tasks: Australian Hansard RAG MVP

**Branch**: `001-hansard-rag-implementation`
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)
**Generated**: 2025-10-21

---

## Task Overview

**Total Tasks**: 45
**Estimated Duration**: 10-12 days
**Test Coverage Target**: >80%
**MVP Scope**: All 3 user stories (FR1, FR2, FR3)
**FastMCP Patterns**: Auto-registration, async tools, Context injection, Resources
**LangChain Integration**: PostgresVectorStore, VertexAIEmbeddings, hybrid search

### Task Distribution

| Phase | User Story | Task Count | Parallelizable |
|-------|------------|------------|----------------|
| Phase 1 | Setup | 8 | 0 |
| Phase 2 | Foundational | 6 | 4 |
| Phase 3 | FR1: Speech Ingestion | 10 | 6 |
| Phase 4 | FR2: Hybrid Search | 10 | 5 |
| Phase 5 | FR3: Speech Retrieval | 7 | 3 |
| Phase 6 | Polish & Integration | 4 | 1 |

---

## Implementation Strategy

**Architecture**: Google ADK-aligned (LangChain + Vertex AI + Cloud SQL pgvector)
**Development Approach**: Test-Driven Development (TDD) per constitution
**Deployment**: Local development with STDIO transport (Cloud Run deployment deferred to v2)

**MVP Delivery**:
1. Complete all foundational tasks (Phase 1-2)
2. Implement User Story 1 (Ingestion) with tests
3. Implement User Story 2 (Search) with tests
4. Implement User Story 3 (Retrieval) with tests
5. Polish and validate with MCP Inspector

**Sample Data**: 65 speeches from `/data/sk-hansard/` (Simon Kennedy MP, 2024-2025)

---

## Phase 1: Setup & Configuration

**Goal**: Initialize project structure, dependencies, and development environment

**Duration**: 1-2 days

### Tasks

- [ ] T001 Create project directory structure per plan.md (src/, tests/, data/, deployment/)
- [ ] T002 Initialize Python project with uv package manager (pyproject.toml)
- [ ] T003 Create fastmcp.json configuration with LangChain dependencies
- [ ] T004 Add core dependencies to pyproject.toml (fastmcp>=2.14.0, langchain-google-vertexai>=2.0.0, langchain-google-cloud-sql-pg>=0.12.0, pydantic>=2.5.0)
- [ ] T005 Add development dependencies to pyproject.toml (pytest, pytest-asyncio, pytest-cov, black, ruff, mypy)
- [ ] T006 Create .env.example file with environment variable templates (GCP_PROJECT_ID, CLOUDSQL_INSTANCE, REGION)
- [ ] T007 Create .gitignore file (exclude .env, *.db, __pycache__, .pytest_cache, data/*.json)
- [ ] T008 Create README.md with local development setup instructions (installation, configuration, running tests, using MCP Inspector)

**Acceptance Criteria**:
-  Project structure matches plan.md
-  `uv sync` installs all dependencies successfully
-  fastmcp.json validates with schema
-  .env.example documents all required variables

---

## Phase 2: Foundational Components

**Goal**: Build reusable components that all user stories depend on

**Duration**: 2-3 days

**Blocking**: None (all can start after Phase 1)

### Models & Validation

- [ ] T009 [P] Create SpeechMetadata Pydantic model in src/models/speech.py (all fields from data-model.md, validators for chamber, state, electorate)
- [ ] T010 [P] Create SpeechDetail Pydantic model in src/models/speech.py (extends SpeechMetadata with full_text, word_count)
- [ ] T011 [P] Create IngestionResult Pydantic model in src/models/results.py (speeches_processed, chunks_created, vectors_stored, duplicates_skipped, errors, processing_time_seconds)
- [ ] T012 [P] Create SearchResult Pydantic model in src/models/results.py (speech_id, chunk_id, excerpt, speaker, party, chamber, date, title, hansard_reference, topic_tags, relevance_score, chunk_index)

### Tests for Models

- [ ] T013 Create test_models.py with SpeechMetadata validation tests (valid inputs, chamber validation, electorate validation, state validation, computed fields)
- [ ] T014 Create test_chunking.py with RecursiveCharacterTextSplitter tests (800 char chunks, 150 overlap, sentence boundaries preserved)

**Acceptance Criteria**:
-  All Pydantic models have >95% test coverage
-  Validators reject invalid Australian states/chambers
-  Computed fields (word_count, content_hash) work correctly

---

## Phase 3: User Story 1 - Speech Ingestion (FR1)

**Goal**: Implement tool to ingest speeches from Markdown files with YAML frontmatter

**Priority**: P1 (Blocking for all other stories)
**Duration**: 3-4 days

**User Story**: As a developer, I want to ingest Australian Hansard speeches from Markdown files so that they can be searched semantically.

### Independent Test Criteria

 **Story Complete When**:
1. Can ingest 65 speeches from `/data/sk-hansard/` directory
2. All speeches validate against SpeechMetadata model
3. Text is chunked into ~200 chunks (800 char size, 150 overlap)
4. Embeddings generated using Vertex AI gemini-embedding-001 (768 dims)
5. Data stored in dual-table schema (speeches + speech_chunks)
6. Ingestion progress reported via MCP Context
7. Duplicate detection works (content_hash)
8. Tool returns IngestionResult with accurate stats
9. Test coverage >80% for ingestion code

### Tests (TDD)

- [ ] T015 Create test_ingest_tool.py with unit tests for ingest_markdown_speeches (file parsing, metadata transformation, party code mapping, hansard reference construction, error handling)
- [ ] T016 Create test_ingest_integration.py with end-to-end ingestion test (ingest sk-hansard dataset, verify 65 speeches processed, verify ~200 chunks created, verify no errors)

### Infrastructure

- [ ] T017 [P] Create text chunking service in src/processing/chunker.py (RecursiveCharacterTextSplitter config: 800 chars, 150 overlap, separators=["\n\n", "\n", ". ", " ", ""])
- [ ] T018 [P] Create Vertex AI embedding wrapper in src/storage/embeddings.py (VertexAIEmbeddings with model_name="gemini-embedding-001", task_type="RETRIEVAL_DOCUMENT", output_dimensionality=768, async methods)
- [ ] T019 Create Cloud SQL vector store manager in src/storage/vector_store.py (PostgresEngine initialization, PostgresVectorStore creation, table initialization with 768-dim vectors, HNSW index creation)
- [ ] T020 Create metadata store manager in src/storage/metadata_store.py (dual-table schema, speeches table CRUD, speech_chunks table operations, duplicate detection via content_hash)

### Tool Implementation

- [ ] T021 Create Markdown parser utility in src/processing/validators.py (parse YAML frontmatter using python-frontmatter, extract markdown body, map sk-hansard fields to SpeechMetadata, party code mapping, chamber normalization, hansard reference construction)
- [ ] T022 [P] Implement ingest_markdown_speeches tool in src/tools/ingest.py (async function with @mcp.tool() decorator, tags=["admin", "ingestion", "stable"], directory_path: str parameter, ctx: Context parameter for progress/logging, use await ctx.report_progress(current, total), raise ToolError for failures, return IngestionResult Pydantic model, full type hints)
- [ ] T023 Import tools in src/server.py to auto-register (from tools import ingest, search, retrieve - FastMCP auto-discovers @mcp.tool decorated functions)
- [ ] T024 Test ingestion with MCP Inspector (run `fastmcp dev src/server.py`, call ingest_markdown_speeches with sk-hansard path, verify 65 speeches ingested, check database tables populated)

**Acceptance Criteria**:
-  All tests pass with >80% coverage
-  Can ingest 65 sk-hansard speeches in <60 seconds
-  Duplicate ingestion skips existing speeches
-  Progress updates visible in MCP Inspector
-  Database contains 65 speeches and ~200 chunks with embeddings
-  Hansard references correctly formatted

---

## Phase 4: User Story 2 - Hybrid Search (FR2)

**Goal**: Implement semantic search with metadata filtering

**Priority**: P1 (Core RAG functionality)
**Duration**: 3-4 days
**Depends On**: Phase 3 (need ingested data)

**User Story**: As an AI assistant user, I want to search parliamentary speeches semantically with metadata filters so that I can find relevant political discourse.

### Independent Test Criteria

 **Story Complete When**:
1. Can search with text query: "climate change policy"
2. Returns top-10 relevant chunks with scores
3. Can filter by speaker: "Simon Kennedy"
4. Can filter by date range: 2024-01-01 to 2024-12-31
5. Can filter by chamber: "House of Representatives"
6. Can filter by party: "Liberal"
7. Can filter by topics: ["energy", "environment"]
8. Results sorted by relevance score (descending)
9. Search latency <500ms (p95) for local queries
10. Tool marked with readOnlyHint=True
11. Test coverage >80% for search code

### Tests (TDD)

- [ ] T025 Create test_search_tool.py with unit tests for search_speeches (query embedding generation, metadata filter construction, result ranking, pagination, error handling)
- [ ] T026 Create test_search_integration.py with end-to-end search tests (unfiltered search, speaker filter, date range filter, multi-filter combination, relevance score validation)
- [ ] T027 Create golden dataset test in tests/integration/test_golden_dataset.py (10 test queries with expected results, measure recall >90%, validate search quality)

### Implementation

- [ ] T028 [P] Create query embedding service in src/storage/embeddings.py (add async aembed_query method with task_type="RETRIEVAL_QUERY", use VertexAIEmbeddings.aembed_query())
- [ ] T029 [P] Create full-text search index in src/storage/metadata_store.py (add PostgreSQL tsvector column to speeches table, create GIN index on to_tsvector('english', full_text), implement async full_text_search method using ts_rank)
- [ ] T030 [P] Create vector search service in src/storage/vector_store.py (use PostgresVectorStore.asimilarity_search_with_score(), build filter dict for metadata, top-K retrieval, return LangChain Document objects with scores)
- [ ] T031 [P] Implement hybrid search combiner in src/storage/vector_store.py (combine vector similarity scores with BM25/full-text scores using Reciprocal Rank Fusion, configurable weights, return unified ranked results)
- [ ] T032 [P] Implement search_speeches tool in src/tools/search.py (async function with @mcp.tool() decorator, tags=["search", "rag", "stable"], readOnlyHint=True annotation, query: str parameter, use_hybrid: bool = True parameter, optional filters (speaker: str | None, party: str | None, etc.), ctx: Context for logging, return List[SearchResult] with full type hints)
- [ ] T033 Add search result enrichment in src/tools/search.py (map LangChain Document objects to SearchResult Pydantic models, extract metadata from Document.metadata, construct excerpt from page_content, normalize and combine hybrid scores)
- [ ] T034 Test search with MCP Inspector (verify tool auto-discovered, run queries against sk-hansard dataset, test vector-only vs hybrid search, verify metadata filtering, check relevance scores, validate response format)

**Acceptance Criteria**:
-  All tests pass with >80% coverage
-  Golden dataset achieves >90% recall
-  Search completes in <500ms (p95)
-  Metadata filters work correctly (AND logic)
-  Results include all required fields from SearchResult model
-  Tool discoverable in MCP Inspector with readOnlyHint

---

## Phase 5: User Story 3 - Speech Retrieval (FR3)

**Goal**: Retrieve complete speech by ID

**Priority**: P2 (Nice-to-have for context)
**Duration**: 2 days
**Depends On**: Phase 3 (need ingested data)

**User Story**: As an AI assistant user, I want to retrieve the full text of a specific speech so that I can read the complete context.

### Independent Test Criteria

 **Story Complete When**:
1. Can retrieve speech by speech_id
2. Returns SpeechDetail with full_text
3. Includes all metadata (speaker, party, chamber, date, hansard_reference)
4. Optional include_context parameter works (returns surrounding chunks)
5. Returns error for non-existent speech_id
6. Tool marked with readOnlyHint=True
7. Test coverage >80% for retrieval code

### Tests (TDD)

- [ ] T035 Create test_retrieve_tool.py with unit tests for get_speech (speech_id lookup, metadata retrieval, context inclusion, error handling for missing ID)
- [ ] T036 Create test_retrieve_integration.py with end-to-end retrieval tests (retrieve by valid ID, verify full text returned, test include_context=True, test non-existent ID error)

### Implementation

- [ ] T037 [P] Create speech retrieval service in src/storage/metadata_store.py (async get_speech_by_id method, query speeches table by UUID, optionally fetch surrounding chunks for context)
- [ ] T038 [P] Implement get_speech tool in src/tools/retrieve.py (async function with @mcp.tool() decorator, tags=["retrieve", "rag", "stable"], readOnlyHint=True annotation, speech_id: str parameter, include_context: bool = False parameter, ctx: Context for logging, return SpeechDetail Pydantic model with full type hints, raise ToolError if speech_id not found)
- [ ] T039 Define speech resource in src/tools/retrieve.py (@mcp.resource("hansard://speech/{speech_id}") decorator, async function accepting speech_id parameter, query database, return speech as TextResource or dict, enables clients to fetch speeches via URI)
- [ ] T040 Define speeches list resource in src/tools/retrieve.py (@mcp.resource("hansard://speeches") decorator with pagination query parameters, return list of speeches with metadata as JSON, enables browsing corpus)
- [ ] T041 Test retrieval with MCP Inspector (verify tool and resources auto-discovered, list_resources shows hansard:// URIs, retrieve speeches by ID, test hansard://speech/{id} resource URI, verify full text returned, test context inclusion, validate error messages)

**Acceptance Criteria**:
-  All tests pass with >80% coverage
-  Retrieval completes in <100ms
-  Full text matches ingested speech
-  Context inclusion works (surrounding chunks)
-  Error handling provides clear messages
-  Tool discoverable in MCP Inspector with readOnlyHint

---

## Phase 6: Polish & Integration Testing

**Goal**: Final integration, documentation, and MCP client validation

**Duration**: 1-2 days
**Depends On**: Phases 3, 4, 5 complete

### Tasks

- [ ] T042 [P] Create server.py with FastMCP setup (initialize mcp = FastMCP("Australian Hansard RAG"), use @mcp.lifespan() async context manager decorator, await PostgresEngine.afrom_instance(project_id, region, instance, database), create VertexAIEmbeddings(model_name="gemini-embedding-001"), await PostgresVectorStore.create(engine, table_name, embedding_service), import tool modules which auto-registers @mcp.tool and @mcp.resource decorated functions, yield during server lifetime, cleanup resources on shutdown)
- [ ] T043 Add dataset stats resource in server.py (@mcp.resource("hansard://dataset/stats") decorator, async function querying database for counts, return dict with speech_count, chunk_count, date_range, unique_speakers, topic_distribution)
- [ ] T044 Run full test suite and validate >80% coverage (pytest --cov=src --cov-report=html, review coverage report, ensure all tools and resources covered, validate async patterns work correctly)
- [ ] T045 Test complete workflow with MCP Inspector (list_tools shows 3 tools with correct metadata, list_resources shows 4+ resources with hansard:// URIs, ingest sk-hansard → search with hybrid mode → retrieve full speech, access resources via URI, verify end-to-end flow works, document example queries and resource URIs in README.md)

**Acceptance Criteria**:
-  All 3 tools visible in MCP Inspector
-  Test coverage >80% overall
-  End-to-end demo works: ingest � search � retrieve
-  README.md has quickstart guide
-  All constitution requirements met

---

## Dependencies & Execution Order

### Critical Path

```
Phase 1 (Setup)
  �
Phase 2 (Foundational: Models + Utils)
  �
Phase 3 (US1: Ingestion) � BLOCKING
  �
Phase 4 (US2: Search) + Phase 5 (US3: Retrieval) � Can run in parallel after Phase 3
  �
Phase 6 (Polish & Integration)
```

### Parallel Execution Opportunities

**Phase 2** (after T008 complete):
- T009, T010, T011, T012 can run in parallel (independent models)

**Phase 3** (after T016 complete):
- T017, T018 can run in parallel (independent services)
- T021, T022 can run in parallel (different concerns)

**Phase 4** (after T027 complete):
- T028, T029, T030 can run in parallel (independent components)

**Phase 5** (after T035 complete):
- T036, T037 can run in parallel (service + tool)

**Cross-Phase** (after Phase 3 complete):
- Phase 4 and Phase 5 can run fully in parallel

---

## Task Checklist Format

All tasks follow this format:
```
- [ ] T### [P] [US#] Description with file path
```

Where:
- `[P]` = Parallelizable (can run concurrently with other [P] tasks in same phase)
- `[US#]` = User Story label (US1=FR1, US2=FR2, US3=FR3)
- File paths are absolute from repository root

---

## Testing Strategy

**Test-Driven Development (TDD)**:
1. Write test first (what should happen)
2. Run test (should fail - red)
3. Implement feature
4. Run test (should pass - green)
5. Refactor while keeping tests green

**Test Coverage**:
- Unit tests: Individual functions and classes
- Integration tests: End-to-end tool workflows
- Golden dataset: Search quality validation (>90% recall)
- MCP Inspector: Manual tool validation

**Coverage Target**: >80% overall, 100% for public tool methods

---

## MCP Inspector Testing Commands

```bash
# Start server in dev mode
fastmcp dev src/server.py

# Browser opens at http://localhost:6274
# MCP Inspector automatically connects

# Test ingestion
{
  "name": "ingest_markdown_speeches",
  "arguments": {
    "directory_path": "/home/user/skai-fastmcp-cloudrun/data/sk-hansard"
  }
}

# Test search (unfiltered)
{
  "name": "search_speeches",
  "arguments": {
    "query": "climate change policy"
  }
}

# Test hybrid search (with filters)
{
  "name": "search_speeches",
  "arguments": {
    "query": "economic management",
    "use_hybrid": true,
    "speaker": "Simon Kennedy",
    "chamber": "House of Representatives",
    "top_k": 5
  }
}

# Test vector-only search
{
  "name": "search_speeches",
  "arguments": {
    "query": "renewable energy policy",
    "use_hybrid": false
  }
}

# Test retrieval
{
  "name": "get_speech",
  "arguments": {
    "speech_id": "<uuid-from-search-results>",
    "include_context": true
  }
}

# List all resources
list_resources()

# Access dataset stats resource
{
  "uri": "hansard://dataset/stats"
}

# Access individual speech resource
{
  "uri": "hansard://speech/<speech-id>"
}

# Browse speeches list resource
{
  "uri": "hansard://speeches"
}
```

---

## Success Metrics

**MVP Acceptance Criteria** (from spec.md):

| Criteria | Target | Validation Method |
|----------|--------|-------------------|
| Speeches ingested | 65 (sk-hansard) | Check database row count |
| Chunks created | ~200 | Check speech_chunks table |
| Embedding dimensions | 768 | Verify vector column |
| Search latency (p95) | <500ms | Pytest performance tests |
| Test coverage | >80% | pytest-cov report |
| Tools discoverable | 3 tools | MCP Inspector list_tools() |
| End-to-end demo | Ingest � Search � Retrieve | Manual MCP Inspector test |
| Golden dataset recall | >90% | Test with 10 test queries |

---

## Next Steps After MVP

**v2 Enhancements** (deferred from MVP):
1. Implement GitHub OAuth (OAuth Proxy + GitHubProvider)
2. Deploy to Cloud Run with Cloud SQL pgvector
3. Add Redis caching for query embeddings
4. Expand to multi-speaker dataset (10,000-50,000 speeches)
5. Implement ChatGPT integration (HTTP transport)
6. Add advanced features (reranking, summarization)

---

**Tasks Generated**: 2025-10-21
**Ready for Implementation**:  Yes
**Estimated Completion**: 10-12 days with TDD workflow
