# Next PR: Vector Search Integration (Hansard RAG Implementation)

**Feature**: 001-hansard-rag-implementation (or 002-vector-search-integration)
**Branch**: `002-vector-search-integration`
**Depends On**: PR #4 (ChatGPT Developer Mode Enhancements) - ✅ Merged

## Overview

Implement the actual data layer for the MCP tools created in PR #4. This includes:
- LangChain vector store integration with Google Cloud SQL PostgreSQL + pgvector
- Vertex AI embeddings (gemini-embedding-001, 768 dimensions)
- Dual-table schema (speeches + speech_chunks)
- HNSW indexing for semantic search
- Full text retrieval from PostgreSQL

## Current State (After PR #4)

✅ **Tool Structure**
- 3 MCP tools with comprehensive metadata
- Tool annotations (readOnlyHint)
- Parameter enums (PartyEnum, ChamberEnum)
- Enhanced descriptions

❌ **Missing (This PR Will Add)**
- Vector search functionality
- Database connections
- LangChain integration
- Vertex AI embeddings
- Sample data population
- Production-ready implementations

## Architecture (From CLAUDE.md)

### Google ADK-Aligned Stack

```
MCP Tools (FastMCP)
    ↓
LangChain Integration Layer
    ├─ langchain-google-vertexai (embeddings)
    ├─ langchain-google-cloud-sql-pg (vector store)
    └─ langchain-core (base classes)
    ↓
Google Cloud Services
    ├─ Vertex AI (gemini-embedding-001, 768-dim)
    └─ Cloud SQL PostgreSQL + pgvector v0.8.0
```

### Database Schema

**Dual-Table Design**:

```sql
-- Full speech text storage
CREATE TABLE speeches (
    id UUID PRIMARY KEY,
    date DATE NOT NULL,
    speaker VARCHAR(255) NOT NULL,
    party VARCHAR(50),
    chamber VARCHAR(50),
    title TEXT,
    full_text TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Vector chunks for semantic search
CREATE TABLE speech_chunks (
    id UUID PRIMARY KEY,
    speech_id UUID REFERENCES speeches(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(768),  -- Vertex AI gemini-embedding-001
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- HNSW index for fast similarity search
CREATE INDEX speech_chunks_embedding_idx ON speech_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 24, ef_construction = 100);
```

## Implementation Tasks

### Phase 1: Database Setup (T001-T010)

#### T001-T003: Cloud SQL Configuration
- [ ] T001: Create Cloud SQL PostgreSQL instance (if not exists)
- [ ] T002: Enable pgvector extension (v0.8.0)
- [ ] T003: Configure IAM authentication for Cloud Run

#### T004-T006: Schema Creation
- [ ] T004: Create `speeches` table with full text storage
- [ ] T005: Create `speech_chunks` table with vector embeddings
- [ ] T006: Create HNSW index on embeddings (m=24, ef_construction=100)

#### T007-T010: Connection Setup
- [ ] T007: Create `src/storage/connection.py` with Cloud SQL connector
- [ ] T008: Implement connection pooling (SQLAlchemy)
- [ ] T009: Add IAM authentication helper
- [ ] T010: Write connection tests

### Phase 2: LangChain Integration (T011-T025)

#### T011-T015: Vector Store Setup
- [ ] T011: Create `src/storage/vector_store.py` with LangChain integration
- [ ] T012: Initialize `CloudSQLVectorStore` with pgvector
- [ ] T013: Configure embedding function (Vertex AI)
- [ ] T014: Implement search method with metadata filtering
- [ ] T015: Write vector store tests

#### T016-T020: Embedding Generation
- [ ] T016: Create `src/processing/embeddings.py`
- [ ] T017: Initialize Vertex AI embeddings (gemini-embedding-001)
- [ ] T018: Implement batch embedding generation
- [ ] T019: Add embedding caching strategy
- [ ] T020: Write embedding tests

#### T021-T025: Text Processing
- [ ] T021: Create `src/processing/chunking.py`
- [ ] T022: Implement semantic chunking (LangChain TextSplitter)
- [ ] T023: Configure chunk size (500-1000 tokens) and overlap (100 tokens)
- [ ] T024: Preserve metadata (speaker, date, party) in chunks
- [ ] T025: Write chunking tests

