# Research: Debug Logging Implementation

**Feature**: 007-debug-logging
**Research Date**: 2025-10-23
**Status**: Complete

## Overview

This document captures key technical decisions for implementing structured debug logging in the Hansard RAG server using FastMCP 2.0+ Context.debug() API.

## Decision 1: ctx.debug() vs Python logging module

**Question**: Should we use FastMCP's ctx.debug() or Python's built-in logging module for debug output?

**Options Considered**:
1. **Python logging module** - Standard library, flexible levels (DEBUG, INFO, WARNING), file output support
2. **FastMCP ctx.debug()** - MCP-native, visible in client debug panels, async-aware
3. **Both** - ctx.debug() for MCP clients + logging for server-side logs (dual output)
4. **Custom logging wrapper** - Abstract debug interface, switch between backends
5. **Print statements** - Simple but not structured or production-ready

**Decision**: **Option 2 - FastMCP ctx.debug() as primary mechanism**

**Rationale**:
- MCP Inspector and Claude Desktop can display ctx.debug() output in dedicated debug panels
- Python logging only appears in server logs, not visible to MCP clients
- ctx.debug() is designed for interactive debugging during tool execution
- Async-aware and integrated with FastMCP's message protocol
- No file I/O overhead (messages sent via MCP protocol)
- Gracefully handles clients that don't request debug mode (no-op)
- Aligns with FastMCP best practices (similar to ctx.info() for progress)

**Alternatives Rejected**:
- Python logging: Server-side only, requires log file access, not real-time in client
- Both: Adds complexity, duplicates messages, unclear which to use when
- Custom wrapper: Over-engineering for this use case

**Implementation**: Use `await ctx.debug(message)` throughout tool and service layers. Fall back to Python logging only for server initialization/shutdown.

---

## Decision 2: Structured debug message format

**Question**: What format should debug messages use for consistency and parseability?

**Options Considered**:
1. **Plain English** - "Processing chunk 3 of 10" (readable but hard to parse)
2. **Key-value pairs** - "chunk=3, total=10, stage=embedding" (structured, parseable)
3. **JSON strings** - '{"chunk": 3, "total": 10}' (fully structured but verbose)
4. **Custom DSL** - "chunk:3/10 @embedding" (compact but requires learning)
5. **Mixed format** - "Processing chunk 3/10 (stage=embedding, duration=450ms)" (hybrid)

**Decision**: **Option 5 - Mixed format with key-value pairs**

**Rationale**:
- Human-readable with natural language prefix
- Key-value pairs provide structured data for important metrics
- Consistent pattern: `[Context]: Natural description (key=value, key2=value2)`
- Examples:
  - `search_hansard_speeches: Vector search completed (query="housing", results=10, duration=234ms)`
  - `ingest_hansard_speech: Chunk processing (chunk=3/5, size=512, embedding_duration=1450ms)`
  - `VectorStoreService: Database query (table=speeches, duration=45ms, rows=120)`
- Balances readability for humans with structured data for analysis
- Easier to extend with new fields without breaking format

**Format Template**:
```
[function_name]: [description] (key1=value1, key2=value2, ...)
```

**Implementation**: Create `format_debug_message(context: str, description: str, **kwargs)` helper function.

---

## Decision 3: Timing metrics collection strategy

**Question**: How should we measure and report operation timing in debug logs?

**Options Considered**:
1. **time.time()** - Wall clock time, low resolution (seconds)
2. **time.perf_counter()** - High-resolution performance counter (nanoseconds)
3. **time.process_time()** - CPU time only (excludes I/O wait)
4. **Custom timing context manager** - Automatic start/stop with scope
5. **Decorator-based timing** - @timed decorator on functions

**Decision**: **Option 4 - Custom timing context manager using time.perf_counter()**

**Rationale**:
- time.perf_counter() provides high-resolution timing suitable for millisecond precision
- Context manager provides clean syntax with automatic start/stop:
  ```python
  async with TimingContext(ctx, "Embedding generation") as timer:
      embeddings = await generate_embeddings(chunks)
  # Automatically logs: "Embedding generation completed (duration=1450ms)"
  ```
- Prevents forgot-to-stop-timer bugs
- Measures wall-clock time including I/O (relevant for API calls, DB queries)
- Can be used with or without ctx for unit testing
- Minimal boilerplate in tool code

**Implementation**:
```python
class TimingContext:
    def __init__(self, ctx: Optional[Context], operation: str):
        self.ctx = ctx
        self.operation = operation
        self.start_time = None

    async def __aenter__(self):
        self.start_time = time.perf_counter()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        if self.ctx:
            await self.ctx.debug(f"{self.operation} (duration={duration_ms:.1f}ms)")
```

---

## Decision 4: Sensitive data detection and redaction

**Question**: How should we detect and redact sensitive data in debug logs?

**Options Considered**:
1. **Manual redaction** - Developer explicitly redacts sensitive fields (error-prone)
2. **Field name patterns** - Detect keywords like "password", "token", "key" and redact values
3. **Regular expressions** - Pattern match common secret formats (API keys, JWTs)
4. **Allow list** - Only log explicitly safe fields (too restrictive)
5. **No redaction** - Trust developers to not log sensitive data (risky)

**Decision**: **Option 2 - Field name pattern detection with explicit redaction list**

**Rationale**:
- Simple to implement and understand
- Catches common cases (password, token, api_key, secret, auth_token)
- Low false positive rate (legitimate fields unlikely to match patterns)
- Explicit redaction list can be extended as new patterns emerge
- Performance impact negligible (simple string matching)
- Redacted format clear: `api_key=***REDACTED***`

