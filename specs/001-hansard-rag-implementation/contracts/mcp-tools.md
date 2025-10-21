# MCP Tools API Contracts

**Branch**: `001-hansard-rag-implementation`
**Date**: 2025-10-21
**Spec**: [../spec.md](../spec.md)
**Data Model**: [../data-model.md](../data-model.md)

---

## Overview

This document defines the FastMCP tool contracts for the Australian Hansard RAG server. All tools follow FastMCP conventions and return `CallToolResult` objects with structured data.

**FastMCP Version**: 2.14.0+
**Protocol**: Model Context Protocol (MCP)
**Server Name**: `australian-hansard-rag`

---

## Tool 1: `search_speeches`

### Description

Hybrid search combining semantic similarity with metadata filtering. Uses pgvector HNSW index for fast vector search + PostgreSQL metadata filtering.

**Primary Use Case**: Find speeches related to a topic/query with optional filters
**Tags**: `["search", "rag", "stable"]`
**Read-Only**: `true`

### Input Schema

```python
from typing import Optional, List
from datetime import date

class SearchSpeechesInput(BaseModel):
    """Input parameters for search_speeches tool."""

    query: str = Field(
        ...,
        description="Search query (natural language question or keywords)",
        min_length=1,
        max_length=1000,
        examples=["What is the government's climate change policy?"]
    )

    speaker: Optional[str] = Field(
        None,
        description="Filter by speaker name (exact match, case-insensitive)",
        max_length=200,
        examples=["Anthony Albanese", "Peter Dutton"]
    )

    party: Optional[str] = Field(
        None,
        description="Filter by political party (exact match, case-insensitive)",
        max_length=100,
        examples=["Labor", "Liberal", "Greens", "National"]
    )

    chamber: Optional[str] = Field(
        None,
        description="Filter by chamber",
        pattern="^(House of Representatives|Senate)$",
        examples=["House of Representatives", "Senate"]
    )

    date_from: Optional[date] = Field(
        None,
        description="Filter speeches from this date onwards (ISO 8601)",
        examples=["2024-01-01"]
    )

    date_to: Optional[date] = Field(
        None,
        description="Filter speeches up to this date (ISO 8601)",
        examples=["2024-12-31"]
    )

    topic_tags: Optional[List[str]] = Field(
        None,
        description="Filter by topic tags (ANY match)",
        max_items=10,
        examples=[["climate change", "environment"]]
    )

    limit: int = Field(
        10,
        description="Maximum number of results to return",
        ge=1,
        le=50
    )

    include_full_text: bool = Field(
        False,
        description="Include complete speech text in results (default: excerpt only)"
    )
```

### Output Schema

```python
from typing import List
from datetime import date

class SearchSpeechesResult(BaseModel):
    """Output from search_speeches tool."""

    results: List[SearchResult] = Field(
        ...,
        description="List of search results, ordered by relevance (descending)"
    )

    total_found: int = Field(
        ...,
        description="Total number of results found (may be > limit)"
    )

    query_embedding_time_ms: float = Field(
        ...,
        description="Time taken to generate query embedding (milliseconds)"
    )

    search_time_ms: float = Field(
        ...,
        description="Time taken for vector search (milliseconds)"
    )

class SearchResult(BaseModel):
    """Individual search result."""

    speech_id: str = Field(..., description="UUID of parent speech")
    chunk_id: str = Field(..., description="UUID of matching chunk")
    excerpt: str = Field(..., description="Matching text excerpt (~800 chars)")
    full_text: Optional[str] = Field(None, description="Complete speech (if requested)")

    # Metadata
    speaker: str
    party: str
    chamber: str
    date: date
    title: str
    hansard_reference: str
    topic_tags: List[str]

    # Search metrics
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity (0-1)")
    chunk_index: int = Field(..., ge=0, description="Position in speech")
```

### Example Usage

