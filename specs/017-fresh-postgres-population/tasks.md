# Implementation Tasks: Fresh PostgreSQL Database & Population

**Feature**: 017-fresh-postgres-population  
**Date**: 2025-10-26  
**Phase**: Task Generation (Phase 1 → Phase 2 implementation)

---

## Task Groups

### Group 1: Database Setup (T001-T005)

#### T001: Create Database & Enable pgvector
**Objective**: Create fresh database and enable pgvector extension  
**Input**: Cloud SQL instance `hansard-db-v2`  
**Output**: Database `hansard_db_fresh` with pgvector extension active  
**Acceptance**:
- [ ] Database `hansard_db_fresh` exists
- [ ] pgvector extension is loaded
- [ ] Connection verified via `gcloud sql connect`

**Implementation File**: `setup_fresh_db.py`  
**Testing**: Manual via psql or automation via `test_database_creation.py`

---

#### T002: Create langchain-postgres Schema Tables
**Objective**: Create `langchain_pg_collection` and `langchain_pg_embedding` tables  
**Input**: Database `hansard_db_fresh`  
**Output**: Tables with correct columns, types, and indexes  
**Acceptance**:
- [ ] `langchain_pg_collection` table exists with uuid, name, cmetadata
- [ ] `langchain_pg_embedding` table exists with id, collection_id, embedding (VECTOR 768), document, cmetadata
- [ ] HNSW index created on embedding column
- [ ] Foreign key constraint from embedding → collection

**Implementation File**: `setup_fresh_db.py` (DDL section)  
**Testing**: 
```python
# Test schema creation
from sqlalchemy import inspect, text
engine = get_engine(database='hansard_db_fresh')
inspector = inspect(engine)
assert 'langchain_pg_collection' in inspector.get_table_names()
assert 'langchain_pg_embedding' in inspector.get_table_names()
```

---

#### T003: Create Collection Record
**Objective**: Insert hansard collection into `langchain_pg_collection`  
**Input**: Database with schema created  
**Output**: One collection record with uuid and metadata  
**Acceptance**:
- [ ] Collection record inserted with name='hansard'
- [ ] UUID generated and stored
- [ ] Metadata JSON includes version, source, timestamp

**Implementation File**: `setup_fresh_db.py` or `populate_speeches.py`  
**Testing**: 
```python
engine = get_engine(database='hansard_db_fresh')
with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT uuid FROM langchain_pg_collection WHERE name='hansard'"
    ))
    collection_uuid = result.scalar_one()
    assert collection_uuid is not None
```

---

#### T004: Verify Database Setup
**Objective**: Comprehensive schema verification  
**Input**: Database `hansard_db_fresh` with schema  
**Output**: Verification report  
**Acceptance**:
- [ ] All tables exist and have correct columns
- [ ] All indexes exist
- [ ] Extensions loaded
- [ ] Constraints in place

**Implementation File**: `verify_data.py` (schema verification section)  
**Testing**: Run `python verify_data.py --database hansard_db_fresh --check-schema`

---

#### T005: Test Database Connection Pooling
**Objective**: Verify connection pool works correctly with Cloud SQL Connector  
**Input**: Cloud SQL instance and database  
**Output**: Verified connection pool with no connection leaks  
**Acceptance**:
- [ ] 100 sequential connections succeed
- [ ] 50 concurrent connections succeed
- [ ] Pool size respects max_overflow setting
- [ ] No "too many connections" errors

**Implementation File**: `src/storage/cloud_sql_engine.py`  
**Testing**: `tests/unit/test_cloud_sql_engine.py::test_connection_pooling`

---

### Group 2: Markdown Parsing & Text Splitting (T006-T010)

#### T006: Implement Markdown Parser with Frontmatter Extraction
**Objective**: Parse markdown files and extract frontmatter metadata  
**Input**: Markdown file path or directory  
**Output**: Parsed content + metadata dict  
**Acceptance**:
- [ ] Frontmatter YAML parsed correctly
- [ ] Required fields extracted: speaker, date, hansard_id, speech_type, url
- [ ] Missing fields handled gracefully (use defaults)
- [ ] Full document text extracted

