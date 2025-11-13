# Tasks: Fix Cloud Run Database IAM Authentication

**Input**: Design documents from `/specs/019-fix-cloudrun-db-auth/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Tests**: TDD approach - tests written FIRST, must FAIL before implementation

**Organization**: Tasks grouped by user story (P1, P2, P3) for independent implementation and testing

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Project type**: Single project (backend service)
- **Source**: `src/` at repository root
- **Tests**: `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ensure baseline test environment and branch are ready

- [ ] T001 Verify feature branch 019-fix-cloudrun-db-auth is checked out
- [ ] T002 Run existing baseline tests to confirm 10/10 pass rate in tests/test_full_ingestion_tdd.py
- [ ] T003 [P] Install test dependencies: pytest-mock, requests-mock (if not present)
- [ ] T004 [P] Create test directory structure: tests/integration/ and tests/mocks/

**Checkpoint**: Baseline tests passing (10/10), test infrastructure ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure changes needed before any user story work

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Add IAM principal detection properties to CloudSQLEngine in src/storage/cloud_sql_engine.py
  - Add instance variables: `_detected_iam_user`, `_detection_method`, `_iam_valid`
  - Add read-only properties: `detected_iam_user`, `detection_method`, `iam_valid`
- [ ] T006 [P] Add IAM detection logging schema to src/storage/cloud_sql_engine.py
  - Log connection attempts at INFO level with detection method
  - Log connection success/failure with IAM user details
- [ ] T007 [P] Create test fixtures for Cloud Run mocking in tests/mocks/cloud_run_fixtures.py
  - Fixture: `mock_cloud_run_env` (sets K_SERVICE env var)
  - Fixture: `mock_metadata_service` (mocks requests to metadata endpoint)
  - Fixture: `mock_local_adc` (mocks google.auth.default for local dev)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Database Connection Works in Cloud Run Environment (Priority: P1) 🎯 MVP

**Goal**: Fix Cloud Run IAM authentication so metadata service properly detects service account email (not "default")

**Independent Test**: Deploy to Cloud Run, call `/debug/iam-user` endpoint, verify correct service account email returned

### Tests for User Story 1 (TDD - Write FIRST, Must FAIL)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T008 [P] [US1] Create test file tests/test_cloud_run_iam_auth.py
- [ ] T009 [P] [US1] Write test_detects_service_account_from_metadata_service in tests/test_cloud_run_iam_auth.py
  - Mock K_SERVICE environment variable
  - Mock metadata service HTTP endpoint
  - Verify detected_iam_user == "666924716777-compute@developer.gserviceaccount.com"
  - Verify detection_method == "METADATA_SERVICE"
  - **Expected: FAIL** (properties not implemented yet)
- [ ] T010 [P] [US1] Write test_rejects_default_placeholder_from_adc in tests/test_cloud_run_iam_auth.py
  - Mock google.auth.default() returning "default" placeholder
  - Verify detected_iam_user != "default"
  - Verify iam_valid == False or fallback method used
  - **Expected: FAIL** (no validation logic for "default" yet)
- [ ] T011 [P] [US1] Write test_logs_iam_detection_method in tests/test_cloud_run_iam_auth.py
  - Mock metadata service
  - Verify INFO log contains detection_method and detected IAM user
  - **Expected: FAIL** (logging not implemented yet)

### Implementation for User Story 1

- [ ] T012 [US1] Implement metadata service IAM detection in src/storage/cloud_sql_engine.py (getconn function, lines 184-193)
  - Check K_SERVICE environment variable
  - Make HTTP request to metadata.google.internal with Metadata-Flavor header
  - Store result in `_detected_iam_user` if successful
  - Set `_detection_method = "METADATA_SERVICE"`
  - Set `_iam_valid = True` if email contains "@" and is not "default"
- [ ] T013 [US1] Add "default" placeholder filtering in src/storage/cloud_sql_engine.py (lines 196-210)
  - After ADC detection, check if email == "default"
  - If "default", skip to next detection method
  - Log warning when "default" placeholder detected
