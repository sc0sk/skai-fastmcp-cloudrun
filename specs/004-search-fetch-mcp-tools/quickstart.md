# Quickstart Guide: Search and Fetch MCP Tools

**Feature**: 004-search-fetch-mcp-tools | **Date**: 2025-10-23 | **Status**: Implementation Complete

## Overview

This guide walks you through setting up the Hansard MCP Server locally for development and testing. The server provides two MCP tools for searching and fetching Australian parliamentary speeches from Simon Kennedy's Hansard records.

## Prerequisites

### Required Software

- **Python 3.11+**: Cloud Run compatible version
- **uv**: Fast Python package manager ([install guide](https://github.com/astral-sh/uv))
- **gcloud CLI**: Google Cloud SDK ([install guide](https://cloud.google.com/sdk/docs/install))
- **PostgreSQL 14+** with pgvector extension (Cloud SQL recommended)
- **Git**: For cloning the repository

### Required Accounts

- **Google Cloud Platform account** with:
  - Cloud SQL instance with PostgreSQL 14+ and pgvector extension
  - Vertex AI API enabled
  - Cloud Run API enabled (optional, for deployment)
  - Service account with Vertex AI User and Cloud SQL Client roles

### Environment Variables

The following environment variables must be set (use `.env` file for local development):

```bash
# GCP Project Configuration
GCP_PROJECT_ID="your-project-id"
GCP_REGION="us-central1"
VERTEX_AI_LOCATION="us-central1"

# Cloud SQL Configuration
CLOUDSQL_INSTANCE="hansard-db-v2"
CLOUDSQL_DATABASE="hansard"
CLOUDSQL_USER="your-username"  # Optional: leave blank for IAM auth
DATABASE_PASSWORD="your-password"  # Optional: leave blank for IAM auth

# Authentication (Local Development)
DANGEROUSLY_OMIT_AUTH="true"  # Bypass OAuth for local testing

# Application Configuration
PYTHONPATH="src"  # Required for relative imports
```

**Note**: For production, use Google Secret Manager to store credentials. Never commit `.env` files to version control.

---

## Setup Steps

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/skai-fastmcp-cloudrun.git
cd skai-fastmcp-cloudrun
```

### 2. Install Dependencies

Using `uv` (recommended):

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

Using `pip` (alternative):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

**Key Dependencies** (from `pyproject.toml`):
- `fastmcp>=2.12.5` - MCP server framework
- `langchain-google-vertexai>=2.0.10` - Vertex AI Embeddings
- `langchain-google-cloud-sql-pg>=0.15.1` - PostgreSQL vector store
- `pydantic>=2.0.0` - Data validation
- `asyncpg>=0.29.0` - Async PostgreSQL driver
- `cloud-sql-python-connector>=1.13.0` - Cloud SQL connection

### 3. Authenticate with Google Cloud

```bash
# Login to Google Cloud
gcloud auth login

# Set application default credentials (for Vertex AI)
gcloud auth application-default login

# Set default project
gcloud config set project YOUR_PROJECT_ID
```

### 4. Create Cloud SQL Instance

If you don't have a Cloud SQL instance, create one:

```bash
# Create PostgreSQL 14 instance with pgvector
gcloud sql instances create hansard-db-v2 \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1

# Set password for postgres user
gcloud sql users set-password postgres \
  --instance=hansard-db-v2 \
  --password=YOUR_SECURE_PASSWORD

# Create hansard database
gcloud sql databases create hansard \
  --instance=hansard-db-v2
```

**Alternative**: Use existing Cloud SQL instance name in `.env` file.

### 5. Initialize Database Schema

Connect to Cloud SQL and run initialization script:

```bash
# Connect via gcloud
gcloud sql connect hansard-db-v2 --user=postgres --database=hansard

# Inside psql, run:
\i scripts/init_hansard_db_v2.sql
```

Or run the SQL script directly:

```bash
cat scripts/init_hansard_db_v2.sql | \
  gcloud sql connect hansard-db-v2 --user=postgres --database=hansard
```

**What this does**:
- Enables pgvector extension
- Creates `speeches` table for full text storage
- Creates `speech_chunks` table for vector embeddings
- Creates HNSW index for fast vector similarity search
- Creates B-tree indexes on common query fields (speaker, date, party)

**Verify**:

```sql
-- Check tables exist
\dt

-- Check pgvector extension
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- Check HNSW index
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'speech_chunks';
```

### 6. Configure Environment Variables

Create `.env` file in project root:

```bash
# Copy template
cp .env.example .env

# Edit with your values
nano .env
```

Example `.env` file:

```bash
# GCP Configuration
GCP_PROJECT_ID="skai-hansard-rag-dev"
GCP_REGION="us-central1"
VERTEX_AI_LOCATION="us-central1"

# Cloud SQL Configuration
CLOUDSQL_INSTANCE="hansard-db-v2"
CLOUDSQL_DATABASE="hansard"
CLOUDSQL_USER="postgres"
DATABASE_PASSWORD="your-secure-password"

# Local Development
DANGEROUSLY_OMIT_AUTH="true"
PYTHONPATH="src"
```

**Security Note**: Add `.env` to `.gitignore` to prevent committing secrets.

### 7. Ingest Sample Data

Load Simon Kennedy's speeches into the database:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run ingestion script
python scripts/populate_hansard_db.py
```

**What this does**:
1. Reads markdown files from `/home/user/sk-hansard-converter/output_md_enhanced/reps/` (default path)
2. Parses YAML frontmatter (29 metadata fields)
3. Validates data with Pydantic models
4. Stores full speech text in `speeches` table
5. Chunks text (500-1500 chars with 200-char overlap)
6. Generates embeddings via Vertex AI (text-embedding-005)
7. Stores chunks and embeddings in `speech_chunks` table

**Expected Output**:

```
Loading speeches from /home/user/sk-hansard-converter/output_md_enhanced/reps/
Found 64 markdown files
Processing: 2024-05-28-climate-change-bill.md
  ✓ Speech ingested: 550e8400-e29b-41d4-a716-446655440000 (8 chunks)
Processing: 2024-06-03-housing-affordability.md
  ✓ Speech ingested: 123e4567-e89b-12d3-a456-426614174001 (12 chunks)
...
✅ Ingestion complete: 64 speeches, 628 chunks
```

**Verify**:

```sql
-- Check speech count
SELECT COUNT(*) FROM speeches;

-- Check chunk count
SELECT COUNT(*) FROM speech_chunks;

-- Sample search (raw SQL)
SELECT speech_id, title, speaker, date
FROM speeches
ORDER BY date DESC
LIMIT 5;
```

---

## Running the Server

### Option 1: FastMCP Development Mode (Recommended)

```bash
# Set environment variables
export DANGEROUSLY_OMIT_AUTH=true
export PYTHONPATH=src

# Run FastMCP dev server
fastmcp dev src/server.py
```

**Expected Output**:

```
🚀 FastMCP Hansard RAG Server starting...
🔄 Warming up database connections and embedding models...
✅ Vector store initialized
✅ Metadata store initialized
✅ Server ready!
⚠️  WARNING: Authentication DISABLED (DANGEROUSLY_OMIT_AUTH=true)
✅ Hansard MCP Server initialized with ChatGPT Developer Mode enhancements
   🔍 search_hansard_speeches [read-only]
   📄 fetch_hansard_speech [read-only]
   ⚠️  ingest_hansard_speech [disabled - CLI/script only]

Available at: stdio://
```

**What this does**:
- Starts MCP server in stdio transport mode (for MCP Inspector)
- Disables OAuth authentication for local testing
- Pre-initializes database connections and embedding models
- Registers two read-only MCP tools

### Option 2: HTTP Mode (for Testing with curl)

```bash
# Run in HTTP mode
PORT=8080 DANGEROUSLY_OMIT_AUTH=true PYTHONPATH=src fastmcp dev src/server.py
```

**Expected Output**:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

**Test with curl**:

```bash
# Health check
curl http://localhost:8080/health

# List MCP tools
curl -X POST http://localhost:8080/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Search speeches
curl -X POST http://localhost:8080/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search_hansard_speeches",
      "arguments": {
        "query": "housing affordability",
        "limit": 5
      }
    },
    "id": 2
  }'
```

### Option 3: Docker (Production-Like Environment)

```bash
# Build Docker image
docker build -t hansard-mcp:latest .

# Run container
docker run -p 8080:8080 \
  -e DANGEROUSLY_OMIT_AUTH=true \
  -e GCP_PROJECT_ID=$GCP_PROJECT_ID \
  -e GCP_REGION=$GCP_REGION \
  -e CLOUDSQL_INSTANCE=$CLOUDSQL_INSTANCE \
  -e CLOUDSQL_DATABASE=$CLOUDSQL_DATABASE \
  -e CLOUDSQL_USER=$CLOUDSQL_USER \
  -e DATABASE_PASSWORD=$DATABASE_PASSWORD \
  hansard-mcp:latest
```

**Alternative**: Use Docker Compose:

```bash
# Start server and Redis (for OAuth token storage)
docker compose -f deployment/docker-compose.yml up
```

---

## Testing the Tools

### Option 1: MCP Inspector (Recommended)

The MCP Inspector is a web-based tool for testing MCP servers.

```bash
# Install MCP Inspector (globally)
npm install -g @modelcontextprotocol/inspector

# Run inspector (connects to stdio server)
npx @modelcontextprotocol/inspector fastmcp dev src/server.py
```

**Expected Output**:

```
MCP Inspector running at: http://localhost:5173
Server: fastmcp dev src/server.py (stdio)
```

**Usage**:
1. Open http://localhost:5173 in browser
2. Click "Connect to Server"
3. Select "search_hansard_speeches" tool
4. Enter query parameters:
   - query: "climate change policy"
   - party: "Liberal"
   - limit: 5
5. Click "Execute"
6. View results in JSON format

### Option 2: Python Script

Create `test_tools.py`:

```python
import asyncio
from src.tools.search import search_hansard_speeches
from src.tools.fetch import fetch_hansard_speech

async def test_search():
    """Test search tool."""
    print("Testing search_hansard_speeches...")
    results = await search_hansard_speeches(
        query="housing affordability",
        party="Liberal",
        limit=5
    )
    print(f"Found {results['total_count']} speeches")

    for speech in results['speeches']:
        print(f"- {speech['title']} ({speech['date']})")
        print(f"  Relevance: {speech['relevance_score']:.2f}")
        print(f"  Excerpt: {speech['excerpt'][:100]}...")

        # Fetch full speech
        print("\nFetching full speech...")
        full_speech = await fetch_hansard_speech(speech['speech_id'])
        print(f"Full text length: {len(full_speech['full_text'])} chars")
        print(f"Word count: {full_speech['word_count']}")

if __name__ == "__main__":
    asyncio.run(test_search())
```

Run:

```bash
PYTHONPATH=src python test_tools.py
```

### Option 3: pytest (Unit and Integration Tests)

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_search_tool.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run integration tests (requires live database)
pytest tests/integration/ -v
```

**Expected Output**:

```
tests/unit/test_search_tool.py::test_search_basic PASSED
tests/unit/test_search_tool.py::test_search_with_filters PASSED
tests/unit/test_fetch_tool.py::test_fetch_valid_id PASSED
tests/unit/test_fetch_tool.py::test_fetch_invalid_id PASSED
tests/integration/test_mcp_tools.py::test_search_fetch_workflow PASSED

======================== 5 passed in 2.34s =========================
```

---

## Common Development Tasks

### Update Database Schema

If you modify the database schema:

```bash
# Connect to Cloud SQL
gcloud sql connect hansard-db-v2 --user=postgres --database=hansard

# Run migration SQL
\i scripts/migrate_add_chunk_id.sql
```

### Re-ingest Speeches

To clear and re-populate the database:

```bash
# Delete all data
python scripts/reset_and_populate.py

# Or manually:
# 1. Connect to database
gcloud sql connect hansard-db-v2 --user=postgres --database=hansard

# 2. Drop tables
DROP TABLE speech_chunks CASCADE;
DROP TABLE speeches CASCADE;

# 3. Re-run initialization
\i scripts/init_hansard_db_v2.sql

# 4. Re-ingest data
python scripts/populate_hansard_db.py
```

### Debug Embedding Generation

Test Vertex AI Embeddings directly:

```python
from langchain_google_vertexai import VertexAIEmbeddings

embeddings = VertexAIEmbeddings(
    model_name="text-embedding-005",
    project="your-project-id",
    location="us-central1"
)

# Generate embedding
text = "This is a test sentence for embedding generation."
vector = embeddings.embed_query(text)
print(f"Embedding dimensions: {len(vector)}")
print(f"First 5 values: {vector[:5]}")
```

### Monitor Database Connections

Check active connections to Cloud SQL:

```sql
-- View active connections
SELECT * FROM pg_stat_activity WHERE datname = 'hansard';

-- Kill idle connections (if needed)
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'hansard' AND state = 'idle' AND pid <> pg_backend_pid();
```

### View Vector Store Statistics

```python
from src.storage.vector_store import get_default_vector_store
from src.storage.metadata_store import get_default_metadata_store
import asyncio

async def get_stats():
    vector_store = await get_default_vector_store()
    metadata_store = await get_default_metadata_store()

    stats = await metadata_store.get_stats()
    print("Database Statistics:")
    print(f"- Total speeches: {stats['speech_count']}")
    print(f"- Unique speakers: {stats['unique_speakers']}")
    print(f"- Date range: {stats['earliest_date']} to {stats['latest_date']}")
    print(f"- Party breakdown: {stats['party_breakdown']}")

asyncio.run(get_stats())
```

---

## Troubleshooting

### Error: "Cloud SQL instance not found"

**Solution**: Verify Cloud SQL instance name in `.env`:

```bash
gcloud sql instances list
```

Update `CLOUDSQL_INSTANCE` to match exact instance name.

### Error: "relation 'speech_chunks' does not exist"

**Solution**: Run database initialization:

```bash
cat scripts/init_hansard_db_v2.sql | \
  gcloud sql connect hansard-db-v2 --user=postgres --database=hansard
```

### Error: "Permission denied for table speeches"

**Solution**: Grant permissions to your database user:

```sql
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_username;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_username;
```

### Error: "Vertex AI embeddings generation failed"

**Solution**: Check Vertex AI API is enabled:

```bash
gcloud services enable aiplatform.googleapis.com
gcloud auth application-default login
```

Verify project ID in `.env` matches authenticated project.

### Error: "HNSW index build failed"

**Solution**: pgvector extension may not be installed:

```sql
-- Check extension
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- Install if missing
CREATE EXTENSION vector;
```

If pgvector is not available, upgrade Cloud SQL instance to PostgreSQL 14+.

### Slow Search Performance

**Solution**: Check HNSW index exists:

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'speech_chunks' AND indexname LIKE '%embedding%';
```

If missing, create index:

```sql
CREATE INDEX speech_chunks_embedding_idx
ON speech_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 24, ef_construction = 100);
```

### Connection Pool Exhausted

**Solution**: Close idle connections or increase pool size:

```python
# In src/storage/vector_store.py
# Add connection pool configuration
engine = await PostgresEngine.afrom_instance(
    ...,
    pool_min_size=5,
    pool_max_size=20
)
```

---

## Next Steps

### Integrating with MCP Clients

**Claude Desktop**:

1. Generate MCP configuration:
   ```bash
   fastmcp install mcp-json
   ```

2. Add to Claude Desktop config (`~/.config/claude/config.json`):
   ```json
   {
     "mcpServers": {
       "hansard": {
         "command": "fastmcp",
         "args": ["run", "/path/to/skai-fastmcp-cloudrun/src/server.py"],
         "env": {
           "GCP_PROJECT_ID": "your-project-id",
           "CLOUDSQL_INSTANCE": "hansard-db-v2",
           "CLOUDSQL_DATABASE": "hansard"
         }
       }
     }
   }
   ```

**VS Code with Continue**:

1. Install Continue extension
2. Add MCP server to `.continue/config.json`:
   ```json
   {
     "mcpServers": [
       {
         "name": "hansard",
         "command": ["fastmcp", "run", "/path/to/src/server.py"]
       }
     ]
   }
   ```

**ChatGPT (Production)**:

1. Deploy to Cloud Run (see deployment guide)
2. Configure OAuth with GitHub
3. Add MCP server URL to ChatGPT settings

### Deploying to Cloud Run

See `/home/user/skai-fastmcp-cloudrun/specs/002-github-oauth-docker/` for full deployment guide.

Quick deployment:

```bash
# Build and push Docker image
docker build -t gcr.io/$GCP_PROJECT_ID/hansard-mcp:latest .
docker push gcr.io/$GCP_PROJECT_ID/hansard-mcp:latest

# Deploy to Cloud Run
gcloud run deploy hansard-mcp-server \
  --image=gcr.io/$GCP_PROJECT_ID/hansard-mcp:latest \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated
```

### Expanding Test Coverage

Add more tests to meet constitution requirements:

```bash
# Create test file
touch tests/unit/test_search_filters.py

# Add tests for:
# - Multiple filter combinations (party + chamber + date)
# - Date range edge cases (start_date > end_date)
# - Invalid enum values (party="InvalidParty")
# - Empty result sets
# - Large result sets (limit=100)
```

---

## Resources

- **FastMCP Documentation**: https://docs.fastmcp.com/
- **LangChain Cloud SQL PostgreSQL**: https://python.langchain.com/docs/integrations/vectorstores/google_cloud_sql_pg
- **Vertex AI Embeddings**: https://cloud.google.com/vertex-ai/docs/generative-ai/embeddings/get-text-embeddings
- **pgvector Documentation**: https://github.com/pgvector/pgvector
- **Project Constitution**: `/home/user/skai-fastmcp-cloudrun/.specify/memory/constitution.md`
- **Feature Spec**: `/home/user/skai-fastmcp-cloudrun/specs/004-search-fetch-mcp-tools/spec.md`
- **Data Model**: `/home/user/skai-fastmcp-cloudrun/specs/004-search-fetch-mcp-tools/data-model.md`

---

## Getting Help

- **Issues**: Open GitHub issue with error logs and `.env` configuration (redact secrets)
- **Questions**: Check existing documentation in `specs/004-search-fetch-mcp-tools/`
- **Contributions**: Follow contribution guidelines in `CONTRIBUTING.md`

---

**Last Updated**: 2025-10-23
**Maintainer**: Simon Kennedy MCP Development Team
**Version**: 1.0.0