```python
# Claude Desktop MCP client
@mcp.tool(tags=["search", "rag", "stable"], readOnlyHint=True)
async def search_speeches(
    query: str,
    speaker: Optional[str] = None,
    party: Optional[str] = None,
    chamber: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    topic_tags: Optional[List[str]] = None,
    limit: int = 10,
    include_full_text: bool = False,
    ctx: Context = None
) -> List[dict]:
    """Search Australian Hansard speeches with semantic similarity + metadata filters."""

    # Progress reporting
    await ctx.info(f"Searching for: {query}")
    await ctx.report_progress(0, 3)

    # Generate query embedding (Vertex AI text-embedding-004)
    start_time = time.time()
    embedding = await query_embeddings.aembed_query(query)
    embedding_time_ms = (time.time() - start_time) * 1000

    await ctx.report_progress(1, 3)

    # Build metadata filter
    filters = {}
    if speaker:
        filters["speaker"] = speaker.lower()
    if party:
        filters["party"] = party
    if chamber:
        filters["chamber"] = chamber
    if topic_tags:
        filters["topic_tags"] = {"$in": topic_tags}

    # Date range filter
    if date_from or date_to:
        date_filter = {}
        if date_from:
            date_filter["$gte"] = date_from
        if date_to:
            date_filter["$lte"] = date_to
        filters["date"] = date_filter

    # Vector search with metadata filtering
    start_time = time.time()
    results = await vector_store.asimilarity_search_with_score(
        query=query,
        k=limit,
        filter=filters if filters else None
    )
    search_time_ms = (time.time() - start_time) * 1000

    await ctx.report_progress(2, 3)

    # Enrich with full text if requested
    enriched_results = []
    for doc, score in results:
        result = {
            "speech_id": doc.metadata["speech_id"],
            "chunk_id": doc.metadata["chunk_id"],
            "excerpt": doc.page_content[:800],
            "speaker": doc.metadata["speaker"],
            "party": doc.metadata["party"],
            "chamber": doc.metadata["chamber"],
            "date": doc.metadata["date"],
            "title": doc.metadata.get("title", ""),
            "hansard_reference": doc.metadata["hansard_reference"],
            "topic_tags": doc.metadata.get("topic_tags", []),
            "relevance_score": float(score),
            "chunk_index": doc.metadata["chunk_index"]
        }

        if include_full_text:
            # Fetch full speech text from speeches table
            full_text_result = await engine.fetch(
                "SELECT full_text FROM speeches WHERE speech_id = $1",
                doc.metadata["speech_id"]
            )
            result["full_text"] = full_text_result[0]["full_text"] if full_text_result else None

        enriched_results.append(result)

    await ctx.report_progress(3, 3)
    await ctx.info(f"Found {len(enriched_results)} results")

    return {
        "results": enriched_results,
        "total_found": len(results),
        "query_embedding_time_ms": embedding_time_ms,
        "search_time_ms": search_time_ms
    }
```

### Performance Requirements

- **Latency**: <200ms p95 (uncached query)
- **Throughput**: 10-50 concurrent queries
- **Cache Hit Rate**: >60% for common queries (via Redis)

---

## Tool 2: `get_speech`

### Description

Retrieve complete speech by ID with all metadata and optional context.

**Primary Use Case**: Get full speech text after finding it via search
**Tags**: `["retrieve", "rag", "stable"]`
**Read-Only**: `true`

### Input Schema

```python
class GetSpeechInput(BaseModel):
    """Input parameters for get_speech tool."""

    speech_id: str = Field(
        ...,
        description="UUID of the speech to retrieve",
        pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )

    include_chunks: bool = Field(
        False,
        description="Include individual chunks with embeddings (default: full text only)"
    )

    include_context: bool = Field(
        False,
        description="Include surrounding speeches (before/after chronologically)"
    )
```

### Output Schema

```python
class GetSpeechResult(BaseModel):
    """Output from get_speech tool."""

    # Speech data
    speech_id: str
    title: str
    full_text: str
    word_count: int

    # Speaker information
    speaker: str
    party: str
    chamber: str
    electorate: Optional[str]
    state: str

    # Parliamentary context
    date: date
    hansard_reference: str
    topic_tags: List[str]

    # Source
    source_url: Optional[str]
    ingestion_timestamp: str  # ISO 8601

    # Optional: Chunks
    chunks: Optional[List[ChunkDetail]] = Field(
        None,
        description="Individual chunks (if requested)"
    )

    # Optional: Context
    context: Optional[SpeechContext] = Field(
        None,
        description="Surrounding speeches (if requested)"
    )

class ChunkDetail(BaseModel):
    """Individual chunk detail."""
    chunk_id: str
    chunk_index: int
    chunk_text: str
    chunk_size: int

class SpeechContext(BaseModel):
    """Chronological context."""
    previous_speech: Optional[SpeechSummary] = None
    next_speech: Optional[SpeechSummary] = None

class SpeechSummary(BaseModel):
    """Brief speech summary for context."""
    speech_id: str
    title: str
    speaker: str
    date: date
```