- [ ] T014 [US1] Add IAM user logging in src/storage/cloud_sql_engine.py (lines 256-266)
  - Log detected_iam_user, detection_method, iam_valid at INFO level
  - Include instance, database, driver in log context
- [ ] T015 [US1] Run tests for User Story 1: pytest tests/test_cloud_run_iam_auth.py -v
  - **Expected: ALL PASS** (3 tests)
- [ ] T016 [US1] Regression test: Run baseline tests to ensure no breakage
  - pytest tests/test_full_ingestion_tdd.py -v
  - **Expected: 10/10 PASS** (no regression)

**Checkpoint**: Cloud Run metadata service detection working, tests passing, no regression

---

## Phase 4: User Story 2 - Local Development Continues to Work (Priority: P2)

**Goal**: Ensure local development with ADC continues working, maintaining 10/10 test pass rate

**Independent Test**: Run pytest tests/test_full_ingestion_tdd.py locally with USE_IAM_AUTH=true, verify 10/10 pass

### Tests for User Story 2 (TDD - Write FIRST, Must FAIL)

- [ ] T017 [P] [US2] Create test file tests/test_local_iam_auth.py
- [ ] T018 [P] [US2] Write test_detects_service_account_from_local_adc in tests/test_local_iam_auth.py
  - Mock google.auth.default() with valid service account credentials
  - Mock service_account_email attribute
  - Verify detected_iam_user == service account email
  - Verify detection_method == "ADC_CREDENTIALS"
  - **Expected: FAIL** (detection method not exposed yet)
- [ ] T019 [P] [US2] Write test_falls_back_to_gcloud_config in tests/test_local_iam_auth.py
  - Mock ADC to fail
  - Mock subprocess gcloud config get-value account
  - Verify detected_iam_user == gcloud account
  - Verify detection_method == "GCLOUD_CONFIG"
  - **Expected: FAIL** (gcloud fallback not instrumented)
- [ ] T020 [P] [US2] Write integration test in tests/integration/test_cloud_sql_connection.py
  - Real Cloud SQL connection with IAM auth (no mocks)
  - Verify connection succeeds, query returns result
  - Verify detected_iam_user is valid (contains "@", not "default")
  - **Expected: FAIL or SKIP** (requires local credentials)

### Implementation for User Story 2

- [ ] T021 [US2] Instrument ADC detection method in src/storage/cloud_sql_engine.py (lines 196-210)
  - Set `_detection_method = "ADC_CREDENTIALS"` when ADC succeeds
  - Validate email is not empty, not "default", contains "@"
  - Set `_iam_valid` based on validation
- [ ] T022 [US2] Instrument gcloud config detection in src/storage/cloud_sql_engine.py (lines 213-224)
  - Set `_detection_method = "GCLOUD_CONFIG"` when gcloud succeeds
  - Validate email format
  - Set `_iam_valid` based on validation
- [ ] T023 [US2] Add fallback instrumentation in src/storage/cloud_sql_engine.py (lines 227-228)
  - Set `_detection_method = "FALLBACK"` when all methods fail
  - Set `_iam_valid = False`
  - Log warning about using fallback
- [ ] T024 [US2] Run tests for User Story 2: pytest tests/test_local_iam_auth.py -v
  - **Expected: 2 unit tests PASS, 1 integration test PASS or SKIP**
- [ ] T025 [US2] Regression test: Verify existing tests still pass
  - pytest tests/test_full_ingestion_tdd.py -v
  - **Expected: 10/10 PASS** (local development preserved)

**Checkpoint**: Local ADC detection working, all tests passing, backward compatibility maintained

---

## Phase 5: User Story 3 - Clear Error Messages for Misconfiguration (Priority: P3)

**Goal**: Provide clear diagnostic messages when connection fails due to misconfiguration

**Independent Test**: Intentionally misconfigure (wrong instance, missing role), verify error messages indicate problem and suggest fix

### Tests for User Story 3 (TDD - Write FIRST, Must FAIL)

