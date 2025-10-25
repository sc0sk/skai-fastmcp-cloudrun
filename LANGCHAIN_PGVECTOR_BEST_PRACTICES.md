# LangChain + pgvector + Google Cloud SQL Best Practices (2025)

Based on Google Cloud documentation and latest LangChain PostgreSQL enhancements.

## 🎯 Current Status: LangChain 1.0 with langchain-postgres

**As of Feature 016 (langchain-postgres-upgrade)**, this project has migrated to:

- **LangChain**: 1.0+ (stable release with improved APIs)
- **Vector Store**: `langchain-postgres` (dedicated PGVector package, replaces `langchain-google-cloud-sql-pg`)
- **Driver**: psycopg3 (sync driver wrapped in async adapter)
- **Connection**: Cloud SQL Connector with IAM authentication (automatic token refresh)
- **Schema**: PGVector standard schema (`langchain_pg_collection`, `langchain_pg_embedding`)
- **Metadata**: JSONB-based (flexible schema without explicit columns)
- **Feature Flag**: `VECTOR_BACKEND=postgres` (instant rollback to legacy if needed)

### Migration Notes

The previous implementation used `langchain-google-cloud-sql-pg` with a custom schema (`hansard_speeches` table). The new implementation uses `langchain-postgres` with the standard PGVector schema. Both backends coexist during the migration period via feature flag.

**Migration Documentation**: See `specs/016-langchain-postgres-upgrade/` for complete migration guide.

## ✅ Current Implementation Status (Post-Feature 016)

### What We're Doing Right:

1. **Native LangChain 1.0 Integration** ✅
   - Using `langchain-postgres>=0.0.12` (dedicated PGVector package)
   - Using `langchain-google-vertexai>=2.0.0` for embeddings (LangChain 1.0 compatible)
   - Cloud SQL Connector for secure IAM-authenticated connections
   - psycopg3 driver with async adapter (`asyncio.to_thread`)

2. **Standard PGVector Schema** ✅
   - `langchain_pg_collection`: Collection metadata table
   - `langchain_pg_embedding`: Vector embeddings with JSONB metadata
   - Standard schema enables easier upgrades and broader LangChain ecosystem compatibility
   - Flexible JSONB metadata (no schema migration required for new fields)

3. **IAM Authentication** ✅
   - Configured with `cloudsql.iam_authentication=on`
   - Cloud SQL Connector handles automatic IAM token refresh (no password management)
   - Service accounts: hansard-db-admin (full), hansard-db-readonly (SELECT only)
   - Principle of least privilege enforced at database and IAM levels

4. **Async Operations** ✅
   - Async adapter wraps sync PGVector operations (`asyncio.to_thread`)
   - All storage services use async/await pattern for non-blocking I/O
   - SQLAlchemy 2.x engine with connection pooling
   - Transient error retry with exponential backoff (1s, 2s, 4s)

5. **Vector Indexing** ✅
   - HNSW index for ANN (Approximate Nearest Neighbor) search
   - Configured with m=16, ef_construction=100 (PGVector defaults)
   - Automatic index creation via LangChain migrations
   - Vector cosine similarity search optimized

6. **Configuration Management** ✅
   - Centralized constants in `src/config.py`
   - Feature flag: `VECTOR_BACKEND=postgres|legacy` for instant rollback
   - Collection name: `POSTGRES_COLLECTION_NAME=hansard`
   - Cloud SQL configuration via environment variables
   - IAM authentication automatic (no password configuration)

7. **Rollback Safety** ✅
   - Feature flag enables instant rollback (<5 minutes)
   - Both backends access same data (after migration)
   - Fail-fast validation prevents misconfiguration
   - Comprehensive staging smoke tests before production

## 📊 Key Best Practices from Google Cloud (2025)

### 1. Schema Design
- **Single-table approach**: Store metadata in columns, not JSONB, for better performance
- **Custom metadata columns**: Define frequently-filtered fields as distinct columns
- **Flexible schema**: Leverage pre-existing database schemas without migration

### 2. Connection & Security
- **Cloud SQL Python Connector**: Embedded in langchain-google-cloud-sql-pg
- **IAM authorization**: Control who can connect at the GCP level
- **Automatic connection pooling**: SQLAlchemy pools configured automatically

### 3. Performance Optimization
- **ANN search**: PostgresVectorStore supports Approximate Nearest Neighbor
- **Async operations**: Non-blocking I/O for concurrent request handling
- **Vector indexes**: Create and maintain directly from LangChain (IaC approach)
- **Hybrid search**: Dense vectors + full-text search for comprehensive results

### 4. Data Population Strategy
- **Text splitting**: Use RecursiveCharacterTextSplitter from LangChain
- **Batch embedding**: Generate vectors for chunks via Vertex AI
- **Streaming ingest**: For large datasets, use streaming APIs

