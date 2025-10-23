# Implementation Tasks: Debug Logging

**Feature**: 007-debug-logging
**Status**: Ready for Implementation
**Created**: 2025-10-23

## Task Dependency Graph

```
TASK-001 (debug utilities)
    ├─> TASK-004 (search tool)
    ├─> TASK-005 (fetch tool)
    ├─> TASK-006 (ingest tool)
    └─> TASK-002 (utility tests)

TASK-004, TASK-005, TASK-006
    ├─> TASK-007 (VectorStoreService)
    ├─> TASK-008 (MetadataStore)
    └─> TASK-003 (integration tests)

TASK-002, TASK-003
    └─> TASK-009 (performance benchmarks)

TASK-009
    └─> TASK-010 (MCP Inspector testing)

TASK-010
    ├─> TASK-011 (quickstart.md)
    └─> TASK-012 (requirements checklist)
```

---

## TASK-001: Create debug utilities module

**Priority**: P0 (blocking)
**Estimated Time**: 45 minutes
**Assignee**: TBD
**Status**: Pending

### Description
Create `src/utils/debug.py` module with utilities for formatting debug messages, sanitizing sensitive data, and timing operations.

### Implementation Details

**File**: `src/utils/debug.py`

**Deliverables**:
1. `SENSITIVE_PATTERNS: List[str]` - Field name patterns to redact
2. `format_debug_message(context: str, description: str, **kwargs) -> str` - Format consistent debug messages
3. `sanitize_debug_data(data: dict) -> dict` - Redact sensitive fields and truncate long values
4. `TimingContext` - Async context manager for automatic timing

**Code Structure**:
```python
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import time

SENSITIVE_PATTERNS = [
    "password", "passwd", "pwd",
    "token", "auth_token", "access_token", "refresh_token",
    "api_key", "apikey", "secret", "secret_key",
    "private_key", "credential", "credentials",
    "authorization", "bearer"
]

def format_debug_message(context: str, description: str, **kwargs) -> str:
    """Format debug message with consistent structure."""
    # Implementation

def sanitize_debug_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive fields and truncate long values."""
    # Implementation

class TimingContext:
    """Async context manager for timing operations."""
    # Implementation
```

### Acceptance Criteria
- [ ] `format_debug_message("search", "Starting", query="test")` returns `"search: Starting (query=test)"`
- [ ] `sanitize_debug_data({"password": "secret"})` returns `{"password": "***REDACTED***"}`
- [ ] Long values (>1KB) truncated with "...truncated" suffix
- [ ] TimingContext measures duration accurately (±5ms tolerance)
- [ ] TimingContext works with ctx=None (no error)
- [ ] Module passes linting (ruff/black)

### Testing
- Unit tests in TASK-002

### Dependencies
- None (foundational task)

### Files Modified
- `src/utils/debug.py` (create new)

---

## TASK-002: Write debug utility unit tests

**Priority**: P1
**Estimated Time**: 30 minutes
**Assignee**: TBD
**Status**: Pending

### Description
Write comprehensive unit tests for debug utility functions to ensure correct formatting, sanitization, and timing.

### Implementation Details

**File**: `tests/unit/test_debug_utils.py`

**Test Cases**:
1. `test_format_debug_message_basic` - Basic formatting with kwargs
2. `test_format_debug_message_empty_kwargs` - No kwargs provided
3. `test_format_debug_message_long_value` - Value >1KB truncated
4. `test_sanitize_debug_data_password` - Password field redacted
5. `test_sanitize_debug_data_api_key` - API key field redacted
6. `test_sanitize_debug_data_token` - Token fields redacted
7. `test_sanitize_debug_data_safe_fields` - Non-sensitive fields preserved
8. `test_sanitize_debug_data_nested` - Nested dicts handled
9. `test_timing_context_measures_duration` - Timing accurate
10. `test_timing_context_with_none_ctx` - No error with None
11. `test_timing_context_with_exception` - Timing logged on exception
12. `test_sensitive_patterns_comprehensive` - All patterns detected

**Example Test**:
```python
def test_format_debug_message_basic():
    result = format_debug_message("search", "Starting", query="test", limit=10)
    assert "search:" in result
    assert "Starting" in result
    assert "query=test" in result or "query='test'" in result
    assert "limit=10" in result

async def test_timing_context_measures_duration():
    mock_ctx = MagicMock()
    async with TimingContext(mock_ctx, "test_operation"):
        await asyncio.sleep(0.1)  # 100ms delay

    mock_ctx.debug.assert_called_once()
    call_args = mock_ctx.debug.call_args[0][0]
    assert "test_operation" in call_args
    assert "duration=" in call_args
    # Verify duration is approximately 100ms (±10ms)
    duration_match = re.search(r"duration=(\d+\.\d+)ms", call_args)
    assert duration_match
    duration = float(duration_match.group(1))
    assert 90 <= duration <= 110
```

