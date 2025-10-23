# Implementation Plan: Debug Logging

**Feature**: 007-debug-logging
**Status**: Draft
**Created**: 2025-10-23

## Summary

Add structured debug logging to all MCP tools using FastMCP's ctx.debug() API. Implement timing utilities, sensitive data redaction, and consistent debug message formatting to help developers and support engineers diagnose performance issues, search quality problems, and infrastructure concerns.

## Technical Context

### Technology Stack
- **Language**: Python 3.11+
- **Framework**: FastMCP 2.0+ (Context.debug() API)
- **Dependencies**: Python time module (time.perf_counter())
- **Testing**: pytest, MCP Inspector

### Architecture Integration
- **Existing Tools**: search_hansard_speeches, fetch_hansard_speech, ingest_hansard_speech
- **Service Layer**: VectorStoreService, MetadataStore, ChunkingService
- **New Module**: src/utils/debug.py (utilities for formatting, timing, sanitization)

### Performance Requirements
- Debug overhead when disabled: <0.1% (target: 0.01-0.02%)
- Debug overhead when enabled: <0.2% (target: 0.075-0.11%)
- Debug message latency: <500ms from event to client display

---

## Phase 0: Research and Planning (COMPLETE)

**Status**: ✓ COMPLETE

**Deliverables**:
- ✓ Technical decision: ctx.debug() vs Python logging → ctx.debug()
- ✓ Technical decision: Debug message format → Mixed format with key-value pairs
- ✓ Technical decision: Timing strategy → TimingContext with time.perf_counter()
- ✓ Technical decision: Sensitive data handling → Field name pattern detection
- ✓ Technical decision: Debug mode detection → FastMCP automatic handling

**Key Findings**:
- ctx.debug() provides MCP client visibility (primary advantage)
- Mixed format balances readability and structured data
- TimingContext async context manager provides clean timing syntax
- Field name patterns (password, token, api_key) sufficient for redaction
- No explicit debug mode checks needed (FastMCP handles gracefully)

---

## Phase 1: Core Utilities Implementation (2 hours)

### Task 1.1: Create debug utilities module (45 minutes)

**File**: `src/utils/debug.py`

**Deliverables**:
1. `format_debug_message(context: str, description: str, **kwargs) -> str`
   - Template: `[context]: [description] (key1=value1, key2=value2)`
   - Handle empty kwargs gracefully
   - Truncate values >1KB with "...truncated" suffix

2. `sanitize_debug_data(data: dict) -> dict`
   - Detect sensitive field names (password, token, api_key, secret, etc.)
   - Redact sensitive values: `api_key=***REDACTED***`
   - Truncate long strings (>1KB)
   - Return sanitized copy (immutable)

3. `SENSITIVE_PATTERNS: List[str]`
   - Constant list: password, token, api_key, secret, auth, bearer, etc.

**Acceptance Criteria**:
- format_debug_message("search", "Starting", query="test") returns expected format
- sanitize_debug_data redacts fields matching patterns
- Long values truncated with clear indication

---

### Task 1.2: Create timing context manager (45 minutes)

**File**: `src/utils/debug.py`

**Deliverables**:
1. `TimingContext` async context manager
   - Constructor: `__init__(ctx: Optional[Context], operation: str)`
   - Start timer on `__aenter__` using time.perf_counter()
   - Log duration on `__aexit__` via ctx.debug()
   - Handle None ctx gracefully
   - Format: "{operation} (duration={duration_ms:.1f}ms)"

2. Exception handling in `__aexit__`
   - Log timing even if inner operation fails
   - Include exception type in debug message
   - Don't suppress exceptions

**Acceptance Criteria**:
- TimingContext measures duration accurately (±5ms)
- Debug message sent on exit with correct duration
- Works with ctx=None (no error)
- Timing still logged when inner operation raises exception

---

### Task 1.3: Write utility unit tests (30 minutes)

**File**: `tests/unit/test_debug_utils.py`

