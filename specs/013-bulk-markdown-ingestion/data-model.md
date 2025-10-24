# Data Model: Bulk Markdown Directory Ingestion

**Feature**: 013-bulk-markdown-ingestion
**Date**: 2025-10-24
**Purpose**: Define data structures for bulk ingestion requests, results, and summaries

## Overview

This feature introduces **three new data models** for batch processing:

1. **BulkIngestionRequest**: Input parameters for batch operation
2. **FileIngestionResult**: Per-file outcome within batch
3. **BulkIngestionSummary**: Aggregated batch results

**Note**: No database schema changes required. All database operations delegate to Feature 012's `ingest_markdown_file()`.

---

## Entity Definitions

### 1. BulkIngestionRequest

**Purpose**: Captures all input parameters for a bulk ingestion operation

**Fields**:

| Field | Type | Required | Default | Validation | Description |
|-------|------|----------|---------|------------|-------------|
| `directory_path` | `str` | Yes | - | Must be existing directory | Absolute or relative path to directory containing markdown files |
| `file_pattern` | `str` | No | `"*.md"` | Valid glob pattern | Glob pattern to filter which files to process (e.g., `"hansard-*.md"`) |
| `max_files` | `int` | No | `100` | `>= 1` | Safety limit on maximum number of files to process |
| `duplicate_policy` | `str` | No | `"skip"` | `"skip" | "error" | "update"` | How to handle duplicate speech_id (passed to single-file tool) |
| `validate_path` | `bool` | No | `True` | - | Whether to validate file paths are within allowed base directory |

**Relationships**:
- None (input model only)

**Validation Rules**:
- `directory_path` MUST exist and be a directory
- `directory_path` MUST be readable by the process
- `file_pattern` MUST be a valid glob pattern (characters: `*`, `?`, `[`, `]`)
- `max_files` MUST be positive integer
- `duplicate_policy` MUST be one of the enum values

**Example**:
```python
BulkIngestionRequest(
    directory_path="/data/hansard_converted",
    file_pattern="*.md",
    max_files=100,
    duplicate_policy="skip",
    validate_path=True
)
```

---

### 2. FileIngestionResult

**Purpose**: Captures the outcome of processing a single file within a batch

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filename` | `str` | Yes | Name of the file (not full path, just basename) |
| `status` | `str` | Yes | Outcome: `"success"`, `"skipped"`, or `"failed"` |
| `speech_id` | `str` | No | Speech ID from frontmatter (if successful) |
| `chunks_created` | `int` | No | Number of embedding chunks created (if successful) |
| `error_type` | `str` | No | Exception class name (if failed, e.g., `"ValidationError"`) |
| `error_message` | `str` | No | Human-readable error description (if failed) |

**Relationships**:
- Contained in `BulkIngestionSummary.failed_files` list

**State Transitions**:
```
[Start] → Processing
    ├→ Success (status="success", speech_id + chunks_created populated)
    ├→ Skipped (status="skipped", e.g., duplicate with policy=skip)
    └→ Failed (status="failed", error_type + error_message populated)
```

**Validation Rules**:
- If `status="success"`: `speech_id` and `chunks_created` MUST be present
- If `status="failed"`: `error_type` and `error_message` MUST be present
- If `status="skipped"`: `error_message` MAY be present (explains why skipped)

**Example (Success)**:
```python
FileIngestionResult(
    filename="267506-2024-05-28-129006.md",
    status="success",
    speech_id="AUH_2024-05-28-p2.s1.per0.reps.u72",
    chunks_created=4
)
```

**Example (Failure)**:
```python
FileIngestionResult(
    filename="invalid-file.md",
    status="failed",
    error_type="ValidationError",
    error_message="Missing required field: speaker"
)
```

---

### 3. BulkIngestionSummary

**Purpose**: Aggregates results across all files in a batch operation

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `total_files` | `int` | Yes | Total number of files discovered matching pattern |
| `success_count` | `int` | Yes | Number of files successfully ingested |
| `skipped_count` | `int` | Yes | Number of files skipped (e.g., duplicates with skip policy) |
| `failed_count` | `int` | Yes | Number of files that failed processing |
| `total_chunks_created` | `int` | Yes | Sum of all chunks created across successful files |
| `failed_files` | `List[FileIngestionResult]` | Yes | Detailed results for each failed file |
| `processing_time_seconds` | `float` | No | Total time taken to process batch (for performance monitoring) |

**Relationships**:
- Contains list of `FileIngestionResult` objects (failures only, for brevity)

**Validation Rules**:
- `total_files` = `success_count` + `skipped_count` + `failed_count` (must balance)
- `len(failed_files)` = `failed_count` (consistency check)
- All counts MUST be non-negative
- `processing_time_seconds` MUST be positive if present

**Example**:
```python
BulkIngestionSummary(
    total_files=64,
    success_count=62,
    skipped_count=1,
    failed_count=1,
    total_chunks_created=248,
    failed_files=[
        FileIngestionResult(
            filename="corrupted-file.md",
            status="failed",
            error_type="YAMLError",
            error_message="Malformed YAML frontmatter at line 5"
        )
    ],
    processing_time_seconds=387.2
)
```

---

## Data Flow

```
[Input]
BulkIngestionRequest
    ↓
