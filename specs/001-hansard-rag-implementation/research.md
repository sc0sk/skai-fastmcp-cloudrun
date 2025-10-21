# Australian Hansard RAG Technical Research

**Branch**: `001-hansard-rag-implementation`
**Date**: 2025-10-21
**Constitution Version**: v2.6.0 (Google ADK-aligned architecture)

---

## Executive Summary

This document consolidates technical research for implementing the Australian Hansard RAG MVP. All decisions align with the project constitution (v2.6.0) which mandates Google ADK-aligned architecture: LangChain + Vertex AI + Cloud SQL pgvector.

**Key Decisions**:
1. **Vector Database**: Cloud SQL PostgreSQL + pgvector v0.8.0 (HNSW indexing, 768-dim vectors)
2. **Embeddings**: Vertex AI gemini-embedding-001 (768 dimensions, task-specific)
3. **Framework**: LangChain async patterns (langchain-google-vertexai + langchain-google-cloud-sql-pg)
4. **Architecture**: Global resource initialization with FastMCP lifespan management

---

## 1. Cloud SQL PostgreSQL + pgvector Setup

### Decision
Use Cloud SQL PostgreSQL with pgvector v0.8.0, HNSW indexing, 768-dimensional vectors, on `db-custom-2-7680` instance (2 vCPU, 7.5 GB RAM).

### Rationale

**Google ADK Alignment** (Constitution Mandate):
- Single database for vectors, metadata, and full text (ACID transactions)
- Native LangChain integration via `langchain-google-cloud-sql-pg`
- Managed service with automated backups and high availability options
- Unified billing and IAM within Google Cloud ecosystem

**pgvector v0.8.0 Features**:
- HNSW index support for fast approximate nearest neighbor search
- Iterative scanning for better recall (`hnsw.iterative_scan`)
- Supports vectors up to 16,000 dimensions (768 dims well within range)
- Production-ready performance for 10k-100k document scale

**Instance Sizing for 10,000 Speeches**:
- 10,000 speeches × ~12,000 chars = 120M chars total
- Text chunking: 800 chars/chunk with 150 overlap ≈ 15,000-20,000 chunks
- Vector storage: 20,000 chunks × 768 dims × 4 bytes = ~61 MB
- HNSW index size: ~61 MB (approximately equal to vector data)
- Metadata + full text: ~150-200 MB
- **Total working set**: ~300-400 MB (fits comfortably in 7.5 GB RAM)

**Why db-custom-2-7680**:
- 2 vCPU: 500 MBps network throughput for Vertex AI API calls
- 7.5 GB RAM: Entire working set stays in memory (>99% cache hit ratio)
- Scalable to 50,000 speeches (~1.5 GB working set) before upgrade needed

### Cost Estimate (us-central1)

**Monthly Costs**:
- Compute (2 vCPU): $60.22/month
- Memory (7.5 GB): $38.33/month
- Storage (20 GB SSD): $3.40/month
- Backups (automated daily): ~$2-5/month
- **Total**: **~$104-108/month**

### HNSW Index Configuration

**Recommended Parameters**:
```sql
CREATE INDEX speech_chunks_embedding_hnsw ON speech_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (
    m = 24,                  -- Higher for 768-dim (default: 16)
    ef_construction = 100    -- Better recall (default: 64)
);
```

**Parameter Justification**:
- **m = 24**: Improves recall for high-dimensional data (+50% memory, +50% build time)
- **ef_construction = 100**: Better index quality (~2-3 min build for 20k vectors)
- **Query-time tuning**: `SET hnsw.ef_search = 40-80` (higher = better recall)

**Performance Expectations**:
- Index build: 2-5 minutes for 20,000 vectors
- Vector search: 50-150ms p95 (HNSW approximate search)
- Concurrent queries: 10-20 simultaneous before CPU saturation

### Connection Pattern (Cloud Run → Cloud SQL)

**Use Unix domain sockets** (automatic via Cloud SQL connector):
- Path: `/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME`
- Encryption: Automatic (no manual SSL configuration)
- Connection pooling: Built-in via Cloud SQL Auth Proxy

### Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|-------------|------|------|------------------|
| Qdrant Cloud | Faster searches (<50ms), specialized | External vendor, separate metadata DB, ~$72/month | NOT Google ADK aligned |
| AlloyDB | 4x faster analytics, 99.99% SLA | 2x cost (~$220/month), overkill for scale | Cost not justified for MVP |
| Vertex AI Vector Search | Billion-scale, <50ms latency | $200-400/month minimum, complex setup | Over-engineered for 10k-50k scale |

---

## 2. LangChain Google Integration

### Decision
Use `langchain-google-vertexai` (v2.0+) and `langchain-google-cloud-sql-pg` (v0.12+) with async patterns throughout.

### Rationale

**Google ADK Standard** (Constitution Mandate):
- Google's Agent Development Kit uses LangChain for production agents
- Battle-tested patterns proven at Google scale
- Native integrations maintained by Google Cloud team
- Future-proof: aligns with Google's agent ecosystem roadmap

**Async Patterns** (Constitution Requirement):
- Cloud Run concurrency optimization (10-80 concurrent requests/container)
- FastMCP Context features (progress reporting, client logging) require async
- Database efficiency: connection pooling works best with async (non-blocking)
- Vertex AI API: async allows parallel embedding generation

### Latest Versions (January 2025)

```bash
pip install langchain-google-vertexai>=2.0.0
pip install langchain-google-cloud-sql-pg>=0.12.0
pip install langchain-core>=0.3.0
```

**Note**: LangChain v0.2 docs will be deprecated October 2025 with v1.0 release. Current v0.3 APIs should remain compatible.

### Code Patterns

#### PostgresEngine Initialization

```python
from langchain_google_cloud_sql_pg import PostgresEngine

# Async initialization (recommended for Cloud Run)
engine = await PostgresEngine.afrom_instance(
    project_id=os.environ["GCP_PROJECT_ID"],
    region="us-central1",
    instance=os.environ["CLOUDSQL_INSTANCE"],
    database="hansard"
)

# Connection pooling automatically configured:
# - pool_size=5 (default)
# - max_overflow=10 (default)
# - pool_timeout=30s
# - pool_recycle=3600s (1 hour)
```

#### PostgresVectorStore Initialization

```python
from langchain_google_cloud_sql_pg import PostgresVectorStore
from langchain_google_vertexai import VertexAIEmbeddings

# Initialize embeddings
embeddings = VertexAIEmbeddings(
    model_name="gemini-embedding-001",
    task_type="RETRIEVAL_DOCUMENT",  # For ingestion
    output_dimensionality=768
)

# Initialize table schema (one-time setup)
await engine.ainit_vectorstore_table(
    table_name="speech_chunks",
    vector_size=768,
    metadata_columns=[
        "speaker TEXT",
        "party TEXT",
        "chamber TEXT",
        "date DATE",
        "speech_id UUID"
    ]
)

# Create vector store
vector_store = await PostgresVectorStore.create(
    engine=engine,
    table_name="speech_chunks",
    embedding_service=embeddings,
    metadata_columns=["speaker", "party", "chamber", "date", "speech_id"]
)
```

### Error Handling Best Practices

```python
from fastmcp import ToolError
from google.api_core import exceptions as google_exceptions
from sqlalchemy.exc import SQLAlchemyError

@mcp.tool
async def search_speeches(query: str, ctx: Context = None) -> List[dict]:
    """Search with comprehensive error handling."""

    try:
        results = await vector_store.asimilarity_search(query, k=10)

    except google_exceptions.ResourceExhausted as e:
        raise ToolError(
            "Vertex AI rate limit exceeded. Please try again in 60 seconds."
        ) from e

    except google_exceptions.PermissionDenied as e:
        raise ToolError(
            "Permission denied for Vertex AI API. Check service account has "
            "'Vertex AI User' role."
        ) from e

    except SQLAlchemyError as e:
        await ctx.error(f"Database error: {str(e)}")
        raise ToolError(
            "Database query failed. Please check Cloud SQL instance is running."
        ) from e
```

### Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|-------------|------|------|------------------|
| Direct pgvector integration | Fewer dependencies, simpler | Reinvent patterns, NOT Google ADK aligned | Constitution mandates Google ADK |
| Sync-only implementation | Simpler code, easier debugging | No progress reporting, poor Cloud Run concurrency | FastMCP Context requires async |
| LangChain v1.0 beta | Latest features, better types | Breaking changes expected, incomplete docs | Wait for stable v1.0 (Oct 2025) |

---

## 3. Vertex AI Embeddings in Production

### Decision
Use Vertex AI `gemini-embedding-001` with 768 dimensions, batch processing for ingestion, and robust error handling.

### Rationale

**State-of-the-Art Quality**:
- #1 on MTEB Multilingual leaderboard
- Excellent for political discourse and complex institutional language
- 768 dimensions (vs 384 for sentence-transformers alternatives)

**Google ADK Standard** (Constitution Mandate):
- Recommended by Google's Agent Development Kit
- Native Cloud integration (IAM, audit logs, quotas)
- Automatic scaling, no model hosting/management

**Cost Predictability**:
- $0.15/1M tokens (synchronous requests)
- $0.075/1M tokens (Batch API - 50% discount)
- Pricing per input token, NOT per dimension

### Rate Limits and Quotas

**Synchronous Requests**:
- Input: 1 text per request
- Token limit: First 2,048 tokens used (charges for full input)
- Practical limit: ~100 requests/second per project

**Batch API** (Recommended for Ingestion):
- Input: Up to 250 texts per request
- Batch job limit: Up to 200,000 requests per job
- Processing time: Most jobs complete within 24 hours
- Cost: **$0.075 per 1M tokens (50% discount)**

### Batch Embedding Patterns

#### Synchronous Batch (Real-time Ingestion)

```python
async def ingest_speeches_batch(texts: List[str], ctx: Context):
    """Ingest with progress reporting and rate limiting."""

    total = len(texts)
    batch_size = 10  # To avoid rate limits
    all_embeddings = []

    for i in range(0, total, batch_size):
        batch = texts[i:i+batch_size]
        await ctx.report_progress(i, total)

        # Generate embeddings
        batch_embeddings = await embeddings.aembed_documents(batch)
        all_embeddings.extend(batch_embeddings)

        # Rate limiting
        await asyncio.sleep(0.1)

    return all_embeddings
```

**Performance**: ~100 texts/second, $0.15 per 1M tokens

#### Batch API (Large-scale Ingestion)

```python
async def batch_embed_speeches(speeches: List[dict], ctx: Context):
    """Use Vertex AI Batch API for large-scale embedding."""

    # 1. Prepare JSONL file
    batch_id = str(uuid.uuid4())
    input_file = f"gs://{BUCKET}/batch-input/{batch_id}.jsonl"

    # 2. Submit batch job
    batch_job = aiplatform.BatchPredictionJob.create(
        job_display_name=f"hansard-embeddings-{batch_id}",
        model_name="publishers/google/models/gemini-embedding-001",
        input_path=input_file,
        output_path=f"gs://{BUCKET}/batch-output/{batch_id}/"
    )

    # 3. Poll for completion
    while not batch_job.has_ended:
        await asyncio.sleep(60)

    return batch_job.output_path
```

**Performance**: 10,000-100,000+ texts per job, $0.075 per 1M tokens (50% cheaper)

### Cost Optimization Strategies

1. **Batch API for Ingestion**: 50% cost reduction ($27 vs $54 for 10k corpus)
2. **Cache Query Embeddings**: Eliminate redundant API calls via Redis
3. **Truncate Long Texts**: Only first 2,048 tokens used, avoid charging for unused
4. **Pre-filter Duplicates**: Don't embed duplicate speeches (10-30% savings)

**Cost Example (10,000 speeches)**:
- 10,000 speeches × 12k chars × 0.25 tokens/char = 30M tokens
- Synchronous: $4.50
- Batch API: $2.25 (50% savings)
- With deduplication (20%): $1.80

### Task Types

