# Research: Admin Markdown Ingestion Technical Decisions

**Feature**: 012-admin-markdown-ingestion
**Date**: 2025-10-24
**Purpose**: Resolve technical unknowns and establish implementation patterns

## Executive Summary

This feature builds upon the existing FastMCP server architecture with OAuth 2.1 security, LangChain integration, and Vertex AI embeddings. Key technical decisions:

- **YAML Frontmatter Parsing**: Use `python-frontmatter` library (industry standard)
- **Admin Authorization**: Extend existing bearer token validation with role-based claims
- **Markdown Processing**: Use built-in Python markdown parsing with chunking strategy
- **Batch Operations**: Implement async batch processing with progress reporting
- **Error Handling**: Transaction-based rollback with detailed error tracking

## Research Areas

### 1. YAML Frontmatter Parsing

**Decision**: Use `python-frontmatter` library

**Rationale**:
- Industry-standard library for parsing markdown files with YAML frontmatter
- Simple API: `frontmatter.load(file)` returns metadata dict and content separately
- Handles malformed YAML gracefully with clear error messages
- Zero-dependency parsing (uses Python's built-in YAML parser)
- Well-maintained with 1.6K+ stars on GitHub

**Alternatives Considered**:
- **PyYAML + custom parser**: More complex, reinventing the wheel
- **markdown2 with metadata extension**: Less focused, requires additional configuration
- **Custom regex parsing**: Fragile, won't handle edge cases properly

**Implementation Pattern**:
```python
import frontmatter

def parse_markdown_file(file_path: str) -> tuple[dict, str]:
    """Parse markdown file with YAML frontmatter.

    Returns:
        (metadata_dict, content_text)

    Raises:
        ValueError: If frontmatter is malformed or missing required fields
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)

    # post.metadata is dict with frontmatter
    # post.content is markdown content as string
    return post.metadata, post.content
```

### 2. Admin Role-Based Authorization

**Decision**: Extend OAuth 2.1 bearer token with role claims, validate admin role before ingestion

**Rationale**:
- Existing OAuth 2.1 implementation already validates bearer tokens
- JWT tokens can carry role claims in payload (e.g., `{"role": "admin", "user": "..."}`)
- No additional authentication infrastructure needed
- Follows industry-standard RBAC (Role-Based Access Control) patterns
- Aligns with constitution requirement for secure authentication

**Alternatives Considered**:
- **Separate admin API keys**: Introduces additional credential management complexity
- **IP allowlisting**: Not secure, breaks cloud/mobile access patterns
- **Database-stored roles**: Requires additional DB queries per request

**Implementation Pattern**:
```python
from fastmcp import Context

async def validate_admin_access(ctx: Context) -> bool:
    """Validate that request has admin role.

    Raises:
        PermissionError: If token lacks admin role
    """
    # Existing auth middleware populates ctx.user with token claims
    user_role = ctx.user.get("role") if ctx.user else None

    if user_role != "admin":
        raise PermissionError(
            "Admin privileges required for ingestion operations. "
            f"Current role: {user_role or 'none'}"
        )

    return True
```

### 3. Markdown Content Chunking Strategy

**Decision**: Use semantic chunking with paragraph boundaries, 500-1000 character target

**Rationale**:
- Paragraph boundaries preserve semantic meaning better than fixed-size chunks
- 500-1000 chars aligns with Vertex AI text-embedding-005 optimal input size
- Existing LangChain `RecursiveCharacterTextSplitter` supports semantic splitting
- Constitution already uses similar chunking strategy (ingest tool implementation)
- Prevents mid-sentence splits that harm embedding quality

**Alternatives Considered**:
- **Fixed 512-character chunks**: Breaks sentences, lower embedding quality
- **Sentence-based chunking**: Too granular, increases embedding API calls
- **Section-based chunking (markdown headers)**: Too coarse for parliamentary speeches

**Implementation Pattern**:
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

def chunk_speech_text(text: str) -> list[str]:
    """Chunk speech text into semantic segments.

    Uses paragraph boundaries with 500-1000 char target.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,  # Preserve context across chunks
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]  # Paragraph > sentence > word
    )

    return splitter.split_text(text)
```

### 4. Bulk Ingestion with Progress Reporting

**Decision**: Async batch processing with FastMCP progress reporting every N files

**Rationale**:
- FastMCP 2.0+ supports `ctx.report_progress()` for long-running operations
- Async processing allows database/API calls without blocking
- Progress updates improve UX per constitution requirement (Principle VII)
- Batch database writes reduce connection overhead
- Individual file failures don't block batch (isolation)

**Alternatives Considered**:
- **Synchronous processing**: Slow, blocks other operations
- **Fire-and-forget background jobs**: No progress visibility, harder to debug
- **Celery/task queue**: Over-engineering for MVP, adds infrastructure dependency

**Implementation Pattern**:
```python
from fastmcp import Context

async def ingest_bulk(
    file_paths: list[str],
    ctx: Context
) -> dict:
    """Ingest multiple markdown files with progress reporting."""
    total = len(file_paths)
    successes = []
    failures = []

    for i, file_path in enumerate(file_paths):
        try:
            await ingest_single_file(file_path)
            successes.append(file_path)
        except Exception as e:
            failures.append({"file": file_path, "error": str(e)})

        # Report progress every file
        await ctx.report_progress(i + 1, total)

    return {
        "total": total,
        "succeeded": len(successes),
        "failed": len(failures),
        "failures": failures
    }
```

### 5. Transaction-Based Error Handling

**Decision**: Use PostgreSQL transactions with rollback on failure, no partial records

**Rationale**:
- PostgreSQL ACID guarantees ensure data consistency
- Single transaction per file: either all data inserted or nothing
- Prevents orphaned vector embeddings without metadata
- Aligns with FR-011 (graceful failure) and SC-006 (zero partial records)
- LangChain PostgresEngine supports transaction context managers

**Alternatives Considered**:
- **Manual cleanup on error**: Complex, error-prone, race conditions
- **Eventual consistency**: Not acceptable for speech metadata integrity
- **Optimistic writes with verification**: Adds latency, doesn't prevent partial writes

**Implementation Pattern**:
```python
async def ingest_single_file(file_path: str):
    """Ingest single file with transaction rollback on error."""
    async with get_db_connection() as conn:
        async with conn.transaction():  # Auto-rollback on exception
            # 1. Parse and validate
            metadata, content = parse_markdown_file(file_path)
            validate_metadata(metadata)

            # 2. Store metadata
            speech_id = await store_speech_metadata(conn, metadata, content)

            # 3. Chunk and embed
            chunks = chunk_speech_text(content)
            embeddings = await generate_embeddings_batch(chunks)

            # 4. Store vectors
            await store_vector_embeddings(conn, speech_id, chunks, embeddings)

            # Transaction commits here if no exceptions
            # Auto-rollback if any step raises
```

### 6. Duplicate Detection Strategy

**Decision**: Check speech_id uniqueness before insertion, configurable skip/update/error policy

**Rationale**:
- Speech ID is natural primary key from frontmatter
- Database unique constraint provides atomic duplicate detection
- Configurable policy allows different behaviors (dev vs prod)
- `ON CONFLICT` clause in PostgreSQL enables efficient upsert
- Prevents data loss from accidental re-ingestion

**Alternatives Considered**:
- **Content-based deduplication (hash)**: Slower, doesn't match speech_id semantics
- **Timestamp-based versioning**: Adds complexity, not required for MVP
- **No duplicate detection**: Data integrity risk, violates FR-013

**Implementation Pattern**:
```python
class DuplicatePolicy(str, Enum):
    SKIP = "skip"      # Silently skip duplicates
    UPDATE = "update"  # Update existing speech
    ERROR = "error"    # Raise error on duplicate

async def store_speech_metadata(
    conn,
    metadata: dict,
    content: str,
    duplicate_policy: DuplicatePolicy = DuplicatePolicy.SKIP
):
    """Store speech metadata with duplicate handling."""
    if duplicate_policy == DuplicatePolicy.SKIP:
        # INSERT ... ON CONFLICT DO NOTHING
        query = """
            INSERT INTO speeches (speech_id, speaker, party, ...)
            VALUES ($1, $2, $3, ...)
            ON CONFLICT (speech_id) DO NOTHING
            RETURNING speech_id
        """
    elif duplicate_policy == DuplicatePolicy.UPDATE:
        # INSERT ... ON CONFLICT DO UPDATE
        query = """
            INSERT INTO speeches (speech_id, ...)
            VALUES ($1, ...)
            ON CONFLICT (speech_id) DO UPDATE SET ...
            RETURNING speech_id
        """
    else:  # ERROR
        # Plain INSERT will fail with unique constraint error
        query = "INSERT INTO speeches (...) VALUES (...) RETURNING speech_id"

    return await conn.fetchval(query, ...)
```

### 7. File Path Validation

**Decision**: Whitelist-based path validation with resolved absolute paths

**Rationale**:
- Prevents directory traversal attacks (e.g., `../../etc/passwd`)
- `pathlib.Path.resolve()` canonicalizes paths and follows symlinks
- Check that resolved path is within allowed base directory
- Aligns with security requirements in spec

**Alternatives Considered**:
- **Regex-based filtering**: Fragile, easy to bypass
- **No validation**: Security vulnerability
- **Chroot jail**: Over-engineering, complex to implement

**Implementation Pattern**:
```python
from pathlib import Path

def validate_file_path(file_path: str, base_dir: str = "/data/hansard") -> Path:
    """Validate file path is within allowed directory.

    Raises:
        ValueError: If path escapes base directory
    """
    base = Path(base_dir).resolve()
    target = Path(file_path).resolve()

    # Check target is within base
    try:
        target.relative_to(base)
    except ValueError:
        raise ValueError(
            f"Path {file_path} is outside allowed directory {base_dir}"
        )

    if not target.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not target.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    return target
```

### 8. Vertex AI Embedding Batch Optimization

**Decision**: Batch embed multiple chunks in single API call (max 250 per batch)

**Rationale**:
- Vertex AI supports batch embedding up to 250 texts per request
- Reduces API latency by 10-50x vs sequential calls
- Lower cost (fewer requests)
- Existing LangChain integration supports batching via `embed_documents()`
- Aligns with performance considerations in spec

**Alternatives Considered**:
- **Sequential embedding**: Too slow for bulk ingestion
- **Larger batches**: API limit is 250 texts
- **Async concurrent requests**: More complex, not needed with batching

**Implementation Pattern**:
```python
from langchain_google_vertexai import VertexAIEmbeddings

async def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts efficiently.

    Uses batching to optimize API usage.
    """
    embeddings_model = VertexAIEmbeddings(
        model_name="text-embedding-005",
        project=os.getenv("GCP_PROJECT_ID"),
        location=os.getenv("GCP_REGION", "us-central1"),
    )

    # LangChain handles batching internally (250 per request)
    embeddings = await embeddings_model.aembed_documents(texts)

    return embeddings
```

## Dependencies Added

- **python-frontmatter** (^1.0.0): YAML frontmatter parsing
- **langchain-text-splitters** (already in project): Semantic text chunking

## Configuration Required

- **ADMIN_ROLE_CLAIM** (env var): Role claim name in JWT (default: "role")
- **ADMIN_ROLE_VALUE** (env var): Required role value (default: "admin")
- **INGESTION_BASE_DIR** (env var): Allowed base directory for file paths (default: "/data/hansard")
- **DUPLICATE_POLICY** (env var): How to handle duplicates - skip/update/error (default: "skip")
- **CHUNK_SIZE** (env var): Target chunk size in characters (default: 1000)
- **CHUNK_OVERLAP** (env var): Overlap between chunks (default: 100)
- **EMBEDDING_BATCH_SIZE** (env var): Texts per batch embedding call (default: 250, max: 250)

## Testing Strategy

### Unit Tests
- Frontmatter parsing (valid, malformed, missing fields)
- Metadata validation (all required fields, format validation)
- Text chunking (semantic boundaries, size limits)
- Path validation (directory traversal, symlinks)
- Duplicate detection (skip, update, error policies)

### Integration Tests
- Single file ingestion end-to-end
- Bulk ingestion with mixed success/failure
- Progress reporting accuracy
- Transaction rollback on database errors
- Admin authorization (valid token, invalid token, missing role)

### Contract Tests
- MCP tool schema validation
- Tool response format (success, error, progress)
- Bearer token validation integration

## Performance Projections

Based on research and existing similar implementations:

- **Single file ingestion**: ~3-5 seconds (1s parse + 1s embed + 1s DB)
- **Bulk ingestion**: ~6 files/minute (10s per file with batching, parallelization)
- **Embedding API latency**: ~200ms for 10 chunks (batched)
- **Database writes**: ~100ms for speech + chunks (transaction)
- **Progress reporting overhead**: <5ms per file

Target metrics from spec (SC-001, SC-002):
- ✅ Under 5 seconds per file (3-5s projected)
- ⚠️ 10 files/minute target vs 6 files/minute projected (optimization needed)

**Optimization opportunity**: Parallel processing of independent files can achieve 10+/min.

## Open Questions Resolved

1. **Q**: How to handle markdown files with no frontmatter?
   **A**: Return clear error, do not ingest (FR-003 validation requirement)

2. **Q**: What if Vertex AI is temporarily unavailable?
   **A**: Retry with exponential backoff (3 attempts), then fail gracefully with error message

3. **Q**: Should we support file encodings other than UTF-8?
   **A**: No for MVP (assumption in spec), add `encoding` parameter in future if needed

4. **Q**: How to handle concurrent ingestion requests?
   **A**: Database transaction isolation handles concurrency, rate limit at API layer if needed

5. **Q**: Should bulk ingestion be resumable if interrupted?
   **A**: No for MVP (adds state complexity), log failures for manual retry