**Implementation File**: `src/ingest/markdown_parser.py`  
**Functions**:
```python
def parse_markdown_file(file_path: Path) -> dict:
    """Parse single markdown file and extract metadata."""
    # Returns: {
    #   'speaker': str,
    #   'date': str (ISO format),
    #   'hansard_id': str,
    #   'speech_type': str,
    #   'url': str,
    #   'content': str
    # }

def parse_directory(dir_path: Path) -> Generator[dict, None, None]:
    """Parse all markdown files in directory."""
    # Yields parsed documents in order
```

**Testing**: 
```python
# tests/unit/test_markdown_parser.py
def test_parse_markdown_with_frontmatter():
    result = parse_markdown_file('data/hansard_converted/example.md')
    assert result['speaker'] == 'John Smith'
    assert result['date'] == '2023-11-15'
    assert len(result['content']) > 0

def test_parse_missing_metadata():
    result = parse_markdown_file('data/hansard_converted/incomplete.md')
    assert result['speaker'] == 'Unknown'  # default value
```

---

#### T007: Implement Text Splitter Wrapper
**Objective**: Split documents into chunks using LangChain  
**Input**: Full document text  
**Output**: List of chunks with metadata  
**Acceptance**:
- [ ] Uses LangChain RecursiveCharacterTextSplitter
- [ ] chunk_size=1000 tokens (approximately)
- [ ] overlap=100 tokens between chunks
- [ ] Preserves metadata with each chunk
- [ ] Handles edge cases (very short docs, etc.)

**Implementation File**: `src/ingest/text_splitter.py`  
**Functions**:
```python
def split_document(
    content: str,
    metadata: dict,
    chunk_size: int = 1000,
    chunk_overlap: int = 100
) -> List[dict]:
    """Split document into chunks with metadata."""
    # Returns list of: {
    #   'content': chunk_text,
    #   'metadata': {...original metadata...},
    #   'chunk_index': int,
    #   'chunk_count': int,
    #   'tokens': int
    # }
```

**Testing**:
```python
# tests/unit/test_text_splitter.py
def test_split_document_creates_chunks():
    chunks = split_document("Long text...", {}, chunk_size=1000)
    assert len(chunks) > 1
    assert all('content' in c for c in chunks)
    assert chunks[0]['chunk_index'] == 0

def test_chunk_overlap_preserved():
    chunks = split_document("Text A. Text B. Text C.", {})
    # Verify overlap exists in content
```

---

#### T008: Implement Vertex AI Embeddings Wrapper
**Objective**: Generate embeddings using Vertex AI API  
**Input**: List of text chunks  
**Output**: List of 768-dimensional embedding vectors  
**Acceptance**:
- [ ] Uses langchain-google-vertexai VertexAIEmbeddings
- [ ] Model: text-embedding-004
- [ ] Dimension: 768
- [ ] Batch processing (batch_size configurable)
- [ ] Retry logic with exponential backoff
- [ ] Rate limit handling

**Implementation File**: `src/embeddings/vertex_ai_embeddings.py`  
**Functions**:
```python
class VertexAIEmbeddingsWrapper:
    def __init__(self, model_name: str = "text-embedding-004"):
        self.embeddings = VertexAIEmbeddings(model_name=model_name)
    
    def embed_documents(
        self, 
        texts: List[str],
        batch_size: int = 100,
        max_retries: int = 3
    ) -> List[List[float]]:
        """Generate embeddings with batch processing and retry."""
        # Returns list of 768-dim vectors
```

**Testing**:
```python
# tests/unit/test_vertex_ai_embeddings.py
def test_embed_documents_returns_correct_dimension():
    wrapper = VertexAIEmbeddingsWrapper()
    embeddings = wrapper.embed_documents(["Hello world"])
    assert len(embeddings[0]) == 768

def test_batch_processing():
    texts = [f"Text {i}" for i in range(250)]
    embeddings = wrapper.embed_documents(texts, batch_size=100)
    assert len(embeddings) == 250
```

---

#### T009: Implement Vector Store Wrapper
**Objective**: Wrapper around langchain-postgres PGVector store  
**Input**: Database connection, collection_id  
**Output**: Insert/search interface  
**Acceptance**:
- [ ] Insert chunks with embeddings and metadata
- [ ] Similarity search returns relevant results
- [ ] Metadata filtering works (speaker, date, etc.)
- [ ] Batch insert optimization