### Acceptance Criteria
- [ ] All tests pass
- [ ] Code coverage >90% for src/utils/debug.py
- [ ] Tests run in <2 seconds
- [ ] No flaky tests (timing tests have appropriate tolerances)

### Dependencies
- TASK-001 (debug utilities module)

### Files Modified
- `tests/unit/test_debug_utils.py` (create new)

---

## TASK-003: Write integration tests for debug logging

**Priority**: P1
**Estimated Time**: 30 minutes
**Assignee**: TBD
**Status**: Pending

### Description
Write integration tests to verify debug logging works correctly in MCP tools with mock Context objects.

### Implementation Details

**File**: `tests/integration/test_debug_logging.py`

**Test Cases**:
1. `test_search_debug_logs_present` - Verify search tool sends debug logs
2. `test_search_debug_timing_accurate` - Verify timing metrics within tolerance
3. `test_fetch_debug_logs_present` - Verify fetch tool sends debug logs
4. `test_ingest_debug_logs_present` - Verify ingest tool sends debug logs
5. `test_sensitive_data_redacted` - Verify password/token fields redacted
6. `test_debug_with_none_ctx` - Verify no errors when ctx=None
7. `test_debug_logs_structured` - Verify consistent format across tools

**Example Test**:
```python
async def test_search_debug_logs_present():
    mock_ctx = MagicMock()
    mock_ctx.debug = AsyncMock()

    await search_hansard_speeches(query="housing", ctx=mock_ctx)

    # Verify debug() was called
    assert mock_ctx.debug.called
    debug_calls = [call.args[0] for call in mock_ctx.debug.call_args_list]

    # Verify expected log entries
    assert any("Starting search" in msg or "search_hansard_speeches" in msg for msg in debug_calls)
    assert any("duration=" in msg for msg in debug_calls)

async def test_sensitive_data_redacted():
    mock_ctx = MagicMock()
    mock_ctx.debug = AsyncMock()

    # Ingest speech with sensitive metadata
    speech_data = {
        "text": "Test speech",
        "api_key": "secret123",  # Should be redacted
        "speaker": "Test Speaker"
    }

    await ingest_hansard_speech(speech_data=speech_data, ctx=mock_ctx)

    debug_calls = [call.args[0] for call in mock_ctx.debug.call_args_list]

    # Verify api_key was redacted
    assert any("***REDACTED***" in msg for msg in debug_calls)
    assert not any("secret123" in msg for msg in debug_calls)
```

### Acceptance Criteria
- [ ] All integration tests pass
- [ ] Tests verify debug() called with expected messages
- [ ] Timing accuracy validated (±10% tolerance)
- [ ] Sensitive data redaction verified
- [ ] Tests work with both ctx provided and ctx=None

### Dependencies
- TASK-004 (search tool debug logging)
- TASK-005 (fetch tool debug logging)
- TASK-006 (ingest tool debug logging)

### Files Modified
- `tests/integration/test_debug_logging.py` (create new)

---

## TASK-004: Add debug logging to search tool

**Priority**: P0
**Estimated Time**: 1 hour
**Assignee**: TBD
**Status**: Pending

### Description
Add structured debug logging to search_hansard_speeches tool with timing metrics, query parameters, and search result details.

### Implementation Details

**File**: `src/tools/search.py`

**Debug Log Points**:
1. **Entry**: Log query parameters (query, party, chamber, date_range, max_results)
2. **Filter application**: Log applied filters and match counts
3. **Embedding generation**: Log time to generate query embedding
4. **Vector search**: Log search time and result count
5. **Similarity scores**: Log top 5 similarity scores
6. **Result enrichment**: Log metadata fetch time
7. **Exit**: Log total operation time and final result count