```python
# Document embeddings (for ingestion)
embeddings_doc = VertexAIEmbeddings(
    model_name="gemini-embedding-001",
    task_type="RETRIEVAL_DOCUMENT",  # Optimized for documents
    output_dimensionality=768
)

# Query embeddings (for search)
embeddings_query = VertexAIEmbeddings(
    model_name="gemini-embedding-001",
    task_type="RETRIEVAL_QUERY",  # Optimized for queries
    output_dimensionality=768
)
```

### Why 768 Dimensions

**Balance**: Quality vs storage/compute efficiency
- **Expandable**: Can increase to 1536 or 3072 without cost increase
- **Performance**: pgvector HNSW handles 768-dim efficiently with m=24
- **Constitution Compliance**: Matches architecture specification (v2.6.0)

**Comparison**:
- sentence-transformers: 384 dims (lower quality)
- gemini-embedding-001: 768 dims (recommended start)
- gemini-embedding-001 max: 3072 dims (best quality, same cost)

### Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|-------------|------|------|------------------|
| sentence-transformers (local) | Free, 384-dim, offline | Lower quality, 512MB memory overhead | NOT Google ADK aligned |
| OpenAI text-embedding-3-large | Excellent quality, 3072-dim | External vendor, $0.13/1M tokens | Not 100% Google Cloud |
| textembedding-gecko@003 | Proven, 768-dim | Deprecated, lower MTEB scores | Use latest recommended model |

---

## 4. FastMCP + LangChain Integration

### Decision
Async-first architecture with global resource initialization via FastMCP lifespan management and connection pooling.

### Rationale

**Async-First** (Constitution Requirement):
- Cloud Run concurrency: Handle 10-80 concurrent requests per container
- FastMCP Context: Progress reporting and client logging require async
- I/O efficiency: Database and Vertex AI API calls are I/O-bound
- Cost savings: Higher concurrency → fewer containers → lower costs

**Global Resource Pattern** (Best Practice):
- Connection pool efficiency: Single pool shared across all requests
- Startup performance: Initialize once vs. per-request overhead
- Memory efficiency: One vector store instance vs. multiple copies
- Lifecycle management: FastMCP lifespan handles cleanup automatically

### Global Resources Pattern

```python
from fastmcp import FastMCP, Context
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_cloud_sql_pg import PostgresEngine, PostgresVectorStore

mcp = FastMCP("Australian Hansard RAG")

# Global resources
_engine: Optional[PostgresEngine] = None
_vector_store: Optional[PostgresVectorStore] = None
_embeddings: Optional[VertexAIEmbeddings] = None

@mcp.lifespan()
async def lifespan():
    """Initialize LangChain resources on startup, cleanup on shutdown."""
    global _engine, _vector_store, _embeddings

    # Startup: Initialize resources
    _embeddings = VertexAIEmbeddings(
        model_name="gemini-embedding-001",
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=768
    )

    _engine = await PostgresEngine.afrom_instance(
        project_id=os.environ["GCP_PROJECT_ID"],
        region="us-central1",
        instance=os.environ["CLOUDSQL_INSTANCE"],
        database="hansard",
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True
    )

    _vector_store = await PostgresVectorStore.create(
        engine=_engine,
        table_name="speech_chunks",
        embedding_service=_embeddings
    )

    print("✓ LangChain resources initialized")

    yield  # Server runs

    # Shutdown: Cleanup
    if _engine:
        await _engine.close()
    print("✓ Resources cleaned up")

# Tools access global resources
@mcp.tool
async def search_speeches(query: str, ctx: Context = None) -> list[dict]:
    """Search using global vector store."""
    results = await _vector_store.asimilarity_search(query, k=10)
    return [{"text": doc.page_content} for doc in results]
```

**Benefits**:
- Single initialization on server startup
- Connection pool shared across all requests
- Automatic cleanup on shutdown
- No per-request overhead

### Connection Pooling Configuration

```python
# Production configuration
engine = await PostgresEngine.afrom_instance(
    # ... connection details ...
    pool_size=5,           # Minimum connections
    max_overflow=10,       # Additional connections when needed
    pool_timeout=30,       # Seconds to wait for connection
    pool_recycle=3600,     # Recycle after 1 hour
    pool_pre_ping=True     # Verify before use
)
```

