# Tasks: OAuth 2.1 Compliance

**Input**: Design documents from `/specs/003-oauth2-1-compliance/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: TDD is mandatory per constitution (Section IV). All test tasks MUST be completed before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- Paths shown below use repository root structure per plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and test framework setup

- [x] T001 Verify project structure matches plan.md (src/server.py exists, test directories present)
- [x] T002 [P] Install pytest-asyncio for async test support in test dependencies
- [x] T003 [P] Create tests/unit/ directory if not exists
- [x] T004 [P] Create tests/integration/ directory if not exists

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Read existing src/server.py to understand current middleware stack order
- [x] T006 Identify where GitHubWhitelistMiddleware is added (must add new middleware before it)
- [x] T007 Review Starlette BaseHTTPMiddleware documentation for middleware patterns

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - ChatGPT OAuth Authentication (Priority: P1) 🎯 MVP

**Goal**: Enable ChatGPT to authenticate with the MCP server by stripping RFC 8707 `resource` parameter from OAuth authorization requests

**Independent Test**: Initiate OAuth authorization flow from ChatGPT and verify successful authentication without 400 Bad Request errors

### Tests for User Story 1 (TDD - Write tests FIRST)

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T008 [P] [US1] Create tests/unit/test_oauth_middleware.py with test_strip_resource_parameter test case
- [ ] T009 [P] [US1] Add test_preserve_non_authorize_paths test to tests/unit/test_oauth_middleware.py
- [ ] T010 [P] [US1] Add test_handle_missing_resource_parameter test to tests/unit/test_oauth_middleware.py
- [ ] T011 [P] [US1] Add test_preserve_other_parameters test to tests/unit/test_oauth_middleware.py
- [ ] T012 [US1] Run pytest tests/unit/test_oauth_middleware.py and verify all tests FAIL (no implementation yet)

### Implementation for User Story 1

- [x] T013 [US1] Create OAuthResourceParameterMiddleware class in src/server.py (after imports, before GitHubWhitelistMiddleware)
- [x] T014 [US1] Implement dispatch() method to check if path == "/authorize" and "resource" in query_params
- [x] T015 [US1] Implement URL manipulation to strip resource parameter using Starlette URL class
- [x] T016 [US1] Add app.add_middleware(OAuthResourceParameterMiddleware) before GitHubWhitelistMiddleware registration
- [x] T017 [US1] Add logging statement for middleware enablement: "✅ OAuth resource parameter middleware enabled (RFC 8707 compatibility)"
- [ ] T018 [US1] Run pytest tests/unit/test_oauth_middleware.py and verify all tests PASS

### Integration Testing for User Story 1

- [ ] T019 [US1] Create tests/integration/test_oauth21_flows.py with test_chatgpt_oauth_flow test case
- [ ] T020 [US1] Add test_oauth_with_resource_parameter_succeeds test to tests/integration/test_oauth21_flows.py
- [ ] T021 [US1] Add test_mcp_tools_work_after_oauth test to tests/integration/test_oauth21_flows.py
- [ ] T022 [US1] Run pytest tests/integration/test_oauth21_flows.py and verify all tests PASS

**Checkpoint**: User Story 1 complete - ChatGPT can now authenticate successfully

---

## Phase 4: User Story 2 - Standard OAuth 2.0 Client Compatibility (Priority: P2)

**Goal**: Ensure existing OAuth 2.0 clients (without `resource` parameter) continue to work without regression

**Independent Test**: Connect with an OAuth 2.0 client that doesn't send the `resource` parameter and verify successful authentication

### Tests for User Story 2 (TDD - Write tests FIRST)

**NOTE: Write these tests FIRST, ensure they FAIL or PASS appropriately**

- [ ] T023 [P] [US2] Create tests/integration/test_oauth20_compatibility.py with test_oauth20_without_resource_parameter test case
- [ ] T024 [P] [US2] Add test_oauth20_with_pkce_succeeds test to tests/integration/test_oauth20_compatibility.py
- [ ] T025 [P] [US2] Add test_no_authentication_failures test to tests/integration/test_oauth20_compatibility.py
- [ ] T026 [US2] Run pytest tests/integration/test_oauth20_compatibility.py and verify all tests PASS (middleware should be transparent)

### Implementation for User Story 2

**NOTE**: This story requires NO new code - it validates backward compatibility

- [ ] T027 [US2] Review OAuthResourceParameterMiddleware to confirm it only modifies requests WITH resource parameter
- [ ] T028 [US2] Add inline comment documenting backward compatibility behavior in src/server.py
- [ ] T029 [US2] Run full test suite (pytest tests/) and verify zero regressions

**Checkpoint**: User Story 2 complete - OAuth 2.0 clients maintain 100% compatibility

---

## Phase 5: User Story 3 - MCP Inspector Testing (Priority: P3)

**Goal**: Enable developers to test the OAuth implementation using MCP Inspector

**Independent Test**: Launch MCP Inspector, connect to the OAuth-protected server, and complete the OAuth flow without errors

### Tests for User Story 3 (TDD - Write tests FIRST)

**NOTE: Write these tests FIRST, ensure they FAIL or PASS appropriately**

- [ ] T030 [P] [US3] Create tests/integration/test_mcp_inspector.py with test_inspector_oauth_flow test case
- [ ] T031 [P] [US3] Add test_inspector_discovers_tools test to tests/integration/test_mcp_inspector.py
- [ ] T032 [US3] Run pytest tests/integration/test_mcp_inspector.py and verify all tests PASS

### Implementation for User Story 3

**NOTE**: This story requires NO new code - it validates development workflow

- [ ] T033 [US3] Test MCP Inspector connection manually: `npx @modelcontextprotocol/inspector`
- [ ] T034 [US3] Connect Inspector to http://localhost:8000/mcp and verify OAuth flow completes
- [ ] T035 [US3] Verify Inspector successfully discovers and invokes search/fetch tools
- [ ] T036 [US3] Document Inspector testing procedure in specs/003-oauth2-1-compliance/quickstart.md (already done - verify only)

**Checkpoint**: User Story 3 complete - MCP Inspector works with OAuth 2.1

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, performance, logging, and production readiness

### Edge Case Handling

- [ ] T037 [P] Add test_multiple_resource_parameters test to tests/unit/test_oauth_middleware.py
- [ ] T038 [P] Add test_empty_resource_value test to tests/unit/test_oauth_middleware.py
- [ ] T039 [P] Add test_resource_in_post_body_ignored test to tests/unit/test_oauth_middleware.py
- [ ] T040 Run pytest tests/unit/test_oauth_middleware.py and verify all edge case tests PASS

### Performance Testing

- [ ] T041 [P] Create tests/integration/test_oauth_performance.py with test_middleware_latency test case
- [ ] T042 Add test to verify middleware adds <10ms overhead per authorization request
- [ ] T043 Run pytest tests/integration/test_oauth_performance.py and verify performance within bounds

### Logging & Monitoring

- [ ] T044 Add optional logging when resource parameter is stripped (for debugging) in src/server.py
- [ ] T045 Verify Cloud Run logs capture original request URL with resource parameter (no code change needed)
- [ ] T046 Document log format and troubleshooting in specs/003-oauth2-1-compliance/quickstart.md (already done - verify only)

### Production Deployment

- [ ] T047 Build Docker image: `gcloud builds submit --config=cloudbuild.yaml --project=skai-fastmcp-cloudrun`
- [ ] T048 Deploy to Cloud Run: `gcloud run deploy hansard-mcp-server --image gcr.io/skai-fastmcp-cloudrun/hansard-mcp:latest`
- [ ] T049 Verify deployment logs show middleware initialization message
- [ ] T050 Test ChatGPT OAuth flow against production URL (https://mcp.simonkennedymp.com.au)
- [ ] T051 Monitor Cloud Run logs for OAuth 2.1 requests with resource parameter
- [ ] T052 Update CLAUDE.md Active Technologies section with OAuth 2.1 compliance (already done - verify only)

**Checkpoint**: Feature complete - OAuth 2.1 compliance deployed to production

---

## Implementation Strategy

### MVP Scope (User Story 1 Only)

**Recommended first delivery**: Implement only Phase 3 (User Story 1) to unblock ChatGPT integration immediately.

**MVP Tasks**: T001-T022 (22 tasks)

**MVP Deliverable**: ChatGPT users can authenticate successfully without 400 Bad Request errors

### Incremental Delivery

- **Sprint 1**: Setup + Foundational + US1 (T001-T022) - **ChatGPT integration unblocked**
- **Sprint 2**: US2 + US3 (T023-T036) - Backward compatibility validated, developer tooling verified
- **Sprint 3**: Polish + Deployment (T037-T052) - Edge cases, performance, production deployment

### Parallel Execution Opportunities

**Phase 1 (Setup)**: All tasks can run in parallel (T002-T004 marked with [P])

**Phase 3 (US1 Tests)**: T008-T011 can run in parallel (all marked with [P])

**Phase 3 (US1 Integration)**: T019-T021 can be written in parallel after T018 completes

**Phase 4 (US2 Tests)**: T023-T025 can run in parallel (all marked with [P])

**Phase 5 (US3 Tests)**: T030-T031 can run in parallel (both marked with [P])

**Phase 6 (Polish)**: T037-T039 can run in parallel (all marked with [P])

---

## Dependencies & Completion Order

### Story Dependencies

1. **User Story 1** (US1) - No dependencies, can start immediately after Foundation
2. **User Story 2** (US2) - Depends on US1 (needs middleware to exist for backward compatibility testing)
3. **User Story 3** (US3) - Depends on US1 (needs working OAuth 2.1 implementation)

### Critical Path

```
T001-T007 (Setup + Foundation)
  ↓
