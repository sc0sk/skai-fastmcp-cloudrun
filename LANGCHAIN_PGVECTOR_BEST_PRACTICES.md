# LangChain + pgvector + Google Cloud SQL Best Practices (2025)

Based on Google Cloud documentation and latest LangChain PostgreSQL enhancements.

## ✅ Current Implementation Status

### What We're Doing Right:

1. **Native Integration Library** ✅
   - Using `langchain-google-cloud-sql-pg` integration
   - Using `langchain-google-vertexai` for embeddings
   - Embedded Cloud SQL Python connector for secure connections

2. **Single-Table Schema** ✅
   - `hansard_speeches` table with metadata as columns (not JSONB)
   - Faster query execution for large collections
   - Defined columns: speaker, party, chamber, date, speech_type, electorate, speaker_id, utterance_id, debate

3. **IAM Authentication** ✅
   - Configured with `cloudsql.iam_authentication=on`
   - Two service accounts: hansard-db-admin (full), hansard-db-readonly (SELECT only)
   - Principle of least privilege

4. **Async Drivers** ✅
   - Using asyncpg for non-blocking I/O
   - All storage services use async/await pattern
   - Connection pooling with SQLAlchemy

5. **Vector Indexing** ✅
   - HNSW index for ANN (Approximate Nearest Neighbor) search
   - Configured with m=24, ef_construction=100
   - Infrastructure-as-code approach via LangChain

6. **Configuration Management** ✅
   - Centralized constants in src/config.py
   - Table names: VECTOR_TABLE_NAME, METADATA_TABLE_NAME
   - Service account names: DB_ADMIN_SERVICE_ACCOUNT, DB_READONLY_SERVICE_ACCOUNT
   - Database configuration: CLOUDSQL_INSTANCE_NAME, CLOUDSQL_TIER, CLOUDSQL_DATABASE_VERSION

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

## 🔧 Implementation Details

### Our Stack:
- **Database**: Cloud SQL PostgreSQL 15 (db-f1-micro)
- **Vector Extension**: pgvector 0.8.0
- **Embedding Model**: text-embedding-005 (768 dimensions)
- **LangChain Packages**:
  - langchain-google-cloud-sql-pg
  - langchain-google-vertexai
- **Python Version**: 3.11+
- **Framework**: FastMCP 2.14.0+

### Table Schema:
```sql
CREATE TABLE hansard_speeches (
    langchain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    langchain_metadata JSONB DEFAULT '{}'::jsonb,
    -- Custom metadata columns for efficient filtering
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

- [Using pgvector, LLMs and LangChain with Google Cloud databases](https://cloud.google.com/blog/products/databases/using-pgvector-llms-and-langchain-with-google-cloud-databases)
- [VectorStore in Cloud SQL for PostgreSQL LangChain package](https://cloud.google.com/blog/products/databases/vectorstore-in-the-cloud-sql-for-postgresql-langchain-package)
- [LangChain Google Cloud SQL PostgreSQL Integration](https://python.langchain.com/docs/integrations/vectorstores/google_cloud_sql_pg/)
- [Open-source enhancements to LangChain PostgreSQL](https://cloud.google.com/blog/products/ai-machine-learning/open-source-enhancements-to-langchain-postgresql)
- [Build LLM-powered applications using LangChain](https://cloud.google.com/sql/docs/postgres/langchain)

## 🎯 Next Steps

1. ✅ Schema initialized (pending manual SQL execution)
2. ⏳ Populate database with sample Hansard speeches
3. ⏳ Test search functionality with queries
4. ⏳ Benchmark performance with large datasets
5. ⏳ Consider upgrading to AlloyDB for ScaNN index support (production)