### 5. Extensions Required
```sql
CREATE EXTENSION IF NOT EXISTS vector;  -- pgvector for vector storage
```

### 6. Latest Enhancements (2025)
- Google Cloud became major contributor to LangChain PostgreSQL package
- Announced at Google Cloud Next '25
- AlloyDB now supports ScaNN index (12 years of Google Research)
- Improved vector search performance and accuracy

## 🔧 Implementation Details (Feature 016: langchain-postgres)

### Our Stack:
- **Database**: Cloud SQL PostgreSQL 15+ (db-custom-4-16384 recommended for production)
- **Vector Extension**: pgvector 0.8.0+
- **Embedding Model**: Vertex AI text-embedding-005 (768 dimensions)
- **LangChain Packages**:
  - `langchain>=1.0.0` (stable LangChain 1.0 release)
  - `langchain-postgres>=0.0.12` (dedicated PGVector integration)
  - `langchain-google-vertexai>=2.0.0` (Vertex AI embeddings, LangChain 1.0 compatible)
  - `langchain-google-genai` (additional Google AI integrations)
- **Database Driver**: psycopg3 (psycopg[binary]>=3.1,<3.3)
- **Connection**: cloud-sql-python-connector>=1.4.0 (IAM auth)
- **Engine**: SQLAlchemy 2.x
- **Python Version**: 3.11+
- **Framework**: FastMCP 2.14.0+

### PGVector Standard Schema:
```sql
-- Collection metadata table
CREATE TABLE langchain_pg_collection (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL UNIQUE,
    cmetadata JSONB
);

-- Embedding table with JSONB metadata
CREATE TABLE langchain_pg_embedding (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID REFERENCES langchain_pg_collection(uuid) ON DELETE CASCADE,
    embedding VECTOR(768) NOT NULL,  -- 768-dim for text-embedding-005
    document TEXT,
    cmetadata JSONB,
    custom_id VARCHAR  -- Maps to langchain_id from legacy schema
);

-- HNSW index for fast vector similarity search
CREATE INDEX ON langchain_pg_embedding 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 100);

-- B-tree index on custom_id for lookups
CREATE INDEX ON langchain_pg_embedding(custom_id);

-- GIN index on JSONB metadata for filtering
CREATE INDEX ON langchain_pg_embedding USING gin(cmetadata);
```

### Legacy Schema (Pre-Feature 016):
```sql
-- Legacy table (still exists for rollback safety)
CREATE TABLE hansard_speeches (
    langchain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    langchain_metadata JSONB DEFAULT '{}'::jsonb,
    -- Custom metadata columns for efficient filtering (legacy approach)
    speaker VARCHAR(200),
    party VARCHAR(100),
    chamber VARCHAR(50),
    date DATE,
    speech_type VARCHAR(100),
    electorate VARCHAR(100),
    speaker_id VARCHAR(20),
    utterance_id VARCHAR(100),
    debate TEXT
);

-- HNSW index for fast vector similarity search
CREATE INDEX hansard_speeches_embedding_idx
ON hansard_speeches
USING hnsw (embedding vector_cosine_ops)
WITH (m = 24, ef_construction = 100);

-- Metadata indexes for SQL filtering
CREATE INDEX idx_hansard_speeches_speaker ON hansard_speeches(speaker);
CREATE INDEX idx_hansard_speeches_party ON hansard_speeches(party);
CREATE INDEX idx_hansard_speeches_chamber ON hansard_speeches(chamber);
CREATE INDEX idx_hansard_speeches_date ON hansard_speeches(date);
```

## 🚀 Recommended Workflow (Post-Feature 016)

### 1. Development
```bash
# Local dev with auth bypass
DANGEROUSLY_OMIT_AUTH=true \
VECTOR_BACKEND=postgres \
fastmcp dev src/server.py
```

### 2. Migration from Legacy to langchain-postgres
```bash
# See complete migration guide
cat specs/016-langchain-postgres-upgrade/migration-procedure.md

# Quick migration (dry-run first)
python scripts/migrate_to_langchain_postgres.py --dry-run

# Execute migration
python scripts/migrate_to_langchain_postgres.py --execute

# Validate migration
python scripts/migrate_to_langchain_postgres.py --validate
```

### 3. Backend Selection (Feature Flag)
```bash
# Use new postgres backend (post-migration)
export VECTOR_BACKEND=postgres

# Instant rollback to legacy backend (if issues detected)
export VECTOR_BACKEND=legacy

# Invalid values fail fast at startup
export VECTOR_BACKEND=invalid  # ValueError with clear message
```