### Phase 3: Tool Implementation (T026-T040)

#### T026-T030: Search Tool Integration
- [ ] T026: Update `src/tools/search.py` with vector search
- [ ] T027: Implement semantic similarity search
- [ ] T028: Add metadata filtering (party, chamber, date range)
- [ ] T029: Return ranked results with relevance scores
- [ ] T030: Write search integration tests

#### T031-T035: Fetch Tool Integration
- [ ] T031: Update `src/tools/fetch.py` with database query
- [ ] T032: Implement speech retrieval by ID
- [ ] T033: Return complete speech with metadata
- [ ] T034: Add error handling (not found, invalid ID)
- [ ] T035: Write fetch integration tests

#### T036-T040: Ingest Tool Integration
- [ ] T036: Update `src/tools/ingest.py` with full pipeline
- [ ] T037: Implement speech validation (Pydantic models)
- [ ] T038: Add chunking + embedding generation
- [ ] T039: Insert speech and chunks into database
- [ ] T040: Write ingest integration tests

### Phase 4: Data Population (T041-T050)

#### T041-T045: Sample Data
- [ ] T041: Create sample Hansard speeches (Simon Kennedy)
- [ ] T042: Parse speech metadata (date, party, chamber)
- [ ] T043: Validate data format
- [ ] T044: Create `scripts/populate_sample_data.py`
- [ ] T045: Test sample data ingestion

#### T046-T050: Production Data Pipeline
- [ ] T046: Create `scripts/ingest_hansard.py` for batch ingestion
- [ ] T047: Implement progress reporting (FastMCP Context)
- [ ] T048: Add deduplication logic
- [ ] T049: Create data validation report
- [ ] T050: Document ingestion procedures

### Phase 5: Testing & Validation (T051-T062)

#### T051-T055: Unit Tests
- [ ] T051: Test vector store CRUD operations
- [ ] T052: Test embedding generation
- [ ] T053: Test chunking logic
- [ ] T054: Test search with filters
- [ ] T055: Test fetch error handling

#### T056-T060: Integration Tests
- [ ] T056: End-to-end search workflow
- [ ] T057: End-to-end ingest → search workflow
- [ ] T058: Test with MCP Inspector
- [ ] T059: Performance benchmarks (search latency)
- [ ] T060: Load testing (concurrent searches)

#### T061-T062: Production Validation
- [ ] T061: Deploy to Cloud Run staging
- [ ] T062: Test with ChatGPT Developer Mode

### Phase 6: Documentation & Deployment (T063-T070)

- [ ] T063: Update README with vector search setup
- [ ] T064: Document database schema
- [ ] T065: Create deployment guide
- [ ] T066: Add troubleshooting guide
- [ ] T067: Create Dockerfile with Cloud SQL proxy
- [ ] T068: Update cloudbuild.yaml
- [ ] T069: Deploy to production
- [ ] T070: Monitor and validate

## File Structure (To Be Created)

```
src/
├── storage/
│   ├── __init__.py
│   ├── connection.py        # Cloud SQL connection with IAM auth
│   └── vector_store.py      # LangChain CloudSQLVectorStore
├── processing/
│   ├── __init__.py
│   ├── embeddings.py        # Vertex AI embedding generation
│   └── chunking.py          # Semantic text chunking
├── models/
│   ├── speech.py            # Pydantic models for speeches
│   └── chunk.py             # Pydantic models for chunks
└── tools/
    ├── search.py            # UPDATE: Add vector search
    ├── fetch.py             # UPDATE: Add database query
    └── ingest.py            # UPDATE: Add full pipeline

scripts/
├── init_database.py         # Initialize schema
├── populate_sample_data.py  # Load sample speeches
└── ingest_hansard.py        # Batch ingestion

tests/
├── unit/
│   ├── test_vector_store.py
│   ├── test_embeddings.py
│   ├── test_chunking.py
│   └── test_tools.py
└── integration/
    ├── test_search_workflow.py
    └── test_ingest_workflow.py
```

