# Tasks: Admin-Protected Markdown Ingestion with Vector Embeddings

**Input**: Design documents from `/specs/012-admin-markdown-ingestion/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD approach specified in quickstart.md - tests included in this task breakdown

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependencies

- [X] T001 Add python-frontmatter dependency to project requirements
- [X] T002 [P] Create directory structure src/tools/ingest/ for shared utilities
- [X] T003 [P] Create test fixtures directory tests/fixtures/markdown/ with sample markdown files
- [X] T004 [P] Configure environment variables for ingestion (ADMIN_ROLE_CLAIM, ADMIN_ROLE_VALUE, INGESTION_BASE_DIR, DUPLICATE_POLICY, CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_BATCH_SIZE)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities that ALL user stories depend on - MUST be complete before ANY user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 [P] Create PartyEnum and ChamberEnum in src/models/enums.py (if not already present)
- [X] T006 [P] Create SpeechFrontmatter Pydantic model in src/models/speech.py with validation (speech_id, speaker, party, chamber, date, title, state, hansard_reference)
- [X] T007 [P] Implement parse_markdown_file() function in src/tools/ingest/markdown_parser.py using python-frontmatter
- [X] T008 [P] Implement validate_file_path() function in src/tools/ingest/path_validator.py with directory traversal prevention
- [X] T009 [P] Implement require_admin_role() function in src/tools/ingest/auth.py with JWT role claim verification
- [X] T010 [P] Create test fixtures: tests/fixtures/markdown/valid_speech.md
- [X] T011 [P] Create test fixtures: tests/fixtures/markdown/no_frontmatter.md
- [X] T012 [P] Create test fixtures: tests/fixtures/markdown/malformed_yaml.md
- [X] T013 [P] Create test fixtures: tests/fixtures/markdown/missing_fields.md
- [X] T014 [P] Write unit tests for markdown_parser.py in tests/unit/test_markdown_parser.py
- [X] T015 [P] Write unit tests for path_validator.py in tests/unit/test_path_validator.py
- [X] T016 [P] Write unit tests for auth.py in tests/unit/test_admin_auth.py

**Checkpoint**: Foundation ready - all parsing, validation, and auth utilities working with tests passing

---

## Phase 3: User Story 2 - Single File Import with Validation (Priority: P2) 🎯 MVP

**Goal**: Enable administrators to import a single markdown file with detailed validation feedback and error reporting

**Why P2 First for MVP**: Single file ingestion is the atomic operation that bulk ingestion builds upon. It's simpler to test, debug, and provides the foundation for bulk operations. Starting with this ensures the core ingestion logic is solid before adding bulk complexity.

**Independent Test**: Provide a single markdown file with valid frontmatter, authenticate with admin token, verify speech appears in database with correct metadata and is searchable via existing search_hansard_speeches tool

### Tests for User Story 2

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T017 [P] [US2] Write unit test for successful single file ingestion in tests/unit/test_ingest_markdown_file.py
- [X] T018 [P] [US2] Write unit test for admin role enforcement in tests/unit/test_ingest_markdown_file.py
- [X] T019 [P] [US2] Write unit test for duplicate handling (skip policy) in tests/unit/test_ingest_markdown_file.py
- [X] T020 [P] [US2] Write unit test for duplicate handling (error policy) in tests/unit/test_ingest_markdown_file.py
- [X] T021 [P] [US2] Write unit test for transaction rollback on embedding failure in tests/unit/test_ingest_markdown_file.py

### Implementation for User Story 2

- [X] T022 [US2] Create DuplicatePolicy enum in src/tools/ingest_markdown_file.py
- [X] T023 [US2] Create IngestFileInput Pydantic model in src/tools/ingest_markdown_file.py
- [X] T024 [US2] Implement ingest_markdown_file() async function with admin auth, path validation, frontmatter parsing in src/tools/ingest_markdown_file.py
- [X] T025 [US2] Add duplicate detection logic with configurable policy (skip/update/error) to ingest_markdown_file()
- [X] T026 [US2] Add text chunking using LangChain RecursiveCharacterTextSplitter to ingest_markdown_file()
- [X] T027 [US2] Add vector embedding generation via Vertex AI to ingest_markdown_file()
- [X] T028 [US2] Add transactional database storage (metadata + embeddings) with rollback to ingest_markdown_file()
- [X] T029 [US2] Add structured result dictionary with status/speech_id/chunks_created/message to ingest_markdown_file()
- [X] T030 [US2] Register ingest_markdown_file as MCP tool in src/server.py with admin metadata
- [X] T031 [US2] Run all US2 unit tests and verify they pass

**Checkpoint**: At this point, single file ingestion should be fully functional - can import one markdown file, validate metadata, generate embeddings, store in database, and verify via search

---

## Phase 4: User Story 3 - Monitor Ingestion Progress (Priority: P3)

**Goal**: Add validate_markdown_file tool for dry-run validation without database changes

**Why P3 Before P1**: Validation tool provides critical quality control for administrators before running bulk operations. It's independent, read-only, and helps catch errors early. This reduces risk when implementing bulk ingestion.

**Independent Test**: Provide a markdown file path, call validate_markdown_file tool, verify it returns detailed validation report without creating database records

### Tests for User Story 3

- [ ] T032 [P] [US3] Write unit test for successful validation in tests/unit/test_validate_markdown_file.py
- [ ] T033 [P] [US3] Write unit test for validation failures (missing fields, malformed YAML) in tests/unit/test_validate_markdown_file.py
- [ ] T034 [P] [US3] Write unit test for duplicate detection check in tests/unit/test_validate_markdown_file.py
- [ ] T035 [P] [US3] Write unit test that validate_markdown_file does NOT create database records in tests/unit/test_validate_markdown_file.py

### Implementation for User Story 3

- [ ] T036 [P] [US3] Create ValidateFileInput Pydantic model in src/tools/validate_markdown_file.py
- [ ] T037 [US3] Implement validate_markdown_file() async function with all validation checks (path, frontmatter, fields, duplicate) in src/tools/validate_markdown_file.py
- [ ] T038 [US3] Add detailed validation report structure with pass/fail for each check in validate_markdown_file()
- [ ] T039 [US3] Register validate_markdown_file as MCP tool in src/server.py with admin metadata and readOnlyHint=true
- [ ] T040 [US3] Run all US3 unit tests and verify they pass

**Checkpoint**: Validation tool is working - administrators can validate files without risk of database changes

---

## Phase 5: User Story 1 - Bulk Import Parliamentary Speeches (Priority: P1)

**Goal**: Enable administrators to import entire directories of markdown files with progress reporting and detailed error summaries

**Why P1 Last**: Bulk ingestion builds on single file ingestion (US2) and benefits from validation tool (US3). Implementing it last ensures core logic is proven before adding complexity of batch processing, progress reporting, and error aggregation.

**Independent Test**: Provide directory with 10 markdown files, authenticate with admin token, run bulk ingestion, verify all speeches appear in database and progress is reported

### Tests for User Story 1

- [ ] T041 [P] [US1] Write unit test for successful bulk ingestion (all files succeed) in tests/unit/test_ingest_markdown_bulk.py
- [ ] T042 [P] [US1] Write unit test for partial success (some files fail) in tests/unit/test_ingest_markdown_bulk.py
- [ ] T043 [P] [US1] Write unit test for file pattern filtering in tests/unit/test_ingest_markdown_bulk.py
- [ ] T044 [P] [US1] Write unit test for max_files limit enforcement in tests/unit/test_ingest_markdown_bulk.py
- [ ] T045 [P] [US1] Write unit test for progress reporting via ctx.report_progress() in tests/unit/test_ingest_markdown_bulk.py

### Implementation for User Story 1

- [ ] T046 [P] [US1] Create IngestBulkInput Pydantic model in src/tools/ingest_markdown_bulk.py
- [ ] T047 [US1] Implement file discovery logic with glob pattern filtering in ingest_markdown_bulk()
- [ ] T048 [US1] Implement bulk ingestion loop calling ingest_markdown_file() for each file in src/tools/ingest_markdown_bulk.py
- [ ] T049 [US1] Add progress reporting via ctx.report_progress() after each file in ingest_markdown_bulk()
- [ ] T050 [US1] Add error isolation (individual file transaction failures don't stop batch) in ingest_markdown_bulk()
- [ ] T051 [US1] Add summary report with success_count, failed_count, and detailed failure list in ingest_markdown_bulk()
- [ ] T052 [US1] Add max_files safety limit enforcement in ingest_markdown_bulk()
- [ ] T053 [US1] Register ingest_markdown_bulk as MCP tool in src/server.py with admin metadata and supportsProgress=true
- [ ] T054 [US1] Run all US1 unit tests and verify they pass

**Checkpoint**: Bulk ingestion is working - can process directories of files with progress reporting and error handling

---

## Phase 6: Integration & End-to-End Testing

**Purpose**: Verify all user stories work together and integrate with existing system

- [ ] T055 [P] Write integration test for single file ingestion end-to-end in tests/integration/test_ingestion_e2e.py
- [ ] T056 [P] Write integration test for bulk ingestion with mixed success/failure in tests/integration/test_ingestion_e2e.py
- [ ] T057 [P] Write integration test for ingestion → search flow (verify ingested speech is searchable) in tests/integration/test_ingestion_e2e.py
- [ ] T058 [P] Write integration test for admin auth rejection (non-admin user attempts ingestion) in tests/integration/test_ingestion_e2e.py
- [ ] T059 Run all integration tests against local database
- [ ] T060 Test all three tools via Claude CLI with admin bearer token
- [ ] T061 Verify ingested speeches appear in search_hansard_speeches results
- [ ] T062 Test error handling with intentionally malformed files

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T063 [P] Add comprehensive logging for all ingestion operations (admin user, file paths, results)
- [ ] T064 [P] Add audit trail recording to database (optional ingestion_logs table)
- [ ] T065 [P] Optimize embedding batch size for Vertex AI API efficiency
- [ ] T066 [P] Add retry logic for transient Vertex AI failures
- [ ] T067 [P] Update CLAUDE.md agent context with new ingestion tools
- [ ] T068 Code cleanup and refactoring across all ingestion modules
- [ ] T069 Performance testing: verify 10 files/min bulk ingestion target
- [ ] T070 Security review: verify path validation, admin auth, input sanitization
- [ ] T071 Run quickstart.md validation against implementation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US2 (Single File) → Can start after Foundational - No dependencies
  - US3 (Validation) → Can start after Foundational - No dependencies on US2 (but uses same parsing utilities)
  - US1 (Bulk) → Depends on US2 completion (calls ingest_markdown_file internally)
- **Integration (Phase 6)**: Depends on all user stories being complete
- **Polish (Phase 7)**: Depends on integration testing completion

### User Story Dependencies

- **User Story 2 (P2 - Single File)**: Can start after Foundational - No dependencies on other stories
- **User Story 3 (P3 - Validation)**: Can start after Foundational - Independent (read-only, no database writes)
- **User Story 1 (P1 - Bulk)**: Depends on User Story 2 completion (reuses ingest_markdown_file function)

**Implementation Order**: Phase 1 → Phase 2 → US2 (Phase 3) → US3 (Phase 4) → US1 (Phase 5) → Integration (Phase 6) → Polish (Phase 7)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- **Setup (Phase 1)**: All tasks T001-T004 can run in parallel
- **Foundational (Phase 2)**:
  - T005-T009 (models and utilities) can run in parallel
  - T010-T013 (test fixtures) can run in parallel
  - T014-T016 (unit tests) can run in parallel after their dependencies
- **Within US2**: Tests T017-T021 can run in parallel
- **Within US3**: Tests T032-T035 can run in parallel
- **Within US1**: Tests T041-T045 can run in parallel
- **Integration (Phase 6)**: Tests T055-T058 can run in parallel
- **Polish (Phase 7)**: Tasks T063-T067 can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Launch all model and utility implementations together:
Task: "Create PartyEnum and ChamberEnum in src/models/enums.py"
Task: "Create SpeechFrontmatter model in src/models/speech.py"
Task: "Implement parse_markdown_file() in src/tools/ingest/markdown_parser.py"
Task: "Implement validate_file_path() in src/tools/ingest/path_validator.py"
Task: "Implement require_admin_role() in src/tools/ingest/auth.py"

# Launch all test fixture creation together:
Task: "Create valid_speech.md fixture"
Task: "Create no_frontmatter.md fixture"
Task: "Create malformed_yaml.md fixture"
Task: "Create missing_fields.md fixture"
```