### 4. Data Population
```bash
# Ingest speeches (with chunking + embedding generation)
# Use the ingest_hansard_speech MCP tool or ingest scripts

# Note: After migration, both backends access same data
# No need to re-ingest when switching backends
```

### 5. Production Deployment
- Use read-only service account for MCP server queries
- Use admin service account for schema migrations and data ingestion
- Enable IAM authentication (no passwords in production)
- Set VECTOR_BACKEND=postgres after successful staging validation
- Keep legacy backend available for instant rollback (<5 minutes)

## 🔄 Migration Strategy (Feature 016)

### Phase 1: Preparation
1. Deploy application with both backends (VECTOR_BACKEND=legacy)
2. Run migration script in dry-run mode
3. Validate prerequisites (tables exist, pgvector enabled, IAM configured)

### Phase 2: Migration
1. Execute migration script (batch processing, idempotent)
2. Validate record counts match (source == target)
3. Run spot-check validation (10 random records)
4. Monitor migration performance (10K rows < 5 minutes)

### Phase 3: Validation
1. Run staging smoke tests (6 tests + checklist)
2. Verify backend switching works (legacy ↔ postgres)
3. Validate IAM authentication (no password fallback)
4. Check performance (P95 latency ≤ 110% of baseline)

### Phase 4: Gradual Rollout
1. Switch to postgres backend in staging (VECTOR_BACKEND=postgres)
2. Monitor for 48 hours (error rate, latency, throughput)
3. Gradual production rollout (10% → 50% → 100% traffic)
4. Monitor closely during rollout (instant rollback available)

### Phase 5: Cleanup (Post-Stability)
1. After 48 hours of stable production operation
2. Remove legacy dependency (`langchain-google-cloud-sql-pg`)
3. Archive old table (rename, do not drop)
4. Final cleanup after backup confirmation

**Complete Migration Guide**: `specs/016-langchain-postgres-upgrade/migration-procedure.md`

## 🚀 Recommended Workflow

### 1. Development
```bash
# Local dev with auth bypass
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py
```

### 2. Schema Initialization
```bash
# Using admin service account
GCP_PROJECT_ID=skai-fastmcp-cloudrun \
GCP_REGION=us-central1 \
CLOUDSQL_INSTANCE=hansard-db-v2 \
CLOUDSQL_DATABASE=hansard \
python3 scripts/init_langchain_schema.py
```

### 3. Data Population
```bash
# Ingest speeches (with chunking + embedding generation)
# Use the ingest_hansard_speech MCP tool
```

### 4. Production Deployment
- Use read-only service account for MCP server queries
- Use admin service account for schema migrations and data ingestion
- Enable IAM authentication (no passwords in production)

## 📚 References

### LangChain 1.0 + langchain-postgres (Current)
- [LangChain PGVector Integration (langchain-postgres)](https://python.langchain.com/docs/integrations/vectorstores/pgvector/)
- [langchain-postgres Package Documentation](https://python.langchain.com/docs/integrations/vectorstores/postgres/)
- [LangChain 1.0 Release Notes](https://blog.langchain.dev/langchain-v01/)
- [Feature 016 Specification](specs/016-langchain-postgres-upgrade/spec.md)
- [Migration Procedure](specs/016-langchain-postgres-upgrade/migration-procedure.md)
- [Quick Start Guide](specs/016-langchain-postgres-upgrade/quickstart.md)

### Google Cloud + PGVector (General)
- [Using pgvector, LLMs and LangChain with Google Cloud databases](https://cloud.google.com/blog/products/databases/using-pgvector-llms-and-langchain-with-google-cloud-databases)
- [VectorStore in Cloud SQL for PostgreSQL LangChain package](https://cloud.google.com/blog/products/databases/vectorstore-in-the-cloud-sql-for-postgresql-langchain-package)
- [Open-source enhancements to LangChain PostgreSQL](https://cloud.google.com/blog/products/ai-machine-learning/open-source-enhancements-to-langchain-postgresql)
- [Build LLM-powered applications using LangChain](https://cloud.google.com/sql/docs/postgres/langchain)
- [Cloud SQL IAM Authentication](https://cloud.google.com/sql/docs/postgres/authentication)

### Legacy Integration (Pre-Feature 016)
- [LangChain Google Cloud SQL PostgreSQL Integration (Legacy)](https://python.langchain.com/docs/integrations/vectorstores/google_cloud_sql_pg/)
- **Note**: `langchain-google-cloud-sql-pg` is deprecated in favor of `langchain-postgres` for LangChain 1.0

## 🎯 Next Steps

1. ✅ Schema initialized (pending manual SQL execution)
2. ⏳ Populate database with sample Hansard speeches
3. ⏳ Test search functionality with queries
4. ⏳ Benchmark performance with large datasets
5. ⏳ Consider upgrading to AlloyDB for ScaNN index support (production)
