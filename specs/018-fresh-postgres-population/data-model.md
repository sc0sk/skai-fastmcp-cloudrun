# Data Model: Fresh PostgreSQL Population

**Feature**: 017-fresh-postgres-population  
**Date**: 2025-10-26

## Entity Relationship Diagram

```
┌─────────────────────────────────┐
│  langchain_pg_collection        │
├─────────────────────────────────┤
│ PK: uuid (UUID)                 │
│    name (TEXT, UNIQUE)          │
│    cmetadata (JSONB)            │
└────────────────┬────────────────┘
                 │ 1
                 │
                 │ N
┌─────────────────────────────────┐
│  langchain_pg_embedding         │
├─────────────────────────────────┤
│ PK: id (TEXT)                   │
│ FK: collection_id (UUID) ─────┐ │
│    embedding (VECTOR 768)      │ │
│    document (TEXT)             │ │
│    cmetadata (JSONB)           │ │
└─────────────────────────────────┘

Index: HNSW on embedding column (vector_cosine_ops)
```

## Entity Details

### Collection Entity

**Table**: `langchain_pg_collection`  
**Purpose**: Group related embeddings (e.g., "hansard-speeches")  
**Lifecycle**: One collection per feature deployment

| Field | Type | Constraints | Purpose |
|-------|------|-------------|---------|
| uuid | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| name | TEXT | UNIQUE NOT NULL | Collection identifier ("hansard") |
| cmetadata | JSONB | NULL OK | Collection-level metadata (e.g., version, source) |

**Sample Data**:
```sql
INSERT INTO langchain_pg_collection (name, cmetadata)
VALUES ('hansard', '{"version": "1.0", "source": "data/hansard_converted", "created": "2025-10-26"}');
```

### Embedding Entity

**Table**: `langchain_pg_embedding`  
**Purpose**: Store speech chunks with vector embeddings and metadata  
**Cardinality**: 1 collection → N embeddings

| Field | Type | Constraints | Purpose |
|-------|------|-------------|---------|
| id | TEXT | PK | Unique chunk identifier (format: `{hansard_id}_{chunk_index}`) |
| collection_id | UUID | FK → langchain_pg_collection.uuid, NOT NULL | Reference to collection |
| embedding | VECTOR(768) | NOT NULL, HNSW index | 768-dimensional embedding from Vertex AI |
| document | TEXT | NOT NULL | Full text of speech chunk (500-1500 tokens) |
| cmetadata | JSONB | NOT NULL | Chunk metadata and speaker info |

**Metadata Structure** (cmetadata JSONB):
```json
{
  "speaker": "John Smith",
  "date": "2023-11-15",
  "hansard_id": "hansard_20231115_001",
  "speech_type": "contribution",
  "hansard_url": "https://hansard.example.com/...",
  "chunk_index": 0,
  "chunk_count": 5,
  "tokens": 1050
}
```

### Chunk ID Schema

**Format**: `{hansard_id}_{chunk_index}`  
**Example**: `hansard_20231115_001_0`, `hansard_20231115_001_1`  
**Purpose**: Stable, unique identifier that preserves source traceability

### Vector Embedding Specification

- **Dimension**: 768 (Vertex AI default)
- **Model**: text-embedding-004 (Vertex AI)
- **Distance Metric**: Cosine similarity (HNSW index uses vector_cosine_ops)
- **Normalization**: Vertex AI handles normalization
- **Query Speed**: <500ms for similarity search via HNSW index

## Data Flow

```
Markdown Files (data/hansard_converted/)
           ↓
    Parse + Extract Metadata (frontmatter)
           ↓
Split into Chunks (RecursiveCharacterTextSplitter)
           ↓
Generate Embeddings (Vertex AI embeddings)
           ↓
Insert into Database (langchain_pg_embedding)
           ↓
Index with HNSW
           ↓
Ready for Vector Search Queries
```

## Schema DDL

