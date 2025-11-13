# Quickstart: Fresh PostgreSQL Database & Population

**Feature**: 017-fresh-postgres-population  
**Duration**: ~20-30 minutes (setup) + 1-2 hours (population)  
**Prerequisites**: 
- Cloud SQL instance `hansard-db-v2` running
- Access to gcloud CLI with project `skai-fastmcp-cloudrun`
- Markdown files in `data/hansard_converted/`

## Quick Setup (5 minutes)

### 1. Create Fresh Database & Schema

```bash
cd /home/user/skai-fastmcp-cloudrun

# Create database, enable pgvector, create schema
python setup_fresh_db_gcloud.py
```

**Expected output**:
```
📊 Setting up fresh hansard database...

1️⃣ Creating database hansard_db_fresh...
✅ Database created: hansard_db_fresh

2️⃣ Enabling pgvector extension...
✅ pgvector extension enabled

3️⃣ Creating langchain-postgres schema...
✅ Schema created: langchain_pg_collection, langchain_pg_embedding

4️⃣ Verifying schema...
✅ Tables: langchain_pg_collection, langchain_pg_embedding
✅ Extensions: pgvector, plpgsql

✨ Fresh database setup complete!
```

### 2. Populate Speeches with Embeddings

```bash
# Bulk load speeches from markdown files
# Splits into chunks, generates Vertex AI embeddings, stores with metadata
python populate_speeches.py \
  --markdown-dir data/hansard_converted/ \
  --collection-name hansard \
  --chunk-size 1000 \
  --chunk-overlap 100 \
  --batch-size 500 \
  --verbose
```

**Expected output**:
```
🚀 Starting bulk population...
📂 Found 523 markdown files in data/hansard_converted/
[████████████████████████████████████████] 100% | 523 files

📊 Chunk Statistics:
   Total chunks: 52,847
   Avg tokens/chunk: 1,050
   Avg chunks/file: 101

🔤 Generating embeddings with Vertex AI...
[████████████████████████████████████████] 100% | 52,847 chunks | 1,234 req/s

💾 Inserting into langchain_pg_embedding...
[████████████████████████████████████████] 100% | 52,847 rows | Batch 500

✅ Population complete:
   - Collection: hansard (uuid: a1b2c3d4-e5f6...)
   - Total embeddings: 52,847
   - Metadata: speaker, date, hansard_id, speech_type, url
   - Storage size: 38GB
   - Duration: 45 min 23 sec

🧪 Running smoke tests...
✅ Search query 1: "climate change" → 24 results in 287ms
✅ Search query 2: "Speaker John Smith" → 156 results in 142ms
✅ Metadata filter: "speaker='Jane Doe' AND date>='2023-01-01'" → 89 results in 98ms

✨ All tests passed!
```

## Detailed Steps

### Step 1: Verify Markdown Files

```bash
# Count markdown files
find data/hansard_converted/ -name "*.md" | wc -l

# Sample first file structure
head -30 data/hansard_converted/hansard_20231115_001.md
```

### Step 2: Check Cloud SQL Connection

```bash
# Test connection to Cloud SQL
gcloud sql connect hansard-db-v2 --user=postgres --database=hansard_db_fresh

# In psql prompt:
SELECT version();
SELECT extname FROM pg_extension;
\dt  -- show tables
\q   -- quit
```

### Step 3: Monitor Population Progress

```bash
# In separate terminal, monitor database growth
while true; do
  gcloud sql connect hansard-db-v2 --user=postgres --database=hansard_db_fresh << EOF
    SELECT 
      'Embeddings' AS table_name, 
      COUNT(*) AS rows,
      pg_size_pretty(pg_total_relation_size('langchain_pg_embedding')) AS size
    FROM langchain_pg_embedding;
EOF
  sleep 10
done
```

### Step 4: Verify Data Integrity

```bash
# Run verification script
python verify_data.py --database hansard_db_fresh

# Expected output:
# ✅ Schema verification
#    - langchain_pg_collection: 1 rows
#    - langchain_pg_embedding: 52,847 rows
# ✅ Metadata verification
#    - All required fields present: 52,847/52,847 (100%)
#    - Unique speakers: 342
#    - Date range: 2020-01-01 to 2023-12-31
# ✅ Vector verification
#    - Embedding dimension: 768 ✅
#    - NULL embeddings: 0 ✅
# ✅ Search performance
#    - HNSW index created: ✅
#    - Search latency p50: 142ms
#    - Search latency p95: 487ms
```

