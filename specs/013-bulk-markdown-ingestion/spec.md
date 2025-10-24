# Feature Specification: Bulk Markdown Directory Ingestion

**Feature Branch**: `013-bulk-markdown-ingestion`
**Created**: 2025-10-24
**Status**: Draft
**Input**: User description: "Build bulk markdown directory ingestion tool with progress reporting, error isolation, and batch processing. Should process entire directories of markdown files (like data/hansard_converted with 64 files), report progress after each file, isolate errors so one failure doesn't stop the batch, and return detailed summary with success/failure counts. Builds on existing ingest_markdown_file tool from feature 012. Must support file pattern filtering, max file limits for safety, and detailed error reporting for each failed file."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bulk Directory Ingestion (Priority: P1)

An administrator needs to ingest a directory containing 64 converted Hansard markdown files into the database. They want to process all files in one operation rather than running 64 individual commands. The system should report progress as files are processed and provide a summary at the end.

**Why this priority**: This is the core value proposition - enabling batch processing of multiple files. Without this, administrators must manually ingest files one by one, which is error-prone and time-consuming.

**Independent Test**: Can be fully tested by pointing the tool at a directory with multiple markdown files and verifying all valid files are ingested with progress updates and final summary.

**Acceptance Scenarios**:

1. **Given** a directory with 10 valid markdown files, **When** administrator runs bulk ingestion on that directory, **Then** all 10 files are successfully ingested and summary shows "10 succeeded, 0 failed"
2. **Given** a directory with 5 valid and 2 invalid markdown files, **When** administrator runs bulk ingestion, **Then** 5 files succeed, 2 fail, and summary lists which files failed with error details
3. **Given** bulk ingestion is processing 20 files, **When** the 5th file fails validation, **Then** processing continues with files 6-20 and final summary reports the failure details

---

### User Story 2 - Progress Monitoring (Priority: P2)

An administrator ingesting a large batch of files (e.g., 100+ files) needs to monitor progress to ensure the operation is working and estimate completion time. They should see real-time updates as each file is processed.

**Why this priority**: Essential for user experience with large batches, but the core ingestion functionality (P1) works without it. Adds transparency and enables administrators to make informed decisions about waiting vs. doing other work.

**Independent Test**: Can be tested by starting a bulk ingestion of 20+ files and observing that progress updates appear after each file with current count and percentage.

**Acceptance Scenarios**:

1. **Given** bulk ingestion is processing 50 files, **When** each file completes, **Then** progress indicator shows current file number, total files, and percentage complete
2. **Given** bulk ingestion is running, **When** administrator checks status mid-operation, **Then** they can see how many files have been processed and how many remain
3. **Given** bulk ingestion encounters a slow file (large content), **When** processing that file, **Then** progress still updates to show the file is being processed (not stuck)

---

### User Story 3 - Selective File Filtering (Priority: P3)

An administrator has a directory with mixed file types (markdown, text, JSON) and only wants to ingest files matching a specific pattern (e.g., only files starting with "hansard-" or only "*.md" files). They need to filter which files get processed without manually moving files around.

**Why this priority**: Nice-to-have for flexibility, but not critical for the initial use case where the directory contains only the files to be ingested. The administrator can prepare a clean directory as a workaround.

**Independent Test**: Can be tested by creating a directory with 10 markdown files where 5 match pattern "speech-*.md" and verifying only those 5 are processed when pattern is specified.

**Acceptance Scenarios**:

1. **Given** a directory with files "speech-1.md", "notes.md", "speech-2.md", **When** administrator specifies pattern "speech-*.md", **Then** only the 2 files matching the pattern are ingested
2. **Given** a directory with 100 files, **When** administrator specifies pattern that matches 20 files, **Then** bulk ingestion processes exactly 20 files and summary reflects this
3. **Given** a directory with no files matching the specified pattern, **When** administrator runs bulk ingestion, **Then** operation completes immediately with message "No files matched pattern"

---

### Edge Cases

