# Implementation Tasks: Real Hansard Data Ingestion

**Feature**: Real Hansard Data Ingestion
**Branch**: `002-real-hansard-ingestion`
**Created**: 2025-10-23

## Overview

This document outlines tasks to implement ingestion of 64 real Australian Hansard parliamentary speeches from markdown files in `data/hansard_reps/`. Tasks are organized by user story priority to enable independent, incremental delivery.

**MVP Scope**: Phase 2 (User Story 1) - Delivers core ingestion functionality for all 64 speeches.

---

## Phase 1: Setup & Prerequisites

**Goal**: Prepare codebase for Hansard markdown ingestion

### Tasks

- [ ] T001 Fix date serialization bug in scripts/chunk_existing_speeches.py line 105 (change `speech['date']` to `speech['date'].isoformat()`)
- [ ] T002 Verify data/hansard_reps/ directory contains 64 markdown files
- [ ] T003 Create scripts/parsers/ directory for markdown parsing utilities
- [ ] T004 Add PyYAML dependency to pyproject.toml if not present

**Estimated Duration**: 15 minutes

---

## Phase 2: User Story 1 - Parse and Ingest Markdown Files (P1)

**User Story**: Import 64 real Hansard speeches from markdown files with YAML frontmatter, enabling MCP server to answer questions about actual parliamentary proceedings.

**Independent Test**: Run ingestion script against data/hansard_reps/, verify all 64 speeches in database with correct metadata, confirm vector embeddings exist.

**Success Criteria**:
- All 64 markdown files successfully processed
- Speeches table contains 64 records with complete metadata
- Speech_chunks table contains embeddings for all speeches
- Zero JSON serialization errors

### Tasks

- [ ] T005 [P] [US1] Create HansardMarkdownParser class in scripts/parsers/hansard_parser.py to parse YAML frontmatter and extract speech text
- [ ] T006 [P] [US1] Implement parse_frontmatter() method to extract speaker, date, chamber, electorate, party, utterance_id from YAML
- [ ] T007 [P] [US1] Implement extract_speech_text() method to get content after second `---` marker
- [ ] T008 [P] [US1] Implement parse_speaker_name() method to convert "LastName, FirstName MP" format to "FirstName LastName"
- [ ] T009 [US1] Create ingest_hansard_markdown.py script in scripts/ directory
- [ ] T010 [US1] Implement discover_markdown_files() function to recursively find .md files in data/hansard_reps/
- [ ] T011 [US1] Implement validate_speech_data() function to check required fields (speaker, date, chamber, text)
- [ ] T012 [US1] Implement convert_to_speech_metadata() function to map parsed data to SpeechMetadata Pydantic model
- [ ] T013 [US1] Implement ingest_single_speech() async function: parse → validate → store metadata → chunk → embed → store chunks
- [ ] T014 [US1] Add date-to-string conversion in chunk metadata preparation (use `.isoformat()` for date fields)
- [ ] T015 [US1] Implement bulk_ingest() async function to process all files in directory with error handling
- [ ] T016 [US1] Add main() entrypoint with environment variable validation (GCP_PROJECT_ID, CLOUDSQL_INSTANCE, etc.)
- [ ] T017 [US1] Test ingestion script locally with DANGEROUSLY_OMIT_AUTH=true against 1-2 sample files
- [ ] T018 [US1] Build Docker image with updated scripts (v026)
- [ ] T019 [US1] Create Cloud Run job ingest-hansard-markdown with environment variables
- [ ] T020 [US1] Execute ingestion job and verify 64 speeches ingested successfully

**Estimated Duration**: 3-4 hours

---

## Phase 3: User Story 2 - Handle Date Serialization (P2)

**User Story**: Ensure date objects are converted to ISO strings before JSON serialization to prevent "Object of type date is not JSON serializable" errors.

**Independent Test**: Ingest speech with date field, verify chunk metadata contains date string, confirm no serialization errors.

**Success Criteria**:
- Zero JSON serialization errors during ingestion
- All chunk metadata date fields stored as ISO strings
- Dates retrievable and displayable from database

### Tasks

- [ ] T021 [P] [US2] Review and update all scripts that create chunk metadata to use `.isoformat()` for date fields
- [ ] T022 [P] [US2] Update scripts/populate_hansard_db.py line 148 to convert date to string
- [ ] T023 [US2] Update scripts/chunk_existing_speeches.py line 105 to convert date to string (if not done in T001)
- [ ] T024 [US2] Add utility function to_json_serializable() in scripts/utils/ for consistent date handling
- [ ] T025 [US2] Test updated scripts with sample speeches containing various date formats
- [ ] T026 [US2] Build Docker image with date serialization fixes (v027)
- [ ] T027 [US2] Re-run chunk-speeches job to test fix (if needed)