**Implementation Pattern**:
```python
from src.utils.debug import format_debug_message, sanitize_debug_data, TimingContext

@mcp.tool()
async def search_hansard_speeches(
    query: str,
    party: Optional[str] = None,
    chamber: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    max_results: int = 10,
    ctx: Context = None
) -> dict:
    if ctx:
        params = sanitize_debug_data({
            "query": query,
            "party": party,
            "chamber": chamber,
            "date_from": date_from,
            "date_to": date_to,
            "max_results": max_results
        })
        await ctx.debug(format_debug_message("search_hansard_speeches", "Starting search", **params))

    async with TimingContext(ctx, "search_hansard_speeches.total"):
        # Existing implementation with debug logging added
        async with TimingContext(ctx, "search_hansard_speeches.vector_search"):
            results = await vector_store.search(query, filters, ctx=ctx)

        if ctx:
            scores = [r.get("similarity", 0) for r in results[:5]]
            await ctx.debug(f"search_hansard_speeches: Vector search complete (results={len(results)}, top_scores={scores})")

        # ... rest of implementation
```

### Acceptance Criteria
- [ ] All major operations logged with timing
- [ ] Query parameters logged at entry
- [ ] Similarity scores logged for top results
- [ ] Total operation time logged at exit
- [ ] No errors when ctx=None
- [ ] Sensitive data (if any) redacted
- [ ] Existing tests still pass

### Dependencies
- TASK-001 (debug utilities)

### Files Modified
- `src/tools/search.py`

---

## TASK-005: Add debug logging to fetch tool

**Priority**: P0
**Estimated Time**: 30 minutes
**Assignee**: TBD
**Status**: Pending

### Description
Add structured debug logging to fetch_hansard_speech tool with timing metrics and database lookup details.

### Implementation Details

**File**: `src/tools/fetch.py`

**Debug Log Points**:
1. **Entry**: Log speech_id parameter
2. **Database lookup**: Log query time and whether speech found
3. **Chunk retrieval** (if include_chunks=True): Log chunk count and retrieval time
4. **Exit**: Log total operation time

**Implementation Pattern**:
```python
from src.utils.debug import format_debug_message, TimingContext

@mcp.tool()
async def fetch_hansard_speech(
    speech_id: str,
    include_chunks: bool = False,
    ctx: Context = None
) -> dict:
    if ctx:
        await ctx.debug(format_debug_message(
            "fetch_hansard_speech",
            "Fetching speech",
            speech_id=speech_id,
            include_chunks=include_chunks
        ))

    async with TimingContext(ctx, "fetch_hansard_speech.total"):
        async with TimingContext(ctx, "fetch_hansard_speech.database_lookup"):
            speech = await metadata_store.get_speech(speech_id, ctx=ctx)

        if ctx:
            found = speech is not None
            await ctx.debug(f"fetch_hansard_speech: Lookup complete (found={found})")

        if include_chunks and speech:
            async with TimingContext(ctx, "fetch_hansard_speech.chunk_retrieval"):
                chunks = await vector_store.get_chunks_for_speech(speech_id, ctx=ctx)

            if ctx:
                await ctx.debug(f"fetch_hansard_speech: Chunks retrieved (count={len(chunks)})")

        # ... rest of implementation
```

### Acceptance Criteria
- [ ] Entry and exit logged with timing
- [ ] Database lookup time logged
- [ ] Speech found/not found status logged
- [ ] Chunk retrieval logged when include_chunks=True
- [ ] No errors when ctx=None
- [ ] Existing tests still pass

### Dependencies
- TASK-001 (debug utilities)

### Files Modified
- `src/tools/fetch.py`

---

## TASK-006: Add debug logging to ingest tool

**Priority**: P0
**Estimated Time**: 1.5 hours
**Assignee**: TBD
**Status**: Pending

### Description
Add comprehensive debug logging to ingest_hansard_speech tool with detailed timing for each processing stage.

### Implementation Details

**File**: `src/tools/ingest.py`

**Debug Log Points**:
1. **Entry**: Log speech metadata (speaker, date, chamber) - sanitized
2. **Validation**: Log validation time and result
3. **Chunking**: Log chunk count, average chunk size, chunking time
4. **Embedding generation**: Log per-chunk or batch timing, total embedding time
5. **Vector storage**: Log storage time, vector count inserted
6. **Metadata storage**: Log storage time
7. **Exit**: Log total operation time, success/failure