- What happens when directory contains 1000+ files (safety concern)?
- How does system handle files that are locked or being written by another process?
- What happens when disk space runs out mid-batch?
- How does system handle symbolic links or directory loops?
- What happens when a file is valid markdown but has duplicate speech_id with an already-ingested file?
- How does system handle very large files (e.g., 100MB markdown file)?
- What happens when administrator cancels operation mid-batch?
- How are file permissions errors handled (files administrator can't read)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a directory path as input and discover all markdown files within that directory
- **FR-002**: System MUST process each discovered file using the existing single-file ingestion logic from feature 012 (ingest_markdown_file)
- **FR-003**: System MUST continue processing remaining files when an individual file fails (error isolation)
- **FR-004**: System MUST report progress after each file is processed, including current file count and total file count
- **FR-005**: System MUST return a summary report containing success count, failure count, and list of failed files with error details
- **FR-006**: System MUST respect administrator-only access control (same security model as single-file ingestion)
- **FR-007**: System MUST support a maximum file limit parameter with default value of 100 files as a safety guard
- **FR-008**: System MUST support optional file pattern filtering (e.g., "*.md", "hansard-*.md") to select which files to process
- **FR-009**: System MUST validate directory exists and is readable before starting batch processing
- **FR-010**: System MUST provide detailed error information for each failed file (filename, error type, error message)
- **FR-011**: System MUST skip subdirectories and only process files in the specified directory (non-recursive)
- **FR-012**: System MUST handle duplicate speech_id errors gracefully according to configured duplicate policy (skip/error)
- **FR-013**: System MUST aggregate progress reporting to avoid overwhelming the client with updates (batch updates every 1-5 files)

### Key Entities *(include if feature involves data)*

- **BulkIngestionRequest**: Represents a single batch operation with directory path, file pattern filter, max file limit, and duplicate policy
- **FileIngestionResult**: Outcome for a single file within the batch (success/failure/skipped, speech_id, chunks created, error details if failed)
- **BulkIngestionSummary**: Aggregated results across all files in the batch (total files, success count, skipped count, failure count, list of failures, total chunks created)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Administrators can ingest 64 markdown files in a single command rather than 64 separate commands
- **SC-002**: System achieves average throughput of at least 10 files per minute over a complete batch (assuming average file size of 1000 words; performance goal, not hard requirement)
- **SC-003**: When 1 out of 20 files fails validation, the other 19 files are still successfully ingested
- **SC-004**: Administrators receive progress updates at least every 5 files during bulk ingestion
- **SC-005**: Error summary provides enough detail for administrators to identify and fix problematic files without re-reading all files
- **SC-006**: System prevents accidental processing of more than 100 files without explicit override (safety mechanism)
- **SC-007**: 95% of bulk ingestion operations complete without manual intervention over a 30-day production window (no hung processes or deadlocks requiring restart)

## Assumptions

- Bulk ingestion will primarily be used for initial data migration of 50-200 files at a time
- Files in the target directory are generally valid and follow the expected frontmatter format from feature 012 conversion script
- Network and database connectivity are stable during batch operations (no retry logic for transient failures)
- The directory structure is flat (no recursive subdirectory traversal needed)
- Progress reporting granularity of "per file" is sufficient (no need for per-chunk or percentage-within-file updates)
- Maximum expected file size is 50MB (no special handling for extremely large files)
- Concurrent bulk ingestion operations are rare (no conflict resolution between simultaneous batches)
- Symbolic links that point to regular files are followed and processed; symlinks to directories or broken symlinks are skipped with no error

## Dependencies

- **Feature 012**: Admin-protected markdown ingestion (ingest_markdown_file tool) - provides the single-file ingestion logic that bulk ingestion orchestrates
- **Cloud SQL PostgreSQL**: Database must be available and accept concurrent write operations
- **Vertex AI Embeddings**: Embedding service must handle batch requests efficiently
- **FastMCP Progress Reporting**: Requires FastMCP 2.14.0+ with ctx.report_progress() support for real-time updates

## Out of Scope

- Recursive directory traversal (subdirectories are skipped)
- Automatic retry of failed files (administrator must manually fix and re-run)
- Parallel processing of multiple files simultaneously (sequential processing only)
- Real-time file watching or incremental ingestion (batch operation is one-time, not continuous)
- Undo/rollback of partial batch (files already ingested remain in database even if batch fails later)
- Deduplication across multiple batch runs (duplicate detection is within a single batch only)
- File preprocessing or transformation (assumes files are already in correct format from feature 012 conversion)
- Cloud Storage or remote file access (local filesystem only)
- Graceful cancellation mid-batch (operation runs to completion or fails; already-ingested files remain in database)