**Estimated Duration**: 1 hour

---

## Phase 4: User Story 3 - Progress Tracking and Error Reporting (P3)

**User Story**: Provide visibility into ingestion progress (files processed, speeches ingested, chunks created) and detailed error logging for failed files.

**Independent Test**: Ingest all 64 files, verify console output shows progress updates and final summary with accurate counts.

**Success Criteria**:
- Progress indicator shows current file number during processing
- Final report shows exact counts: 64 speeches, X chunks, 0 errors
- Error log captures file path and specific error for any failures

### Tasks

- [ ] T028 [P] [US3] Add IngestionStats dataclass in scripts/ingest_hansard_markdown.py to track counts
- [ ] T029 [P] [US3] Implement progress_reporter() function to log every N files (e.g., every 10)
- [ ] T030 [US3] Update bulk_ingest() to call progress_reporter() and update IngestionStats
- [ ] T031 [US3] Implement generate_summary_report() function to output final statistics
- [ ] T032 [US3] Add error_logger() function to write detailed errors to ingestion_errors.log
- [ ] T033 [US3] Update exception handlers in ingest_single_speech() to call error_logger()
- [ ] T034 [US3] Test progress reporting with full 64-file ingestion
- [ ] T035 [US3] Build Docker image with progress tracking (v028)
- [ ] T036 [US3] Execute final ingestion job and capture summary report

**Estimated Duration**: 1.5 hours

---

## Phase 5: Verification & Polish

**Goal**: Confirm successful ingestion and clean up

### Tasks

- [ ] T037 Run check-db Cloud Run job to verify 64 speeches and expected chunk count
- [ ] T038 Test MCP search_hansard_speeches tool with query about known speech content
- [ ] T039 Test MCP fetch_hansard_speech tool to retrieve full speech by ID
- [ ] T040 Update CLAUDE.md with ingestion commands and data sources
- [ ] T041 Commit all changes to 002-real-hansard-ingestion branch
- [ ] T042 Create pull request with summary of ingestion results

**Estimated Duration**: 30 minutes

---

## Dependencies & Execution Order

### Story Dependencies

```
Phase 1 (Setup) → Phase 2 (US1) → Phase 3 (US2) → Phase 4 (US3) → Phase 5 (Verification)
                       ↓
                  MVP Complete
```

- **US1** is foundational - must complete first
- **US2** can be done in parallel with US1 (fixing existing scripts)
- **US3** can be done in parallel with or after US1
- **US2 + US3** are enhancements, not blockers

### Parallel Execution Opportunities

**Phase 1** (All parallelizable):
- T001-T004 can run simultaneously

**Phase 2 - US1** (Parser + Script development):
- T005-T008 (Parser methods) can run in parallel
- T010-T012 (Utility functions) can run in parallel
- T009, T013-T016 (Main script) must be sequential
- T017-T020 (Testing/Deployment) must be sequential

**Phase 3 - US2** (Date fixes):
- T021-T023 (Script updates) can run in parallel
- T024-T027 (Testing) must be sequential

**Phase 4 - US3** (Progress tracking):
- T028-T029 (Stats + Reporter) can run in parallel
- T030-T033 (Integration) must be sequential
- T034-T036 (Testing) must be sequential

---

## Implementation Strategy

### MVP Scope (Recommended)

**Deliver first**: Phase 1 + Phase 2 (US1)
- Covers core ingestion of all 64 speeches
- Provides immediate value (searchable real data)
- Estimated: 4 hours

### Incremental Delivery

1. **Sprint 1**: Phase 1 + Phase 2 (US1) - Core ingestion
2. **Sprint 2**: Phase 3 (US2) - Date serialization fixes (if needed)
3. **Sprint 3**: Phase 4 (US3) - Progress tracking enhancements
4. **Sprint 4**: Phase 5 - Verification and polish

### Critical Path

```
T001 (Date fix) → T009 (Script creation) → T013 (Ingest function) → T016 (Entrypoint) → T017-T020 (Deploy & Execute)
```

**Blockers to watch**:
- T001: Date serialization fix is critical - blocks all ingestion
- T005-T008: Parser must work correctly for ingestion to succeed
- T019: Cloud Run job configuration must include all required env vars

---

## Task Summary

- **Total Tasks**: 42
- **Phase 1 (Setup)**: 4 tasks
- **Phase 2 (US1 - Core Ingestion)**: 16 tasks
- **Phase 3 (US2 - Date Serialization)**: 7 tasks
- **Phase 4 (US3 - Progress Tracking)**: 9 tasks
- **Phase 5 (Verification)**: 6 tasks

**Parallel Tasks**: 15 tasks marked [P] can run concurrently
**Estimated Total Duration**: 6-7 hours
**MVP Duration**: 4 hours (Phase 1 + Phase 2)
