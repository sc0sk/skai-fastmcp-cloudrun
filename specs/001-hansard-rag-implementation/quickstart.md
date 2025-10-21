# Quickstart: Australian Hansard RAG

**Branch**: `001-hansard-rag-implementation`
**Date**: 2025-10-21
**For**: Local development setup

---

## Prerequisites

- Python 3.11+
- Google Cloud Project with billing enabled
- Google Cloud SDK (`gcloud`) installed
- Git

---

## Setup (Local Development)

### 1. Clone Repository

```bash
git clone https://github.com/sc0sk/skai-fastmcp-cloudrun.git
cd skai-fastmcp-cloudrun
git checkout 001-hansard-rag-implementation
```

### 2. Install Dependencies

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install fastmcp>=2.14.0
pip install langchain-google-vertexai>=2.0.0
pip install langchain-google-cloud-sql-pg>=0.12.0
pip install langchain-core>=0.3.0
pip install pydantic>=2.5.0
pip install asyncpg>=0.29.0
pip install pytest>=7.4.0
pip install pytest-asyncio>=0.21.0
```

### 3. Google Cloud Setup

```bash
# Login to Google Cloud
gcloud auth login
gcloud auth application-default login

# Set project
export GCP_PROJECT_ID="your-project-id"
gcloud config set project $GCP_PROJECT_ID

# Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable run.googleapis.com
```

### 4. Create Cloud SQL Instance

```bash
# Create PostgreSQL instance with pgvector
gcloud sql instances create hansard-db \
    --database-version=POSTGRES_15 \
    --tier=db-custom-2-7680 \
    --region=us-central1 \
    --root-password="$(openssl rand -base64 32)" \
    --database-flags=cloudsql.iam_authentication=on

# Create database
gcloud sql databases create hansard --instance=hansard-db

# Get connection name
export INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe hansard-db \
    --format="value(connectionName)")

echo "Instance connection name: $INSTANCE_CONNECTION_NAME"
```

### 5. Initialize Database Schema

```bash
# Connect via Cloud SQL Proxy
cloud-sql-proxy $INSTANCE_CONNECTION_NAME &

# Run schema initialization
python scripts/init_database.py
```

**scripts/init_database.py**:
```python
import asyncio
import os
from langchain_google_cloud_sql_pg import PostgresEngine

