# Feature 017 Specification Kit Complete ✨

**Feature**: Fresh PostgreSQL Database Setup & Speech Population  
**Branch**: `017-fresh-postgres-population`  
**Created**: 2025-10-26  
**Status**: Planning Phase Complete → Ready for Phase 2 Implementation

## What Was Created

Using GitHub spec-kit methodology, a complete feature specification package was generated:

### 📋 Specification Documents

#### 1. **spec.md** - Feature Specification
- **5 prioritized user stories** (P1-P3) covering:
  - P1: Database creation with pgvector
  - P1: Bulk speech loading with embeddings
  - P1: Metadata storage (speaker, date, hansard_id, etc.)
  - P2: Data verification & search functionality
  - P2: Cloud Run backend switch
- **15 functional requirements** (FR-001 through FR-015)
- **4 key entities**: Speech Chunk, Collection, Metadata, Vector Embedding
- **10 success criteria** including:
  - 100% file success rate
  - 95%+ chunk insertion success
  - <500ms search latency
  - >80% search precision

#### 2. **plan.md** - Implementation Plan
- **Technical context** fully defined:
  - Python 3.11+ with LangChain 1.0
  - langchain-postgres, Vertex AI embeddings
  - Cloud SQL + pgvector
- **Constitution check**: All 5 gates passed ✅
- **Project structure**: Source code + tests layout
- **4 implementation phases**:
  - Phase 0: Research
  - Phase 1: Design & Contracts
  - Phase 2: Implementation
  - Phase 3: Testing
  - Phase 4: Deployment
- **Dependencies & constraints** documented with impact analysis

#### 3. **data-model.md** - Data Model & Schema
- **Entity-Relationship Diagram** (ERD):
  - `langchain_pg_collection` (1 collection)
  - `langchain_pg_embedding` (N embeddings per collection)
  - HNSW index on 768-dimensional vectors
- **Complete DDL** with all table creation scripts
- **Metadata structure** (JSONB):
  ```json
  {
    "speaker": "string",
    "date": "ISO date",
    "hansard_id": "string",
    "speech_type": "string",
    "hansard_url": "string",
    "chunk_index": 0,
    "tokens": 1050
  }
  ```
- **Data flow diagram**: Markdown → Parse → Split → Embed → Store → Search
- **Monitoring queries** for production observation
- **Migration path** for re-initialization

#### 4. **quickstart.md** - Quick Start Guide
- **4-step quick setup** (5 minutes):
  1. Create fresh database & schema
  2. Populate speeches with embeddings
  3. Verify data integrity
  4. Run smoke tests
- **Detailed step-by-step instructions** with expected output
- **Smoke test examples** for all major features
- **Troubleshooting guide** for common issues
- **Time estimates**: 40-60 minutes total for full population
- **Configuration reference**: Tunable parameters (chunk size, batch size, etc.)

#### 5. **tasks.md** - Implementation Breakdown
- **35 specific tasks** organized into 6 groups:
  - **Group 1** (T001-T005): Database setup
  - **Group 2** (T006-T010): Markdown parsing & text splitting
  - **Group 3** (T011-T020): Unit + integration tests
  - **Group 4** (T021-T025): Verification & smoke tests
  - **Group 5** (T026-T030): Cloud Run deployment
  - **Group 6** (T031-T035): Documentation & summary
- **Task dependencies** mapped out in DAG format
- **Execution timeline**: 20-27 hours total (1 week)
- **Success criteria** for all 35 tasks

### 📁 Directory Structure Created

```
specs/017-fresh-postgres-population/
├── spec.md              # Feature specification (comprehensive)
├── plan.md              # Implementation plan with technical context
├── data-model.md        # Schema design + entity relationships
├── quickstart.md        # Quick setup guide with examples
├── tasks.md             # 35-task breakdown with dependencies
└── [ready for Phase 2]
    ├── research.md      # (To be created in Phase 0)
    └── contracts/       # (To be created in Phase 1)
```

## Next Steps (Phase 2 Implementation)

### Immediate: Execute T001-T010 (Core Implementation)

```bash
# 1. Create fresh database & schema (T001-T004)
python setup_fresh_db_gcloud.py

# 2. Implement markdown parser (T006)
# - Create: src/ingest/markdown_parser.py
# - TDD: Write tests first in tests/unit/test_markdown_parser.py

# 3. Implement text splitter (T007)
# - Create: src/ingest/text_splitter.py
# - TDD: Tests in tests/unit/test_text_splitter.py

# 4. Implement embeddings wrapper (T008)
# - Create: src/embeddings/vertex_ai_embeddings.py
# - TDD: Tests in tests/unit/test_vertex_ai_embeddings.py

# 5. Implement vector store (T009)
# - Create: src/storage/vector_store.py
# - TDD: Tests in tests/unit/test_vector_store.py

# 6. Orchestrate bulk loader (T010)
# - Create: scripts/populate_speeches.py
# - TDD: Integration tests in tests/integration/test_bulk_load_e2e.py
```