- [ ] T026 [P] [US3] Create test file tests/test_iam_error_handling.py
- [ ] T027 [P] [US3] Write test_clear_error_for_invalid_iam_user in tests/test_iam_error_handling.py
  - Mock all detection methods to return invalid users
  - Verify error message mentions "IAM user detection failed"
  - Verify error message suggests checking IAM roles
  - **Expected: FAIL** (error handling not implemented)
- [ ] T028 [P] [US3] Write test_clear_error_for_pgvector_extension in tests/test_iam_error_handling.py
  - Mock extension check to return False
  - Verify RuntimeError raised with "pgvector extension is not enabled"
  - Verify error message shows CREATE EXTENSION command
  - **Expected: PASS** (already implemented in postgres_vector_store.py:317-340)
- [ ] T029 [P] [US3] Write test_clear_error_for_missing_database_user in tests/test_iam_error_handling.py
  - Mock connection to raise "role ... does not exist"
  - Verify error message displays attempted user and expected user
  - Verify error message suggests checking database users
  - **Expected: FAIL** (error enhancement not implemented)

### Implementation for User Story 3

- [ ] T030 [US3] Add validation for detected IAM user in src/storage/cloud_sql_engine.py (after line 228)
  - Raise RuntimeError if `_iam_valid == False` and all methods failed
  - Include detected user, detection method, and troubleshooting steps in error
  - Suggest checking: IAM roles, K_SERVICE env var, ADC setup, gcloud auth
- [ ] T031 [US3] Enhance database user mismatch error in src/storage/cloud_sql_engine.py (getconn exception handling)
  - Catch "role ... does not exist" errors
  - Re-raise with context: attempted user, service account email, database
  - Suggest running GRANT statements from GRANT_CLOUD_RUN_PERMISSIONS.sql
- [ ] T032 [US3] Add connection failure logging in src/storage/cloud_sql_engine.py
  - Log ERROR level for permanent failures (auth, user mismatch)
  - Include suggestion field in structured logs
  - Log example troubleshooting commands
- [ ] T033 [US3] Run tests for User Story 3: pytest tests/test_iam_error_handling.py -v
  - **Expected: ALL PASS** (3 tests)
- [ ] T034 [US3] Regression test: Verify all previous tests still pass
  - pytest tests/ -v
  - **Expected: 10 baseline + 3 US1 + 2 US2 + 3 US3 = 18 PASS**

**Checkpoint**: All error handling tests passing, clear diagnostic messages implemented

---

## Phase 6: Cloud Run Deployment & Validation

**Purpose**: Deploy to Cloud Run and validate IAM authentication works in production

- [ ] T035 Deploy updated code to Cloud Run using gcloud run deploy
  - Service: hansard-mcp-server
  - Region: us-central1
  - Service account: 666924716777-compute@developer
  - Environment: USE_IAM_AUTH=true
- [ ] T036 Test debug endpoint /debug/iam-user from Cloud Run
  - Expected: detected_iam_user = "666924716777-compute@developer.gserviceaccount.com"
  - Expected: detection_method = "METADATA_SERVICE"
  - Expected: iam_valid = true
  - Expected: connection_test = "SUCCESS"
- [ ] T037 [P] Test search MCP tool from Cloud Run
  - POST to /mcp/tools/search_hansard_speeches
  - Query: "housing affordability"
  - Expected: 5 results returned, no auth errors
- [ ] T038 [P] Test fetch MCP tool from Cloud Run
  - POST to /mcp/tools/fetch_hansard_speech
  - Use existing speech ID from database
  - Expected: Full speech text returned, no auth errors
- [ ] T039 Review Cloud Run logs for IAM authentication events
  - Filter: jsonPayload.event="CloudSQLEngine connecting"
  - Verify: iam_user != "default"
  - Verify: detection_method = "METADATA_SERVICE"
  - Verify: No authentication errors

**Checkpoint**: Cloud Run deployment successful, all MCP tools working, IAM auth confirmed

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, and 24-hour stability validation

- [ ] T040 [P] Update quickstart.md with actual test results and debugging tips
  - Document what was fixed
  - Include example debug endpoint responses
  - Add troubleshooting section from test learnings
