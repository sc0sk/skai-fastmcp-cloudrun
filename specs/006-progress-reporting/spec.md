# Feature Specification: MCP Progress Reporting

**Feature Branch**: `006-progress-reporting`
**Created**: 2025-10-23
**Status**: Draft
**Input**: "Implement MCP progress reporting for long-running operations like speech ingestion to provide real-time feedback to users through MCP clients"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin Ingests Single Speech with Progress Feedback (Priority: P1)

A system administrator using MCP Inspector needs to ingest a new parliamentary speech into the database. The operation takes 8-12 seconds (parsing, chunking, embedding generation, storage), and the admin wants to see real-time progress updates to confirm the operation is working and hasn't stalled.

**Why this priority**: This is the MVP - long-running operations without feedback create user anxiety and confusion. The ingest operation is our primary long-running tool, making it the ideal first candidate for progress reporting. This establishes the pattern for all future long-running operations.

**Independent Test**: Can be fully tested by invoking the ingest tool via MCP Inspector with a sample speech, observing progress updates in the UI (percentage and stage descriptions), verifying the progress bar updates at least 5 times during execution, and confirming the speech is successfully stored with 100% completion reported.

**Acceptance Scenarios**:

1. **Given** an admin opens MCP Inspector and selects the ingest tool, **When** they provide speech data and execute the tool, **Then** progress updates appear within 1 second showing "Validating speech..." at 0%
2. **Given** the tool is processing, **When** it moves between stages, **Then** progress updates show clear stage transitions: Validation (0-20%), Chunking (20-40%), Embedding (40-70%), Vector Storage (70-90%), Metadata Storage (90-100%)
3. **Given** the embedding generation stage is running, **When** processing multiple chunks, **Then** progress percentage increases smoothly from 40% to 70% based on chunks processed
4. **Given** the operation completes successfully, **When** storage finishes, **Then** final progress update shows 100% with success message
5. **Given** MCP Inspector displays progress, **When** watching the progress bar, **Then** the bar fills smoothly without jumping backwards or stalling
6. **Given** the client doesn't support progress tokens, **When** the tool executes, **Then** the operation completes successfully without errors related to progress reporting

---

### User Story 2 - Data Manager Bulk Ingests Multiple Speeches (Priority: P2)

A data manager running a CLI script needs to ingest 20 parliamentary speeches sequentially. They want to see progress for each individual speech (micro-progress) and overall batch progress (macro-progress) to estimate completion time and identify any problematic speeches.

**Why this priority**: Builds on P1 by addressing batch operations. While not MVP, bulk ingestion is a common administrative task. This scenario validates that progress reporting scales to multiple operations and helps users monitor longer-running batch jobs.

**Independent Test**: Can be tested by creating a Python script that ingests 20 speeches sequentially, verifying per-speech progress updates appear for each operation, confirming batch-level progress shows "Processing speech 3/20...", and validating total time estimation becomes accurate after processing 3-5 speeches.

**Acceptance Scenarios**:

1. **Given** a script is ingesting 20 speeches, **When** processing the first speech, **Then** progress shows "Speech 1/20: Validating speech... 0%" and updates through all stages
2. **Given** the first speech completes, **When** the second speech begins, **Then** progress resets to 0% for the new speech with updated counter "Speech 2/20..."
3. **Given** 5 speeches have been processed, **When** displaying estimated completion time, **Then** time estimate is within ±20% of actual remaining time
4. **Given** a speech ingestion fails with an error, **When** the batch continues, **Then** error is logged with speech identifier and batch continues with next speech
5. **Given** all 20 speeches complete, **When** script finishes, **Then** summary shows: "20/20 speeches ingested successfully, 0 errors, total time: X minutes"

---

### User Story 3 - Researcher Monitors Large Search Result Processing (Priority: P3)

A researcher using Claude Desktop performs a search that returns 150 matching speech chunks. The system needs to fetch full speech records for each chunk and deduplicate them, which takes 5-8 seconds. The researcher wants progress updates to understand the operation is actively processing their query.

**Why this priority**: Future enhancement that applies progress reporting to read operations. Lower priority because search/fetch operations are typically faster than ingestion, but provides value for large result sets and demonstrates progress reporting across different operation types.

**Independent Test**: Can be tested by performing a search query that returns 100+ chunks, verifying progress updates show "Processing result 45/150..." during result processing, confirming progress appears only when processing takes >5 seconds (faster queries skip progress), and validating final results are returned correctly.

**Acceptance Scenarios**:

1. **Given** a search returns 150 chunks, **When** fetching full speeches, **Then** progress shows "Fetching speech records... 0%" and updates every 10 speeches processed
2. **Given** duplicate speeches are being deduplicated, **When** processing the deduplication, **Then** progress shows "Deduplicating results... 70%" with percentage based on records processed
3. **Given** the search completes quickly (<5 seconds), **When** returning results, **Then** no progress updates are shown to avoid UI flicker
4. **Given** the operation takes >5 seconds, **When** progress is reported, **Then** updates occur at meaningful intervals (every 10% or every 15 results, whichever is less frequent)
5. **Given** Claude Desktop displays search results, **When** progress completes, **Then** final results appear with correct deduplication and sorting

---

### Edge Cases