async def init_schema():
    """Initialize database schema."""

    engine = await PostgresEngine.afrom_instance(
        project_id=os.environ["GCP_PROJECT_ID"],
        region="us-central1",
        instance="hansard-db",
        database="hansard"
    )

    # Enable pgvector extension
    await engine.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Create speeches table
    await engine.execute("""
        CREATE TABLE IF NOT EXISTS speeches (
            speech_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title TEXT NOT NULL,
            full_text TEXT NOT NULL,
            word_count INTEGER NOT NULL,
            content_hash TEXT NOT NULL UNIQUE,
            speaker TEXT NOT NULL,
            party TEXT NOT NULL,
            chamber TEXT NOT NULL CHECK (chamber IN ('House of Representatives', 'Senate')),
            electorate TEXT,
            state TEXT NOT NULL,
            date DATE NOT NULL,
            hansard_reference TEXT NOT NULL,
            topic_tags TEXT[] NOT NULL DEFAULT '{}',
            source_url TEXT,
            ingestion_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)

    # Create speech_chunks table
    await engine.execute("""
        CREATE TABLE IF NOT EXISTS speech_chunks (
            chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            speech_id UUID NOT NULL REFERENCES speeches(speech_id) ON DELETE CASCADE,
            chunk_text TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_size INTEGER NOT NULL,
            embedding vector(768) NOT NULL,
            speaker TEXT NOT NULL,
            party TEXT NOT NULL,
            chamber TEXT NOT NULL,
            date DATE NOT NULL,
            topic_tags TEXT[] NOT NULL DEFAULT '{}',
            langchain_metadata JSONB,
            UNIQUE(speech_id, chunk_index)
        );
    """)

    # Create HNSW index
    await engine.execute("""
        CREATE INDEX IF NOT EXISTS speech_chunks_embedding_hnsw
        ON speech_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 24, ef_construction = 100);
    """)

    # Create metadata indexes
    await engine.execute("CREATE INDEX IF NOT EXISTS idx_speeches_speaker ON speeches(speaker);")
    await engine.execute("CREATE INDEX IF NOT EXISTS idx_speeches_party ON speeches(party);")
    await engine.execute("CREATE INDEX IF NOT EXISTS idx_speeches_date ON speeches(date DESC);")
    await engine.execute("CREATE INDEX IF NOT EXISTS idx_chunks_speech_id ON speech_chunks(speech_id);")

    print("✓ Database schema initialized")
    await engine.close()

if __name__ == "__main__":
    asyncio.run(init_schema())
```

### 6. Create FastMCP Server

**src/server.py**:
```python
from fastmcp import FastMCP, Context
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_cloud_sql_pg import PostgresEngine, PostgresVectorStore
from typing import Optional, List
import os

# Initialize FastMCP
mcp = FastMCP("Australian Hansard RAG")

# Global resources
_engine: Optional[PostgresEngine] = None
_vector_store: Optional[PostgresVectorStore] = None
_embeddings_query: Optional[VertexAIEmbeddings] = None
_embeddings_doc: Optional[VertexAIEmbeddings] = None

@mcp.lifespan()
async def lifespan():
    """Initialize LangChain resources on startup."""
    global _engine, _vector_store, _embeddings_query, _embeddings_doc

    # Initialize embeddings
    _embeddings_query = VertexAIEmbeddings(
        model_name="gemini-embedding-001",
        project=os.environ["GCP_PROJECT_ID"],
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=768
    )

    _embeddings_doc = VertexAIEmbeddings(
        model_name="gemini-embedding-001",
        project=os.environ["GCP_PROJECT_ID"],
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=768
    )

    # Initialize database engine
    _engine = await PostgresEngine.afrom_instance(
        project_id=os.environ["GCP_PROJECT_ID"],
        region="us-central1",
        instance="hansard-db",
        database="hansard"
    )

    # Initialize vector store
    _vector_store = await PostgresVectorStore.create(
        engine=_engine,
        table_name="speech_chunks",
        embedding_service=_embeddings_query
    )

    print("✓ FastMCP server ready")
    yield

    # Cleanup
    if _engine:
        await _engine.close()

@mcp.tool(tags=["search", "rag", "stable"], readOnlyHint=True)
async def search_speeches(
    query: str,
    limit: int = 10,
    ctx: Context = None
) -> List[dict]:
    """Search Australian Hansard speeches."""

    await ctx.info(f"Searching for: {query}")

    results = await _vector_store.asimilarity_search_with_score(
        query=query,
        k=limit
    )

    return [
        {
            "speech_id": doc.metadata.get("speech_id"),
            "excerpt": doc.page_content[:500],
            "speaker": doc.metadata.get("speaker"),
            "relevance_score": float(score)
        }
        for doc, score in results
    ]

if __name__ == "__main__":
    mcp.run()
```

### 7. Run Server Locally

```bash
# Set environment variables
export GCP_PROJECT_ID="your-project-id"
export INSTANCE_CONNECTION_NAME="your-project:us-central1:hansard-db"

# Run server (stdio mode for MCP Inspector)
python src/server.py

# Or run in HTTP mode
python src/server.py --transport http --port 8080
```

### 8. Test with MCP Inspector

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Run inspector
mcp-inspector python src/server.py
```

**Open**: http://localhost:5173

**Test search_speeches**:
```json
{
  "query": "climate change policy",
  "limit": 5
}
```

---

## Ingest Sample Data

**scripts/ingest_sample.py**:
```python
import asyncio
import csv
from langchain_google_cloud_sql_pg import PostgresEngine
from langchain_google_vertexai import VertexAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os

async def ingest_csv(csv_path: str):
    """Ingest speeches from CSV file."""

    # Initialize resources
    engine = await PostgresEngine.afrom_instance(
        project_id=os.environ["GCP_PROJECT_ID"],
        region="us-central1",
        instance="hansard-db",
        database="hansard"
    )

    embeddings = VertexAIEmbeddings(
        model_name="gemini-embedding-001",
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=768
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )

    # Read CSV
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Insert speech
            speech_id = await engine.fetchval(
                """
                INSERT INTO speeches (
                    title, full_text, word_count, content_hash,
                    speaker, party, chamber, state, date, hansard_reference
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING speech_id
                """,
                row['title'],
                row['full_text'],
                len(row['full_text'].split()),
                hashlib.sha256(row['full_text'].encode()).hexdigest(),
                row['speaker'],
                row['party'],
                row['chamber'],
                row['state'],
                row['date'],
                row['hansard_reference']
            )

            # Chunk and embed
            chunks = splitter.split_text(row['full_text'])
            embeddings_list = await embeddings.aembed_documents(chunks)

            # Insert chunks
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings_list)):
                await engine.execute(
                    """
                    INSERT INTO speech_chunks (
                        speech_id, chunk_text, chunk_index, chunk_size, embedding,
                        speaker, party, chamber, date
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    speech_id, chunk, idx, len(chunk), embedding,
                    row['speaker'], row['party'], row['chamber'], row['date']
                )

            print(f"✓ Ingested: {row['title']}")

    await engine.close()
    print(f"✓ Ingestion complete")

if __name__ == "__main__":
    asyncio.run(ingest_csv("data/sample_speeches.csv"))
```

**Run ingestion**:
```bash
python scripts/ingest_sample.py
```

---

## Testing

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

**tests/test_search.py**:
```python
import pytest
from fastmcp.testing import test_mcp
from src.server import mcp

@pytest.mark.asyncio
async def test_search_speeches():
    """Test search_speeches tool."""

    async with test_mcp(mcp) as client:
        result = await client.call_tool(
            "search_speeches",
            {"query": "climate change", "limit": 5}
        )

        assert len(result) <= 5
        assert all("relevance_score" in r for r in result)
```

---

## Next Steps

1. **Add more tools**: Implement `get_speech`, `ingest_speech`, `list_speakers`
2. **Add tests**: Achieve >80% test coverage per constitution
3. **Deploy to Cloud Run**: Follow constitution deployment guidelines
4. **Configure MCP clients**: Add to Claude Desktop, Cursor, etc.

---

## Troubleshooting

### Cloud SQL Connection Issues

```bash
# Check Cloud SQL Proxy is running
ps aux | grep cloud-sql-proxy

# Restart proxy
killall cloud-sql-proxy
cloud-sql-proxy $INSTANCE_CONNECTION_NAME &
```

### Vertex AI Permission Errors

```bash
# Grant Vertex AI User role
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
    --member="user:your-email@example.com" \
    --role="roles/aiplatform.user"
```

### pgvector Extension Not Found

```sql
-- Connect to database and enable extension
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## CI/CD & GitHub Setup

### Configure GitHub Secrets

For CI/CD deployment to Cloud Run, configure GitHub secrets following the template:

**See**: [.github/secrets-template.md](/.github/secrets-template.md)

**Required Secrets**:
- `GCP_PROJECT_ID` - Your Google Cloud Project ID
- `GCP_SERVICE_ACCOUNT_KEY` - Service account JSON key (base64-encoded)
- `GCP_REGION` - Deployment region (e.g., `us-central1`)
- `CLOUDSQL_INSTANCE` - Cloud SQL instance name (e.g., `hansard-db`)

**Quick Setup**:
```bash
# Set project ID
gh secret set GCP_PROJECT_ID --body "your-project-id"

# Create service account and set key
# (See .github/secrets-template.md for full instructions)

# Set region and instance
gh secret set GCP_REGION --body "us-central1"
gh secret set CLOUDSQL_INSTANCE --body "hansard-db"

# Verify
gh secret list
```

### Deploy to Cloud Run

**Automatic Deployment** (via GitHub Actions):
- Push to `main` branch triggers deployment
- Workflow: `.github/workflows/deploy.yml` (to be created in Phase 6)

**Manual Deployment**:
```bash
# Build container
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/hansard-mcp-server

# Deploy to Cloud Run
gcloud run deploy hansard-mcp-server \
    --image gcr.io/$GCP_PROJECT_ID/hansard-mcp-server \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars GCP_PROJECT_ID=$GCP_PROJECT_ID \
    --add-cloudsql-instances $INSTANCE_CONNECTION_NAME
```

---

## Resources

- **Repository**: https://github.com/sc0sk/skai-fastmcp-cloudrun
- **FastMCP Docs**: https://github.com/jlowin/fastmcp
- **LangChain Google**: https://python.langchain.com/docs/integrations/providers/google
- **Vertex AI Embeddings**: https://cloud.google.com/vertex-ai/docs/generative-ai/embeddings
- **Cloud SQL pgvector**: https://cloud.google.com/sql/docs/postgres/extensions

---

**Quickstart Version**: 1.0
**Last Updated**: 2025-10-21