**Implementation Pattern**:
```python
from src.utils.debug import format_debug_message, sanitize_debug_data, TimingContext

@mcp.tool()
async def ingest_hansard_speech(
    speech_data: dict,
    generate_embeddings: bool = True,
    ctx: Context = None
) -> dict:
    if ctx:
        metadata = sanitize_debug_data({
            "speaker": speech_data.get("speaker"),
            "date": speech_data.get("date"),
            "chamber": speech_data.get("chamber"),
            "text_length": len(speech_data.get("text", ""))
        })
        await ctx.debug(format_debug_message("ingest_hansard_speech", "Starting ingestion", **metadata))

    async with TimingContext(ctx, "ingest_hansard_speech.total"):
        async with TimingContext(ctx, "ingest_hansard_speech.validation"):
            validate_speech_data(speech_data)

        async with TimingContext(ctx, "ingest_hansard_speech.chunking"):
            chunks = await chunker.chunk_text(speech_data["text"])

        if ctx:
            avg_size = sum(len(c) for c in chunks) / len(chunks) if chunks else 0
            await ctx.debug(f"ingest_hansard_speech: Chunks created (count={len(chunks)}, avg_size={avg_size:.0f})")

        if generate_embeddings:
            async with TimingContext(ctx, "ingest_hansard_speech.embedding"):
                embeddings = await vector_store.generate_embeddings(chunks, ctx=ctx)

            async with TimingContext(ctx, "ingest_hansard_speech.vector_storage"):
                await vector_store.add_chunks(chunks, embeddings, metadata, ctx=ctx)

        async with TimingContext(ctx, "ingest_hansard_speech.metadata_storage"):
            speech_id = await metadata_store.add_speech(speech_data, ctx=ctx)

        if ctx:
            await ctx.debug(f"ingest_hansard_speech: Ingestion complete (speech_id={speech_id})")

        # ... rest of implementation
```

### Acceptance Criteria
- [ ] All major stages logged with timing
- [ ] Chunk statistics logged (count, avg size)
- [ ] Embedding generation time logged
- [ ] Storage operations timed
- [ ] Total operation time logged
- [ ] No errors when ctx=None
- [ ] Sensitive data redacted
- [ ] Existing tests still pass

### Dependencies
- TASK-001 (debug utilities)

### Files Modified
- `src/tools/ingest.py`

---

## TASK-007: Add debug logging to VectorStoreService

**Priority**: P1
**Estimated Time**: 45 minutes
**Assignee**: TBD
**Status**: Pending

### Description
Add debug logging to VectorStoreService methods to provide visibility into vector search and embedding operations.

### Implementation Details

**File**: `src/storage/vector_store.py`

**Methods to Instrument**:
1. `search(query, filters, ctx)` - Embedding generation time, search time, similarity scores
2. `add_chunks(chunks, embeddings, metadata, ctx)` - Batch processing time, insertion time
3. `generate_embeddings(texts, ctx)` - Per-batch or total embedding generation time

**Implementation Pattern**:
```python
from src.utils.debug import TimingContext

async def search(
    self,
    query: str,
    filters: Optional[dict] = None,
    max_results: int = 10,
    ctx: Context = None
) -> List[dict]:
    async with TimingContext(ctx, "VectorStoreService.generate_query_embedding"):
        query_embedding = await self._generate_embedding(query)

    async with TimingContext(ctx, "VectorStoreService.vector_search"):
        results = await self._search_vectors(query_embedding, filters, max_results)

    if ctx:
        scores = [r.get("similarity", 0) for r in results[:5]]
        await ctx.debug(f"VectorStoreService: Search complete (results={len(results)}, top_scores={scores})")

    return results
```

### Acceptance Criteria
- [ ] Embedding generation time logged
- [ ] Vector search time logged
- [ ] Similarity scores logged
- [ ] Batch operations show count metrics
- [ ] No errors when ctx=None
- [ ] Existing tests still pass

### Dependencies
- TASK-001 (debug utilities)
- TASK-004, TASK-005, TASK-006 (tools pass ctx to services)

### Files Modified
- `src/storage/vector_store.py`

---

## TASK-008: Add debug logging to MetadataStore

**Priority**: P1
**Estimated Time**: 45 minutes
**Assignee**: TBD
**Status**: Pending

### Description
Add debug logging to MetadataStore methods to provide visibility into database operations.

### Implementation Details

**File**: `src/storage/metadata_store.py`

**Methods to Instrument**:
1. `get_speech(speech_id, ctx)` - Query time, found status
2. `add_speech(speech_data, ctx)` - Insert time, speech_id
3. `get_speeches_by_ids(speech_ids, ctx)` - Batch query time, result count