- What happens if the client connects but doesn't send a progressToken? (Operation must complete successfully without progress)
- What if progress is updated too frequently (>10 times per second)? (Should throttle to prevent UI spam)
- How does progress behave if an operation fails mid-stage? (Should report error without showing 100%)
- What if embedding generation fails for one chunk in a multi-chunk operation? (Should report partial progress and error)
- How does progress work for nested operations (ingestion calls vector store calls embeddings)? (Should show combined progress weighted by operation time)
- What if the operation completes faster than expected and stages are skipped? (Progress should jump forward, never backward)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The ingest_hansard_speech tool MUST report progress during speech processing operations
- **FR-002**: Progress updates MUST include percentage completion from 0 to 100
- **FR-003**: Multi-stage operations MUST report progress for each major stage with clear stage names
- **FR-004**: Progress reporting MUST work when client provides progressToken in tool call
- **FR-005**: Progress reporting MUST NOT cause errors when client does not provide progressToken
- **FR-006**: Progress updates MUST occur at meaningful milestones, not on every minor operation (minimum 5% progress change between updates)
- **FR-007**: Operations MUST always report 100% progress upon successful completion
- **FR-008**: Progress messages MUST use user-friendly stage descriptions (e.g., "Chunking text..." not "Stage 2/5")
- **FR-009**: All operations expected to take longer than 5 seconds MUST report progress
- **FR-010**: Progress MUST be reported using the FastMCP Context.report_progress() API
- **FR-011**: Operations MUST complete successfully regardless of whether progress reporting is supported by the client
- **FR-012**: Progress reporting MUST be testable and verifiable via MCP Inspector

### Non-Functional Requirements

- **NFR-001**: Progress reporting overhead MUST NOT exceed 1% of total operation time
- **NFR-002**: Progress updates MUST appear in the client UI within 1 second of the actual operation progress
- **NFR-003**: Progress percentages MUST be accurate within ±5% of actual completion
- **NFR-004**: Progress reporting code MUST be maintainable and not tightly couple progress logic to business logic
- **NFR-005**: Error messages related to progress reporting MUST clearly distinguish progress failures from operation failures

### Key Entities

- **Progress Context**: FastMCP Context object with report_progress() method that accepts progress (float) and optional total (float)
- **Progress Token**: Client-provided token in tool call request that enables progress reporting for that specific invocation
- **Progress Stage**: Logical phase of operation (Validation, Chunking, Embedding, Storage) with defined percentage ranges
- **Progress Update**: Single report_progress() call with percentage and associated user-friendly message via ctx.info()
- **Long-Running Operation**: Any tool execution expected to take >5 seconds based on typical data volumes

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users see first progress update within 1 second of starting a long-running operation
- **SC-002**: Progress percentages are accurate within ±5% of actual operation completion at each stage
- **SC-003**: All operations taking longer than 5 seconds report progress with at least 5 distinct updates
- **SC-004**: Progress updates are visible and functional in MCP Inspector during testing
- **SC-005**: Operations complete successfully both with and without progressToken support, with zero progress-related errors
- **SC-006**: User satisfaction survey shows 4/5 or higher rating for statement "I always knew what the system was doing during long operations"
- **SC-007**: Zero crashes, exceptions, or operation failures caused by progress reporting code
- **SC-008**: Stage transition messages are clear and accurate, with 100% of test users able to identify current operation phase from progress message alone
- **SC-009**: Progress reporting adds less than 100ms overhead to total operation time for typical speech ingestion (8-12 seconds)

## Dependencies *(mandatory)*

- FastMCP 2.0+ with Context.report_progress() API support
- MCP Inspector for testing progress visualization
- Existing ingest_hansard_speech tool implementation (placeholder in src/tools/ingest.py)
- VectorStoreService.add_chunks() method for embedding generation stage
- MetadataStore.add_speech() method for final storage stage
- Client applications that support progressToken (MCP Inspector, Claude Desktop with MCP 2.0+)

## Assumptions *(mandatory)*

- MCP clients that support progress will send progressToken in tool requests when they want progress updates
- FastMCP Context.report_progress() gracefully handles cases where progressToken is not provided
- Operations can estimate progress reasonably based on current stage and items processed
- Embedding generation is the longest stage (40-70% of total time) and benefits most from granular progress
- Users prefer stage-based progress messages over raw percentage numbers
- Progress updates every 5-10% are sufficient to maintain user confidence without spamming the UI
- The ingest tool will be registered with FastMCP server (currently placeholder/CLI-only)

## Constraints *(mandatory)*

- MUST use existing FastMCP Context.report_progress() API without modifications
- MUST NOT add more than 100ms overhead to operation execution time
- MUST NOT break existing tool functionality or tests when progress code is added
- MUST NOT require database schema changes
- MUST work with both MCP Inspector (progressToken support) and Claude Desktop (may or may not support)
- Progress reporting code MUST be maintainable and not add significant complexity
- Error handling MUST prevent progress reporting failures from causing operation failures

## Out of Scope

- Custom progress UI components (rely on client default progress indicators)
- Progress persistence across server restarts or client disconnections
- Progress reporting for fast operations (<5 seconds) like search_hansard_speeches or fetch_hansard_speech
- Cancellation or pause/resume of long-running operations based on progress state
- Progress history or logging beyond standard operation logs
- User-configurable progress update frequency or verbosity settings
- Progress reporting for background or scheduled jobs (focus on interactive MCP tool calls)
- Estimated time remaining calculations (clients may provide this based on progress percentage)
- Progress for operations that have indeterminate completion time
- Nested progress tracking (sub-operations reporting independent progress)
