# Research: Bulk Markdown Directory Ingestion

**Feature**: 013-bulk-markdown-ingestion
**Date**: 2025-10-24
**Purpose**: Research technical approaches for batch file processing, progress reporting, and error isolation

## Key Research Questions

1. How to efficiently discover and process files in a directory?
2. How to report progress for long-running batch operations?
3. How to isolate errors so one failure doesn't stop the entire batch?
4. How to handle file pattern filtering (glob patterns)?
5. How to prevent accidental processing of too many files (safety mechanism)?

## Research Findings

### 1. File Discovery and Processing

**Decision**: Use Python's `pathlib.Path.glob()` for file discovery

**Rationale**:
- Built-in to Python standard library (no additional dependencies)
- Supports glob patterns (*, **, ?, [abc]) for filtering
- Returns Path objects that work seamlessly with file operations
- More modern and intuitive than `os.listdir()` or `glob.glob()`
- Non-recursive by default (matches requirement FR-011)

**Alternatives Considered**:
- `os.listdir()` + manual filtering: More verbose, requires manual pattern matching
- `glob.glob()`: Returns strings instead of Path objects, less type-safe
- `os.walk()`: Recursive by default, would require additional logic to prevent

**Implementation Pattern**:
```python
from pathlib import Path

def discover_files(directory: str, pattern: str = "*.md") -> List[Path]:
    """Discover markdown files matching pattern in directory."""
    dir_path = Path(directory)

    # Validate directory exists
    if not dir_path.exists() or not dir_path.is_dir():
        raise ValueError(f"Directory not found or not a directory: {directory}")

    # Discover files matching pattern (non-recursive)
    files = list(dir_path.glob(pattern))

    # Filter out directories (keep only files)
    return [f for f in files if f.is_file()]
```

---

### 2. Progress Reporting

**Decision**: Use FastMCP's `ctx.report_progress()` with batched updates

**Rationale**:
- Built-in to FastMCP 2.14.0+ (already required by Feature 006)
- Provides standardized progress reporting interface for MCP clients
- Supports both absolute (current/total) and percentage-based reporting
- Client applications can display progress bars or percentage indicators
- Batching updates (every N files) prevents overwhelming slow clients

**Alternatives Considered**:
- Custom progress callback: Would require non-standard client implementation
- Logging only: No structured progress data, harder for clients to display
- No progress reporting: Poor UX for large batches (requirement P2)

**Implementation Pattern**:
```python
async def process_batch(files: List[Path], ctx: Context) -> BatchSummary:
    """Process files with progress reporting."""
    total_files = len(files)

    for i, file_path in enumerate(files, 1):
        # Process file...
        result = await process_single_file(file_path)

        # Report progress every file (or batch every N files for performance)
        if i % 1 == 0:  # Report every file
            await ctx.report_progress(i, total_files)

    return summary
```

**Progress Batching Strategy**:
- For < 20 files: Report after each file (immediate feedback)
- For 20-100 files: Report every 5 files (balance between feedback and overhead)
- For > 100 files: Report every 10 files (reduce overhead)

---

### 3. Error Isolation

**Decision**: Use try-except blocks around individual file processing with error accumulation

**Rationale**:
- Each file's ingestion is independent (database transactions are per-file from Feature 012)
- Catching exceptions per file allows batch to continue
- Failed files can be logged and reported in summary
- No special framework or library needed - standard Python exception handling
- Matches requirement FR-003 (continue on failure)

**Alternatives Considered**:
- Fail-fast approach: Would violate FR-003 requirement
- Multiprocessing with separate processes: Overkill for sequential processing, adds complexity
- Database savepoints: Already handled by Feature 012's transaction logic

**Implementation Pattern**:
```python
async def process_batch(files: List[Path]) -> BatchSummary:
    """Process files with error isolation."""
    successes: List[IngestionResult] = []
    failures: List[Dict[str, Any]] = []

    for file_path in files:
        try:
            result = await ingest_markdown_file(str(file_path), ...)
            successes.append(result)
        except Exception as e:
            failures.append({
                "file": file_path.name,
                "error_type": type(e).__name__,
                "error_message": str(e)
            })

    return BatchSummary(
        total_files=len(files),
        success_count=len(successes),
        failure_count=len(failures),
        failures=failures
    )
```

---

### 4. File Pattern Filtering

