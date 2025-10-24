# Next Steps: Initialize Database Schema

## Current Status

✅ **Completed:**
1. Configuration constants refactored to [src/config.py](src/config.py)
2. Service accounts created (hansard-db-admin, hansard-db-readonly) with Cloud SQL Client IAM role
3. Fresh PostgreSQL 15 instance (hansard-db-v2, db-f1-micro) with `hansard` database
4. MCP server defined cleanly in [src/server.py](src/server.py) (no duplication)
5. Tools cleanly separated in src/tools/ (search.py, fetch.py, ingest.py)
6. Constitution updated with Configuration Management best practices
7. Documentation created:
   - [init_hansard_schema.sql](init_hansard_schema.sql) - Complete schema SQL
   - [DATABASE_SETUP.md](DATABASE_SETUP.md) - Setup instructions
   - [LANGCHAIN_PGVECTOR_BEST_PRACTICES.md](LANGCHAIN_PGVECTOR_BEST_PRACTICES.md) - 2025 best practices from Google Cloud

❌ **Remaining: One Manual Step**

The database is empty and needs the LangChain schema initialized with the **langchain_id** column (currently missing, causing search failures).

## How to Initialize Schema

### Option 1: Google Cloud Console SQL Editor (Easiest)

1. Go to https://console.cloud.google.com/sql/instances/hansard-db-v2/
2. Click "Open Cloud Shell Editor" or navigate to the SQL editor
3. Copy the contents of [init_hansard_schema.sql](init_hansard_schema.sql)
4. Paste into the SQL editor and execute

### Option 2: Install psql and Run SQL File

```bash
# Install PostgreSQL client (requires sudo)
sudo apt-get update && sudo apt-get install -y postgresql-client

# Execute SQL file
PGPASSWORD=temporarypassword123 psql "host=136.115.241.202 dbname=hansard user=postgres sslmode=require" < init_hansard_schema.sql
```

### Option 3: Copy SQL Commands Manually

Connect to the database and run these commands:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create hansard_speeches table with LangChain schema
CREATE TABLE IF NOT EXISTS hansard_speeches (
    langchain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    langchain_metadata JSONB DEFAULT '{}'::jsonb,
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

-- Create HNSW vector index for similarity search
CREATE INDEX IF NOT EXISTS hansard_speeches_embedding_idx
ON hansard_speeches
USING hnsw (embedding vector_cosine_ops)
WITH (m = 24, ef_construction = 100);

-- Create metadata indexes for efficient filtering
CREATE INDEX IF NOT EXISTS idx_hansard_speeches_speaker ON hansard_speeches(speaker);
CREATE INDEX IF NOT EXISTS idx_hansard_speeches_party ON hansard_speeches(party);
CREATE INDEX IF NOT EXISTS idx_hansard_speeches_chamber ON hansard_speeches(chamber);
CREATE INDEX IF NOT EXISTS idx_hansard_speeches_date ON hansard_speeches(date);
```

## After Schema Initialization

### 1. Verify Schema

```sql
\d hansard_speeches
```

You should see the `langchain_id` column listed.

### 2. Test Search Functionality

```bash
PYTHONPATH=src \
GCP_PROJECT_ID=skai-fastmcp-cloudrun \
GCP_REGION=us-central1 \
CLOUDSQL_INSTANCE=hansard-db-v2 \
CLOUDSQL_DATABASE=hansard \
CLOUDSQL_USER=postgres \
DATABASE_PASSWORD=temporarypassword123 \
uv run python3 -c "
import asyncio
from tools.search import search_hansard_speeches

async def test():
    result = await search_hansard_speeches(query='climate', limit=5)
    print(f'Total results: {result.get(\"total_results\", 0)}')
    print('✅ Search working! (0 results expected - database is empty)')

asyncio.run(test())
"
```

If you see "✅ Search working!" without errors, the schema is correctly initialized!

### 3. Populate Database

Use the Hansard speeches from `/home/user/sk-hansard-converter/output_md_enhanced/reps/` to populate the database.

## Why This Matters

The **langchain_id** column is required by LangChain's PostgresVectorStore. Without it, all searches fail with:

```
ValueError: Id column, langchain_id, does not exist.
```

Once initialized, the system will be ready for:
- ✅ Vector similarity search
- ✅ Hybrid search (vectors + SQL filters)
- ✅ Data ingestion with automatic embedding generation
- ✅ Production deployment

## Implementation Follows Google Cloud 2025 Best Practices

Our implementation aligns with the latest recommendations:
- ✅ Single-table schema with metadata columns (not JSONB)
- ✅ Native `langchain-google-cloud-sql-pg` integration
- ✅ Async drivers (asyncpg) for performance
- ✅ HNSW indexing for ANN search
- ✅ IAM authentication support
- ✅ Configurable constants (no hardcoded values)

See [LANGCHAIN_PGVECTOR_BEST_PRACTICES.md](LANGCHAIN_PGVECTOR_BEST_PRACTICES.md) for details.