**Test Cases**:
1. test_format_debug_message_basic - Basic formatting with kwargs
2. test_format_debug_message_empty_kwargs - No kwargs provided
3. test_format_debug_message_long_value - Value >1KB truncated
4. test_sanitize_debug_data_password - Password field redacted
5. test_sanitize_debug_data_api_key - API key field redacted
6. test_sanitize_debug_data_safe_fields - Non-sensitive fields preserved
7. test_timing_context_measures_duration - Timing accurate
8. test_timing_context_with_none_ctx - No error with None
9. test_timing_context_with_exception - Timing logged on exception

**Acceptance Criteria**:
- All tests pass
- Code coverage >90% for debug.py

---

## Phase 2: Tool Integration (3 hours)

### Task 2.1: Add debug logging to search tool (1 hour)

**File**: `src/tools/search.py`

**Debug Log Points**:
1. Entry: Log query parameters (query, party, chamber, date_range, max_results)
2. Filter application: Log applied filters and match counts
3. Vector search: Log embedding generation time, search time, result count
4. Similarity scores: Log top 5 similarity scores
5. Result enrichment: Log metadata fetch time
6. Exit: Log total operation time and final result count

**Implementation Pattern**:
```python
@mcp.tool()
async def search_hansard_speeches(
    query: str,
    party: Optional[str] = None,
    chamber: Optional[str] = None,
    max_results: int = 10,
    ctx: Context = None
) -> dict:
    if ctx:
        params = sanitize_debug_data({
            "query": query, "party": party, "chamber": chamber, "max_results": max_results
        })
        await ctx.debug(format_debug_message("search_hansard_speeches", "Starting search", **params))

    async with TimingContext(ctx, "search_hansard_speeches.vector_search"):
        results = await vector_store.search(query, filters)

    if ctx:
        await ctx.debug(f"search_hansard_speeches: Results returned (count={len(results)})")
```

**Acceptance Criteria**:
- Debug logs appear in MCP Inspector when debug enabled
- No errors when debug disabled
- Timing metrics accurate
- Sensitive data (if any) redacted

---

### Task 2.2: Add debug logging to fetch tool (30 minutes)

**File**: `src/tools/fetch.py`

**Debug Log Points**:
1. Entry: Log speech_id parameter
2. Database lookup: Log query time and whether speech found
3. Chunk retrieval: Log chunk count and retrieval time
4. Exit: Log total operation time

**Implementation Pattern**:
```python
@mcp.tool()
async def fetch_hansard_speech(
    speech_id: str,
    include_chunks: bool = False,
    ctx: Context = None
) -> dict:
    if ctx:
        await ctx.debug(format_debug_message("fetch_hansard_speech", "Fetching speech", speech_id=speech_id, include_chunks=include_chunks))

    async with TimingContext(ctx, "fetch_hansard_speech.database_lookup"):
        speech = await metadata_store.get_speech(speech_id)

    if ctx:
        found = speech is not None
        await ctx.debug(f"fetch_hansard_speech: Lookup complete (found={found})")
```

**Acceptance Criteria**:
- Debug logs show speech lookup timing
- Missing speech_id logged clearly
- Chunk retrieval time logged when include_chunks=True

---

### Task 2.3: Add debug logging to ingest tool (1.5 hours)

**File**: `src/tools/ingest.py`

**Debug Log Points**:
1. Entry: Log speech metadata (speaker, date, chamber)
2. Validation: Log validation time and result
3. Chunking: Log chunk count, average chunk size, chunking time
4. Embedding generation: Log per-chunk embedding time, total embedding time
5. Vector storage: Log storage time, vector count
6. Metadata storage: Log storage time
7. Exit: Log total operation time, success/failure