**Decision**: Use glob patterns with `pathlib.Path.glob()` (from Finding #1)

**Rationale**:
- Glob patterns are familiar to administrators (used in shells: `*.md`, `hansard-*.md`)
- Native support in pathlib without additional dependencies
- Flexible enough for common use cases (prefix, suffix, wildcards)
- No regex complexity for simple filtering needs

**Supported Patterns**:
- `*.md` - All markdown files
- `speech-*.md` - Files starting with "speech-"
- `2024-*.md` - Files starting with "2024-"
- `*.txt` - Different file extension
- `*` - All files (default to `*.md` for safety)

**Pattern Validation**:
- Accept any valid glob pattern
- Provide helpful error if pattern is invalid
- Default to `*.md` if no pattern specified
- Document pattern syntax in tool description

---

### 5. Safety Mechanism (Max File Limit)

**Decision**: Implement configurable `max_files` parameter with default of 100

**Rationale**:
- Prevents accidental processing of entire filesystem if wrong directory specified
- 100 is reasonable default for typical batch sizes (meets use case of 64 files)
- Can be overridden for larger batches (e.g., 500 files)
- Fail-fast validation before processing starts (check file count early)
- Matches requirement FR-007

**Alternatives Considered**:
- No limit: Dangerous, could accidentally process thousands of files
- Fixed limit: Too restrictive, different use cases have different needs
- Confirm prompt: Not suitable for programmatic/MCP tool usage

**Implementation Pattern**:
```python
def validate_file_count(files: List[Path], max_files: int = 100) -> None:
    """Validate file count is within safety limit."""
    if len(files) > max_files:
        raise ValueError(
            f"Safety limit exceeded: Found {len(files)} files, "
            f"max allowed is {max_files}. "
            f"Increase max_files parameter if this is intentional."
        )
```

---

## Technology Decisions

### Core Dependencies

All functionality can be implemented using **existing dependencies** from Feature 012:

- **Python 3.11+**: Already required for Cloud Run compatibility
- **Pydantic v2**: For input validation and result models
- **FastMCP 2.14.0+**: For MCP tool registration and progress reporting
- **pathlib**: Standard library (Python built-in)
- **asyncio**: Standard library (already used by Feature 012)

**No new dependencies required** ✅

### Integration with Feature 012

**Decision**: Call `ingest_markdown_file()` directly for each file

**Rationale**:
- Reuses all validation, parsing, chunking, and storage logic
- No code duplication
- Consistent error handling and security (admin auth)
- Transaction boundaries are correct (one transaction per file)
- Progress reporting can wrap the single-file tool

**Integration Pattern**:
```python
from tools.ingest_markdown_file import ingest_markdown_file

async def bulk_ingest(directory: str, ctx: Context) -> BatchSummary:
    files = discover_files(directory, pattern)

    for file_path in files:
        result = await ingest_markdown_file(
            file_path=str(file_path),
            duplicate_policy=duplicate_policy,
            validate_path=validate_path,
            ctx=ctx  # Pass context for auth and progress
        )
```

---

## Performance Considerations

### Expected Performance

Based on Feature 012 single-file ingestion:
- Average file size: 1000 words (from test data)
- Estimated processing time: ~5-10 seconds per file (parsing + chunking + embedding + storage)
- Batch of 64 files: ~5-10 minutes total
- Meets SC-002: 10 files/minute target

### Bottlenecks

1. **Vertex AI embedding generation**: Slowest operation (API call latency)
2. **Database writes**: PostgreSQL inserts for metadata + embeddings
3. **Network latency**: Cloud SQL connection overhead

**Note**: These are the same bottlenecks as Feature 012 single-file ingestion. No optimization needed for bulk tool - the goal is to provide batch orchestration, not faster per-file processing.

### Scalability

- Sequential processing is acceptable for initial implementation (FR allows it)
- Could parallelize in future (out of scope per spec)
- Max 100 files default prevents resource exhaustion

---

## Error Handling Strategy

### Error Categories

1. **Pre-processing errors** (fail-fast):
   - Directory not found
   - Directory not readable
   - No files match pattern
   - File count exceeds safety limit

2. **Per-file errors** (isolate and continue):
   - File cannot be read (permissions)
   - Invalid YAML frontmatter
   - Validation errors (missing required fields)
   - Duplicate speech_id (based on policy)
   - Database errors (connection, constraint violations)
   - Embedding generation failures

3. **Batch-level errors** (report in summary):
   - Partial batch completion
   - List of all failed files with details

### Error Recovery

- **No automatic retry**: Administrator must fix files and re-run (per spec's "Out of Scope")
- **Clear error messages**: Include filename, error type, and specific message
- **Idempotent operation**: Re-running batch processes only remaining files (if duplicate_policy=skip)

---

## Security Considerations

**Decision**: Reuse admin authorization from Feature 012

**Rationale**:
- Bulk ingestion has same security requirements as single-file
- `require_admin_role()` validates JWT claims
- `validate_file_path()` prevents directory traversal
- All security controls inherit from base tool

**Additional Considerations**:
- Validate directory path is within allowed base directory
- Prevent directory traversal in pattern (e.g., `../../../etc/*`)
- Limit file count to prevent resource exhaustion (DoS)

---

## Testing Strategy

### Unit Tests

- File discovery with various patterns
- Progress reporting at different batch sizes
- Error isolation (continue on failure)
- Safety limit enforcement
- Summary report generation

### Integration Tests

- Full batch with mixed valid/invalid files
- Large batch with progress monitoring
- Directory with subdirectories (verify skipped)
- Various glob patterns

### Test Data

- Use converted files from `data/hansard_converted/` (64 real files)
- Create test fixtures with intentional errors
- Small batches (5-10 files) for fast tests

---

## Summary

All technical decisions can be implemented with **zero new dependencies**:
- ✅ File discovery: `pathlib.Path.glob()`
- ✅ Progress reporting: `ctx.report_progress()` from FastMCP
- ✅ Error isolation: Standard Python try-except
- ✅ Pattern filtering: Built-in glob patterns
- ✅ Safety limits: Simple count validation
- ✅ Integration: Direct calls to `ingest_markdown_file()`

Implementation is straightforward orchestration layer over existing Feature 012 tool.