### Example Usage

```python
@mcp.tool(tags=["retrieve", "rag", "stable"], readOnlyHint=True)
async def get_speech(
    speech_id: str,
    include_chunks: bool = False,
    include_context: bool = False,
    ctx: Context = None
) -> dict:
    """Retrieve complete speech by ID."""

    await ctx.info(f"Retrieving speech: {speech_id}")

    # Fetch from speeches table
    result = await engine.fetch(
        """
        SELECT
            speech_id, title, full_text, word_count,
            speaker, party, chamber, electorate, state,
            date, hansard_reference, topic_tags,
            source_url, ingestion_timestamp
        FROM speeches
        WHERE speech_id = $1
        """,
        speech_id
    )

    if not result:
        raise ToolError(f"Speech not found: {speech_id}")

    speech = result[0]

    response = {
        "speech_id": str(speech["speech_id"]),
        "title": speech["title"],
        "full_text": speech["full_text"],
        "word_count": speech["word_count"],
        "speaker": speech["speaker"],
        "party": speech["party"],
        "chamber": speech["chamber"],
        "electorate": speech["electorate"],
        "state": speech["state"],
        "date": speech["date"].isoformat(),
        "hansard_reference": speech["hansard_reference"],
        "topic_tags": speech["topic_tags"],
        "source_url": speech["source_url"],
        "ingestion_timestamp": speech["ingestion_timestamp"].isoformat()
    }

    # Optional: Include chunks
    if include_chunks:
        chunks_result = await engine.fetch(
            """
            SELECT chunk_id, chunk_index, chunk_text, chunk_size
            FROM speech_chunks
            WHERE speech_id = $1
            ORDER BY chunk_index
            """,
            speech_id
        )
        response["chunks"] = [
            {
                "chunk_id": str(c["chunk_id"]),
                "chunk_index": c["chunk_index"],
                "chunk_text": c["chunk_text"],
                "chunk_size": c["chunk_size"]
            }
            for c in chunks_result
        ]

    # Optional: Include context
    if include_context:
        # Fetch previous speech (chronologically)
        prev_result = await engine.fetch(
            """
            SELECT speech_id, title, speaker, date
            FROM speeches
            WHERE date < $1 AND chamber = $2
            ORDER BY date DESC
            LIMIT 1
            """,
            speech["date"],
            speech["chamber"]
        )

        # Fetch next speech
        next_result = await engine.fetch(
            """
            SELECT speech_id, title, speaker, date
            FROM speeches
            WHERE date > $1 AND chamber = $2
            ORDER BY date ASC
            LIMIT 1
            """,
            speech["date"],
            speech["chamber"]
        )

        response["context"] = {
            "previous_speech": {
                "speech_id": str(prev_result[0]["speech_id"]),
                "title": prev_result[0]["title"],
                "speaker": prev_result[0]["speaker"],
                "date": prev_result[0]["date"].isoformat()
            } if prev_result else None,
            "next_speech": {
                "speech_id": str(next_result[0]["speech_id"]),
                "title": next_result[0]["title"],
                "speaker": next_result[0]["speaker"],
                "date": next_result[0]["date"].isoformat()
            } if next_result else None
        }

    await ctx.info("Speech retrieved successfully")
    return response
```

### Performance Requirements

- **Latency**: <50ms p95 (single database query)
- **Throughput**: 50-100 concurrent requests

---

## Tool 3: `ingest_speech`

### Description

Ingest a single speech: validate metadata, chunk text, generate embeddings, store in database.

**Primary Use Case**: Add new speeches to the RAG system
**Tags**: `["ingest", "write", "stable"]`
**Read-Only**: `false`

### Input Schema