[Discovery]
Discover files matching pattern in directory
Validate count <= max_files
    ↓
[Processing Loop]
For each file:
    try:
        result = ingest_markdown_file(file)
        → FileIngestionResult(status="success")
    except Exception as e:
        → FileIngestionResult(status="failed")
    ↓
[Aggregation]
Collect all FileIngestionResult objects
Calculate totals (success/skip/fail counts)
Sum chunks_created
    ↓
[Output]
BulkIngestionSummary
```

---

## Integration with Feature 012

### Data Reuse

This feature **does NOT create new database entities**. All database operations are delegated to Feature 012:

- Speech metadata → `speeches` table (via `metadata_store.store_speech()`)
- Embedding chunks → `langchain_pg_embedding` table (via `vector_store.add_chunks()`)

### Input Transformation

```python
# Bulk request parameters
bulk_request = BulkIngestionRequest(
    directory_path="/data/hansard_converted",
    file_pattern="*.md",
    max_files=100,
    duplicate_policy="skip"
)

# Transform to single-file parameters
for file_path in discovered_files:
    single_file_result = await ingest_markdown_file(
        file_path=str(file_path),           # From discovery
        duplicate_policy=bulk_request.duplicate_policy,  # Pass through
        validate_path=bulk_request.validate_path,        # Pass through
        ctx=ctx                             # For auth & progress
    )
```

### Result Transformation

```python
# Single-file result (from Feature 012)
{
    "status": "success",
    "speech_id": "AUH_2024-05-28-p2.s1.per0.reps.u72",
    "chunks_created": 4,
    "message": "Ingested ... with 4 chunks"
}

# Transform to FileIngestionResult
FileIngestionResult(
    filename=file_path.name,
    status="success",
    speech_id=result["speech_id"],
    chunks_created=result["chunks_created"]
)
```

---

## Validation Strategy

### Input Validation

**Pydantic Model** for `BulkIngestionRequest`:
```python
from pydantic import BaseModel, Field, field_validator
from pathlib import Path

class BulkIngestionRequest(BaseModel):
    directory_path: str = Field(
        ...,
        description="Path to directory containing markdown files"
    )
    file_pattern: str = Field(
        default="*.md",
        description="Glob pattern to filter files (e.g., '*.md', 'hansard-*.md')"
    )
    max_files: int = Field(
        default=100,
        ge=1,
        description="Maximum number of files to process (safety limit)"
    )
    duplicate_policy: Literal["skip", "error", "update"] = Field(
        default="skip",
        description="How to handle duplicate speech_id"
    )
    validate_path: bool = Field(
        default=True,
        description="Whether to validate paths are within base directory"
    )

    @field_validator('directory_path')
    def validate_directory_exists(cls, v):
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Directory does not exist: {v}")
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {v}")
        return v
```

### Output Validation

**Pydantic Model** for `BulkIngestionSummary`:
```python
class FileIngestionResult(BaseModel):
    filename: str
    status: Literal["success", "skipped", "failed"]
    speech_id: Optional[str] = None
    chunks_created: Optional[int] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None