T008-T018 (US1 Tests + Implementation) ← CRITICAL for ChatGPT
  ↓
T019-T022 (US1 Integration Tests)
  ↓
T023-T029 (US2 Backward Compatibility)
  ↓
T030-T036 (US3 Inspector Testing)
  ↓
T037-T052 (Polish + Deployment)
```

### Parallelization Strategy

- Setup phase (T002-T004): 3 tasks in parallel
- US1 tests (T008-T011): 4 tasks in parallel
- US2 tests (T023-T025): 3 tasks in parallel
- US3 tests (T030-T031): 2 tasks in parallel
- Edge cases (T037-T039): 3 tasks in parallel

**Total Parallelizable Tasks**: 15 out of 52 tasks (29%)

---

## Task Summary

- **Total Tasks**: 52
- **Setup**: 4 tasks (T001-T004)
- **Foundational**: 3 tasks (T005-T007)
- **User Story 1**: 15 tasks (T008-T022) - 🎯 MVP
- **User Story 2**: 7 tasks (T023-T029)
- **User Story 3**: 7 tasks (T030-T036)
- **Polish**: 16 tasks (T037-T052)

**Parallelizable**: 15 tasks marked with [P]

**MVP Estimate**: ~22 tasks to unblock ChatGPT integration

**Full Feature Estimate**: 52 tasks total for complete OAuth 2.1 compliance with all stories

---

## Testing Strategy

Per constitution Section IV (Test-Driven Development - NON-NEGOTIABLE), all tests MUST be written before implementation:

1. **Unit Tests** (tests/unit/test_oauth_middleware.py): Test middleware logic in isolation
2. **Integration Tests** (tests/integration/test_oauth*_*.py): Test end-to-end OAuth flows
3. **Performance Tests** (tests/integration/test_oauth_performance.py): Verify <10ms overhead
4. **Manual Testing**: MCP Inspector, ChatGPT integration

**Red-Green-Refactor Cycle**:
- Red: Write failing tests (T008-T012)
- Green: Implement minimum code to pass tests (T013-T018)
- Refactor: Clean up code while maintaining green tests (covered in implementation tasks)

---

## Success Criteria Validation

Each user story maps to specific success criteria from spec.md:

| User Story | Success Criteria | Validation Tasks |
|------------|------------------|------------------|
| US1 | SC-001: ChatGPT 100% success rate | T019-T022, T050 |
| US1 | SC-002: <5 second auth flow | T042-T043 |
| US2 | SC-003: Zero OAuth 2.0 failures | T023-T029 |
| US1 | SC-004: Clear logs for troubleshooting | T044-T046 |
| US3 | SC-005: Inspector connects on first attempt | T033-T035 |

All success criteria covered by test tasks.