```python
class IngestSpeechInput(BaseModel):
    """Input parameters for ingest_speech tool."""

    # Use SpeechMetadata from data-model.md
    # All fields from SpeechMetadata (title, full_text, speaker, party, etc.)

    title: str = Field(..., min_length=1, max_length=500)
    full_text: str = Field(..., min_length=10)
    speaker: str = Field(..., min_length=1, max_length=200)
    party: str = Field(..., min_length=1, max_length=100)
    chamber: str = Field(..., pattern="^(House of Representatives|Senate)$")
    electorate: Optional[str] = Field(None, max_length=100)
    state: str = Field(..., pattern="^(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)$")
    date: date = Field(...)
    hansard_reference: str = Field(..., min_length=1, max_length=500)
    topic_tags: List[str] = Field(default_factory=list, max_items=20)
    source_url: Optional[str] = Field(None, max_length=1000)

    skip_if_duplicate: bool = Field(
        True,
        description="Skip ingestion if speech already exists (based on content hash)"
    )
```

### Output Schema

```python
class IngestSpeechResult(BaseModel):
    """Output from ingest_speech tool."""

    speech_id: str = Field(..., description="UUID of ingested speech")
    status: str = Field(..., description="'created' or 'skipped' (if duplicate)")

    # Ingestion metrics
    chunks_created: int = Field(..., description="Number of chunks generated")
    embeddings_generated: int = Field(..., description="Number of embeddings created")
    total_time_ms: float = Field(..., description="Total ingestion time (milliseconds)")
    embedding_time_ms: float = Field(..., description="Time for embedding generation")

    # Content metrics
    word_count: int
    content_hash: str = Field(..., description="SHA-256 hash for deduplication")
```

### Example Usage

```python
@mcp.tool(tags=["ingest", "write", "stable"])
async def ingest_speech(
    title: str,
    full_text: str,
    speaker: str,
    party: str,
    chamber: str,
    state: str,
    date: str,  # ISO 8601
    hansard_reference: str,
    electorate: Optional[str] = None,
    topic_tags: Optional[List[str]] = None,
    source_url: Optional[str] = None,
    skip_if_duplicate: bool = True,
    ctx: Context = None
) -> dict:
    """Ingest a single speech into the RAG system."""

    start_time = time.time()
    await ctx.info(f"Ingesting speech: {title}")
    await ctx.report_progress(0, 5)

    # Validate with Pydantic
    try:
        speech_data = SpeechMetadata(
            title=title,
            full_text=full_text,
            speaker=speaker,
            party=party,
            chamber=chamber,
            electorate=electorate,
            state=state,
            date=date,
            hansard_reference=hansard_reference,
            topic_tags=topic_tags or [],
            source_url=source_url
        )
    except ValidationError as e:
        raise ToolError(f"Validation failed: {e}")

    await ctx.report_progress(1, 5)

    # Check for duplicate
    if skip_if_duplicate:
        exists = await engine.fetchval(
            "SELECT EXISTS(SELECT 1 FROM speeches WHERE content_hash = $1)",
            speech_data.content_hash
        )
        if exists:
            await ctx.info("Speech already exists (duplicate), skipping")
            return {
                "speech_id": None,
                "status": "skipped",
                "chunks_created": 0,
                "embeddings_generated": 0,
                "total_time_ms": (time.time() - start_time) * 1000,
                "embedding_time_ms": 0,
                "word_count": speech_data.word_count,
                "content_hash": speech_data.content_hash
            }

    # Insert into speeches table
    result = await engine.fetchval(
        """
        INSERT INTO speeches (
            title, full_text, word_count, content_hash,
            speaker, party, chamber, electorate, state,
            date, hansard_reference, topic_tags, source_url
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        RETURNING speech_id
        """,
        speech_data.title,
        speech_data.full_text,
        speech_data.word_count,
        speech_data.content_hash,
        speech_data.speaker,
        speech_data.party,
        speech_data.chamber,
        speech_data.electorate,
        speech_data.state,
        speech_data.date,
        speech_data.hansard_reference,
        speech_data.topic_tags,
        speech_data.source_url
    )
    speech_id = str(result)

    await ctx.report_progress(2, 5)
    await ctx.info(f"Created speech: {speech_id}")

    # Chunk text
    chunks = splitter.split_text(speech_data.full_text)
    await ctx.info(f"Generated {len(chunks)} chunks")

    await ctx.report_progress(3, 5)

    # Generate embeddings
    embedding_start = time.time()
    embeddings = await document_embeddings.aembed_documents(chunks)
    embedding_time_ms = (time.time() - embedding_start) * 1000

    await ctx.report_progress(4, 5)
    await ctx.info(f"Generated {len(embeddings)} embeddings")

    # Insert chunks
    for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        await engine.execute(
            """
            INSERT INTO speech_chunks (
                speech_id, chunk_text, chunk_index, chunk_size, embedding,
                speaker, party, chamber, date, topic_tags
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            speech_id,
            chunk_text,
            idx,
            len(chunk_text),
            embedding,
            speech_data.speaker,
            speech_data.party,
            speech_data.chamber,
            speech_data.date,
            speech_data.topic_tags
        )

    await ctx.report_progress(5, 5)
    total_time_ms = (time.time() - start_time) * 1000
    await ctx.info(f"Ingestion complete in {total_time_ms:.0f}ms")

    return {
        "speech_id": speech_id,
        "status": "created",
        "chunks_created": len(chunks),
        "embeddings_generated": len(embeddings),
        "total_time_ms": total_time_ms,
        "embedding_time_ms": embedding_time_ms,
        "word_count": speech_data.word_count,
        "content_hash": speech_data.content_hash
    }
```

