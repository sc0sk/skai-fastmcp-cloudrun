# Requirements Validation Checklist: Debug Logging

**Feature**: 007-debug-logging
**Status**: Ready for Validation
**Created**: 2025-10-23

This checklist validates all functional requirements (FR), non-functional requirements (NFR), and success criteria (SC) defined in the feature specification.

---

## Functional Requirements Validation

### FR-001: All MCP tools MUST support debug logging via ctx.debug() method

**Validation Method**: Code inspection + Integration tests

**Test Cases**:
- `tests/integration/test_debug_logging.py::test_search_debug_logs_present`
- `tests/integration/test_debug_logging.py::test_fetch_debug_logs_present`
- `tests/integration/test_debug_logging.py::test_ingest_debug_logs_present`

**Validation Steps**:
1. Inspect `src/tools/search.py` - verify ctx.debug() calls present
2. Inspect `src/tools/fetch.py` - verify ctx.debug() calls present
3. Inspect `src/tools/ingest.py` - verify ctx.debug() calls present
4. Run integration tests - verify all tools call ctx.debug()

**Evidence**:
- [ ] search_hansard_speeches calls ctx.debug() at entry, stages, and exit
- [ ] fetch_hansard_speech calls ctx.debug() at entry, database lookup, and exit
- [ ] ingest_hansard_speech calls ctx.debug() at all major stages
- [ ] All integration tests pass

**Status**: ⬜ Pending

---

### FR-002: Debug logs MUST include variable names and current values at key execution points

**Validation Method**: MCP Inspector manual testing + Log content inspection

**Test Cases**:
- Manual testing with MCP Inspector (see quickstart.md)
- `tests/integration/test_debug_logging.py::test_debug_logs_contain_variables`

**Validation Steps**:
1. Enable debug mode in MCP Inspector
2. Run search tool with query="housing", party="LP"
3. Verify debug logs show: `query='housing'`, `party='LP'`
4. Run fetch tool with speech_id="ABC123"
5. Verify debug logs show: `speech_id='ABC123'`
6. Run ingest tool with speech data
7. Verify debug logs show: `speaker=...`, `date=...`, `chunk_count=...`

**Evidence**:
- [ ] Search tool logs query parameters with values
- [ ] Fetch tool logs speech_id with value
- [ ] Ingest tool logs speech metadata and chunk statistics
- [ ] Variable values accurate (match input parameters)

**Status**: ⬜ Pending

---

### FR-003: Debug logs MUST include timing metrics showing operation duration in milliseconds

**Validation Method**: MCP Inspector manual testing + Timing validation tests

**Test Cases**:
- Manual testing with MCP Inspector (see quickstart.md)
- `tests/integration/test_debug_logging.py::test_debug_timing_accurate`

**Validation Steps**:
1. Enable debug mode in MCP Inspector
2. Run any tool (search, fetch, ingest)
3. Verify debug logs contain timing messages: "(duration=XXXms)"
4. Verify timing format: decimal with 1 decimal place (e.g., "234.5ms")
5. Verify timing accuracy: ±10% of actual operation time

**Evidence**:
- [ ] All major operations logged with duration
- [ ] Duration format consistent: "(duration=123.4ms)"
- [ ] Timing accurate within ±10% tolerance
- [ ] TimingContext used for all timing measurements

**Status**: ⬜ Pending

---

### FR-004: Debug logs MUST NOT appear in production output unless client explicitly enables debug mode

**Validation Method**: MCP Inspector manual testing with debug mode off

**Test Cases**:
- Manual testing with MCP Inspector (debug mode disabled)
- `tests/integration/test_debug_logging.py::test_no_debug_when_disabled`

**Validation Steps**:
1. Disable debug mode in MCP Inspector (toggle off)
2. Run search, fetch, and ingest tools
3. Verify NO debug logs appear in debug panel
4. Verify tools still return correct results
5. Enable debug mode, run same tools
6. Verify debug logs NOW appear

**Evidence**:
- [ ] No debug logs when debug mode disabled
- [ ] Tools work correctly regardless of debug mode
- [ ] Debug logs appear when debug mode enabled
- [ ] FastMCP Context.debug() handles mode detection automatically

**Status**: ⬜ Pending

---

### FR-005: Debug logs MUST use structured format with consistent key-value syntax

**Validation Method**: Code inspection + Log format validation tests