**Implementation Pattern**:
```python
from src.utils.debug import TimingContext

async def get_speech(
    self,
    speech_id: str,
    ctx: Context = None
) -> Optional[dict]:
    async with TimingContext(ctx, "MetadataStore.get_speech"):
        speech = await self._query_by_id(speech_id)

    if ctx:
        found = speech is not None
        await ctx.debug(f"MetadataStore: Speech lookup (speech_id={speech_id}, found={found})")

    return speech

async def get_speeches_by_ids(
    self,
    speech_ids: List[str],
    ctx: Context = None
) -> List[dict]:
    async with TimingContext(ctx, "MetadataStore.get_speeches_by_ids"):
        speeches = await self._query_by_ids(speech_ids)

    if ctx:
        await ctx.debug(f"MetadataStore: Batch lookup (requested={len(speech_ids)}, found={len(speeches)})")

    return speeches
```

### Acceptance Criteria
- [ ] Database query timing visible
- [ ] Found/not found status logged
- [ ] Batch operations show count metrics
- [ ] No errors when ctx=None
- [ ] Existing tests still pass

### Dependencies
- TASK-001 (debug utilities)
- TASK-004, TASK-005, TASK-006 (tools pass ctx to services)

### Files Modified
- `src/storage/metadata_store.py`

---

## TASK-009: Write performance benchmarks

**Priority**: P1
**Estimated Time**: 30 minutes
**Assignee**: TBD
**Status**: Pending

### Description
Create performance benchmarks to measure debug logging overhead and verify it meets <0.1% constraint when disabled.

### Implementation Details

**File**: `tests/performance/test_debug_overhead.py`

**Benchmarks**:
1. Search tool: debug enabled vs disabled
2. Fetch tool: debug enabled vs disabled
3. Ingest tool: debug enabled vs disabled
4. VectorStoreService.search: debug enabled vs disabled

**Implementation Pattern**:
```python
import time
from unittest.mock import MagicMock, AsyncMock

async def test_search_debug_overhead():
    """Verify search tool debug overhead <0.1% when disabled."""
    iterations = 100

    # Baseline: ctx=None (debug disabled)
    start = time.perf_counter()
    for _ in range(iterations):
        await search_hansard_speeches(query="test", ctx=None)
    baseline_time = time.perf_counter() - start

    # With debug: mock ctx (debug enabled but no-op)
    mock_ctx = MagicMock()
    mock_ctx.debug = AsyncMock()
    start = time.perf_counter()
    for _ in range(iterations):
        await search_hansard_speeches(query="test", ctx=mock_ctx)
    debug_time = time.perf_counter() - start

    # Calculate overhead
    overhead_pct = ((debug_time - baseline_time) / baseline_time) * 100

    print(f"Search tool overhead: {overhead_pct:.3f}%")
    assert overhead_pct < 0.1, f"Debug overhead {overhead_pct:.3f}% exceeds 0.1% target"
```

### Acceptance Criteria
- [ ] All benchmarks run successfully
- [ ] Overhead <0.1% when ctx=None
- [ ] Overhead <0.2% when ctx provides debug
- [ ] Results documented in quickstart.md
- [ ] Benchmarks can be run via pytest

### Dependencies
- TASK-002, TASK-003 (all tests passing)

### Files Modified
- `tests/performance/test_debug_overhead.py` (create new)

---

## TASK-010: Manual testing with MCP Inspector

**Priority**: P1
**Estimated Time**: 1 hour
**Assignee**: TBD
**Status**: Pending

### Description
Perform manual testing with MCP Inspector to verify debug logs appear correctly in the debug panel.

### Testing Procedure

1. **Setup**:
   ```bash
   # Terminal 1: Start server
   PYTHONPATH=src DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

   # Terminal 2: Start MCP Inspector
   npx @modelcontextprotocol/inspector
   ```

2. **Test Scenarios**:
   - Enable debug mode in MCP Inspector
   - Run search_hansard_speeches with query="housing"
   - Verify debug logs appear in debug panel
   - Verify timing metrics present and accurate
   - Run fetch_hansard_speech with valid speech_id
   - Verify database lookup timing logged
   - Run ingest_hansard_speech with sample data
   - Verify all stages logged with timing
   - Disable debug mode
   - Verify no debug logs appear

3. **Validation**:
   - Debug logs formatted correctly
   - Timing metrics accurate (±10% of actual)
   - No errors in server logs
   - No errors in MCP Inspector

### Acceptance Criteria
- [ ] All debug logs visible in MCP Inspector debug panel
- [ ] Timing metrics accurate (±10% tolerance)
- [ ] No errors with debug enabled
- [ ] No debug logs when debug disabled
- [ ] All tools tested (search, fetch, ingest)

