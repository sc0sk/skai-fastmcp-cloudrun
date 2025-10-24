````markdown
# Implementation Plan: Bulk Markdown Directory Ingestion

**Branch**: `013-bulk-markdown-ingestion` | **Date**: 2025-10-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/013-bulk-markdown-ingestion/spec.md`

## Summary

This feature adds bulk directory ingestion capability that orchestrates the existing single-file markdown ingestion tool (Feature 012) across multiple files. Administrators can process entire directories of markdown files in a single operation with progress reporting, error isolation, and comprehensive summary reporting. The implementation wraps the existing `ingest_markdown_file` tool with directory discovery, file filtering, sequential processing with error handling, and batch summary generation.

**Technical Approach**: Build a new MCP tool `ingest_markdown_directory` that discovers markdown files in a directory, applies optional pattern filtering, enforces safety limits, and calls the existing `ingest_markdown_file` tool for each file while collecting results and reporting progress. Uses FastMCP progress reporting for real-time updates and returns detailed batch summary with success/failure breakdown.

## Technical Context

**Language/Version**: Python 3.11+ (Cloud Run compatibility requirement)
**Primary Dependencies**: FastMCP 2.14.0+, pathlib (stdlib), glob patterns
**Storage**: Existing Cloud SQL PostgreSQL (via Feature 012 ingest_markdown_file tool)
**Testing**: pytest with async support, FastMCP test utilities
**Target Platform**: Google Cloud Run (Linux containers)
**Project Type**: Single project (extends existing MCP server)
**Performance Goals**: 10+ files/minute sequential processing, <1s directory discovery
**Constraints**: <100 file default limit (safety), progress updates every 1-5 files, non-recursive (single directory only)
**Scale/Scope**: Support 50-200 file batches, handle up to 1000 files with override

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate ✅

| Principle | Compliance | Notes |
|-----------|------------|-------|
| **I. FastMCP Server-First** | ✅ PASS | New tool `ingest_markdown_directory` exposed as MCP tool with clear schema |
| **II. Secure Authentication** | ✅ PASS | Inherits admin-only auth from Feature 012 (ingest_markdown_file) |
| **III. Secrets Management** | ✅ PASS | No new credentials, uses existing configuration |
| **IV. Test-Driven Development** | ✅ PASS | TDD workflow for directory discovery, filtering, batch orchestration |
| **VII. Progress Transparency** | ✅ PASS | Reports progress via ctx.report_progress() after each file |
| **VIII. Python & Pydantic** | ✅ PASS | Python 3.11+, Pydantic v2 for input validation |
| **XI. Tool Implementation** | ✅ PASS | Returns structured dict, raises ToolError on failures, progress reporting |

**Result**: ✅ All gates passed, proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/013-bulk-markdown-ingestion/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (implementation plan)
├── research.md          # Technical decisions (completed)
├── data-model.md        # Entity models (to be created)
├── quickstart.md        # Implementation guide (to be created)
├── contracts/           # MCP tool contracts (to be created)
│   └── mcp-tools.json  # Tool schema
└── checklists/          # Validation checklists
    └── requirements.md  # Spec quality (all passing)
```

### Source Code (repository root)

```text
src/
├── tools/
│   ├── ingest_markdown_file.py          # EXISTING: Single file ingestion (Feature 012)
│   ├── ingest_markdown_directory.py     # NEW: Bulk directory ingestion tool
│   └── ingestion_utils/                 # EXISTING: Shared utilities (Feature 012)
│       ├── __init__.py
│       ├── markdown_parser.py           # EXISTING: YAML frontmatter parsing
│       ├── path_validator.py            # EXISTING: Path security validation
│       └── auth.py                      # EXISTING: Admin role verification
├── models/
│   ├── enums.py                         # EXISTING: PartyEnum, ChamberEnum
│   └── speech.py                        # EXISTING: SpeechFrontmatter model
├── storage/
│   ├── vector_store.py                  # EXISTING: Vector embeddings storage
│   └── metadata_store.py                # EXISTING: Speech metadata storage
└── server.py                            # EXISTING: Register new tool

tests/
├── unit/
│   ├── test_ingest_markdown_file.py     # EXISTING: Single file tests
│   └── test_ingest_markdown_directory.py # NEW: Bulk ingestion tests
├── integration/
│   └── test_bulk_ingestion_e2e.py       # NEW: End-to-end batch tests
└── fixtures/
    └── markdown/                        # EXISTING: Test markdown files
        └── bulk_test/                   # NEW: Bulk test directory
            ├── valid_01.md
            ├── valid_02.md
            ├── invalid_missing_date.md
            └── invalid_bad_yaml.md
```