### Performance Requirements

- **Latency**: <2s for typical speech (~12,000 chars, ~15 chunks)
- **Throughput**: 1-5 speeches/second (batch ingestion via separate tool)

---

## Tool 4: `list_speakers` (Optional - Metadata Query)

### Description

List all speakers with speech counts and metadata.

**Primary Use Case**: Discover available speakers for filtering
**Tags**: `["metadata", "stable"]`
**Read-Only**: `true`

### Input Schema

```python
class ListSpeakersInput(BaseModel):
    """Input parameters for list_speakers tool."""

    chamber: Optional[str] = Field(
        None,
        description="Filter by chamber",
        pattern="^(House of Representatives|Senate)$"
    )

    party: Optional[str] = Field(
        None,
        description="Filter by party"
    )

    min_speeches: int = Field(
        1,
        description="Minimum number of speeches (default: 1)",
        ge=1
    )

    limit: int = Field(
        100,
        description="Maximum number of speakers to return",
        ge=1,
        le=500
    )
```

### Output Schema

```python
class ListSpeakersResult(BaseModel):
    """Output from list_speakers tool."""

    speakers: List[SpeakerSummary]
    total_speakers: int

class SpeakerSummary(BaseModel):
    """Summary of a speaker's speeches."""

    speaker: str
    party: str
    chamber: str
    state: str
    electorate: Optional[str]

    speech_count: int
    first_speech_date: date
    last_speech_date: date
    total_words: int
    top_topics: List[str] = Field(..., description="Most common topic tags")
```

### Example Query

```sql
SELECT
    speaker,
    party,
    chamber,
    state,
    MAX(electorate) as electorate,
    COUNT(*) as speech_count,
    MIN(date) as first_speech_date,
    MAX(date) as last_speech_date,
    SUM(word_count) as total_words,
    (SELECT ARRAY_AGG(DISTINCT unnest) FROM unnest(ARRAY_AGG(topic_tags)) LIMIT 5) as top_topics
FROM speeches
WHERE chamber = $1 OR $1 IS NULL
  AND party = $2 OR $2 IS NULL
GROUP BY speaker, party, chamber, state
HAVING COUNT(*) >= $3
ORDER BY speech_count DESC
LIMIT $4
```

---

## Error Handling

All tools must handle errors consistently:

```python
from fastmcp import ToolError

# Validation errors
raise ToolError("Invalid input: {specific_error}")

# Not found
raise ToolError(f"Speech not found: {speech_id}")

# Vertex AI rate limits
raise ToolError("Rate limit exceeded. Please try again in 60 seconds.")

# Database errors
raise ToolError("Database error. Please check Cloud SQL instance is running.")

# Duplicate detection
# (Not an error - return status: "skipped")
```

---

## Summary

| Tool | Purpose | Read-Only | Performance Target |
|------|---------|-----------|-------------------|
| `search_speeches` | Semantic search + filters | Yes | <200ms p95 |
| `get_speech` | Retrieve by ID | Yes | <50ms p95 |
| `ingest_speech` | Add single speech | No | <2s per speech |
| `list_speakers` | Metadata discovery | Yes | <100ms p95 |

**Total Tools**: 4 (3 core + 1 optional)
**Protocol**: Model Context Protocol (MCP)
**Framework**: FastMCP 2.14.0+

---

**Contracts Version**: 1.0
**Next**: See [../quickstart.md](../quickstart.md) for local development setup