**Test Cases**:
- `tests/unit/test_debug_utils.py::test_format_debug_message_basic`
- `tests/integration/test_debug_logging.py::test_debug_logs_structured`

**Validation Steps**:
1. Inspect all ctx.debug() calls in tools and services
2. Verify format: `[context]: [description] (key1=value1, key2=value2)`
3. Run integration tests to capture actual debug messages
4. Parse debug messages to verify consistent structure

**Evidence**:
- [ ] All debug messages follow template format
- [ ] Context prefix present (function/class name)
- [ ] Key-value pairs in parentheses
- [ ] format_debug_message() helper used consistently

**Status**: ⬜ Pending

---

### FR-006: Debug logs MUST include execution context information (function name, operation stage)

**Validation Method**: MCP Inspector manual testing + Log content inspection

**Test Cases**:
- Manual testing with MCP Inspector
- `tests/integration/test_debug_logging.py::test_debug_includes_context`

**Validation Steps**:
1. Enable debug mode in MCP Inspector
2. Run ingest tool (multi-stage operation)
3. Verify debug logs show context: `ingest_hansard_speech.validation`, `ingest_hansard_speech.chunking`, etc.
4. Verify nested operations show hierarchy: `VectorStoreService.generate_query_embedding`

**Evidence**:
- [ ] Function names present in debug logs
- [ ] Operation stages labeled (e.g., ".validation", ".chunking")
- [ ] Nested operations show parent context
- [ ] Context enables tracing execution flow

**Status**: ⬜ Pending

---

### FR-007: Sensitive data (passwords, tokens, API keys, secrets) MUST be automatically detected and redacted in debug logs

**Validation Method**: Security audit + Redaction tests

**Test Cases**:
- `tests/unit/test_debug_utils.py::test_sanitize_debug_data_password`
- `tests/unit/test_debug_utils.py::test_sanitize_debug_data_api_key`
- `tests/unit/test_debug_utils.py::test_sanitize_debug_data_token`
- `tests/integration/test_debug_logging.py::test_sensitive_data_redacted`

**Validation Steps**:
1. Review SENSITIVE_PATTERNS list in src/utils/debug.py
2. Test sanitize_debug_data() with sensitive field names
3. Verify redaction format: `api_key=***REDACTED***`
4. Run integration test with sensitive data in speech metadata
5. Verify sensitive values NOT present in debug logs

**Evidence**:
- [ ] SENSITIVE_PATTERNS includes common sensitive field names
- [ ] sanitize_debug_data() detects and redacts sensitive fields
- [ ] Redaction format consistent: `***REDACTED***`
- [ ] No sensitive data in debug logs during security audit

**Status**: ⬜ Pending

---

### FR-008: Debug mode MUST be controlled per-client request, not via global server configuration

**Validation Method**: Architecture review + Multi-client testing

**Test Cases**:
- Manual testing with multiple MCP Inspector instances
- Code review of debug mode detection logic

**Validation Steps**:
1. Review FastMCP Context.debug() implementation
2. Verify debug mode determined by client request (not env var)
3. Connect two MCP Inspector instances to same server
4. Enable debug in one, disable in other
5. Verify debug logs only appear in enabled client

**Evidence**:
- [ ] No global DEBUG environment variable or flag
- [ ] FastMCP Context.debug() checks per-request debug mode
- [ ] Multiple clients can have different debug settings
- [ ] Server supports concurrent debug/non-debug clients

**Status**: ⬜ Pending

---

### FR-009: Debug logs MUST be visible in MCP Inspector's debug panel when debug mode is enabled

**Validation Method**: MCP Inspector manual testing

**Test Cases**:
- Manual testing with MCP Inspector (see quickstart.md)

**Validation Steps**:
1. Start MCP server and MCP Inspector
2. Connect to server
3. Enable debug mode (toggle in UI)
4. Verify debug panel appears
5. Run any tool
6. Verify debug logs appear in debug panel (not main output)

**Evidence**:
- [ ] Debug logs visible in MCP Inspector debug panel
- [ ] Logs appear in real-time during execution
- [ ] Logs formatted correctly in UI
- [ ] Debug panel separate from tool results

**Status**: ⬜ Pending

---

### FR-010: Long variable values (>1KB) MUST be truncated with clear indication of truncation

**Validation Method**: Unit tests + Integration test with long values

**Test Cases**:
- `tests/unit/test_debug_utils.py::test_format_debug_message_long_value`
- `tests/integration/test_debug_logging.py::test_long_values_truncated`