**Implementation Pattern**:
```python
@mcp.tool()
async def ingest_hansard_speech(
    speech_data: dict,
    generate_embeddings: bool = True,
    ctx: Context = None
) -> dict:
    if ctx:
        metadata = sanitize_debug_data(speech_data)
        await ctx.debug(format_debug_message("ingest_hansard_speech", "Starting ingestion", **metadata))

    async with TimingContext(ctx, "ingest_hansard_speech.validation"):
        validate_speech_data(speech_data)

    async with TimingContext(ctx, "ingest_hansard_speech.chunking"):
        chunks = await chunker.chunk_text(speech_data["text"])

    if ctx:
        avg_size = sum(len(c) for c in chunks) / len(chunks)
        await ctx.debug(f"ingest_hansard_speech: Chunks created (count={len(chunks)}, avg_size={avg_size:.0f})")

    async with TimingContext(ctx, "ingest_hansard_speech.embedding"):
        embeddings = await vector_store.generate_embeddings(chunks)
```

**Acceptance Criteria**:
- All major stages logged with timing
- Chunk count and sizes logged
- Embedding generation time logged
- Storage operations timed

---

## Phase 3: Service Layer Integration (1.5 hours)

### Task 3.1: Add debug to VectorStoreService (45 minutes)

**File**: `src/storage/vector_store.py`

**Methods to Instrument**:
1. `search(query: str, filters: dict, ctx: Context = None)`
   - Log embedding generation time
   - Log vector search time
   - Log result count and top similarity scores

2. `add_chunks(chunks: List[str], metadata: dict, ctx: Context = None)`
   - Log batch embedding generation time
   - Log database insertion time
   - Log chunk count

**Implementation Pattern**:
```python
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
        scores = [r["similarity"] for r in results[:5]]
        await ctx.debug(f"VectorStoreService: Search complete (results={len(results)}, top_scores={scores})")
```

**Acceptance Criteria**:
- Embedding generation time visible in debug logs
- Vector search time logged
- Similarity scores logged

---

### Task 3.2: Add debug to MetadataStore (45 minutes)

**File**: `src/storage/metadata_store.py`

**Methods to Instrument**:
1. `get_speech(speech_id: str, ctx: Context = None)`
   - Log database query time
   - Log whether speech found

2. `add_speech(speech_data: dict, ctx: Context = None)`
   - Log database insert time
   - Log success/failure

3. `get_speeches_by_ids(speech_ids: List[str], ctx: Context = None)`
   - Log batch query time
   - Log result count vs requested count

**Implementation Pattern**:
```python
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
```

**Acceptance Criteria**:
- Database query timing visible
- Batch operations show count metrics
- Missing records logged clearly

---

## Phase 4: Testing and Validation (2 hours)

### Task 4.1: Manual testing with MCP Inspector (1 hour)

**Test Scenarios**:
1. Enable debug mode in MCP Inspector
2. Run search_hansard_speeches with query="housing"
3. Verify debug logs appear in debug panel
4. Verify timing metrics present and accurate
5. Run fetch_hansard_speech with valid and invalid IDs
6. Verify database lookup timing logged
7. Run ingest_hansard_speech with sample data
8. Verify all stages logged with timing
9. Disable debug mode
10. Verify no debug logs appear

**Documentation**: Create quickstart.md with testing procedure

**Acceptance Criteria**:
- All debug logs visible in MCP Inspector
- Timing metrics accurate (±10% of actual)
- No errors with debug enabled or disabled

---

### Task 4.2: Performance benchmarks (30 minutes)

**File**: `tests/performance/test_debug_overhead.py`

**Benchmarks**:
1. Measure search tool execution time with debug enabled vs disabled
2. Measure ingest tool execution time with debug enabled vs disabled
3. Calculate overhead percentage
4. Verify <0.1% overhead when disabled
5. Verify <0.2% overhead when enabled

**Implementation**:
```python
async def test_search_debug_overhead():
    # Baseline: debug disabled
    start = time.perf_counter()
    for _ in range(100):
        await search_hansard_speeches(query="test", ctx=None)
    baseline_time = time.perf_counter() - start

    # With debug
    mock_ctx = MagicMock()
    start = time.perf_counter()
    for _ in range(100):
        await search_hansard_speeches(query="test", ctx=mock_ctx)
    debug_time = time.perf_counter() - start

    overhead_pct = ((debug_time - baseline_time) / baseline_time) * 100
    assert overhead_pct < 0.1  # Less than 0.1% overhead
```