---

## Implementation Strategy

### MVP First (User Story 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 2 (Single File Ingestion)
4. **STOP and VALIDATE**: Test US2 independently with manual file ingestion
5. Deploy/demo if ready - this is a functional MVP (admin can import speeches one at a time)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 2 (Single File) → Test independently → Deploy/Demo (MVP!)
3. Add User Story 3 (Validation) → Test independently → Deploy/Demo
4. Add User Story 1 (Bulk) → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 2 (Single File)
   - Developer B: User Story 3 (Validation) - can proceed in parallel with US2
3. After US2 complete:
   - Developer A or B: User Story 1 (Bulk)
4. Stories complete and integrate independently

---

## Task Summary

- **Total Tasks**: 71
- **Setup**: 4 tasks
- **Foundational**: 12 tasks (CRITICAL PATH)
- **User Story 2 (Single File)**: 15 tasks (5 tests + 10 implementation)
- **User Story 3 (Validation)**: 9 tasks (4 tests + 5 implementation)
- **User Story 1 (Bulk)**: 9 tasks (5 tests + 4 implementation)
- **Integration**: 8 tasks
- **Polish**: 9 tasks

**Parallel Opportunities**: 27 tasks marked [P] can run in parallel within their phase

**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 2) = 31 tasks for single file ingestion MVP

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD workflow)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- US1 (Bulk) depends on US2 (Single File) - implement in that order
- US3 (Validation) is independent and can be developed in parallel with US2