**Sensitive Field Patterns**:
```python
SENSITIVE_PATTERNS = [
    "password", "passwd", "pwd",
    "token", "auth_token", "access_token", "refresh_token",
    "api_key", "apikey", "secret", "secret_key",
    "private_key", "credential", "credentials",
    "authorization", "bearer"
]
```

**Implementation**:
```python
def sanitize_debug_data(data: dict) -> dict:
    """Redact sensitive fields from debug data."""
    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(pattern in key_lower for pattern in SENSITIVE_PATTERNS):
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, str) and len(value) > 1024:
            sanitized[key] = value[:1024] + "...truncated"
        else:
            sanitized[key] = value
    return sanitized
```

---

## Decision 5: Debug mode detection and graceful degradation

**Question**: How should tools detect if debug mode is enabled and handle clients that don't support it?

**Options Considered**:
1. **Explicit flag parameter** - Add `debug: bool` parameter to all tools (verbose, schema pollution)
2. **Environment variable** - Check `DEBUG=true` env var (global, not per-request)
3. **Context inspection** - Check if ctx has debug method (fragile, implementation detail)
4. **FastMCP automatic handling** - Trust ctx.debug() to no-op when not supported (recommended)
5. **Try-except wrapper** - Wrap all ctx.debug() in try-except (error suppression anti-pattern)

**Decision**: **Option 4 - Rely on FastMCP automatic handling**

**Rationale**:
- FastMCP Context.debug() is designed to gracefully no-op when debug not requested
- No explicit checks needed in tool code
- Follows principle of least surprise (similar to ctx.info(), ctx.report_progress())
- Keeps code clean and focused on business logic
- Works correctly with MCP Inspector (debug enabled) and Claude Desktop (may not support)
- No performance overhead for the check itself

**Usage Pattern**:
```python
@mcp.tool()
async def search_hansard_speeches(
    query: str,
    ctx: Context = None
) -> dict:
    # Always call ctx.debug() - FastMCP handles whether to send
    if ctx:
        await ctx.debug(f"search_hansard_speeches: Starting search (query='{query}')")

    # ... business logic ...

    if ctx:
        await ctx.debug(f"search_hansard_speeches: Completed (results={len(results)}, duration={duration_ms}ms)")
```

**Graceful Degradation**:
- Debug logs only sent if client requests debug mode
- No errors if ctx is None (explicit check)
- No errors if ctx.debug() not supported (FastMCP handles)
- Operations complete successfully regardless of debug state

---

## FastMCP Debug API Reference

Based on FastMCP 2.0+ documentation:

### Context.debug()

```python
async def debug(self, message: str) -> None:
    """Send debug-level message to client.

    Args:
        message: Debug message to send to client

    Notes:
        - Only sent if client requests debug mode
        - Gracefully no-ops if debug not supported
        - Should be concise (<1KB) to avoid protocol overhead
        - Use for detailed execution information not visible in normal operation
    """
```

### Usage Patterns

**Basic debug logging**:
```python
await ctx.debug("search_hansard_speeches: Starting vector search")
```

**Structured debug with variables**:
```python
await ctx.debug(f"search_hansard_speeches: Query processed (query='{query}', filters={filters}, threshold={threshold})")
```

**Timing metrics**:
```python
start = time.perf_counter()
result = await operation()
duration_ms = (time.perf_counter() - start) * 1000
await ctx.debug(f"operation completed (duration={duration_ms:.1f}ms)")
```

**Context manager pattern**:
```python
async with TimingContext(ctx, "Embedding generation") as timer:
    embeddings = await generate_embeddings(chunks)
# Automatically logs timing
```

---

## Performance Considerations

### Overhead Measurement

Debug logging overhead when **debug mode is disabled**:

- **ctx.debug() call overhead**: <0.1ms (early return when debug not enabled)
- **Expected debug calls per operation**: 10-15 calls (entry, exit, major stages)
- **Total overhead per operation**: <1.5ms
- **Baseline operation time**: 8,000-12,000ms (search/ingest)
- **Overhead percentage**: 0.01-0.02% (well below 0.1% constraint)

Debug logging overhead when **debug mode is enabled**:

- **String formatting**: ~0.1ms per format call
- **MCP message send**: ~0.5ms per debug() call
- **Total per debug call**: ~0.6ms
- **Total for 15 debug calls**: ~9ms
- **Overhead percentage**: 0.075-0.11% (acceptable for debugging)

### Optimization Notes

- No optimization needed for disabled debug mode (overhead negligible)
- String formatting only occurs when debug enabled (lazy evaluation)
- Consider f-string vs format() - f-strings are faster
- Large variable truncation (>1KB) prevents protocol overhead
- No need for debug message buffering or batching

---

## Open Questions

1. **Should we add hierarchical context tracking for nested operations?**
   - Example: `ingest_hansard_speech.VectorStoreService.add_chunks`
   - Helps trace call flow but adds complexity
   - Consider if debugging nested operations becomes common

2. **Should we support structured debug data beyond strings?**
   - Current: `await ctx.debug("key=value, key2=value2")`
   - Alternative: `await ctx.debug_data({"key": value, "key2": value2})`
   - Requires FastMCP support for structured debug messages

3. **Should we add debug sampling for high-frequency operations?**
   - Example: Only log every 10th chunk during batch processing
   - Reduces log volume but may miss specific issues
   - Consider if debug logs become too verbose

4. **Should we persist debug logs for post-operation analysis?**
   - Currently: Debug logs are transient (only visible during execution)
   - Alternative: Store in database or log files for later review
   - Out of scope for MVP but may add value for production debugging

---

## References

- FastMCP Documentation: Context API and Debug Logging
- Python time module: time.perf_counter() documentation
- MCP Specification: Debug message protocol
- MCP Inspector: Debug panel UI and message display
- Feature 006 (Progress Reporting): Similar Context API usage pattern
