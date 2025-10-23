# Feature Specification: Debug Logging

**Feature Branch**: `007-debug-logging`
**Created**: 2025-10-23
**Status**: Draft
**Input**: "Implement structured debugging logging using ctx.debug() to send detailed execution information, variable states, and timing metrics to help diagnose issues during tool execution"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Diagnoses Slow Ingest Operation (Priority: P1)

A developer receives a user complaint that speech ingestion is taking 20+ seconds instead of the expected 8-12 seconds. They need to identify which stage is causing the bottleneck without modifying code or adding custom logging. Using MCP Inspector's debug mode, they can see detailed timing metrics for each processing stage and pinpoint the issue.

**Why this priority**: This is the MVP - debugging slow operations is the primary use case for debug logging. Without visibility into internal operation timing, developers must rely on guesswork or code instrumentation. This provides immediate value for performance troubleshooting.

**Independent Test**: Can be fully tested by enabling debug mode in MCP Inspector, running the ingest tool with sample speech data, observing debug logs showing stage timings (e.g., "Validation: 45ms", "Chunking: 1200ms", "Embedding: 8500ms"), and verifying the bottleneck stage is clearly identified.

**Acceptance Scenarios**:

1. **Given** a developer opens MCP Inspector and enables debug mode, **When** they run the ingest tool, **Then** debug logs appear showing timing for each major stage within 1 second of stage completion
2. **Given** the embedding generation stage is running, **When** processing multiple chunks, **Then** debug logs show per-chunk timing: "Chunk 1/5: 1450ms", "Chunk 2/5: 1380ms"
3. **Given** the operation completes, **When** reviewing debug logs, **Then** total operation time is displayed: "Total execution: 12,340ms"
4. **Given** debug mode is disabled, **When** running the same operation, **Then** no debug logs appear and operation completes normally
5. **Given** a bottleneck is identified (e.g., embedding API slow), **When** developer reviews debug logs, **Then** actionable information is present (API latency, chunk size, retry count)
6. **Given** operation timing data is logged, **When** comparing to baseline, **Then** performance regression is quantifiable (e.g., "Embedding 3x slower than expected")

---

### User Story 2 - Support Team Diagnoses Search Result Quality Issues (Priority: P2)

A support engineer receives a ticket: "Search for 'housing policy' returns irrelevant speeches about infrastructure". They need to understand why the vector search is returning low-quality results without access to the production database. Using debug logging, they can see the actual similarity scores, applied filters, and query parameters to diagnose the issue.

**Why this priority**: Builds on P1 by addressing search quality debugging. While slower than performance issues, search quality problems require visibility into vector search internals (similarity scores, filters). This scenario demonstrates debug logging's value across different tool types.

**Independent Test**: Can be tested by enabling debug mode, performing a search query that returns unexpected results, verifying debug logs show similarity scores for all returned chunks (e.g., "Result 1: score=0.85", "Result 2: score=0.31"), and confirming filter application is logged correctly.

**Acceptance Scenarios**:

1. **Given** a support engineer enables debug mode, **When** they run a search query, **Then** debug logs show the processed query: "Vector search query: 'housing policy', filters: {party: None, chamber: 'REPS'}"
2. **Given** vector search returns results, **When** viewing debug logs, **Then** similarity scores are displayed for each result: "Speech ABC123: similarity=0.89", "Speech DEF456: similarity=0.31"
3. **Given** low similarity scores are detected, **When** engineer reviews debug logs, **Then** threshold information is shown: "Similarity threshold: 0.7, 3/10 results below threshold"
4. **Given** filters are applied, **When** viewing debug logs, **Then** filter application is logged: "Applied filters: party=LP (matched 45 speeches), chamber=REPS (matched 120 speeches)"
5. **Given** the query returns zero results, **When** debug mode is enabled, **Then** logs explain why: "Vector search returned 0 results, tried 768-dim embedding lookup in speeches_embeddings"

---

### User Story 3 - Administrator Monitors Database Connection Health (Priority: P3)

A system administrator notices intermittent timeouts during batch ingestion jobs. They suspect database connection pool exhaustion but have no visibility into connection state during operations. Using debug logging, they can see connection pool metrics, query execution times, and retry attempts to validate their hypothesis.

**Why this priority**: Future enhancement that extends debug logging to infrastructure concerns. Lower priority because connection issues are less frequent than performance/quality issues, but provides value for production operations debugging and capacity planning.

**Independent Test**: Can be tested by enabling debug mode during a batch ingestion operation, verifying debug logs show database metrics ("DB connection acquired from pool in 12ms", "Active connections: 3/10"), confirming query execution times are logged, and validating retry logic is visible in logs.

**Acceptance Scenarios**:

1. **Given** debug mode is enabled, **When** any tool acquires a database connection, **Then** debug logs show: "DB connection pool: 3/10 active, acquired in 12ms"
2. **Given** a database query executes, **When** viewing debug logs, **Then** query timing is displayed: "Query execution: SELECT FROM speeches WHERE id=$1 - 45ms"
3. **Given** connection pool is near capacity, **When** requesting a new connection, **Then** debug logs show: "DB connection pool: 9/10 active, waited 250ms for available connection"
4. **Given** a database operation fails and retries, **When** viewing debug logs, **Then** retry attempts are logged: "DB query failed (timeout), retry 1/3 in 100ms"
5. **Given** connection metrics are logged, **When** administrator analyzes multiple operations, **Then** trends are identifiable: "Average connection acquisition: 15ms, 90th percentile: 85ms"

---

### Edge Cases

