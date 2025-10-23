# Technical Research: Search and Fetch MCP Tools

**Feature**: 004-search-fetch-mcp-tools | **Date**: 2025-10-23 | **Status**: Implementation Complete

## Overview

This document captures the technical decisions made during implementation of the search and fetch MCP tools for Australian Hansard parliamentary speeches. The implementation provides semantic vector search with metadata filtering and full speech retrieval capabilities.

## Decision 1: LangChain PostgresVectorStore for Vector Search

**Chosen**: LangChain PostgresVectorStore with default schema (`langchain_pg_embedding` table)

**Rationale**:
- **Native integration**: Seamless compatibility with Vertex AI Embeddings and Cloud SQL PostgreSQL
- **Auto-handled embeddings**: LangChain automatically generates and stores embeddings during document ingestion
- **Built-in metadata filtering**: PostgresVectorStore supports JSONB metadata filters out of the box via `filter` parameter
- **Standard schema**: Uses LangChain's default column names (`langchain_id`, `content`, `embedding`, `langchain_metadata`)
- **HNSW indexing**: Supports pgvector's HNSW index for fast approximate nearest neighbor search
- **Google ADK alignment**: LangChain is the recommended framework in the project constitution (v2.6.0)

**Alternatives Considered**:
- **Direct pgvector queries**: Would provide more control but requires manual embedding generation, storage logic, and metadata filter construction. Adds complexity without significant benefit for MVP.
- **Qdrant Cloud**: External managed vector database. Rejected due to additional service cost, network latency, and complexity of cross-service metadata synchronization.

**Implementation Details**:
- Table created via `engine.ainit_vectorstore_table(table_name="speech_chunks", vector_size=768)`
- Embeddings generated automatically during `vector_store.aadd_texts()`
- Similarity search uses cosine similarity by default (`<=>` operator in pgvector)
- Metadata stored in JSONB column for flexible filtering

**Reference**: `/home/user/skai-fastmcp-cloudrun/src/storage/vector_store.py` (lines 74-122)

---

## Decision 2: Dual-Table Architecture

**Chosen**: Two-table schema with `speeches` (metadata + full text) and `speech_chunks` (vectors + denormalized metadata)