**Structure Decision**: Single project structure maintained. New bulk ingestion tool (`ingest_markdown_directory.py`) added alongside existing single-file tool. All shared utilities from Feature 012 are reused. No new models or storage logic needed - bulk tool orchestrates existing components. Test structure mirrors source with new bulk-specific tests.

## Complexity Tracking

*No constitution violations - this section left intentionally empty.*

All design decisions align with constitution requirements:
- FastMCP tool pattern followed
- Admin authentication inherited from Feature 012
- Progress reporting via ctx.report_progress()
- No new dependencies introduced
- TDD workflow specified
- Sequential processing (simple, meets requirements)

## Phase 0: Research ✅

**Status**: Complete
**Output**: [research.md](./research.md)

### Key Decisions

1. **File Discovery**: Use `pathlib.Path.glob()` for pattern matching (stdlib, no dependencies)
2. **Progress Reporting**: FastMCP `ctx.report_progress()` with adaptive frequency (1/5/10 files)
3. **Error Isolation**: Try-except per file with error collection in summary
4. **Safety Limits**: Default max_files=100 with override parameter
5. **Directory Validation**: Validate exists, is_dir, readable before processing
6. **Batch Summary**: Structured dict with counts and per-file details
7. **Pattern Matching**: Glob patterns (`*.md`, `hansard-*.md`) with graceful no-match handling
8. **Authentication**: Inherit admin auth from Feature 012's `ingest_markdown_file` tool

### Dependencies

No new dependencies required - all using Python stdlib and existing Feature 012:
- `pathlib`: File discovery (built-in)
- `typing`: Type hints (built-in)
- `fastmcp`: Already required
- `ingest_markdown_file`: Provided by Feature 012

### Performance Considerations

- Sequential processing: 10 files/minute (matches Feature 012 per-file performance)
- Memory bounded: One file processed at a time
- Progress overhead: <1ms per update (negligible)
- Scalability: Supports up to 1000 files with override

## Phase 1: Design ✅