- [ ] T041 [P] Create checklists/implementation.md with completion checklist
  - All tests passing (18 total)
  - Cloud Run deployment successful
  - Debug endpoint returning correct IAM user
  - MCP tools working in Cloud Run
  - No regression in local development
- [ ] T042 Run full test suite to confirm all tests passing
  - pytest tests/ -v --tb=short
  - Expected: 18 tests PASS (10 baseline + 8 new)
- [ ] T043 Code review: Review IAM detection logic for edge cases
  - Verify timeout handling for metadata service
  - Verify graceful fallback on failures
  - Verify logging doesn't expose sensitive data
- [ ] T044 Monitor Cloud Run for 24-hour stability (per SC-006)
  - Script: Hourly curl to /debug/iam-user for 24 hours
  - Verify: connection_test = "SUCCESS" all 24 checks
  - Verify: No IAM token expiry errors in logs
- [ ] T045 [P] Update CLAUDE.md with learnings about IAM detection patterns
  - Document Cloud Run metadata service pattern
  - Document "default" placeholder filtering
  - Document TDD approach for IAM authentication
- [ ] T046 Commit all changes with detailed commit message
  - Include: What was fixed, how it was tested, results
  - Reference: spec.md, plan.md, tasks.md
  - Include TDD test results summary

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-5)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - HIGHEST PRIORITY
  - User Story 2 (P2): Can start after Foundational - Independent of US1
  - User Story 3 (P3): Can start after Foundational - Independent of US1/US2
- **Cloud Run Deployment (Phase 6)**: Depends on US1 completion (minimum) or all user stories (recommended)
- **Polish (Phase 7)**: Depends on Cloud Run deployment validation

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories - Can implement independently
- **User Story 2 (P2)**: No dependencies on other stories - Can implement independently (but benefits from US1 tests)
- **User Story 3 (P3)**: No dependencies on other stories - Can implement independently (enhances errors from US1/US2)

### Within Each User Story

**TDD Workflow (Critical)**:
1. Write tests FIRST (Tasks marked "Write test_...")
2. Run tests → **Verify they FAIL**
3. Implement code (Tasks marked "Implement...")
4. Run tests → **Verify they PASS**
5. Regression test → **Verify no breakage**

**Dependencies within stories**:
- Tests before implementation (TDD)
- Properties before logging (need data to log)
- Detection logic before validation (need data to validate)
- Implementation before regression test

### Parallel Opportunities

**Within Setup (Phase 1)**:
- T003 and T004 can run in parallel

**Within Foundational (Phase 2)**:
- T006 and T007 can run in parallel (different files)

**Within User Story 1**:
- T009, T010, T011 (all tests) can run in parallel
- T012, T013, T014 must run sequentially (same file)

**Within User Story 2**:
- T018, T019, T020 (all tests) can run in parallel
- T021, T022, T023 must run sequentially (same file, same function)

**Within User Story 3**:
- T027, T028, T029 (all tests) can run in parallel
- T030, T031, T032 must run sequentially (same file)

**Within Cloud Run Deployment (Phase 6)**:
- T037 and T038 (test different tools) can run in parallel

**Within Polish (Phase 7)**:
- T040, T041, T045 (different files) can run in parallel

**Across User Stories**:
- After Foundational (Phase 2) completes, US1, US2, US3 can all run in parallel (if team capacity allows)

---

## Parallel Example: User Story 1

```bash
# Step 1: Launch all test writing tasks in parallel
Task: "Write test_detects_service_account_from_metadata_service in tests/test_cloud_run_iam_auth.py"
Task: "Write test_rejects_default_placeholder_from_adc in tests/test_cloud_run_iam_auth.py"
Task: "Write test_logs_iam_detection_method in tests/test_cloud_run_iam_auth.py"

# Step 2: Run tests, verify they FAIL
pytest tests/test_cloud_run_iam_auth.py -v

# Step 3: Implement fixes sequentially (same file)
# T012 → T013 → T014

# Step 4: Run tests, verify they PASS
pytest tests/test_cloud_run_iam_auth.py -v

# Step 5: Regression test
pytest tests/test_full_ingestion_tdd.py -v
```