**Acceptance Criteria**:
- Overhead measurements documented
- All overhead targets met
- Results included in quickstart.md

---

### Task 4.3: Integration tests (30 minutes)

**File**: `tests/integration/test_debug_logging.py`

**Test Cases**:
1. test_search_debug_logs_present - Verify debug logs sent via mock ctx
2. test_search_debug_timing_accurate - Verify timing metrics within 10%
3. test_fetch_debug_logs_present - Verify fetch tool debug logs
4. test_ingest_debug_logs_present - Verify ingest tool debug logs
5. test_sensitive_data_redacted - Verify password/token fields redacted
6. test_debug_with_none_ctx - Verify no errors when ctx=None

**Implementation Pattern**:
```python
async def test_search_debug_logs_present():
    mock_ctx = MagicMock()
    await search_hansard_speeches(query="test", ctx=mock_ctx)

    # Verify debug() was called
    assert mock_ctx.debug.called
    debug_calls = [call.args[0] for call in mock_ctx.debug.call_args_list]

    # Verify expected log entries
    assert any("Starting search" in msg for msg in debug_calls)
    assert any("duration=" in msg for msg in debug_calls)
```

**Acceptance Criteria**:
- All integration tests pass
- Mock ctx verified to receive debug calls
- Timing accuracy validated

---

## Phase 5: Documentation (1 hour)

### Task 5.1: Create quickstart.md (30 minutes)

**File**: `specs/007-debug-logging/quickstart.md`

**Content**:
1. Testing with MCP Inspector (step-by-step)
2. Expected debug log examples
3. Performance benchmark results
4. Troubleshooting guide

---

### Task 5.2: Create requirements checklist (30 minutes)

**File**: `specs/007-debug-logging/checklists/requirements.md`

**Content**:
- FR validation checklist (FR-001 through FR-012)
- NFR validation checklist (NFR-001 through NFR-005)
- SC validation checklist (SC-001 through SC-009)
- Test methods for each requirement

---

## Risks and Mitigations

### Risk 1: Debug logging impacts performance
- **Likelihood**: Low
- **Impact**: Medium
- **Mitigation**: Performance benchmarks in Phase 4, overhead targets (<0.1% disabled, <0.2% enabled)

### Risk 2: Sensitive data accidentally logged
- **Likelihood**: Medium
- **Impact**: High
- **Mitigation**: Sanitize all debug data through sanitize_debug_data(), security audit in testing phase

### Risk 3: Debug logs too verbose or not useful
- **Likelihood**: Medium
- **Impact**: Low
- **Mitigation**: Manual testing with MCP Inspector to validate log usefulness, iterate on log points

### Risk 4: FastMCP ctx.debug() API changes
- **Likelihood**: Low
- **Impact**: Medium
- **Mitigation**: Use stable FastMCP 2.0+ API, test with MCP Inspector to validate compatibility

---

## Success Metrics

### Implementation Quality
- All unit tests pass (>90% coverage for debug.py)
- All integration tests pass
- Performance benchmarks meet targets

### User Value
- Developers can identify bottlenecks within 5 minutes using debug logs
- Support team can diagnose 80%+ of issues using debug logs alone
- Zero sensitive data leakage in security audit

### Technical Excellence
- Debug overhead <0.1% when disabled
- Debug logs appear in MCP Inspector <500ms after event
- Code is maintainable (debug logic doesn't obscure business logic)

---

## Timeline Estimate

- Phase 0: Research and Planning - COMPLETE
- Phase 1: Core Utilities Implementation - 2 hours
- Phase 2: Tool Integration - 3 hours
- Phase 3: Service Layer Integration - 1.5 hours
- Phase 4: Testing and Validation - 2 hours
- Phase 5: Documentation - 1 hour

**Total**: 9.5 hours (approximately 1.5 days)

---

## References

- FastMCP Documentation: Context.debug() API
- Research Document: 007-debug-logging/research.md
- Feature Specification: 007-debug-logging/spec.md
- Feature 006: Progress Reporting (similar Context API usage)