**Pool Size Calculation**:
```
pool_size = expected_concurrent_requests / containers
max_overflow = 2 × pool_size (for burst traffic)

Example for 20 concurrent requests, 4 containers:
pool_size = 20 / 4 = 5
max_overflow = 10
```

### Memory Management

```python
async def embed_in_batches(
    texts: List[str],
    batch_size: int = 10,
    ctx: Context = None
) -> List[List[float]]:
    """Memory-efficient batching."""

    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_embeddings = await _embeddings.aembed_documents(batch)
        all_embeddings.extend(batch_embeddings)

        await ctx.report_progress(i + len(batch), len(texts))
        await asyncio.sleep(0.01)  # Allow GC

    return all_embeddings
```

**Memory Limits**:
- Cloud Run (512 MB): batch_size=10
- Local development (2-4 GB): batch_size=50-100
- High-memory Cloud Run (1-2 GB): batch_size=25-50

### Alternatives Considered

| Alternative | Pros | Cons | Rejected Because |
|-------------|------|------|------------------|
| Per-request resources | Simpler code, no global state | Connection pool per request, high overhead | Violates performance constraints |
| Sync-only | Simpler code, standard patterns | No Cloud Run concurrency, no Context features | Constitution mandates async |
| Manual connection mgmt | Full control, fewer dependencies | Reinvent pooling/retry logic, NOT ADK aligned | LangChain provides battle-tested patterns |

---

## Summary: Key Technical Decisions

| Component | Decision | Rationale | Cost Impact |
|-----------|----------|-----------|-------------|
| **Vector Database** | Cloud SQL PostgreSQL + pgvector v0.8.0 | Google ADK aligned, single DB for all data | ~$108/month |
| **Instance** | db-custom-2-7680 (2 vCPU, 7.5 GB) | Fits 10k-50k speeches in RAM, >99% cache hit | Baseline cost |
| **HNSW Index** | m=24, ef_construction=100 | Optimized for 768-dim, better recall | 2-5 min build time |
| **Connection** | Unix domain socket (Cloud Run → Cloud SQL) | Automatic encryption, recommended for Cloud Run | Free |
| **Embeddings** | Vertex AI gemini-embedding-001 (768-dim) | State-of-the-art, Google ADK standard, native Cloud | $0.075-0.15 / 1M tokens |
| **Batch Processing** | Batch API for ingestion, sync for queries | 50% cost savings, handles rate limits | $2.25 vs $4.50 for 10k |
| **Framework** | LangChain (async-first) | Google ADK aligned, battle-tested, native async | No cost |
| **Architecture** | Global resources + lifespan management | Cloud Run concurrency, connection pooling, Context support | Cost savings (fewer containers) |
| **Text Chunking** | RecursiveCharacterTextSplitter (800, 150 overlap) | Preserves semantic boundaries, RAG best practice | No cost |

**Total Infrastructure**: ~$108-120/month for 10,000 speeches
**Initial Ingestion**: ~$2.25 one-time (Batch API for 10,000 speeches)
**Ongoing Queries**: ~$2/month (1,000 searches with embedding cache)

---

## Implementation Recommendations

1. **Constitution Compliance First**:
   - Use Google ADK stack (LangChain + Vertex AI + Cloud SQL pgvector)
   - Follow async patterns throughout
   - Implement lifespan resource management

2. **Development Workflow**:
   - Local: In-memory testing with smaller datasets
   - Staging: Cloud SQL + Vertex AI with reduced instance (db-custom-1-3840)
   - Production: Full configuration per this research

3. **Testing Strategy**:
   - MCP Inspector for interactive tool testing
   - pytest with `fastmcp.testing.test_mcp` for unit/integration tests
   - Test connection pooling under load
   - Validate HNSW index performance with golden dataset

4. **Monitoring**:
   - Track Vertex AI costs via Cloud Billing API
   - Monitor Cloud SQL connection pool saturation
   - Alert on >5% error rate for Vertex AI API calls
   - Dashboard for query latency p50/p95/p99

---

**Research Completed**: 2025-10-21
**Next Phase**: Data Model & Contracts (Phase 1)