**Validation Steps**:
1. Test sanitize_debug_data() with 2KB string value
2. Verify truncation at 1KB with "...truncated" suffix
3. Run ingest tool with 50KB speech text
4. Verify text not fully logged in debug (truncated)

**Evidence**:
- [ ] sanitize_debug_data() truncates values >1KB
- [ ] Truncation suffix: "...truncated"
- [ ] Full speech text not logged (only length: `text_length=50000`)
- [ ] Unit tests verify truncation behavior

**Status**: ⬜ Pending

---

### FR-011: Debug logging MUST gracefully handle cases where ctx object is unavailable

**Validation Method**: Unit tests + Code inspection

**Test Cases**:
- `tests/unit/test_debug_utils.py::test_timing_context_with_none_ctx`
- `tests/integration/test_debug_logging.py::test_debug_with_none_ctx`

**Validation Steps**:
1. Review all ctx.debug() calls - verify `if ctx:` guard
2. Test TimingContext with ctx=None
3. Verify no AttributeError or NoneType errors
4. Run tools with ctx=None parameter
5. Verify tools complete successfully

**Evidence**:
- [ ] All ctx.debug() calls guarded with `if ctx:`
- [ ] TimingContext handles ctx=None gracefully
- [ ] No errors when ctx=None
- [ ] Tools work correctly without ctx

**Status**: ⬜ Pending

---

### FR-012: Debug logs MUST NOT cause tool execution to fail if debug() call throws an error

**Validation Method**: Error injection tests

**Test Cases**:
- `tests/integration/test_debug_logging.py::test_debug_error_resilience`