**Implementation File**: `src/storage/vector_store.py`  
**Functions**:
```python
class PGVectorStore:
    def __init__(self, db: str = 'hansard_db_fresh'):
        self.engine = get_engine(database=db)
        self.collection_id = get_collection_uuid('hansard')
    
    def add_documents(
        self,
        docs: List[dict],  # {id, content, embedding, metadata}
        batch_size: int = 500
    ) -> int:
        """Insert documents with embeddings."""
        # Returns count of inserted rows
    
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: dict = None
    ) -> List[Document]:
        """Search and return relevant documents."""
```

**Testing**:
```python
# tests/unit/test_vector_store.py
def test_add_documents():
    store = PGVectorStore()
    docs = [{'id': 'test_1', 'content': '...', 'embedding': [...], 'metadata': {...}}]
    count = store.add_documents(docs)
    assert count == 1

def test_similarity_search():
    results = store.similarity_search("climate policy", k=5)
    assert len(results) <= 5
```

---

#### T010: Implement Bulk Loader Orchestration
**Objective**: Orchestrate entire pipeline: parse → split → embed → store  
**Input**: Markdown directory path  
**Output**: All embeddings stored in database  
**Acceptance**:
- [ ] Loads all markdown files
- [ ] Processes in batches
- [ ] Shows progress bar
- [ ] Handles errors gracefully
- [ ] Logs statistics (files, chunks, embeddings, rows)
- [ ] Executes smoke tests at end

**Implementation File**: `scripts/populate_speeches.py` or `src/populate/bulk_loader.py`  
**Functions**:
```python
def bulk_load_speeches(
    markdown_dir: Path,
    collection_name: str = 'hansard',
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
    batch_size: int = 500,
    verbose: bool = True
) -> dict:
    """Orchestrate full pipeline."""
    # Returns: {
    #   'files_processed': int,
    #   'chunks_created': int,
    #   'embeddings_generated': int,
    #   'rows_inserted': int,
    #   'duration_seconds': float,
    #   'errors': List[str]
    # }
```

**Testing**:
```python
# tests/integration/test_bulk_load_e2e.py
def test_bulk_load_end_to_end(tmp_path):
    # Create test markdown files
    # Run bulk loader
    # Verify all data in database
    result = bulk_load_speeches(markdown_dir=tmp_path)
    assert result['files_processed'] == 2
    assert result['chunks_created'] > 0
    assert result['rows_inserted'] > 0
```

---

### Group 3: Unit Tests (T011-T020)

#### T011-T015: Unit Tests for Core Components
**Objective**: Write unit tests for each component  
**Files**:
- [ ] T011: `tests/unit/test_markdown_parser.py` (test_parse_*, test_missing_*, test_edge_cases_*)
- [ ] T012: `tests/unit/test_text_splitter.py` (test_split_*, test_overlap_*, test_chunk_count_*)
- [ ] T013: `tests/unit/test_vertex_ai_embeddings.py` (test_embed_*, test_batch_*, test_retry_*)
- [ ] T014: `tests/unit/test_vector_store.py` (test_add_*, test_search_*, test_filter_*)
- [ ] T015: `tests/unit/test_cloud_sql_engine.py` (test_connection_*, test_pool_*, test_iam_auth_*)

**Acceptance**: 
- [ ] All tests pass
- [ ] Coverage >85%
- [ ] No warnings

**Testing Command**: `pytest tests/unit/ -v --cov=src`

---

#### T016-T017: Integration Tests
**Objective**: End-to-end integration tests  
**Files**:
- [ ] T016: `tests/integration/test_bulk_load_e2e.py` (full pipeline with test data)
- [ ] T017: `tests/integration/test_search_queries.py` (smoke tests for search functionality)

**Acceptance**:
- [ ] E2E test loads sample files and verifies database state
- [ ] Search tests execute sample queries and verify results
- [ ] Metadata filtering works

**Testing Command**: `pytest tests/integration/ -v`

---

#### T018: Test Database Connection Recovery
**Objective**: Verify graceful handling of connection failures  
**Implementation**: `tests/unit/test_cloud_sql_engine.py::test_connection_recovery`  
**Acceptance**:
- [ ] Simulated connection loss handled
- [ ] Retry logic works
- [ ] Pool recovery succeeds

---

#### T019: Test Data Consistency
**Objective**: Verify no data loss or corruption  
**Implementation**: `tests/integration/test_data_consistency.py`  
**Acceptance**:
- [ ] All chunks have embedding vectors
- [ ] All chunks have metadata
- [ ] No duplicate IDs
- [ ] Vector dimensionality always 768