### Then: Execute T011-T025 (Testing & Verification)

```bash
# Run all tests
pytest tests/ -v --cov=src --cov-report=html

# Verify database state
python verify_data.py --database hansard_db_fresh

# Run smoke tests
python smoke_tests.py
```

### Finally: Execute T026-T035 (Production Deployment)

```bash
# Update Cloud Run service
gcloud run services update hansard-mcp \
  --set-env-vars VECTOR_BACKEND=postgres

# Production smoke tests
curl -X POST https://hansard-mcp-xxx.a.run.app/search \
  -H "Content-Type: application/json" \
  -d '{"query": "climate policy", "k": 5}'
```

## Key Design Decisions

### 1. **Fresh Database vs Migration**
- **Decision**: Create new `hansard_db_fresh` database
- **Why**: Avoids complex migration issues, cleaner state
- **Implication**: Old database can coexist (for rollback)

### 2. **langchain-postgres Schema**
- **Decision**: Use standard langchain-postgres tables
- **Why**: Compatible with LangChain 1.0, proven schema
- **Implication**: Portable to other projects using LangChain

### 3. **Vertex AI Embeddings (768-dimensional)**
- **Decision**: Use text-embedding-004 model via langchain-google-vertexai
- **Why**: Enterprise-grade, supports 768-dim vectors, auto-batching
- **Implication**: Tied to Google Cloud, but cost-effective

### 4. **HNSW Index for Search**
- **Decision**: Use pgvector's HNSW index (vs Exact)
- **Why**: Scales to 100k+ embeddings, <500ms search latency
- **Implication**: Slight approximation accuracy loss (<5%)

### 5. **Metadata in JSONB**
- **Decision**: Store all metadata in single JSONB column
- **Why**: Flexible schema, filterable with GIN index, single row per chunk
- **Implication**: Requires JSON parsing in queries

### 6. **TDD for Implementation**
- **Decision**: Write tests before code (Red → Green → Refactor)
- **Why**: Ensures 85%+ code coverage, catches bugs early
- **Implication**: 30% more code initially, but 60% faster debugging

## Success Metrics (Phase Completion)

✅ **Planning Phase Complete When**:
- [x] Feature specification (spec.md) complete
- [x] Implementation plan (plan.md) complete with all gates passing
- [x] Data model (data-model.md) documented with DDL
- [x] Quickstart guide (quickstart.md) ready with examples
- [x] Task breakdown (tasks.md) with 35 tasks and dependencies
- [x] All documentation in specs/017-fresh-postgres-population/

📊 **Implementation Phase Success Criteria**:
- [ ] All T001-T035 tasks completed
- [ ] Unit test coverage >85%
- [ ] All integration tests pass
- [ ] Zero data loss verified
- [ ] Search latency p95 <500ms
- [ ] 52,847+ speech chunks successfully loaded
- [ ] Metadata present for 90%+ chunks
- [ ] Cloud Run service successfully deployed

🎯 **Production Deployment Success Criteria**:
- [ ] VECTOR_BACKEND=postgres configured
- [ ] Cloud Run service startup succeeds
- [ ] Production smoke tests all pass (5/5)
- [ ] Real-time monitoring confirmed
- [ ] Backup strategy tested
- [ ] Rollback procedure documented

## Continuation Instructions for Phase 2

**When ready to start implementation**:

1. Update todo list with T001-T010 as "in-progress"
2. Create files: `src/ingest/markdown_parser.py`, etc.
3. Write unit tests first (TDD)
4. Run tests: `pytest tests/unit/ -v`
5. Implement code until tests pass
6. Commit with message: `feat(017): T00X - [Task Name]`
7. Move to next task

**Expected Timeline**: 
- Implementation: 1 week (20-27 hours)
- Testing: Built-in (TDD approach)
- Deployment: 1-2 days

---

**Current Status**: ✅ **PLANNING PHASE COMPLETE**  
**Ready for**: Phase 2 Implementation (T001-T035)  
**Spec Kit Feature**: 017-fresh-postgres-population  
**Repository**: skai-fastmcp-cloudrun  

For questions, refer to `specs/017-fresh-postgres-population/` directory.
