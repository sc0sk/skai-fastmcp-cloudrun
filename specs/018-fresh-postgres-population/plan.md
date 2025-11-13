# Implementation Plan: Fresh PostgreSQL Database Setup & Speech Population

**Branch**: `017-fresh-postgres-population` | **Date**: 2025-10-26 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/017-fresh-postgres-population/spec.md`

## Summary

Create fresh PostgreSQL database with pgvector extension and langchain-postgres schema, then bulk load Hansard speeches from markdown files with LangChain 1.0 text splitting and Vertex AI embeddings, storing embeddings, text, and metadata in PostgreSQL. This bypasses the migration complexity and provides a clean, populated vector database ready for Cloud Run deployment.

## Technical Context

**Language/Version**: Python 3.11+ (Cloud Run requirement)  
**Primary Dependencies**: 
- LangChain 1.0+ (langchain-core, langchain, langchain-text-splitters)
- langchain-google-vertexai>=2.0 (Vertex AI embeddings)
- langchain-postgres (PGVector vector store)
- sqlalchemy 2.x with cloud-sql-python-connector
- python-frontmatter (markdown parsing)
- psycopg[binary]>=3.2 (PostgreSQL driver)

**Storage**: PostgreSQL 15 on Cloud SQL with pgvector extension, langchain-postgres schema  
**Testing**: pytest, manual smoke tests with sample search queries  
**Target Platform**: Cloud SQL instance (hansard-db-v2), Cloud Run deployment  
**Project Type**: Single Python project (src/)  
**Performance Goals**: 
- Database setup: <60s
- Bulk population: ~50-100 chunks/second 
- Search latency: <500ms via HNSW index
- Handle ~50k+ speech chunks

**Constraints**: 
- Must use IAM authentication (no passwords)
- Embeddings must be 768-dimensional (Vertex AI default)
- Metadata must be filterable (JSONB with standard fields)
- Data must survive Cloud Run deployment restarts

**Scale/Scope**: 
- ~500+ Hansard markdown files
- ~50k-100k speech chunks after splitting
- ~40GB+ database size for embeddings

## Constitution Check

**GATES**: All passed ✅

- **Gate 1 - Language Clarity**: Python 3.11+ ✅ (specified, Cloud Run compatible)
- **Gate 2 - Dependencies Available**: LangChain 1.0, Vertex AI, pgvector all available ✅
- **Gate 3 - Storage Strategy**: PostgreSQL + pgvector well-defined ✅
- **Gate 4 - Testing Strategy**: Unit tests + smoke tests defined ✅
- **Gate 5 - Deployment Path**: Cloud Run + Cloud SQL well-established ✅

## Project Structure

### Documentation (this feature)

```
specs/017-fresh-postgres-population/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Database schema research & LangChain 1.0 integration patterns
├── data-model.md        # Entity relationships: Chunk, Collection, Metadata
├── quickstart.md        # Quick setup guide
├── tasks.md             # Implementation tasks (to be generated)
└── contracts/           # Integration contracts (optional)
```

### Source Code (repository root)

```
src/
├── storage/
│   ├── cloud_sql_engine.py         # Cloud SQL connection with IAM auth
│   ├── vector_store.py             # LangChain PGVector wrapper
│   └── __init__.py
├── ingest/
│   ├── markdown_parser.py          # Parse frontmatter & extract metadata
│   ├── text_splitter.py            # LangChain RecursiveCharacterTextSplitter wrapper
│   └── __init__.py
├── embeddings/
│   ├── vertex_ai_embeddings.py     # Vertex AI embeddings API wrapper
│   └── __init__.py
└── populate/
    ├── bulk_loader.py              # Main bulk loading orchestration
    └── __init__.py

scripts/
├── setup_fresh_db.py               # Create database, schema, extensions
├── populate_speeches.py            # Bulk load speeches with embeddings
├── verify_data.py                  # Smoke tests & data verification
└── switch_backend.py               # Update Cloud Run env var

tests/
├── unit/
│   ├── test_markdown_parser.py     # Parse frontmatter, extract metadata
│   ├── test_text_splitter.py       # Chunk splitting logic
│   ├── test_cloud_sql_engine.py    # IAM auth, connection pooling
│   └── test_vector_store.py        # Insert, search operations
└── integration/
    ├── test_bulk_load_e2e.py       # End-to-end load test
    └── test_search_queries.py      # Sample search verification
```

**Structure Decision**: Single-project structure with logical subdirectories (storage, ingest, embeddings, populate) mirroring the data flow: markdown files → parsing → splitting → embedding → storage. Tests mirror source structure with unit + integration layers.

## Phase Breakdown

### Phase 0: Research (Complete before coding)
- [ ] Document langchain-postgres schema structure
- [ ] Research Vertex AI embeddings API limits (batch size, rate limits)
- [ ] Verify Cloud SQL IAM auth flow with new database
- [ ] Map markdown frontmatter schema to cmetadata JSONB structure

### Phase 1: Design & Contracts
- [ ] Create data-model.md documenting entities and relationships
- [ ] Define integration contracts (database schema DDL, API responses)
- [ ] Design bulk loader algorithm (parallel vs sequential, batch sizing)
- [ ] Design metadata extraction from frontmatter

### Phase 2: Implementation
- [ ] Implement database setup (creation, schema, indexes)
- [ ] Implement markdown parser with frontmatter extraction
- [ ] Implement LangChain text splitter wrapper
- [ ] Implement bulk loader with retry logic
- [ ] Implement smoke test queries

### Phase 3: Testing
- [ ] Unit tests for each component
- [ ] Integration test for end-to-end load
- [ ] Verify data integrity (count, metadata, vectors)
- [ ] Performance test (latency, throughput)

### Phase 4: Deployment
- [ ] Update Cloud Run service VECTOR_BACKEND env var
- [ ] Deploy updated service
- [ ] Run final verification in production

## Dependencies & Constraints

| Dependency | Version | Why | Impact if Missing |
|------------|---------|-----|-------------------|
| LangChain 1.0+ | 0.3+ | Core orchestration layer | Cannot split/embed |
| langchain-google-vertexai | 2.0+ | Embeddings generation | Must use alternate embedding service |
| langchain-postgres | 0.0.16+ | PGVector vector store | Must write custom SQL |
| cloud-sql-python-connector | 1.18+ | Cloud SQL IAM auth | Cannot authenticate without password |
| python-frontmatter | 1.1+ | Parse markdown metadata | Manual YAML parsing required |
| psycopg[binary] | 3.2+ | PostgreSQL driver | Use different driver (less reliable) |

## Success Metrics

- ✅ Database created with correct schema
- ✅ All speeches loaded with embeddings and metadata
- ✅ Sample searches return relevant results
- ✅ Cloud Run service successfully connects to new database
- ✅ Zero data loss (all chunks have vectors)
- ✅ Search latency <500ms