---

#### T020: Test Performance & Latency
**Objective**: Verify search performance meets SLA  
**Implementation**: `tests/integration/test_performance.py`  
**Acceptance**:
- [ ] Search latency p95 <500ms
- [ ] Insert throughput >50 chunks/sec
- [ ] Metadata filtering <100ms

---

### Group 4: Smoke Tests & Verification (T021-T025)

#### T021: Create Verification Script
**Objective**: Comprehensive data verification  
**Implementation File**: `scripts/verify_data.py` or `src/populate/verify_data.py`  
**Functions**:
```python
def verify_database_setup(database: str) -> dict:
    """Verify schema and data integrity."""
    return {
        'schema_ok': bool,
        'total_embeddings': int,
        'total_collections': int,
        'null_embeddings': int,
        'required_fields_present': int,
        'date_range': (str, str),
        'unique_speakers': int,
        'vector_dimension': int,
        'status': str  # "✅ PASS" or "❌ FAIL"
    }
```

**Testing**: `python verify_data.py --database hansard_db_fresh`

---

#### T022: Create Smoke Test Suite
**Objective**: Sample search queries to verify functionality  
**Implementation File**: `scripts/smoke_tests.py`  
**Queries**:
- [ ] Query 1: Search "climate policy" (general query)
- [ ] Query 2: Search "Speaker John Smith" + filter by speaker
- [ ] Query 3: Search with date range filter
- [ ] Query 4: Verify metadata filtering works
- [ ] Query 5: Verify vector similarity (cosine distance)

**Acceptance**:
- [ ] All queries return results
- [ ] Results are ranked by relevance
- [ ] Latency <500ms per query

---

#### T023: Document Test Results
**Objective**: Create TEST_RESULTS_017.md  
**Content**:
- [ ] Unit test results (count, coverage %)
- [ ] Integration test results
- [ ] Performance metrics (latency, throughput)
- [ ] Data verification results
- [ ] Smoke test results

---

#### T024: Create Data Backup Strategy
**Objective**: Document backup procedure  
**Implementation**: `scripts/backup_database.sh`  
**Commands**:
```bash
# Export database
gcloud sql export sql hansard-db-v2 \
  gs://skai-fastmcp-cloudrun-backups/hansard_db_fresh_$(date +%Y%m%d).sql

# Or use Cloud SQL point-in-time recovery
```

---

#### T025: Create Rollback Plan
**Objective**: Document rollback procedure if needed  
**Documentation**: `ROLLBACK_PLAN.md`  
**Steps**:
1. Identify issue (data corruption, performance degradation, etc.)
2. Choose recovery method:
   - Restore from backup
   - Point-in-time recovery
   - Switch VECTOR_BACKEND back to in-memory
3. Execute recovery
4. Verify service works

---

### Group 5: Deployment & Cloud Run Update (T026-T035)

#### T026: Update Cloud Run Service Configuration
**Objective**: Configure Cloud Run job/service to use new database  
**Commands**:
```bash
# Update Cloud Run service environment variables
gcloud run services update hansard-mcp \
  --set-env-vars \
    VECTOR_BACKEND=postgres,\
    DATABASE_NAME=hansard_db_fresh,\
    CLOUD_SQL_CONNECTION=skai-fastmcp-cloudrun:us-central1:hansard-db-v2
```

**Acceptance**:
- [ ] Environment variables updated
- [ ] Service redeployed
- [ ] Service startup succeeds

---

#### T027: Verify Cloud Run Service Connection
**Objective**: Test service can connect to new database  
**Implementation**: `tests/integration/test_cloud_run_e2e.py`  
**Steps**:
1. Deploy service
2. Wait for startup (30s)
3. Make test request to `/health` endpoint
4. Verify database connection works
5. Make test search request

**Acceptance**:
- [ ] Health check passes
- [ ] Search query succeeds
- [ ] Results are from postgres backend

---

#### T028: Production Smoke Tests
**Objective**: Final validation in production  
**Implementation**: `scripts/production_smoke_tests.py`  
**Queries**:
```bash
# Query 1: Simple search
curl -X POST \
  https://hansard-mcp-xxx.a.run.app/search \
  -H "Content-Type: application/json" \
  -d '{"query": "climate policy", "k": 5}'

# Query 2: With metadata filter
curl -X POST \
  https://hansard-mcp-xxx.a.run.app/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "education reform",
    "k": 5,
    "filters": {"speaker": "Jane Doe"}
  }'
```