**Rationale**:
- **speeches table**: Stores complete speech text and all 29 metadata fields. Optimized for fast retrieval by `speech_id` (primary key). Avoids redundant full_text storage in every chunk.
- **speech_chunks table** (LangChain's `langchain_pg_embedding`): Stores chunk text, embeddings (768-dim vectors), and denormalized metadata in JSONB. Optimized for vector similarity search with HNSW index.
- **Separation of concerns**: Vector search operations use `speech_chunks`, full text retrieval uses `speeches`. Clean separation improves query performance.
- **Efficient storage**: Full speech text stored once in `speeches`, not duplicated across chunks.
- **Fast lookups**: Both tables indexed on `speech_id` for efficient joins during result enrichment.

**Alternatives Considered**:
- **Single table**: Store everything in vector table. Rejected because full_text would be duplicated in every chunk (wasteful storage) and vector search would be slower due to larger row size.
- **Three tables** (speeches, chunks, embeddings): Over-engineering for MVP. Adds complexity of managing chunk metadata separately from embeddings.

**Implementation Details**:
- `speeches` table: UUID primary key, all 29 metadata fields, `full_text` column
- `speech_chunks` table: UUID chunk_id, foreign key to `speeches.speech_id`, embedding vector(768), JSONB metadata
- Cascade delete: Deleting speech removes all chunks (`ON DELETE CASCADE`)
- Indexing: HNSW on embeddings, B-tree on speech_id, speaker, date

**Reference**: `/home/user/skai-fastmcp-cloudrun/init_hansard_db_v2.sql` (lines 19-64)

---

## Decision 3: Vertex AI text-embedding-005 (768 dimensions)

**Chosen**: Vertex AI Embeddings with `text-embedding-005` model, 768-dimensional output

**Rationale**:
- **Google ADK alignment**: Constitution v2.6.0 mandates Google Cloud services for AI/ML workloads
- **Managed service**: No model hosting, scaling, or maintenance required. Vertex AI handles infrastructure.
- **Optimal dimensions**: 768 dimensions provides strong semantic understanding without excessive storage or compute overhead (compared to 1536-dim models).
- **Task-specific configuration**: Model supports `task_type` parameter for retrieval optimization (e.g., `RETRIEVAL_DOCUMENT`, `RETRIEVAL_QUERY`)
- **Native integration**: LangChain's `langchain-google-vertexai` package provides first-class support

**Alternatives Considered**:
- **sentence-transformers local**: Open-source models (e.g., `all-MiniLM-L6-v2`). Rejected due to self-hosting complexity, GPU requirements, and maintenance burden.
- **OpenAI embeddings**: `text-embedding-3-large` (1536 dims). Rejected due to external dependency outside Google Cloud, higher cost per query, and constitution violation.
- **Gemini embeddings**: Considered but `text-embedding-005` is optimized specifically for retrieval tasks.

**Implementation Details**:
- Model: `text-embedding-005`
- Output dimensionality: 768
- Task type: `RETRIEVAL_DOCUMENT` for chunks during ingestion, `RETRIEVAL_QUERY` for search queries
- Wrapper: `LangChainEmbeddingsWrapper` in `src/storage/embeddings.py` handles async embedding generation

**Reference**: `/home/user/skai-fastmcp-cloudrun/src/storage/vector_store.py` (lines 56-63)

---

## Decision 4: JSONB Metadata Filtering

**Chosen**: Store all 29 frontmatter fields in `langchain_metadata` JSONB column with PostgreSQL native operators

**Rationale**:
- **Flexible schema**: Add new metadata fields without database migrations. JSONB supports arbitrary JSON structures.
- **LangChain compatibility**: PostgresVectorStore's `filter` parameter directly maps to JSONB queries
- **Native PostgreSQL operators**: Use `->>`, `@>`, `->`, and comparison operators for complex filters
- **Index support**: PostgreSQL supports GIN indexes on JSONB for fast filtering (added in Phase 3)
- **Type flexibility**: JSONB handles strings, numbers, arrays, dates without schema changes

**Alternatives Considered**:
- **Normalized tables**: Create separate columns for each metadata field (speaker, party, chamber, etc.). Rejected because:
  - Requires 29+ columns in vector table (complex schema)
  - Rigid schema changes require migrations
  - Joins become complex for multi-field filters
- **Separate metadata service**: External key-value store (e.g., Firestore). Rejected due to added latency, synchronization complexity, and increased operational overhead.

**Implementation Details**:
- Metadata stored as JSONB in `langchain_metadata` column
- LangChain automatically serializes dict metadata during `aadd_texts()`
- Filter syntax: `{"party": "Liberal", "chamber": "House of Representatives"}`
- Date filtering: Custom filter keys `date_from` and `date_to` mapped to PostgreSQL date comparisons
- All 29 metadata fields accessible: speaker, party, chamber, electorate, state, date, hansard_reference, title, topic_tags, etc.

**Reference**: `/home/user/skai-fastmcp-cloudrun/src/tools/search.py` (lines 73-90)

---

## Decision 5: ValueError for User-Facing Errors

**Chosen**: Raise `ValueError` with descriptive messages for invalid user inputs (malformed speech_id, invalid dates, etc.)

**Rationale**:
- **MCP client compatibility**: FastMCP and MCP clients handle `ValueError` gracefully, converting to user-friendly error responses
- **Clear error messages**: Error text directly displayed to users (e.g., "Speech not found: {speech_id}")
- **Separation of concerns**: Internal errors (DB connection failures, embedding service errors) logged separately via Python logging, not raised as ValueError
- **Standard Python convention**: ValueError is idiomatic for invalid input arguments

**Alternatives Considered**:
- **ToolError exceptions**: FastMCP 2.14.0+ introduces `ToolError` class with structured error handling. Not used because:
  - Requires FastMCP 2.14.0+ (project currently on 2.12.5+)
  - ValueError already provides sufficient functionality for MVP
  - Migration to ToolError deferred to Phase 4
- **Custom exception classes**: Define `SpeechNotFoundError`, `InvalidDateError`, etc. Rejected as over-engineering for MVP. Standard ValueError sufficient.
- **HTTP status codes**: Return 404/400 status codes. Rejected because MCP tools operate at RPC level, not HTTP level.

**Implementation Details**:
- Fetch tool: Raises `ValueError(f"Speech not found: {speech_id}")` when speech_id doesn't exist
- Search tool: Pydantic validation raises ValueError for invalid date patterns (regex `^\d{4}-\d{2}-\d{2}$`)
- Internal errors: Logged via `logging.error()` and re-raised as generic exceptions for MCP framework to handle

**Reference**: `/home/user/skai-fastmcp-cloudrun/src/tools/fetch.py` (lines 40-43)

---

## Decision 6: Speech Reconstruction from Chunks

**Chosen**: Enrich search results with full speech metadata from `speeches` table, not just chunk metadata

**Rationale**:
- **Complete context**: Users need full speech metadata (title, word_count, hansard_reference) not available in chunk records
- **Minimal latency**: Single query per unique speech_id (multiple chunks from same speech deduplicated)
- **Result quality**: Provides actionable information for users to decide which speeches to fetch
- **Hybrid approach**: Vector search finds relevant chunks, metadata store enriches with full speech details

**Alternatives Considered**:
- **Return only chunk data**: Simpler implementation but poor UX. Users can't see speech titles or determine speech boundaries.
- **Denormalize all fields**: Store all 29 fields in chunk metadata. Rejected due to data redundancy (10+ chunks per speech) and stale data risk.
- **Join query**: Single SQL query joining `speech_chunks` and `speeches`. Rejected because LangChain PostgresVectorStore doesn't support custom joins.

**Implementation Details**:
- Search tool returns chunk_id, excerpt (first 500 chars), relevance_score, chunk_index
- For each unique speech_id, query `metadata_store.get_speech()` to retrieve full metadata
- Enriched results include: title, word_count, hansard_reference, speaker, party, chamber, state, date
- Deduplication: Multiple chunks from same speech only fetch metadata once

**Reference**: `/home/user/skai-fastmcp-cloudrun/src/tools/search.py` (lines 93-116)

---

## Decision 7: HNSW Indexing for Vector Search

**Chosen**: pgvector HNSW index with `m=24`, `ef_construction=100`

**Rationale**:
- **Performance**: HNSW (Hierarchical Navigable Small World) provides O(log n) approximate nearest neighbor search
- **Accuracy vs. speed**: Parameters balanced for 95%+ recall with <500ms search time for 10,000+ speeches
- **pgvector native**: HNSW is built into pgvector extension (no external dependencies)
- **Tunable parameters**: `m` controls graph connectivity, `ef_construction` controls build-time accuracy
- **Proven at scale**: HNSW used in production by Spotify, Microsoft, and other large-scale vector search applications

**Alternatives Considered**:
- **IVFFlat index**: Flat inverted file index. Faster to build but lower accuracy and slower search (O(n) within cells).
- **No index**: Sequential scan. Rejected due to poor performance at scale (O(n) for every query).
- **DiskANN**: Disk-based approximate nearest neighbor. Not supported by pgvector 0.8.0.

**Implementation Details**:
- Index type: HNSW with cosine similarity operator (`vector_cosine_ops`)
- Parameters: `m=24` (moderate connectivity), `ef_construction=100` (high accuracy during build)
- Query-time tuning: `SET hnsw.ef_search = 200;` for higher accuracy (if needed)
- Storage: Index stored on-disk, loaded into memory on first query

**Reference**: `/home/user/skai-fastmcp-cloudrun/init_hansard_db_v2.sql` (lines 52-56)

---

## Decision 8: Client-Side Date Filtering

**Chosen**: Custom filter keys (`date_from`, `date_to`) handled by tool logic, not LangChain

**Rationale**:
- **LangChain limitation**: PostgresVectorStore's `filter` parameter only supports exact equality matches on JSONB fields
- **Range queries**: Date filtering requires `>=` and `<=` comparisons, not supported by LangChain's default filtering
- **Client-side workaround**: Retrieve larger result set, filter dates in Python, then limit to requested count
- **Performance acceptable**: For MVP dataset (64 speeches, 628 chunks), client-side filtering adds <100ms overhead

**Alternatives Considered**:
- **Custom SQL query**: Bypass LangChain, write raw SQL with date range filters. Rejected because:
  - Loses LangChain's embedding generation and vector search logic
  - Requires manual vector similarity calculation (complex SQL)
  - Harder to maintain and test
- **Extend LangChain**: Fork LangChain to add range query support. Rejected due to maintenance burden and upstream merge complexity.
- **Database views**: Create PostgreSQL views with date filters. Rejected because views don't help with dynamic date ranges.

**Implementation Details**:
- Search tool receives `start_date` and `end_date` as ISO 8601 strings (e.g., "2024-05-28")
- Filter exact matches (party, chamber) passed to LangChain's `filter` parameter
- Date range filtering: Fetch results, filter `metadata["date"]` in Python, then return top `k` results
- Future improvement (Phase 4): Implement hybrid search with direct SQL for date filtering

**Reference**: `/home/user/skai-fastmcp-cloudrun/src/tools/search.py` (lines 73-90)

---

## Decision 9: Async-First Implementation

**Chosen**: All tool functions and storage methods use `async`/`await` pattern

**Rationale**:
- **FastMCP requirement**: MCP tools must be async for non-blocking I/O operations
- **Database I/O**: All PostgreSQL queries use `asyncpg` (async driver) to avoid blocking event loop
- **Embedding generation**: Vertex AI Embeddings API called asynchronously via `langchain-google-vertexai`
- **Concurrent requests**: Async enables handling 10+ concurrent search requests without thread pool overhead
- **Production ready**: Cloud Run expects async ASGI application (Starlette/FastAPI)

**Alternatives Considered**:
- **Synchronous with thread pool**: Run sync code in thread pool via `asyncio.to_thread()`. Rejected due to:
  - Overhead of thread creation/teardown
  - Limited to `os.cpu_count()` concurrent operations
  - Poor performance under load
- **Sync-only**: FastMCP requires async tools (not an option)

**Implementation Details**:
- All tools: `async def search_hansard_speeches(...)`, `async def fetch_hansard_speech(...)`
- All storage methods: `async def similarity_search(...)`, `async def get_speech(...)`
- Database connection: `asyncpg.connect()` and `Connector.connect_async()`
- Embedding service: `await embeddings.aembed_documents()`

**Reference**: `/home/user/skai-fastmcp-cloudrun/src/tools/search.py` (line 18), `/home/user/skai-fastmcp-cloudrun/src/storage/vector_store.py` (lines 123-176)

---

## Decision 10: Pydantic v2 for Data Validation

**Chosen**: Pydantic v2 models for all input validation and data serialization

**Rationale**:
- **FastMCP integration**: FastMCP uses Pydantic for automatic input validation and JSON schema generation
- **Type safety**: Pydantic enforces types at runtime, catching errors before database operations
- **Rich validation**: Support for regex patterns (ISO 8601 dates), min/max constraints (limit 1-100), custom validators (chamber validation)
- **Performance**: Pydantic v2 rewritten in Rust, 5-10x faster than v1
- **Constitution compliance**: Project constitution v2.6.0 mandates Pydantic v2

**Alternatives Considered**:
- **Manual validation**: Check types with isinstance(), validate patterns with re.match(). Rejected due to error-prone repetitive code.
- **dataclasses**: Standard library, but lacks validation. Requires additional validation layer.
- **Marshmallow**: Alternative validation library. Rejected because FastMCP expects Pydantic models.

**Implementation Details**:
- SpeechMetadata model: 29 fields with validators for chamber, state, topic_tags
- Field constraints: `min_length`, `max_length`, `pattern` (ISO 8601 dates), `ge`/`le` (limit range)
- Computed fields: `word_count` and `content_hash` auto-calculated from full_text
- Enum types: `PartyEnum`, `ChamberEnum` as Literal types for MCP tool parameters

**Reference**: `/home/user/skai-fastmcp-cloudrun/src/models/speech.py` (lines 11-108), `/home/user/skai-fastmcp-cloudrun/src/models/enums.py`

---

## MCP Tool Contract Format

MCP tool contracts use JSON Schema format with the following structure:

```json
{
  "name": "tool_name",
  "description": "Tool description with 'Use this when...' guidance",
  "inputSchema": {
    "type": "object",
    "properties": {
      "param_name": {
        "type": "string",
        "description": "Parameter description",
        "pattern": "^regex$"
      }
    },
    "required": ["param_name"]
  }
}
```

**Response format** (not part of MCP spec, documented for client developers):

```json
{
  "speeches": [
    {
      "chunk_id": "uuid",
      "speech_id": "uuid",
      "excerpt": "text...",
      "relevance_score": 0.85,
      "chunk_index": 0,
      "speaker": "Name",
      "party": "Liberal",
      "chamber": "House of Representatives",
      "date": "2024-06-03",
      "title": "Speech title"
    }
  ],
  "total_count": 10,
  "query": "search query"
}
```

---

## Error Handling Strategies

**Strategy 1: Input Validation (Pydantic)**
- Type errors, pattern mismatches, range violations caught before tool execution
- FastMCP converts Pydantic validation errors to structured MCP error responses
- Example: Invalid date pattern "2024-13-45" raises ValidationError

**Strategy 2: Business Logic Errors (ValueError)**
- User-facing errors: speech_id not found, empty search results, invalid filter combinations
- Raised as ValueError with descriptive messages
- MCP clients display error message to user

**Strategy 3: Infrastructure Errors (Exceptions)**
- Database connection failures, embedding service timeouts, network errors
- Logged via Python logging module
- Re-raised as generic exceptions for FastMCP to handle (returns 500-level errors to client)

**Strategy 4: Graceful Degradation**
- Empty search results: Return `{"speeches": [], "total_count": 0}` (not an error)
- Missing optional metadata: Use None or empty list
- Partial failures: Log warning, continue processing

**Reference**: `/home/user/skai-fastmcp-cloudrun/src/tools/fetch.py` (lines 40-43), `/home/user/skai-fastmcp-cloudrun/src/models/speech.py` (lines 56-88)

---

## Performance Considerations

**Search Performance (<3s target)**:
1. Vector similarity search: <500ms (HNSW index)
2. Metadata enrichment: <100ms per unique speech (B-tree index on speech_id)
3. Embedding generation: <1s (Vertex AI Embeddings)
4. Network latency: <500ms (Cloud Run to Cloud SQL via private IP)

**Fetch Performance (<2s target)**:
1. Primary key lookup: <10ms (indexed)
2. Network latency: <500ms (Cloud Run to Cloud SQL)

**Optimization Techniques**:
- Connection pooling: Reuse database connections (Cloud SQL Connector)
- Embedding caching: LangChain stores embeddings, no re-computation
- HNSW index: O(log n) search instead of O(n) sequential scan
- Minimal data transfer: Return excerpts (500 chars) in search, full text only in fetch

---

## Future Improvements (Post-MVP)

1. **Hybrid search** (vector + keyword): Combine pgvector similarity with PostgreSQL full-text search (tsvector)
2. **Server-side date filtering**: Implement custom SQL query for date ranges (avoid client-side filtering)
3. **Caching layer**: Redis cache for frequently requested speeches (reduce database load)
4. **Pagination**: Support `offset` parameter for large result sets (>100 speeches)
5. **Batch fetch**: `fetch_hansard_speeches([speech_id1, speech_id2, ...])` for multiple speeches
6. **Reranking**: Use Vertex AI Ranking API to improve result relevance
7. **CallToolResult migration**: Upgrade to FastMCP 2.14.0+ structured result format

---

## References

- LangChain PostgresVectorStore: https://python.langchain.com/docs/integrations/vectorstores/google_cloud_sql_pg
- Vertex AI Embeddings: https://cloud.google.com/vertex-ai/docs/generative-ai/embeddings/get-text-embeddings
- pgvector HNSW: https://github.com/pgvector/pgvector#hnsw
- FastMCP Documentation: https://docs.fastmcp.com/
- Project Constitution: `/home/user/skai-fastmcp-cloudrun/.specify/memory/constitution.md`