---

## Implementation Strategy

### MVP First (User Story 1 Only - Minimum Viable Fix)

1. Complete Phase 1: Setup → Baseline confirmed
2. Complete Phase 2: Foundational → Properties and logging ready
3. Complete Phase 3: User Story 1 → Cloud Run metadata detection working
4. **STOP and VALIDATE**: Run tests, deploy to Cloud Run, test debug endpoint
5. **Success Criteria**: `/debug/iam-user` returns correct service account (not "default")

**Estimated Tasks**: T001-T016 (16 tasks)
**Estimated Time**: 2-4 hours
**Deliverable**: Cloud Run IAM authentication working (critical blocker resolved)

### Incremental Delivery (Recommended Full Implementation)

1. Setup + Foundational → T001-T007 → Foundation ready
2. Add User Story 1 → T008-T016 → Cloud Run working → **Deploy & Validate**
3. Add User Story 2 → T017-T025 → Local dev validated → **Regression Test**
4. Add User Story 3 → T026-T034 → Error handling improved → **All Tests Passing**
5. Cloud Run Deployment → T035-T039 → Production validation → **MCP Tools Working**
6. Polish → T040-T046 → Documentation + 24h stability → **Feature Complete**

**Total Tasks**: 46
**Estimated Time**: 6-8 hours
**Success Criteria**: All 18 tests passing, Cloud Run working, 24h stable

### Parallel Team Strategy

With 2 developers:

1. **Both**: Complete Setup + Foundational together (T001-T007)
2. **Split after Foundational**:
   - Developer A: User Story 1 (T008-T016) - CRITICAL PATH
   - Developer B: User Story 2 (T017-T025) + User Story 3 (T026-T034)
3. **Merge**: Developer A deploys US1 to Cloud Run (T035-T039)
4. **Both**: Polish together (T040-T046)

**Estimated Time**: 4-5 hours (parallelized)

---

## Task Statistics

**Total Tasks**: 46
- Phase 1 (Setup): 4 tasks
- Phase 2 (Foundational): 3 tasks
- Phase 3 (User Story 1 - P1): 9 tasks (3 tests + 6 implementation)
- Phase 4 (User Story 2 - P2): 9 tasks (3 tests + 6 implementation)
- Phase 5 (User Story 3 - P3): 8 tasks (3 tests + 5 implementation)
- Phase 6 (Cloud Run Deployment): 5 tasks
- Phase 7 (Polish): 8 tasks

**Test Tasks**: 15 (all marked TDD - write first, must fail)
**Parallel Tasks**: 16 (marked [P])
**Story Tasks**: 26 (marked [US1], [US2], or [US3])

**Independent Testing Criteria**:
- **US1**: Deploy to Cloud Run, `/debug/iam-user` returns correct SA email
- **US2**: Run local tests with ADC, 10/10 pass rate maintained
- **US3**: Trigger misconfiguration, verify error messages are clear

**Success Metrics** (from spec.md):
- ✅ SC-001: Cloud Run connects within 30s
- ✅ SC-002: All MCP tools work (search <10s, fetch <1s, ingest <60s)
- ✅ SC-003: 10/10 local tests still pass
- ✅ SC-004: Debug endpoint returns correct email (not "default")
- ✅ SC-005: Zero auth errors in Cloud Run logs
- ✅ SC-006: 24-hour connection stability (T044)
- ✅ SC-007: Error messages reduce troubleshooting time 75%

---

## Notes

- **[P] tasks** = Different files, no dependencies, can parallelize
- **[Story] label** = Maps task to specific user story for traceability
- **TDD Critical**: Tests MUST be written first, MUST fail before implementation
- **Each user story** independently completable and testable
- **Regression testing**: After each story, run baseline tests (10/10 must pass)
- **Commit strategy**: Commit after each user story phase completes
- **MVP**: Can stop after US1 (T016) if only critical blocker needs fixing
- **Full implementation**: Complete all 46 tasks for comprehensive solution