### Dependencies
- TASK-004, TASK-005, TASK-006 (all tools instrumented)
- TASK-007, TASK-008 (services instrumented)

### Files Modified
- None (manual testing only)

---

## TASK-011: Create quickstart.md

**Priority**: P2
**Estimated Time**: 30 minutes
**Assignee**: TBD
**Status**: Pending

### Description
Create quickstart guide for testing debug logging with MCP Inspector and interpreting debug logs.

### Implementation Details

**File**: `specs/007-debug-logging/quickstart.md`

**Content Sections**:
1. **Overview** - What is debug logging and why use it
2. **Testing with MCP Inspector** - Step-by-step setup and testing
3. **Expected Debug Logs** - Examples for each tool
4. **Performance Benchmarks** - Results from TASK-009
5. **Troubleshooting** - Common issues and solutions
6. **Debug Log Format** - Explanation of structured format

**Expected Debug Log Examples**:
```
search_hansard_speeches: Starting search (query='housing', party=None, chamber='REPS', max_results=10)
search_hansard_speeches.vector_search (duration=234.5ms)
VectorStoreService.generate_query_embedding (duration=45.2ms)
VectorStoreService.vector_search (duration=189.3ms)
VectorStoreService: Search complete (results=10, top_scores=[0.89, 0.85, 0.82, 0.79, 0.76])
search_hansard_speeches: Vector search complete (results=10, top_scores=[0.89, 0.85, 0.82, 0.79, 0.76])
search_hansard_speeches.total (duration=456.8ms)
```

### Acceptance Criteria
- [ ] Quickstart covers all testing scenarios
- [ ] Examples are accurate and tested
- [ ] Performance benchmark results included
- [ ] Troubleshooting section addresses common issues
- [ ] Document is clear and easy to follow

### Dependencies
- TASK-009 (performance benchmarks)
- TASK-010 (MCP Inspector testing)

### Files Modified
- `specs/007-debug-logging/quickstart.md` (create new)

---

## TASK-012: Create requirements validation checklist

**Priority**: P2
**Estimated Time**: 30 minutes
**Assignee**: TBD
**Status**: Pending

### Description
Create comprehensive checklist to validate all functional requirements, non-functional requirements, and success criteria.

### Implementation Details

**File**: `specs/007-debug-logging/checklists/requirements.md`

**Content Structure**:
1. **Functional Requirements (FR-001 through FR-012)**
   - Requirement text
   - Validation method
   - Test case reference
   - Status (pass/fail)

2. **Non-Functional Requirements (NFR-001 through NFR-005)**
   - Requirement text
   - Measurement method
   - Actual measurement
   - Status (pass/fail)

3. **Success Criteria (SC-001 through SC-009)**
   - Criterion text
   - Validation method
   - Evidence
   - Status (pass/fail)

**Example Entry**:
```markdown
### FR-001: All MCP tools MUST support debug logging via ctx.debug() method

**Validation Method**: Manual inspection of tool code + integration tests

**Test Cases**:
- tests/integration/test_debug_logging.py::test_search_debug_logs_present
- tests/integration/test_debug_logging.py::test_fetch_debug_logs_present
- tests/integration/test_debug_logging.py::test_ingest_debug_logs_present

**Evidence**:
- search_hansard_speeches calls ctx.debug() at 5 points
- fetch_hansard_speech calls ctx.debug() at 3 points
- ingest_hansard_speech calls ctx.debug() at 7 points
- All integration tests pass

**Status**: ✅ PASS
```

### Acceptance Criteria
- [ ] All FRs have validation methods
- [ ] All NFRs have measurement methods
- [ ] All SCs have validation methods
- [ ] Test case references provided
- [ ] Checklist can be used for feature sign-off

### Dependencies
- TASK-002, TASK-003 (all tests complete)
- TASK-009 (performance benchmarks)
- TASK-010 (manual testing)

### Files Modified
- `specs/007-debug-logging/checklists/requirements.md` (create new)

---

## Summary

**Total Tasks**: 12
**Estimated Total Time**: 9.5 hours

**Critical Path**:
TASK-001 → TASK-004/005/006 → TASK-007/008 → TASK-003 → TASK-009 → TASK-010 → TASK-011/012

**Parallel Work Opportunities**:
- TASK-004, TASK-005, TASK-006 can be done in parallel after TASK-001
- TASK-007, TASK-008 can be done in parallel after tools
- TASK-011, TASK-012 can be done in parallel after testing

**Blocking Tasks**:
- TASK-001 blocks all implementation tasks
- TASK-010 blocks documentation tasks