**Acceptance**:
- [ ] Both queries return 200 OK
- [ ] Results include embedding vectors
- [ ] Latency <1 second per request

---

#### T029: Document Deployment Runbook
**Objective**: Create `DEPLOYMENT_RUNBOOK_017.md`  
**Content**:
- [ ] Prerequisites
- [ ] Step-by-step deployment
- [ ] Verification checklist
- [ ] Rollback procedure
- [ ] Support contacts

---

#### T030: Create Monitoring & Alerts
**Objective**: Set up Cloud Monitoring for vector database  
**Metrics**:
- [ ] Search latency (p50, p95, p99)
- [ ] Embedding generation rate
- [ ] Database size growth
- [ ] Query error rate
- [ ] Connection pool usage

**Implementation**: `cloud_monitoring_config.yaml` or via Cloud Console

---

### Group 6: Documentation & Summary (T031-T035)

#### T031: Update DEPLOYMENT_GUIDE.md
**Objective**: Add Feature 017 to main deployment guide  
**Content**:
- [ ] Reference to 017-fresh-postgres-population feature
- [ ] Quick steps for fresh database setup
- [ ] Link to quickstart guide
- [ ] Deployment workflow

---

#### T032: Create FEATURE_017_COMPLETION_SUMMARY.md
**Objective**: Feature completion summary  
**Content**:
- [ ] All user stories completed
- [ ] Success criteria met
- [ ] Test coverage >85%
- [ ] Performance metrics achieved
- [ ] Data integrity verified
- [ ] Production deployed successfully

---

#### T033: Update copilot-instructions.md
**Objective**: Add Feature 017 to active technologies  
**Content**:
```markdown
## Active Technologies
- PostgreSQL via Cloud SQL with pgvector (017-fresh-postgres-population)
- LangChain 1.0+ with Vertex AI embeddings and bulk population (017-fresh-postgres-population)
- Bulk speech ingestion with metadata extraction and HNSW indexing (017-fresh-postgres-population)
```

---

#### T034: Create Video/Demo Script
**Objective**: Document demo/walkthrough  
**Steps**:
1. Show markdown files in data/
2. Run `populate_speeches.py`
3. Watch progress (live database queries)
4. Run smoke tests
5. Show Cloud Run service making searches
6. Display metrics in Cloud Console

---

#### T035: Archive and Cleanup
**Objective**: Final cleanup and archival  
**Actions**:
- [ ] Commit all code to main branch
- [ ] Tag release: `v017-fresh-postgres-population`
- [ ] Close all related GitHub issues
- [ ] Archive temporary scripts
- [ ] Update README.md with feature completion

---

## Task Dependencies

```
T001 → T002 → T003 → T004 → T005
                ↓
T006 → T007 → T008 → T009 → T010 (can start in parallel with T001)
                ↓
        T011-T020 (unit + integration tests)
                ↓
        T021-T025 (verification + smoke tests)
                ↓
        T026-T030 (deployment to Cloud Run)
                ↓
        T031-T035 (documentation + summary)
```

## Execution Timeline

| Phase | Tasks | Est. Duration | Start Date | End Date |
|-------|-------|---------------|-----------|----------|
| Phase 1: Planning | All specs, plan, data-model, quickstart | 2-3 hours | Today | Today |
| Phase 2: Implementation | T001-T010 (core code) | 8-10 hours | Tomorrow | +1-2 days |
| Phase 3: Testing | T011-T025 (tests + verification) | 6-8 hours | +2-3 days | +4-5 days |
| Phase 4: Deployment | T026-T035 (production + docs) | 4-6 hours | +5-6 days | +6-7 days |
| **Total** | 35 tasks | **20-27 hours** | Today | **+1 week** |

## Success Criteria

All tasks complete when:
- ✅ All 35 tasks marked "completed"
- ✅ Unit test coverage >85%
- ✅ All integration tests pass
- ✅ Production smoke tests pass
- ✅ Zero data loss verified
- ✅ Search latency p95 <500ms
- ✅ Feature 017 documented in copilot-instructions.md