class BulkIngestionSummary(BaseModel):
    total_files: int = Field(ge=0)
    success_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    total_chunks_created: int = Field(ge=0)
    failed_files: List[FileIngestionResult] = Field(default_factory=list)
    processing_time_seconds: Optional[float] = Field(default=None, gt=0)

    @field_validator('failed_files')
    def validate_failed_files_count(cls, v, info):
        # Ensure failed_files list matches failed_count
        if 'failed_count' in info.data and len(v) != info.data['failed_count']:
            raise ValueError("failed_files length must match failed_count")
        return v
```

---

## Error Handling

### Error Categorization

| Category | Handling | Included in Summary |
|----------|----------|---------------------|
| **Pre-processing errors** | Raise immediately, stop batch | N/A (batch never starts) |
| **Per-file errors** | Catch, log, continue processing | Yes (in `failed_files`) |
| **Batch-level errors** | Should not occur (all handled per-file) | N/A |

### Pre-processing Errors

These errors **prevent batch from starting**:

1. `FileNotFoundError`: Directory does not exist
2. `NotADirectoryError`: Path is a file, not a directory
3. `PermissionError`: Directory is not readable
4. `ValueError`: No files match pattern
5. `ValueError`: File count exceeds `max_files` limit

**Response**: Raise exception immediately with clear error message

### Per-file Errors

These errors are **isolated to individual files**:

1. `FileNotFoundError`: File was deleted between discovery and processing
2. `PermissionError`: File is not readable
3. `ValidationError`: Invalid YAML frontmatter or missing required fields
4. `ValueError`: Duplicate speech_id with policy="error"
5. `DatabaseError`: Connection or constraint violation
6. `APIError`: Vertex AI embedding generation failure

**Response**: Catch exception, create `FileIngestionResult(status="failed")`, continue with next file

---

## Performance Considerations

### Memory Management

- Process files **sequentially** (one at a time)
- Do NOT load all files into memory simultaneously
- Each file's chunks are sent to database immediately (not batched across files)
- Summary object holds only metadata (filenames + error messages), not full content

### Expected Memory Usage

- **Per file**: ~2-5 MB (markdown content + embeddings before storage)
- **Batch of 100 files**: ~10-50 MB peak (processing one file at a time)
- **Summary result**: ~50-100 KB (metadata only, not speech content)

### Scalability

Current design handles up to 100 files per batch by default:
- **64 files** (current use case): ✅ Well within limits
- **100 files**: ✅ Default safety limit
- **500 files**: Requires explicit `max_files` override
- **1000+ files**: May need chunking into multiple batches (out of scope)

---

## Testing Data

### Valid Test Cases

1. **Empty directory**: 0 files, summary shows all zeros
2. **Single file**: 1 file, verify transforms correctly
3. **Small batch**: 5 files, all valid
4. **Mixed batch**: 10 files, 7 valid + 3 invalid
5. **Pattern filtering**: 20 files, pattern matches 8
6. **Duplicate handling**: Files with duplicate speech_ids

### Invalid Test Cases

1. **Directory not found**: Raise FileNotFoundError
2. **Path is a file**: Raise NotADirectoryError
3. **No matching files**: Raise ValueError or return empty summary
4. **Exceeds max_files**: Raise ValueError
5. **Permission denied**: Raise PermissionError

### Test Data Location

- Use existing converted files: `/home/user/skai-fastmcp-cloudrun/data/hansard_converted/` (64 files)
- Create test fixtures: `/home/user/skai-fastmcp-cloudrun/tests/fixtures/bulk_ingestion/`
  - `valid/` - 5-10 valid files
  - `invalid/` - Files with various errors
  - `mixed/` - Combination of valid and invalid

---

## Summary

Three new data models support bulk ingestion:

1. **BulkIngestionRequest**: Input parameters (directory, pattern, limits)
2. **FileIngestionResult**: Per-file outcome (success/skip/fail)
3. **BulkIngestionSummary**: Aggregated results (counts, failures list)

**Key Design Principles**:
- ✅ No new database entities (delegates to Feature 012)
- ✅ Pydantic validation for all models
- ✅ Error isolation (per-file failures don't stop batch)
- ✅ Memory efficient (sequential processing)
- ✅ Detailed error reporting (failed_files list)