**Validation Steps**:
1. Mock ctx.debug() to raise exception
2. Run tool with error-throwing ctx.debug()
3. Verify tool completes successfully despite debug error
4. Verify tool result correct (debug error doesn't affect logic)

**Evidence**:
- [ ] Tools complete successfully when ctx.debug() raises error
- [ ] Tool results correct despite debug errors
- [ ] Error logged but doesn't propagate
- [ ] Debug logging failures don't break operations

**Status**: ⬜ Pending

---

## Non-Functional Requirements Validation

### NFR-001: Debug logging overhead MUST NOT exceed 0.1% of total operation time when debug mode is disabled

**Validation Method**: Performance benchmarks

**Test Cases**:
- `tests/performance/test_debug_overhead.py::test_search_debug_overhead`
- `tests/performance/test_debug_overhead.py::test_fetch_debug_overhead`
- `tests/performance/test_debug_overhead.py::test_ingest_debug_overhead`

**Measurement Method**:
1. Run 100 iterations of each tool with ctx=None (debug disabled)
2. Measure baseline execution time
3. Run 100 iterations with mock ctx (debug calls present but no-op)
4. Measure debug-enabled execution time
5. Calculate overhead percentage: ((debug_time - baseline_time) / baseline_time) * 100

**Expected Results**:
- Search tool overhead: <0.1%
- Fetch tool overhead: <0.1%
- Ingest tool overhead: <0.1%

**Actual Results**:
- [ ] Search tool: ___% (expected: <0.1%)
- [ ] Fetch tool: ___% (expected: <0.1%)
- [ ] Ingest tool: ___% (expected: <0.1%)

**Status**: ⬜ Pending

---

### NFR-002: Debug logs MUST appear in client within 500ms of the actual logged event

**Validation Method**: Manual timing measurement

**Measurement Method**:
1. Enable debug mode in MCP Inspector
2. Run tool and start timer when operation begins
3. Observe when first debug log appears in debug panel
4. Measure latency between operation start and first log
5. Verify <500ms for all operations

**Expected Results**:
- First debug log appears <500ms after operation start
- Debug logs appear in real-time during operation
- No significant delay between log generation and display

**Actual Results**:
- [ ] Search tool: ___ms (expected: <500ms)
- [ ] Fetch tool: ___ms (expected: <500ms)
- [ ] Ingest tool: ___ms (expected: <500ms)

**Status**: ⬜ Pending

---

### NFR-003: Debug logging code MUST be maintainable and not obscure business logic

**Validation Method**: Code review

**Review Criteria**:
1. Debug logging code clearly separated from business logic
2. TimingContext usage doesn't obscure operation flow
3. Debug messages concise and readable
4. No complex debug logic intertwined with business logic

**Review Checklist**:
- [ ] Business logic readable despite debug logging
- [ ] Debug code uses utilities (not inline complexity)
- [ ] TimingContext usage clean and clear
- [ ] Debug messages self-explanatory

**Status**: ⬜ Pending

---

### NFR-004: Debug message formatting MUST be consistent across all tools

**Validation Method**: Code inspection + Format validation tests

**Test Cases**:
- `tests/integration/test_debug_logging.py::test_debug_format_consistent`

**Validation Steps**:
1. Extract all debug messages from integration tests
2. Parse message format
3. Verify all follow template: `[context]: [description] (key=value, ...)`
4. Verify consistent key naming across tools

**Review Checklist**:
- [ ] All messages use format_debug_message() helper
- [ ] Timing messages use TimingContext (consistent format)
- [ ] Key names consistent (e.g., "duration" not "time" or "elapsed")
- [ ] Context prefixes follow naming convention

**Status**: ⬜ Pending

---

### NFR-005: Debug logging MUST NOT impact memory usage by more than 5% during operation execution

**Validation Method**: Memory profiling

**Measurement Method**:
1. Use memory_profiler to measure baseline memory usage
2. Run operation with debug disabled
3. Measure peak memory usage
4. Run operation with debug enabled
5. Calculate memory overhead percentage

**Expected Results**:
- Memory overhead <5% for all operations

**Actual Results**:
- [ ] Search tool: ___% (expected: <5%)
- [ ] Fetch tool: ___% (expected: <5%)
- [ ] Ingest tool: ___% (expected: <5%)

**Status**: ⬜ Pending

---

## Success Criteria Validation

### SC-001: Developers identify performance bottlenecks within 5 minutes of enabling debug mode, with zero false investigations (100% accuracy)

**Validation Method**: User testing with planted bottlenecks

**Test Scenario**:
1. Introduce artificial delay in embedding generation (3x slower)
2. Ask developer to identify bottleneck using debug logs
3. Measure time to identification
4. Verify correct bottleneck identified

**Acceptance Criteria**:
- Developer identifies bottleneck in <5 minutes
- Correct stage identified (embedding, not chunking or storage)
- No false positives (developer doesn't investigate wrong stages)

**Results**:
- [ ] Time to identification: ___ minutes (expected: <5)
- [ ] Correct stage identified: Yes/No
- [ ] False investigations: ___ (expected: 0)

**Status**: ⬜ Pending

---

### SC-002: Debug logs contain actionable information (specific variable states, accurate timing metrics) in 100% of logged events

**Validation Method**: Manual review of debug logs + Audit

**Validation Steps**:
1. Enable debug mode and run all tools
2. Collect all debug log messages
3. Review each message for actionability:
   - Does it show specific values (not just "processing...")?
   - Does it include timing where relevant?
   - Can developer take action based on this log?
4. Calculate percentage of actionable logs

**Acceptance Criteria**:
- 100% of debug logs contain actionable information
- No vague or useless messages (e.g., "doing something...")

**Results**:
- [ ] Total debug messages: ___
- [ ] Actionable messages: ___
- [ ] Percentage: ___% (expected: 100%)

**Status**: ⬜ Pending

---

### SC-003: Performance overhead when debug mode is disabled is measured at <0.1% in all tool operations

**Validation Method**: Performance benchmarks (same as NFR-001)

**Test Cases**:
- `tests/performance/test_debug_overhead.py` (all tests)

**Acceptance Criteria**:
- Search tool: <0.1% overhead
- Fetch tool: <0.1% overhead
- Ingest tool: <0.1% overhead

**Results**:
- [ ] Search tool: ___% ✅/❌
- [ ] Fetch tool: ___% ✅/❌
- [ ] Ingest tool: ___% ✅/❌

**Status**: ⬜ Pending

---

### SC-004: Debug logs are visible and correctly formatted in MCP Inspector debug panel in 100% of test cases

**Validation Method**: MCP Inspector manual testing (all scenarios in quickstart.md)

**Test Cases**:
1. Search tool with various parameters
2. Fetch tool with valid and invalid speech_id
3. Ingest tool with sample speech data
4. All tools with debug enabled/disabled

**Acceptance Criteria**:
- Debug logs appear in debug panel (not main output)
- Formatting preserved (key-value pairs readable)
- No garbled or malformed messages
- 100% of test cases show correct display

**Results**:
- [ ] Test cases run: ___
- [ ] Test cases passed: ___
- [ ] Success rate: ___% (expected: 100%)

**Status**: ⬜ Pending

---

### SC-005: Support team resolves 80%+ of user-reported issues using debug logs alone, without requiring code changes or database access

**Validation Method**: Simulated support scenarios

**Test Scenarios**:
1. "Search returns irrelevant results" → Check similarity scores in debug logs
2. "Ingest is slow" → Check timing breakdown in debug logs
3. "Fetch returns empty" → Check database lookup in debug logs
4. "Search returns no results" → Check query processing in debug logs

**Acceptance Criteria**:
- 80%+ of scenarios diagnosable using debug logs
- No need to modify code or query database directly

**Results**:
- [ ] Scenarios tested: ___
- [ ] Scenarios resolved: ___
- [ ] Success rate: ___% (expected: ≥80%)

**Status**: ⬜ Pending

---

### SC-006: Zero instances of sensitive data leakage in debug logs during security audit

**Validation Method**: Security audit with sensitive data test cases

**Test Cases**:
1. Ingest speech with api_key in metadata
2. Ingest speech with password in metadata
3. Ingest speech with auth_token in metadata
4. Search with sensitive query terms (should not be redacted)

**Acceptance Criteria**:
- Zero instances of actual sensitive values in logs
- Sensitive fields show "***REDACTED***"
- Non-sensitive data (query terms, speech content) not redacted

**Results**:
- [ ] Test cases run: ___
- [ ] Sensitive data leaks: ___ (expected: 0)
- [ ] Redactions correct: Yes/No

**Status**: ⬜ Pending

---

### SC-007: Debug logging works correctly with all existing tools (search, fetch, ingest) with zero compatibility issues

**Validation Method**: Integration tests + Manual testing

**Test Cases**:
- All integration tests in `tests/integration/test_debug_logging.py`
- Manual testing with MCP Inspector (all tools)

**Acceptance Criteria**:
- All tools work with debug enabled
- All tools work with debug disabled
- All tools work with ctx=None
- No errors or exceptions related to debug logging

**Results**:
- [ ] Integration tests passed: ___/___
- [ ] Manual tests passed: ___/___
- [ ] Compatibility issues: ___ (expected: 0)

**Status**: ⬜ Pending

---

### SC-008: Debug logs provide sufficient detail to diagnose root cause in 90%+ of reported performance/quality issues

**Validation Method**: Simulated issue scenarios + Root cause analysis

**Test Scenarios**:
1. Slow embedding generation → Root cause: Vertex AI API latency
2. Low similarity scores → Root cause: Query mismatch
3. Connection timeouts → Root cause: Pool exhaustion
4. Missing results → Root cause: Filter too restrictive

**Acceptance Criteria**:
- 90%+ of scenarios lead to root cause identification
- Debug logs provide sufficient information without additional instrumentation

**Results**:
- [ ] Scenarios tested: ___
- [ ] Root causes identified: ___
- [ ] Success rate: ___% (expected: ≥90%)

**Status**: ⬜ Pending

---

### SC-009: Time to diagnose production issues reduced by 50% compared to pre-debug-logging baseline

**Validation Method**: Timed diagnosis with and without debug logging

**Test Method**:
1. Establish baseline: Diagnose issue without debug logs (only server logs)
2. Measure time to root cause identification
3. Diagnose same issue with debug logging enabled
4. Measure time to root cause identification
5. Calculate time reduction percentage

**Acceptance Criteria**:
- Diagnosis time reduced by ≥50% with debug logging

**Results**:
- [ ] Baseline diagnosis time: ___ minutes
- [ ] With debug diagnosis time: ___ minutes
- [ ] Time reduction: ___% (expected: ≥50%)

**Status**: ⬜ Pending

---

## Summary

### Completion Status

**Functional Requirements**: 0/12 validated
**Non-Functional Requirements**: 0/5 validated
**Success Criteria**: 0/9 validated

**Overall Progress**: 0/26 (0%)

### Sign-Off

This feature is ready for sign-off when:
- [ ] All Functional Requirements validated (12/12)
- [ ] All Non-Functional Requirements validated (5/5)
- [ ] All Success Criteria validated (9/9)
- [ ] No critical issues identified
- [ ] Documentation complete (spec.md, research.md, plan.md, tasks.md, quickstart.md)

**Feature Owner**: _______________
**Date**: _______________
**Signature**: _______________