```sql
-- Create collection table
CREATE TABLE IF NOT EXISTS langchain_pg_collection (
    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    cmetadata JSONB
);

-- Create embedding table
CREATE TABLE IF NOT EXISTS langchain_pg_embedding (
    id TEXT PRIMARY KEY,
    collection_id UUID REFERENCES langchain_pg_collection(uuid) ON DELETE CASCADE,
    embedding VECTOR(768) NOT NULL,
    document TEXT NOT NULL,
    cmetadata JSONB NOT NULL
);

-- Create HNSW index for fast vector similarity search
CREATE INDEX IF NOT EXISTS idx_embedding_hnsw 
ON langchain_pg_embedding 
USING HNSW (embedding VECTOR (768) ops=vector_cosine_ops);

-- Create index on collection_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_embedding_collection_id 
ON langchain_pg_embedding (collection_id);

-- Create index on metadata fields for filtering
CREATE INDEX IF NOT EXISTS idx_embedding_metadata_speaker 
ON langchain_pg_embedding USING gin (cmetadata);
```

## Constraints & Validations

### Data Integrity

| Constraint | Rule | Enforcement |
|-----------|------|-------------|
| Unique chunks | id must be unique | PRIMARY KEY constraint |
| Valid collection | collection_id must exist | FOREIGN KEY constraint |
| Valid vectors | embedding dimension = 768 | CHECK constraint (app-level) |
| Complete metadata | cmetadata must have required fields | Application validation |
| Non-null text | document must not be empty | NOT NULL constraint |

### Performance Considerations

| Aspect | Target | Strategy |
|--------|--------|----------|
| Insert throughput | 50-100 chunks/sec | Batch inserts (batch_size=500) |
| Search latency | <500ms | HNSW index on embedding |
| Metadata filtering | <100ms | GIN index on cmetadata JSONB |
| Storage size | ~40GB for 100k chunks | 768-dim vectors: ~3KB each |

## Migration Path (if re-initializing)

1. Create new collection: `INSERT INTO langchain_pg_collection (name, cmetadata) VALUES (...)`
2. Drop old embeddings: `DELETE FROM langchain_pg_embedding WHERE collection_id = :old_id`
3. Load new embeddings: Run bulk_loader.py
4. Verify new data: Run verify_data.py
5. Update Cloud Run: Set VECTOR_BACKEND env var if needed

## Metadata Filtering Examples

### Query by Speaker
```sql
SELECT * FROM langchain_pg_embedding 
WHERE cmetadata->>'speaker' = 'John Smith'
ORDER BY (cmetadata->>'date')::date DESC;
```

### Query by Date Range
```sql
SELECT * FROM langchain_pg_embedding 
WHERE (cmetadata->>'date')::date BETWEEN '2023-01-01' AND '2023-12-31'
ORDER BY (cmetadata->>'date')::date DESC;
```

### Metadata Filtering for Vector Search
```sql
WITH query_embedding AS (
    SELECT :embedding_vector::vector AS vec
)
SELECT 
    id, document, cmetadata,
    1 - (embedding <=> (SELECT vec FROM query_embedding)) AS similarity
FROM langchain_pg_embedding 
WHERE cmetadata->>'speaker' = :speaker
ORDER BY similarity DESC
LIMIT 10;
```

## Statistics & Monitoring

### Expected Metrics

| Metric | Expected Value | Formula |
|--------|----------------|---------|
| Total collections | 1 | Fixed |
| Total embeddings | 50k-100k | Number of markdown files × avg chunks/file |
| Avg chunk size | 1000 tokens | Config parameter |
| Vector storage | ~3KB per embedding | 768 dimensions × 4 bytes |
| Total DB size | ~40GB | embeddings × 3KB + indexes |
| Search latency p95 | <500ms | Via HNSW index |

### Monitoring Queries

```sql
-- Count embeddings
SELECT COUNT(*) FROM langchain_pg_embedding;

-- Distribution by speaker
SELECT cmetadata->>'speaker' AS speaker, COUNT(*) 
FROM langchain_pg_embedding 
GROUP BY cmetadata->>'speaker' 
ORDER BY COUNT(*) DESC;

-- Date range coverage
SELECT 
    MIN((cmetadata->>'date')::date) AS earliest,
    MAX((cmetadata->>'date')::date) AS latest
FROM langchain_pg_embedding;

-- Check for missing metadata
SELECT COUNT(*) FROM langchain_pg_embedding 
WHERE cmetadata IS NULL 
   OR cmetadata->>'speaker' IS NULL 
   OR cmetadata->>'date' IS NULL;
```