- What happens if ctx.debug() is called with very large variable values (e.g., full speech text 50KB+)? (Should truncate to 1KB with "...truncated" suffix)
- How does debug logging behave when exceptions occur mid-operation? (Should log exception type and message without full stack trace)
- What if debug() is called with sensitive data (passwords, API keys, tokens)? (Must detect and redact: "api_key=***REDACTED***")
- How does debug logging perform with high-frequency calls (100+ per second)? (Should not throttle but warn if overhead >1%)
- What if client requests debug mode but server doesn't support ctx.debug()? (Graceful degradation - no errors)
- How are nested operations logged (tool calls service calls storage)? (Should use hierarchical prefixes: "tool.service.method")

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All MCP tools MUST support debug logging via ctx.debug() method
- **FR-002**: Debug logs MUST include variable names and current values at key execution points
- **FR-003**: Debug logs MUST include timing metrics showing operation duration in milliseconds
- **FR-004**: Debug logs MUST NOT appear in production output unless client explicitly enables debug mode
- **FR-005**: Debug logs MUST use structured format with consistent key-value syntax
- **FR-006**: Debug logs MUST include execution context information (function name, operation stage)
- **FR-007**: Sensitive data (passwords, tokens, API keys, secrets) MUST be automatically detected and redacted in debug logs
- **FR-008**: Debug mode MUST be controlled per-client request, not via global server configuration
- **FR-009**: Debug logs MUST be visible in MCP Inspector's debug panel when debug mode is enabled
- **FR-010**: Long variable values (>1KB) MUST be truncated with clear indication of truncation
- **FR-011**: Debug logging MUST gracefully handle cases where ctx object is unavailable
- **FR-012**: Debug logs MUST NOT cause tool execution to fail if debug() call throws an error

### Non-Functional Requirements

- **NFR-001**: Debug logging overhead MUST NOT exceed 0.1% of total operation time when debug mode is disabled
- **NFR-002**: Debug logs MUST appear in client within 500ms of the actual logged event
- **NFR-003**: Debug logging code MUST be maintainable and not obscure business logic
- **NFR-004**: Debug message formatting MUST be consistent across all tools
- **NFR-005**: Debug logging MUST NOT impact memory usage by more than 5% during operation execution

### Key Entities

- **Debug Context**: FastMCP Context object with debug() method that accepts message strings
- **Debug Message**: Structured string with key-value pairs showing variable states and timing
- **Timing Metric**: Duration measurement in milliseconds for an operation or operation stage
- **Execution Context**: Function name, operation stage, and call hierarchy for a debug log entry
- **Sensitive Data Pattern**: List of field name patterns to detect and redact (password, token, key, secret, api_key)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers identify performance bottlenecks within 5 minutes of enabling debug mode, with zero false investigations (100% accuracy)
- **SC-002**: Debug logs contain actionable information (specific variable states, accurate timing metrics) in 100% of logged events
- **SC-003**: Performance overhead when debug mode is disabled is measured at <0.1% in all tool operations
- **SC-004**: Debug logs are visible and correctly formatted in MCP Inspector debug panel in 100% of test cases
- **SC-005**: Support team resolves 80%+ of user-reported issues using debug logs alone, without requiring code changes or database access
- **SC-006**: Zero instances of sensitive data leakage in debug logs during security audit
- **SC-007**: Debug logging works correctly with all existing tools (search, fetch, ingest) with zero compatibility issues
- **SC-008**: Debug logs provide sufficient detail to diagnose root cause in 90%+ of reported performance/quality issues
- **SC-009**: Time to diagnose production issues reduced by 50% compared to pre-debug-logging baseline

## Dependencies *(mandatory)*

- FastMCP 2.0+ with Context.debug() API support
- MCP Inspector for testing debug log visualization
- Existing MCP tools: search_hansard_speeches, fetch_hansard_speech, ingest_hansard_speech
- Python time module (time.perf_counter()) for high-resolution timing
- Existing service layer: VectorStoreService, MetadataStore, ChunkingService

## Assumptions *(mandatory)*

- MCP clients that support debug mode will request debug logs via appropriate protocol mechanism
- FastMCP Context.debug() gracefully handles cases where debug is not supported by client
- Debug logs are intended for development and support, not end users
- Timing overhead of time.perf_counter() is negligible (<1 microsecond per call)
- Structured key-value format (e.g., "key=value, key2=value2") is sufficient for debug needs
- Debug logs do not need to persist beyond the current operation (no log file storage)
- Sensitive data can be detected via field name patterns (password, token, key, secret, api_key)

## Constraints *(mandatory)*

- MUST use existing FastMCP Context.debug() API without modifications
- MUST NOT add more than 0.1% performance overhead when debug mode is disabled
- MUST NOT break existing tool functionality or automated tests
- MUST NOT require database schema changes or new infrastructure
- MUST NOT log full stack traces (use exception type and message only)
- Debug messages MUST be concise (<1KB per message) to avoid MCP protocol overhead
- MUST NOT use Python's built-in logging module as primary debug mechanism (use ctx.debug() for MCP visibility)

## Out of Scope

- Custom debug log viewers or UI components (rely on MCP Inspector)
- Debug log persistence to files or databases
- Debug log aggregation across multiple operations or time windows
- User-configurable debug verbosity levels (e.g., DEBUG, TRACE, VERBOSE)
- Debug logging for background jobs or scheduled tasks (focus on interactive MCP tool calls)
- Performance profiling or flame graphs (debug logs provide timing, not detailed profiles)
- Automatic anomaly detection in debug logs
- Debug log export or sharing functionality
- Real-time streaming of debug logs to external monitoring systems
- Custom filtering or search within debug logs (rely on client capabilities)
