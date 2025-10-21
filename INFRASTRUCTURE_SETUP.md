# Infrastructure Setup Guide

**Status**: ✅ Cloud SQL Created | ⚠️ Schema Initialization Pending

## Completed Setup

### 1. Cloud SQL PostgreSQL Instance ✅

**Instance Details:**
- Name: `hansard-db`
- Version: PostgreSQL 15
- Region: us-central1
- Tier: db-custom-2-4096 (2 vCPU, 4GB RAM)
- Public IP: 34.30.112.76
- Connection: `skai-fastmcp-cloudrun:us-central1:hansard-db`
- Database: `hansard`

### 2. GCP Credentials ✅

- Application Default Credentials configured
- User: scott.coleman@aph.gov.au
- Project: skai-fastmcp-cloudrun
- Vertex AI access: Ready

### 3. Scripts Created ✅

- `scripts/setup-cloudsql.sh` - Cloud SQL instance creation
- `scripts/init_database.py` - Database schema initialization
- `scripts/ingest_hansard.py` - CLI ingestion tool

---

## Quick Setup (Recommended)

We've created an automated script to guide you through the remaining setup steps:

```bash
./scripts/complete-setup.sh
```

This script will:
1. ✅ Check if psql client is installed
2. ✅ Enable pgvector extension
3. ✅ Initialize database schema
4. ✅ Validate sample data
5. ✅ Run dry-run ingestion test
6. ✅ Optionally run full ingestion

**Estimated time**: 5-10 minutes

---

## Manual Steps (Alternative)

If you prefer to run each step manually, follow these instructions:

### Step 1: Install PostgreSQL Client

Choose one option:

**Option A: Install psql client**
```bash
# On Ubuntu/Debian
sudo apt-get install postgresql-client

# On macOS
brew install postgresql@15

# On Windows (WSL)
sudo apt-get install postgresql-client
```

**Option B: Install Cloud SQL Proxy**
```bash
# Download Cloud SQL Proxy
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy
sudo mv cloud-sql-proxy /usr/local/bin/
```

### Step 2: Enable pgvector Extension

**Using gcloud (requires psql):**
```bash
gcloud sql connect hansard-db --user=postgres --database=hansard
```

Then in the psql prompt:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
\dx vector
\q
```

**Using Cloud SQL Proxy:**
```bash
# Terminal 1: Start proxy
cloud-sql-proxy skai-fastmcp-cloudrun:us-central1:hansard-db

# Terminal 2: Connect with psql
psql -h 127.0.0.1 -U postgres -d hansard
```

Then execute:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Step 3: Initialize Database Schema

Once pgvector is enabled, run:

```bash
python scripts/init_database.py
```

This will create:
- `speeches` table (metadata storage)
- `speech_chunks` table (768-dim vector storage)
- HNSW index for similarity search
- All necessary indexes

### Step 4: Ingest Sample Data

```bash
# Dry run (validate only)
python scripts/ingest_hansard.py --directory data/sk-hansard --dry-run

# Full ingestion
python scripts/ingest_hansard.py --directory data/sk-hansard
```

Expected results:
- 65 speeches processed
- ~200 chunks created
- 768-dim embeddings generated with Vertex AI

### Step 5: Test MCP Server

```bash
# Start server
fastmcp dev src/server.py

# Access MCP Inspector at http://localhost:6274

# Test search tool
{
  "name": "search",
  "arguments": {
    "query": "climate change policy",
    "limit": 5
  }
}

# Test fetch tool
{
  "name": "fetch",
  "arguments": {
    "speech_id": "<uuid-from-search>"
  }
}
```

---

## Connection Methods

### Method 1: gcloud SQL Connect (Easiest)

```bash
gcloud sql connect hansard-db --user=postgres --database=hansard
```

- Automatically whitelists your IP
- Requires psql client
- Connection lasts 5 minutes

### Method 2: Cloud SQL Proxy (Recommended for Development)

```bash
# Start proxy
cloud-sql-proxy skai-fastmcp-cloudrun:us-central1:hansard-db

# In another terminal, connect
psql -h 127.0.0.1 -U postgres -d hansard
```

- Creates local Unix socket connection
- No IP whitelisting needed
- Better for scripts and applications

### Method 3: Direct Connection (Not Recommended)

Requires firewall rules and password setup.

---

## Database Schema

### speeches Table

```sql
CREATE TABLE speeches (
    speech_id UUID PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    full_text TEXT NOT NULL,
    speaker VARCHAR(200) NOT NULL,
    party VARCHAR(100) NOT NULL,
    chamber VARCHAR(50) NOT NULL,
    electorate VARCHAR(100),
    state VARCHAR(3),
    date DATE NOT NULL,
    hansard_reference VARCHAR(500) NOT NULL,
    word_count INTEGER,
    content_hash VARCHAR(64) UNIQUE NOT NULL,
    topic_tags TEXT[],
    source_url VARCHAR(1000),
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### speech_chunks Table

```sql
CREATE TABLE speech_chunks (
    chunk_id UUID PRIMARY KEY,
    speech_id UUID REFERENCES speeches(speech_id),
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_size INTEGER NOT NULL,
    embedding vector(768) NOT NULL,  -- pgvector
    speaker VARCHAR(200) NOT NULL,
    party VARCHAR(100) NOT NULL,
    chamber VARCHAR(50) NOT NULL,
    state VARCHAR(3),
    date DATE NOT NULL,
    hansard_reference VARCHAR(500) NOT NULL
);
```

### HNSW Index

```sql
CREATE INDEX idx_speech_chunks_embedding_hnsw
ON speech_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 24, ef_construction = 100);
```

---

## Troubleshooting

### Issue: "psql: command not found"

**Solution**: Install PostgreSQL client (see Step 1 above)

### Issue: "ERROR: extension 'vector' is not available"

**Solution**: pgvector is only available in PostgreSQL 12+. Our instance is PostgreSQL 15, so this should work. If not, check Cloud SQL flags.

### Issue: "Connection refused"

**Solution**:
1. Check if your IP is whitelisted: `gcloud sql instances describe hansard-db --format="value(ipConfiguration.authorizedNetworks)"`
2. Use gcloud sql connect instead (auto-whitelists)
3. Or use Cloud SQL Proxy

### Issue: "password authentication failed"

**Solution**: Use Cloud SQL's IAM authentication or set a password:
```bash
gcloud sql users set-password postgres --instance=hansard-db --password=YOUR_PASSWORD
```

---

## Cost Estimate

**Cloud SQL Instance** (`db-custom-2-4096`):
- ~$100-150/month
- 2 vCPUs, 4GB RAM
- 10GB SSD storage (expandable)
- Automated backups included

**Vertex AI Embeddings** (gemini-embedding-001):
- ~$2/month for 65 speeches (~200 chunks)
- $0.00025 per 1,000 characters
- One-time ingestion cost: ~$1.50

**Total Initial Cost**: ~$1.50 ingestion + ~$100-150/month

---

## Next Steps

1. ✅ Cloud SQL created
2. ⚠️ **Complete manual steps above**
3. ⏳ Test ingestion
4. ⏳ Test MCP tools
5. ⏳ Deploy to Cloud Run (optional)

**Estimated Time**: 15-30 minutes for manual setup
