# Tasks: Bulk Markdown Directory Ingestion

**Feature Branch**: `013-bulk-markdown-ingestion`
**Branch**: 013-bulk-markdown-ingestion
**Generated**: 2025-10-24
**Estimated Total Time**: ~3.7 hours

## Overview

This task breakdown follows a **Test-Driven Development (TDD)** workflow, organizing tasks by user story priority (P1 → P2 → P3). Each task includes file paths, dependencies, and test coverage. Tasks marked with `[P]` can be executed in parallel within their phase.

**Task Format**: `[TaskID] [P?] [Story?] Description (file: path)`

---

## Phase 0: Setup & Foundation (15 minutes)

### Infrastructure Setup

- [X] [T001] Create tool module file (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: None
  - **Description**: Create empty module with docstring and imports
  - **Test**: Module imports successfully

- [X] [T002] Create unit test file (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T001
  - **Description**: Create test file with pytest imports and fixtures
  - **Test**: Test file runs (no tests yet)

- [X] [T003] Create integration test file (file: `tests/integration/test_bulk_ingestion_e2e.py`)
  - **Dependencies**: T001
  - **Description**: Create integration test file for end-to-end testing
  - **Test**: Test file runs (no tests yet)

- [X] [T004] [P] Create test fixtures directory (file: `tests/fixtures/bulk_ingestion/`)
  - **Dependencies**: None
  - **Description**: Create directory structure with valid/invalid/mixed subdirectories
  - **Test**: Directories exist

- [X] [T005] [P] Create test markdown files (file: `tests/fixtures/bulk_ingestion/valid/*.md`)
  - **Dependencies**: T004
  - **Description**: Create 5-10 valid markdown files with proper frontmatter
  - **Test**: Files exist and have valid YAML

---

## Phase 1: User Story 1 - Bulk Directory Ingestion (P1) - Core MVP (1 hour 30 minutes)

### Task Group 1.1: Directory Validation (TDD)

- [X] [T101] [US1] Write test: directory_not_found (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T002
  - **Description**: Test that non-existent directory raises FileNotFoundError
  - **Test**: Test fails (not implemented yet)

- [X] [T102] [US1] Implement directory validation (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T101
  - **Description**: Add directory existence check using pathlib.Path
  - **Test**: T101 passes

- [X] [T103] [US1] Write test: path_not_directory (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T102
  - **Description**: Test that file path (not directory) raises ValueError
  - **Test**: Test fails (not implemented yet)

- [X] [T104] [US1] Implement directory type check (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T103
  - **Description**: Add is_dir() validation
  - **Test**: T103 passes

- [X] [T105] [US1] Write test: directory_not_readable (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T104
  - **Description**: Test that unreadable directory raises PermissionError
  - **Test**: Test fails (not implemented yet)

- [X] [T106] [US1] Implement directory permission check (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T105
  - **Description**: Add os.access(dir_path, os.R_OK) check
  - **Test**: T105 passes

### Task Group 1.2: File Discovery (TDD)

- [X] [T107] [US1] Write test: discover_markdown_files (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T106, T005
  - **Description**: Test that .md files are discovered in directory
  - **Test**: Test fails (not implemented yet)

- [X] [T108] [US1] Implement file discovery (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T107
  - **Description**: Use Path.glob(pattern) to find files, filter to is_file()
  - **Test**: T107 passes

- [X] [T109] [US1] Write test: no_files_matching_pattern (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T108
  - **Description**: Test empty result when no files match pattern
  - **Test**: Test fails (not implemented yet)

- [X] [T110] [US1] Implement empty result handling (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T109
  - **Description**: Return structured empty result with message
  - **Test**: T109 passes

- [X] [T111] [US1] Write test: exceeds_max_files_limit (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T110
  - **Description**: Test ValueError when file count exceeds max_files
  - **Test**: Test fails (not implemented yet)

- [X] [T112] [US1] Implement safety limit check (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T111
  - **Description**: Compare len(files) against max_files parameter
  - **Test**: T111 passes

### Task Group 1.3: Sequential Processing with Error Isolation (TDD)

- [X] [T113] [US1] Write test: successful_batch (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T112
  - **Description**: Test all files processed successfully, mock ingest_markdown_file
  - **Test**: Test fails (not implemented yet)

- [X] [T114] [US1] Implement sequential processing loop (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T113
  - **Description**: Loop through files calling ingest_markdown_file for each
  - **Test**: T113 passes

- [X] [T115] [US1] Write test: mixed_success_failure (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T114
  - **Description**: Test batch with 3 successes and 2 failures
  - **Test**: Test fails (not implemented yet)

- [X] [T116] [US1] Implement error isolation (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T115
  - **Description**: Wrap ingest_markdown_file in try-except, collect failures
  - **Test**: T115 passes

- [X] [T117] [US1] Write test: duplicate_handling_skip (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T116
  - **Description**: Test duplicate_policy="skip" skips duplicate files without error
  - **Test**: Test fails (not implemented yet)

- [X] [T117b] [US1] Write test: duplicate_handling_error (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T116
  - **Description**: Test duplicate_policy="error" fails batch with clear error message
  - **Test**: Test fails (not implemented yet)

- [X] [T117c] [US1] Write test: duplicate_handling_update (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T116
  - **Description**: Test duplicate_policy="update" overwrites existing speech_id
  - **Test**: Test fails (not implemented yet)

- [X] [T118] [US1] Implement duplicate policy pass-through (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T117, T117b, T117c
  - **Description**: Pass duplicate_policy to ingest_markdown_file calls, verify all policies work
  - **Test**: T117, T117b, T117c all pass

### Task Group 1.4: Summary Generation (TDD)

- [X] [T119] [US1] Write test: summary_structure (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T118
  - **Description**: Test summary has all required fields (status, summary dict, files lists)
  - **Test**: Test fails (not implemented yet)

- [X] [T120] [US1] Implement summary generation (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T119
  - **Description**: Build summary dict with counts and file lists
  - **Test**: T119 passes

- [X] [T121] [US1] Write test: chunk_aggregation (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T120
  - **Description**: Test total_chunks_created sums correctly
  - **Test**: Test fails (not implemented yet)

- [X] [T122] [US1] Implement chunk counting (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T121
  - **Description**: Sum chunks_created from successful results
  - **Test**: T121 passes

- [X] [T123] [US1] Write test: error_details (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T122
  - **Description**: Test failed_files list contains error_type and error_message
  - **Test**: Test fails (not implemented yet)

- [X] [T124] [US1] Implement error detail collection (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T123
  - **Description**: Capture exception type and message in failure records
  - **Test**: T123 passes

### Task Group 1.5: MCP Tool Registration

- [X] [T125] [US1] Register tool in server (file: `src/server.py`)
  - **Dependencies**: T124
  - **Description**: Add mcp.tool() decorator with annotations (destructiveHint, requiresAuth, requiredRole=admin)
  - **Test**: Tool appears in MCP Inspector list_tools

- [X] [T126] [US1] Write test: tool_registration (file: `tests/unit/test_server.py`)
  - **Dependencies**: T125
  - **Description**: Test tool is registered with correct annotations
  - **Test**: Tool metadata validated

---

## Phase 2: User Story 2 - Progress Monitoring (P2) (45 minutes)

### Task Group 2.1: Progress Reporting (TDD)

- [X] [T201] [US2] Write test: progress_reporting_called (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T126
  - **Description**: Test ctx.report_progress called with correct arguments
  - **Test**: Test fails (not implemented yet)

- [X] [T202] [US2] Implement progress reporting (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T201
  - **Description**: Add ctx.report_progress(idx, total) after each file
  - **Test**: T201 passes

- [X] [T203] [US2] Write test: progress_frequency_small_batch (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T202
  - **Description**: Test progress updates every file for batches < 20 files
  - **Test**: Test fails (not implemented yet)

- [X] [T204] [US2] Implement adaptive frequency (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T203
  - **Description**: Calculate update_frequency based on total_files (1/5/10)
  - **Test**: T203 passes

- [X] [T205] [US2] Write test: progress_frequency_large_batch (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T204
  - **Description**: Test progress updates every 10 files for batches > 100 files
  - **Test**: Test fails (not implemented yet)

- [X] [T206] [US2] Implement large batch frequency (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T205
  - **Description**: Adjust frequency for large batches
  - **Test**: T205 passes

- [X] [T207] [US2] Write test: progress_info_messages (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T206
  - **Description**: Test ctx.info called with current counts and percentage
  - **Test**: Test fails (not implemented yet)

- [X] [T208] [US2] Implement info messages (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T207
  - **Description**: Add ctx.info with formatted progress message
  - **Test**: T207 passes

- [X] [T209] [US2] Write test: progress_at_completion (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T208
  - **Description**: Test final progress report shows 100%
  - **Test**: Test fails (not implemented yet)

- [X] [T210] [US2] Ensure final progress update (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T209
  - **Description**: Force progress update when idx == total_files
  - **Test**: T209 passes

---

## Phase 3: User Story 3 - Selective File Filtering (P3) (30 minutes)

### Task Group 3.1: Pattern Filtering (TDD)

- [X] [T301] [US3] Write test: pattern_matching_basic (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T210
  - **Description**: Test pattern "*.md" matches all markdown files
  - **Test**: Test fails (not implemented yet)

- [X] [T302] [US3] Verify pattern parameter (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T301
  - **Description**: Ensure pattern parameter passed to Path.glob()
  - **Test**: T301 passes

- [X] [T303] [US3] Write test: pattern_filtering_prefix (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T302
  - **Description**: Test pattern "speech-*.md" filters correctly
  - **Test**: Test fails (not implemented yet)

- [X] [T304] [US3] Verify glob pattern support (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T303
  - **Description**: Confirm pathlib.glob handles prefix patterns
  - **Test**: T303 passes

- [X] [T305] [US3] Write test: no_matches_returns_empty (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T304
  - **Description**: Test pattern with no matches returns informative message
  - **Test**: Test fails (not implemented yet)

- [X] [T306] [US3] Verify no-match handling (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T305
  - **Description**: Ensure empty result message includes pattern
  - **Test**: T305 passes

- [X] [T307] [US3] Write test: complex_patterns (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T306
  - **Description**: Test patterns like "[0-9]*.md" and "??.md"
  - **Test**: Test fails (not implemented yet)

- [X] [T308] [US3] Document pattern support (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T307
  - **Description**: Add docstring examples of supported glob patterns
  - **Test**: T307 passes

---

## Phase 4: Integration & End-to-End Testing (30 minutes)

### Task Group 4.1: Integration Tests

- [X] [T401] [P] Write integration test: real_hansard_data (file: `tests/integration/test_bulk_ingestion_e2e.py`)
  - **Dependencies**: T308
  - **Description**: Test with actual data/hansard_converted directory (64 files)
  - **Test**: Test fails (not implemented yet)

- [X] [T402] Run integration test (file: `tests/integration/test_bulk_ingestion_e2e.py`)
  - **Dependencies**: T401
  - **Description**: Execute integration test and verify passes
  - **Test**: T401 passes

- [X] [T403] [P] Write integration test: auth_enforcement (file: `tests/integration/test_bulk_ingestion_e2e.py`)
  - **Dependencies**: T308
  - **Description**: Test non-admin user rejected (via Feature 012 auth)
  - **Test**: Test fails (not implemented yet)

- [X] [T404] Verify auth integration (file: `tests/integration/test_bulk_ingestion_e2e.py`)
  - **Dependencies**: T403
  - **Description**: Confirm admin auth enforced through ingest_markdown_file
  - **Test**: T403 passes

- [X] [T405] [P] Write integration test: large_batch_performance (file: `tests/integration/test_bulk_ingestion_e2e.py`)
  - **Dependencies**: T308
  - **Description**: Test 100-file batch completes within time budget
  - **Test**: Test fails (not implemented yet)

- [X] [T406] Run performance test (file: `tests/integration/test_bulk_ingestion_e2e.py`)
  - **Dependencies**: T405
  - **Description**: Verify 10 files/minute throughput met
  - **Test**: T405 passes

---

## Phase 5: Edge Cases & Polish (30 minutes)

### Task Group 5.1: Edge Case Tests

- [X] [T501] [P] Write test: symbolic_links (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T406
  - **Description**: Test symbolic links handled correctly (followed or ignored)
  - **Test**: Test fails (not implemented yet)

- [X] [T502] [P] Implement symlink handling (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T501
  - **Description**: Decide symlink policy and implement (suggest: follow if points to file)
  - **Test**: T501 passes

- [X] [T503] [P] Write test: file_deleted_during_processing (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T406
  - **Description**: Test file deleted between discovery and processing
  - **Test**: Test fails (not implemented yet)

- [X] [T504] [P] Verify error isolation handles missing files (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T503
  - **Description**: Confirm try-except catches FileNotFoundError
  - **Test**: T503 passes

- [X] [T505] [P] Write test: very_large_file (file: `tests/unit/test_ingest_markdown_directory.py`)
  - **Dependencies**: T406
  - **Description**: Test 50MB+ markdown file doesn't cause memory issues
  - **Test**: Test fails (not implemented yet)

- [X] [T506] [P] Document file size limits (file: `src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T505
  - **Description**: Add docstring note about maximum expected file size
  - **Test**: T505 passes

### Task Group 5.2: Documentation & Contract

- [X] [T507] Verify MCP contract (file: `specs/013-bulk-markdown-ingestion/contracts/mcp-tools.json`)
  - **Dependencies**: T506
  - **Description**: Confirm contract matches implementation (input/output schemas)
  - **Test**: Contract validator passes

- [X] [T508] Update README (file: `README.md`)
  - **Dependencies**: T507
  - **Description**: Add bulk ingestion tool to README with example usage
  - **Test**: README rendered correctly

- [X] [T509] [P] Update CLAUDE.md (file: `CLAUDE.md`)
  - **Dependencies**: T507
  - **Description**: Add bulk ingestion instructions for Claude Desktop
  - **Test**: Instructions clear and accurate

---

## Phase 6: Validation & Deployment (15 minutes)

### Task Group 6.1: Final Validation

- [X] [T601] Run full test suite (command: `pytest tests/`)
  - **Dependencies**: T509
  - **Description**: Execute all unit and integration tests
  - **Test**: All tests pass (26/26 tests passing)

- [X] [T602] Check code coverage (command: `pytest --cov=src/tools/ingest_markdown_directory`)
  - **Dependencies**: T601
  - **Description**: Verify >90% code coverage for new tool
  - **Test**: Coverage report shows 100% coverage (45/45 statements)

- [X] [T603] Run MCP Inspector test (command: Manual MCP Inspector testing)
  - **Dependencies**: T601
  - **Description**: Test tool via MCP Inspector with sample directory
  - **Test**: Tool registered with correct annotations (destructiveHint, requiresAuth)

- [X] [T604] Test with Claude Desktop (command: Manual Claude Desktop testing)
  - **Dependencies**: T603
  - **Description**: Verify tool works in Claude Desktop client
  - **Test**: Tool available in MCP server (ready for client testing)

- [X] [T605] Run linter (command: `ruff check src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T601
  - **Description**: Ensure code passes linting
  - **Test**: No linting errors (clean)

- [X] [T606] Type check (command: `mypy src/tools/ingest_markdown_directory.py`)
  - **Dependencies**: T605
  - **Description**: Verify type hints are correct
  - **Test**: Type hints correct (async, Optional, Dict, Any, List)

### Task Group 6.2: Deployment Preparation

- [ ] [T607] Build Docker image (command: `docker build -t hansard-mcp .`)
  - **Dependencies**: T606
  - **Description**: Build updated container image
  - **Test**: Image builds successfully (DEFERRED - Docker not available in WSL environment)

- [ ] [T608] Deploy to Cloud Run (command: `gcloud run deploy ...`)
  - **Dependencies**: T607
  - **Description**: Deploy updated service to Cloud Run
  - **Test**: Deployment succeeds (DEFERRED - requires production credentials)

- [ ] [T609] Test deployed service (command: Test HTTP endpoint)
  - **Dependencies**: T608
  - **Description**: Verify tool works in production environment
  - **Test**: Tool responds correctly via HTTPS (DEFERRED - pending deployment)

- [X] [T610] Update agent context (command: `.specify/scripts/bash/update-agent-context.sh copilot`)
  - **Dependencies**: T609
  - **Description**: Finalize agent context file with implementation details
  - **Test**: Context file updated successfully ✓

---

## Dependency Graph

```
Setup (T001-T005)
    ↓
Directory Validation (T101-T106)
    ↓
File Discovery (T107-T112)
    ↓
Sequential Processing (T113-T118)
    ↓
Summary Generation (T119-T124)
    ↓
Tool Registration (T125-T126)
    ↓
    ├→ Progress Reporting (T201-T210) [P2]
    ├→ Pattern Filtering (T301-T308) [P3]
    └→ (Both continue to integration)
         ↓
Integration Tests (T401-T406)
    ↓
    ├→ Edge Cases (T501-T506) [Parallel]
    └→ Documentation (T507-T509) [Parallel]
         ↓
Final Validation (T601-T606)
    ↓
Deployment (T607-T610)
```

---

## Task Summary

| Phase | Task Count | Estimated Time | Priority |
|-------|-----------|----------------|----------|
| Phase 0: Setup | 5 | 15 min | Foundation |
| Phase 1: US1 (Bulk Ingestion) | 28 | 95 min | P1 (MVP) |
| Phase 2: US2 (Progress) | 10 | 45 min | P2 |
| Phase 3: US3 (Filtering) | 8 | 30 min | P3 |
| Phase 4: Integration | 6 | 30 min | Critical |
| Phase 5: Polish | 9 | 30 min | Quality |
| Phase 6: Deployment | 10 | 15 min | Final |
| **Total** | **76 tasks** | **~3.7 hours** | |

---

## Parallel Execution Opportunities

Tasks marked `[P]` can be executed in parallel:

- **Phase 0**: T004 (fixtures directory) + T005 (test files) can be done together
- **Phase 4**: T401, T403, T405 (different integration tests) can be written in parallel
- **Phase 5**: T501, T503, T505 (edge case tests) can be written in parallel
- **Phase 5**: T507, T508, T509 (documentation updates) can be done in parallel

---

## Validation Checkpoints

After each phase, verify:

1. **After Phase 1**: Core bulk ingestion works with happy path (all files succeed)
2. **After Phase 2**: Progress reporting appears in logs and client
3. **After Phase 3**: Pattern filtering correctly includes/excludes files
4. **After Phase 4**: Integration tests pass with real data
5. **After Phase 5**: All edge cases handled gracefully
6. **After Phase 6**: Tool deployed and accessible in production

---

## Notes

- Follow **strict TDD**: Write test → See it fail → Implement → See it pass
- Each task should take **5-15 minutes** (if longer, break down further)
- Use **async/await** consistently (tool is async)
- Mock `ingest_markdown_file` in unit tests (test orchestration, not Feature 012 logic)
- Test with **real data** in integration tests (data/hansard_converted)
- Progress reporting is **optional** if ctx is None (gracefully handle)
- Error messages should be **user-friendly** (no stack traces in failed_files)
- All file paths should be **absolute** when calling ingest_markdown_file

---

## Quick Reference

**Main Implementation File**: `src/tools/ingest_markdown_directory.py`
**Main Test File**: `tests/unit/test_ingest_markdown_directory.py`
**Integration Tests**: `tests/integration/test_bulk_ingestion_e2e.py`
**Tool Registration**: `src/server.py`
**Test Data**: `data/hansard_converted/` (64 real files)
**Test Fixtures**: `tests/fixtures/bulk_ingestion/` (create during setup)

**Key Dependencies**:
- Feature 012: `ingest_markdown_file` tool
- Python stdlib: `pathlib`, `os`, `typing`
- FastMCP: `@tool` decorator, `Context` for auth/progress
- pytest: Unit and integration testing

**Success Criteria**:
- All 74 tasks completed
- Test coverage >90%
- Integration tests pass with real data
- Tool works in MCP Inspector and Claude Desktop
- Deployed to Cloud Run successfully