## Dependencies to Add

```toml
[project]
dependencies = [
    "fastmcp>=2.12.5",
    "pydantic>=2.0",
    "langchain-google-vertexai",      # Vertex AI embeddings
    "langchain-google-cloud-sql-pg",  # Cloud SQL vector store
    "langchain-core",                 # LangChain base
    "sqlalchemy>=2.0",                # Database ORM
    "asyncpg",                        # Async PostgreSQL driver
    "cloud-sql-python-connector",     # Cloud SQL IAM auth
]
```

## Environment Variables Required

```bash
# Google Cloud
GOOGLE_CLOUD_PROJECT=skai-fastmcp-cloudrun
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Cloud SQL
CLOUD_SQL_INSTANCE=skai-fastmcp-cloudrun:us-central1:hansard-db
CLOUD_SQL_DATABASE=hansard
CLOUD_SQL_USER=mcp-service-account@skai-fastmcp-cloudrun.iam

# Vertex AI
VERTEX_AI_LOCATION=us-central1
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSION=768
```

## Success Criteria

| Criteria | Target |
|----------|--------|
| Search latency | <500ms p95 |
| Semantic accuracy | >80% relevant results in top 5 |
| Ingest throughput | >10 speeches/minute |
| Vector store size | ~64 speeches, ~500 chunks |
| Test coverage | >80% line coverage |

## Migration from PR #4

**Current State (Placeholder)**:
```python
async def search_hansard_speeches(...) -> dict:
    return {"speeches": [], "total_count": 0, "message": "Placeholder"}
```

**After This PR (Functional)**:
```python
async def search_hansard_speeches(...) -> dict:
    # 1. Generate query embedding
    query_embedding = await embeddings.embed_query(query)

    # 2. Search vector store
    results = await vector_store.similarity_search(
        query_embedding,
        k=limit,
        filters={"party": party, "chamber": chamber, ...}
    )

    # 3. Fetch full speeches from database
    speeches = [await fetch_speech(r.metadata["speech_id"]) for r in results]

    return {"speeches": speeches, "total_count": len(speeches)}
```

## Testing Strategy

### Unit Tests (Fast, No External Dependencies)
- Mock vector store operations
- Mock embedding generation
- Test chunking logic
- Test parameter validation

### Integration Tests (Slow, Requires Database)
- Real Cloud SQL connection
- Real Vertex AI embeddings
- End-to-end workflows
- Performance benchmarks

### Manual Tests (Requires ChatGPT)
- Test queries: "Find speeches about housing"
- Test filters: "Search Labor party speeches from July 2024"
- Test edge cases: "What did Anthony Albanese say?" (out of scope)

## Rollout Plan

1. **Staging Deployment**
   - Deploy to Cloud Run staging environment
   - Test with small dataset (10 speeches)
   - Validate search accuracy

2. **Production Deployment**
   - Populate full dataset (64 speeches)
   - Monitor performance metrics
   - Gradual rollout with canary deployment

3. **ChatGPT Integration**
   - Configure ChatGPT Developer Mode
   - Test with real user queries
   - Collect feedback and iterate

## Estimated Effort

- **Phase 1 (Database)**: 2-3 hours
- **Phase 2 (LangChain)**: 4-6 hours
- **Phase 3 (Tool Implementation)**: 3-4 hours
- **Phase 4 (Data)**: 2-3 hours
- **Phase 5 (Testing)**: 3-4 hours
- **Phase 6 (Deployment)**: 2-3 hours

**Total**: 16-23 hours of development work

## Next Steps

1. ✅ Review this plan
2. 🔄 Create feature branch: `git checkout -b 002-vector-search-integration`
3. 🔄 Run `/speckit.specify` with feature description
4. 🔄 Run `/speckit.plan` to generate detailed plan
5. 🔄 Run `/speckit.tasks` to create task breakdown
6. 🔄 Run `/speckit.implement` to execute tasks
7. 🔄 Test, commit, and create PR #5

---

**Ready to start? Let me know when you'd like to begin!**