## Testing the Setup

### Run Smoke Tests

```bash
# Test 1: Simple search query
python -c "
from src.storage.vector_store import PGVectorStore
store = PGVectorStore(db='hansard_db_fresh')
results = store.similarity_search('climate policy', k=5)
for r in results:
    print(f'  - {r.metadata[\"speaker\"]}: {r.page_content[:80]}...')
"

# Test 2: Metadata filtering
python -c "
from src.storage.vector_store import PGVectorStore
store = PGVectorStore(db='hansard_db_fresh')
results = store.similarity_search(
    'education reform',
    k=5,
    filter={'speaker': 'John Smith'}
)
for r in results:
    print(f'  - {r.metadata[\"date\"]}: {r.page_content[:80]}...')
"

# Test 3: Verify embeddings
python -c "
from sqlalchemy import text
from src.storage.cloud_sql_engine import get_engine
engine = get_engine(database='hansard_db_fresh')
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT 
          COUNT(*) as total,
          COUNT(DISTINCT collection_id) as collections,
          COUNT(CASE WHEN embedding IS NULL THEN 1 END) as null_embeddings
        FROM langchain_pg_embedding
    '''))
    row = result.fetchone()
    print(f'Embeddings: {row[0]:,}')
    print(f'Collections: {row[1]}')
    print(f'NULL vectors: {row[2]}')
"
```

## Troubleshooting

### Issue: Connection refused
**Solution**: Ensure Cloud SQL Proxy is running or Cloud SQL Connector has IAM permissions
```bash
# Check IAM roles
gcloud projects get-iam-policy skai-fastmcp-cloudrun \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:*@skai-fastmcp-cloudrun.iam.gserviceaccount.com"
```

### Issue: Embeddings generation slow
**Solution**: Increase batch size or use parallel processing
```bash
# Reduce chunk size or increase batch size
python populate_speeches.py --batch-size 1000 --parallel-workers 4
```

### Issue: Running out of disk space
**Solution**: Monitor Cloud SQL storage
```bash
# Check instance size
gcloud sql instances describe hansard-db-v2 --format='value(settings.storageAutoResizeLimit)'

# Increase if needed
gcloud sql instances patch hansard-db-v2 --storage-size 100GB
```

## Next Steps

### After Population

1. **Verify in Production**:
   ```bash
   # Query from Cloud Run service
   curl -X POST https://hansard-mcp-xxx.a.run.app/search \
     -H "Content-Type: application/json" \
     -d '{"query": "climate policy", "k": 5}'
   ```

2. **Update Cloud Run Service**:
   ```bash
   gcloud run services update hansard-mcp \
     --set-env-vars VECTOR_BACKEND=postgres,DATABASE_NAME=hansard_db_fresh
   ```

3. **Monitor & Alert**:
   - Set up Cloud Monitoring alerts for slow searches
   - Track embedding generation rate
   - Monitor database size growth

4. **Backup Strategy**:
   ```bash
   # Export database
   gcloud sql export sql hansard-db-v2 gs://your-bucket/hansard_db_fresh_backup.sql
   ```

## Configuration Reference

| Parameter | Default | Options | Use Case |
|-----------|---------|---------|----------|
| chunk-size | 1000 | 500-2000 | Smaller = more granular search, Larger = context preservation |
| chunk-overlap | 100 | 50-200 | Prevents loss of context between chunks |
| batch-size | 500 | 100-1000 | Larger = faster insertion, but uses more memory |
| parallel-workers | 4 | 1-16 | More = faster embedding generation, but rate limit sensitive |

## Time Estimates

| Operation | Files | Duration |
|-----------|-------|----------|
| Database setup | N/A | <1 min |
| Markdown parsing | 500 | 2-3 min |
| Chunk splitting | 50k chunks | 5-10 min |
| Embedding generation | 50k chunks | 20-40 min (depends on Vertex AI quota) |
| Database insertion | 50k rows | 5-10 min |
| **Total** | 500 files | **40-60 min** |