**Status**: Complete
**Outputs**: [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

### Data Model Summary

**New Entities**:
1. **BulkIngestionRequest**: Input validation model (directory_path, pattern, max_files, duplicate_policy)
2. **FileIngestionResult**: Per-file outcome (file_name, status, speech_id, chunks, error details)
3. **BulkIngestionSummary**: Batch aggregate (total, succeeded, skipped, failed, total_chunks, file lists)

**Reused Entities** (Feature 012):
- SpeechFrontmatter: Parsed metadata
- SpeechMetadata: Database storage
- VectorChunk: Embedding storage
- IngestionResult: Single-file return value

### API Contracts

One MCP tool defined in [contracts/mcp-tools.json](./contracts/mcp-tools.json):

**Tool**: `ingest_markdown_directory`
- **Input**: BulkIngestionRequest (directory_path, pattern, max_files, duplicate_policy, validate_path)
- **Output**: BulkIngestionSummary (status, summary stats, successful_files, failed_files, message)
- **Annotations**: destructiveHint, requiresAuth, requiredRole=admin, progressReporting, errorIsolation

### Quickstart Implementation

3-step implementation guide (~45 minutes total):
1. Create bulk ingestion tool (30 min) - directory validation, file discovery, sequential processing, progress reporting
2. Register MCP tool (5 min) - add to server.py with annotations
3. Write tests (10 min) - directory validation, pattern matching, error isolation, progress reporting

**Complete code provided in** [quickstart.md](./quickstart.md)

## Phase 2: Tasks

**Status**: Not started (use `/speckit.tasks` command)
**Output**: Will generate `tasks.md` with dependency-ordered task breakdown

This phase is handled by the `/speckit.tasks` command which will:
- Break down quickstart into atomic tasks
- Add test coverage for edge cases
- Define integration testing tasks
- Create deployment verification tasks
- Order tasks by dependencies

## Post-Design Constitution Check ✅

Re-evaluated after completing Phase 1 design:

| Principle | Compliance | Design Verification |
|-----------|------------|---------------------|
| **Cloud Run Standards** | ✅ PASS | Uses existing container, env config, HTTPS |
| **Structured Results** | ✅ PASS | Returns dict with status/summary/files/message |
| **Code Quality** | ✅ PASS | Type hints, Pydantic validation, async/await |
| **Tool Metadata** | ✅ PASS | destructiveHint, requiresAuth, progress annotations |

**Result**: ✅ Design conforms to all constitution principles

## Implementation Notes

### Critical Path

1. ✅ Spec complete and validated (checklists/requirements.md all passing)
2. ✅ Research decisions documented (research.md)
3. ✅ Data model defined (data-model.md)
4. ✅ Contracts specified (contracts/mcp-tools.json)
5. ✅ Quickstart guide created (quickstart.md)
6. ⏳ Tasks breakdown (use `/speckit.tasks`)
7. ⏳ Implementation (use `/speckit.implement`)

### Success Metrics Alignment

Spec requirements vs implementation approach:

| Requirement | Implementation | Confidence |
|-------------|----------------|------------|
| SC-001: Single command for 64 files | One tool call processes all | ✅ High |
| SC-002: 10 files/minute | Sequential at ~5-10s/file = 6-12 files/min | ✅ High |
| SC-003: 1/20 fail, 19 succeed | Error isolation with try-except | ✅ High |
| SC-004: Progress every 5 files | Adaptive frequency (1/5/10) | ✅ High |
| SC-005: Detailed error reporting | Per-file error_type + error_message | ✅ High |
| SC-006: Safety limit (100 default) | max_files parameter with validation | ✅ High |
| SC-007: 95% complete w/o intervention | Automatic error isolation, no hung processes | ✅ High |

### Security Considerations

- ✅ Admin-only access via Feature 012's bearer token validation
- ✅ Path traversal prevention via Feature 012's validate_file_path()
- ✅ Safety limits prevent resource exhaustion (max_files)
- ✅ Non-recursive glob prevents descending into subdirectories
- ✅ Error messages sanitized (no system path exposure)
- ✅ HTTPS-only (Cloud Run automatic)
- ✅ Audit logging (via Feature 012 ingestion operations)

### Testing Strategy

**Unit Tests** (TDD approach):
- Directory validation (exists, readable, not file)
- File discovery (patterns, empty dir, filtering)
- Safety limit enforcement (max_files exceeded)
- Progress calculation (small/medium/large batches)
- Error isolation (continue on failure)
- Summary generation (counts, aggregation)
- Pattern matching (glob patterns, no matches)

**Integration Tests**:
- End-to-end bulk ingestion (real hansard_converted/)
- Mixed success/failure scenarios
- Progress reporting accuracy
- Admin auth verification (via Feature 012)
- Large batch (100+ files with override)

**Contract Tests**:
- MCP tool schema validation
- Response format compliance
- Error response structure

### Deployment Checklist

- [ ] Tool implementation created (ingest_markdown_directory.py)
- [ ] Tool registered in server.py with annotations
- [ ] Unit tests written and passing
- [ ] Integration tests with real data passing
- [ ] MCP Inspector testing completed
- [ ] Admin auth working (non-admin rejected)
- [ ] Progress reporting verified
- [ ] Error handling verified (all edge cases)
- [ ] Documentation updated (README, CLAUDE.md)
- [ ] Cloud Run deployment tested

## Agent Context Updated

**Command**: Run `.specify/scripts/bash/update-agent-context.sh copilot`

**Expected Changes**:
- Add "Feature 013: Bulk markdown directory ingestion" to recent changes
- Add technology: Python 3.11+, pathlib (stdlib), FastMCP 2.14.0+
- No new database changes (reuses Feature 012 storage)
- Update commands: pytest for new tests

## Next Commands

1. **Generate tasks**: `/speckit.tasks` - Break down implementation into atomic tasks with dependencies
2. **Implement feature**: `/speckit.implement` - Execute tasks following TDD workflow
3. **Clarify ambiguities** (optional): `/speckit.clarify` - Spec is complete, no clarifications needed
4. **Analyze consistency** (optional): `/speckit.analyze` - Cross-artifact consistency check

## Artifacts Generated

- ✅ [spec.md](./spec.md) - Feature specification (13 functional requirements, 7 success criteria)
- ✅ [research.md](./research.md) - 8 technical decisions with rationale (zero new dependencies)
- ✅ [data-model.md](./data-model.md) - 3 new entities + 4 reused from Feature 012
- ✅ [contracts/mcp-tools.json](./contracts/mcp-tools.json) - 1 MCP tool schema with examples
- ✅ [quickstart.md](./quickstart.md) - 3-step implementation guide (~45 min)
- ✅ [checklists/requirements.md](./checklists/requirements.md) - Spec validation (all pass)
- ✅ plan.md (this file) - Complete implementation plan

**Planning phase complete!** Ready for task breakdown with `/speckit.tasks` command.

---

## Summary

**Feature**: Bulk markdown directory ingestion with progress reporting and error isolation

**Implementation Approach**: Orchestration layer over existing Feature 012 single-file ingestion tool

**Key Design Decisions**:
- Sequential processing (simple, meets requirements)
- Python stdlib for file discovery (zero new dependencies)
- Error isolation via try-except per file
- Progress reporting with adaptive frequency
- Structured summary with detailed per-file results
- Safety limits to prevent accidental large batches
- Admin authentication inherited from Feature 012

**Estimated Implementation Time**: ~45 minutes following quickstart guide

**Next Step**: Run `/speckit.tasks` to generate dependency-ordered task breakdown
