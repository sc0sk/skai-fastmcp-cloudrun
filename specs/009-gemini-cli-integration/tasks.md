# Tasks: Google Gemini CLI Integration

**Input**: Design documents from `/home/user/skai-fastmcp-cloudrun/specs/009-gemini-cli-integration/`
**Prerequisites**: spec.md, plan.md, research.md, data-model.md, quickstart.md, contracts/ (all complete)

**Feature Type**: Documentation-only (no code changes, no tests required)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each documentation deliverable.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create documentation directory structure for user-facing Gemini CLI guides

- [X] T001 Create `/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/` directory
- [X] T002 Create `/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/` subdirectory

**Checkpoint**: Directory structure ready for documentation files

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create overview documentation that ALL user stories reference

**Critical**: No user story work can begin until this phase is complete

- [X] T003 Write `/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/README.md` overview with navigation to all guides
- [X] T004 Copy `/home/user/skai-fastmcp-cloudrun/specs/009-gemini-cli-integration/contracts/stdio-config.json` to `/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/stdio-config.json`
- [X] T005 Copy `/home/user/skai-fastmcp-cloudrun/specs/009-gemini-cli-integration/contracts/sse-config.json` to `/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/sse-config.json`
- [X] T006 Copy `/home/user/skai-fastmcp-cloudrun/specs/009-gemini-cli-integration/contracts/test-scenarios.json` to `/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/test-scenarios.json`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Local Development with STDIO Transport (Priority: P1)

**Goal**: Developers complete local STDIO setup in under 10 minutes using step-by-step guide

**Independent Test**: Follow `stdio-setup.md` from scratch, configure Gemini CLI, run test commands, and verify tools are discoverable

### Implementation for User Story 1

- [X] T007 [US1] Write `/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/stdio-setup.md` with prerequisites section (Gemini CLI installation, FastMCP installation, Python version requirements)
- [X] T008 [US1] Add quick setup section to `stdio-setup.md` (5-minute configuration steps with copy-paste examples for macOS/Linux/Windows)
- [X] T009 [US1] Add verification section to `stdio-setup.md` (3 test commands: tool discovery, search query, fetch by ID with expected outputs)
- [X] T010 [US1] Add troubleshooting section to `stdio-setup.md` (3 common issues: command not found, module import errors, empty tool list with diagnostic commands)
- [X] T011 [US1] Add configuration reference section to `stdio-setup.md` (minimal vs full config examples, environment variable explanations)
- [X] T012 [US1] Create `/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/stdio-quickstart.sh` shell script with automated setup commands for Unix systems
- [X] T013 [US1] Create `/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/stdio-quickstart.ps1` PowerShell script with automated setup commands for Windows

**Checkpoint**: User Story 1 complete - users can set up local STDIO connection in under 10 minutes

---

## Phase 4: User Story 2 - Remote Cloud Run Integration with SSE Transport (Priority: P2)

**Goal**: Users configure remote SSE connection to Cloud Run and execute queries in under 15 minutes

**Independent Test**: Follow `sse-setup.md`, configure Cloud Run endpoint, authenticate, run search query, and verify results from cloud database

### Implementation for User Story 2

- [X] T014 [US2] Write `/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/sse-setup.md` with prerequisites section (deployed Cloud Run service, authentication token generation, network access)
- [X] T015 [US2] Add Cloud Run deployment section to `sse-setup.md` (verify service URL, check authentication requirements, test endpoint availability)
- [X] T016 [US2] Add authentication section to `sse-setup.md` (user identity token vs service account token with gcloud commands, token rotation best practices)
- [X] T017 [US2] Add SSE configuration section to `sse-setup.md` (copy-paste config template, URL format explanation, header requirements)
- [X] T018 [US2] Add verification section to `sse-setup.md` (connection test, tool discovery, remote query execution with expected response times)
- [X] T019 [US2] Add performance section to `sse-setup.md` (cold start delays, query response times, timeout configuration recommendations)
- [X] T020 [US2] Add security section to `sse-setup.md` (token expiration, credentials management, production best practices)
- [X] T021 [US2] Create `/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/sse-token-refresh.sh` shell script to automate token generation and config updates

**Checkpoint**: User Story 2 complete - users can set up remote SSE connection and understand production deployment

---

## Phase 5: User Story 3 - Comprehensive Setup Documentation (Priority: P3)

**Goal**: Self-service documentation with troubleshooting that resolves 80% of issues without external support

**Independent Test**: Intentionally misconfigure Gemini CLI, use troubleshooting guide to diagnose and fix, verify all test scenarios pass

### Implementation for User Story 3

- [X] T022 [P] [US3] Write `/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md` with overview of common failure categories (connection, authentication, version compatibility, data issues)
- [X] T023 [P] [US3] Add connection issues section to `troubleshooting.md` (STDIO process not starting, SSE endpoint unreachable, timeout errors with diagnostic commands)
- [X] T024 [P] [US3] Add authentication issues section to `troubleshooting.md` (token expired, missing credentials, permission denied errors with solutions)
- [X] T025 [P] [US3] Add version compatibility section to `troubleshooting.md` (Gemini CLI version mismatches, FastMCP version requirements, Python version issues)
- [X] T026 [P] [US3] Add data issues section to `troubleshooting.md` (database not initialized, empty results, query errors with verification commands)
- [X] T027 [P] [US3] Write `/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/test-scenarios.md` with test execution guide (prerequisite checks, recommended test order, success criteria)
- [X] T028 [P] [US3] Add Test 1 (Tool Discovery) to `test-scenarios.md` with command, expected output, success criteria, and troubleshooting steps
- [X] T029 [P] [US3] Add Test 2 (Search Query) to `test-scenarios.md` with sample queries, expected results format, and failure debugging
- [X] T030 [P] [US3] Add Test 3 (Fetch by ID) to `test-scenarios.md` with ID format requirements, full speech output example, and common errors
- [X] T031 [P] [US3] Add platform-specific notes section to `troubleshooting.md` (macOS PATH issues, Windows PowerShell execution policy, Linux permissions)

**Checkpoint**: User Story 3 complete - comprehensive troubleshooting and testing documentation enables self-service setup

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final review, integration testing, and project documentation updates

- [X] T032 Review all documentation files for consistency in formatting, terminology, and code examples
- [X] T033 Verify all file paths in documentation are absolute paths (no relative paths)
- [X] T034 Test all copy-paste code examples for syntax correctness (JSON configs, shell commands, PowerShell scripts)
- [X] T035 Verify all cross-references between documents are correct (README navigation links, troubleshooting references)
- [X] T036 Update `/home/user/skai-fastmcp-cloudrun/CLAUDE.md` with new documentation paths and Gemini CLI integration commands
- [X] T037 Add Gemini CLI integration section to CLAUDE.md under "Commands" with references to new docs

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 2 (P2): Can start after Foundational - No dependencies on other stories
  - User Story 3 (P3): Can start after Foundational - No dependencies on other stories
  - **All three user stories can proceed in parallel** (different .md files)
- **Polish (Phase 6)**: Depends on all user stories being complete

### Within Each User Story

**User Story 1 (STDIO)**:
- T007 (prerequisites) → T008 (setup) → T009 (verification) → T010 (troubleshooting) → T011 (reference)
- T012 and T013 (scripts) can run in parallel after T008

**User Story 2 (SSE)**:
- T014 (prerequisites) → T015 (deployment) → T016 (auth) → T017 (config) → T018 (verification)
- T019 (performance) and T020 (security) can run in parallel after T018
- T021 (script) depends on T016

**User Story 3 (Documentation Polish)**:
- T022-T026 (troubleshooting sections) can all run in parallel (different sections)
- T027-T030 (test scenarios) can all run in parallel (different test cases)
- T031 (platform notes) can run in parallel with other tasks

### Parallel Opportunities

**After Foundational phase completes, these tasks can run in parallel**:

```bash
# Launch all User Story 1 foundational tasks
Task T007: "Write stdio-setup.md prerequisites"
Task T014: "Write sse-setup.md prerequisites"
Task T022: "Write troubleshooting.md overview"

# Launch all script creation tasks together (different files)
Task T012: "Create stdio-quickstart.sh"
Task T013: "Create stdio-quickstart.ps1"
Task T021: "Create sse-token-refresh.sh"

# Launch all troubleshooting sections together (different sections)
Task T023: "Add connection issues section"
Task T024: "Add authentication issues section"
Task T025: "Add version compatibility section"
Task T026: "Add data issues section"

# Launch all test scenario tasks together (different test cases)
Task T028: "Add Test 1 (Tool Discovery)"
Task T029: "Add Test 2 (Search Query)"
Task T030: "Add Test 3 (Fetch by ID)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only - Local STDIO)

1. Complete Phase 1: Setup (2 tasks, 5 min)
2. Complete Phase 2: Foundational (4 tasks, 15 min)
3. Complete Phase 3: User Story 1 (7 tasks, 45 min)
4. **STOP and VALIDATE**: Test local STDIO setup following `stdio-setup.md`
5. Deploy/share documentation for local development use case

**Estimated time**: 65 minutes for MVP

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (20 min)
2. Add User Story 1 → Test independently → Share local dev docs (45 min) **MVP!**
3. Add User Story 2 → Test independently → Share remote SSE docs (50 min)
4. Add User Story 3 → Test independently → Share comprehensive docs (50 min)
5. Polish → Final review and publish (30 min)

**Total estimated time**: 2.5 hours (matches plan.md estimate)

### Parallel Team Strategy

With multiple documentation writers:

1. Team completes Setup + Foundational together (20 min)
2. Once Foundational is done:
   - **Writer A**: User Story 1 (stdio-setup.md + scripts)
   - **Writer B**: User Story 2 (sse-setup.md + scripts)
   - **Writer C**: User Story 3 (troubleshooting.md + test-scenarios.md)
3. Stories complete independently, then integrate in Polish phase

**Estimated time with 3 writers**: 90 minutes total (parallel execution)

---

## Deliverable Files Summary

### User-Facing Documentation (`/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/`)

| File | User Story | Purpose | Estimated Words |
|------|-----------|---------|----------------|
| `README.md` | Foundation | Navigation and overview | 300 |
| `stdio-setup.md` | US1 (P1) | Local STDIO setup guide | 1500 |
| `sse-setup.md` | US2 (P2) | Remote SSE setup guide | 1800 |
| `troubleshooting.md` | US3 (P3) | Common issues and solutions | 1200 |
| `test-scenarios.md` | US3 (P3) | Verification test guide | 800 |

### Configuration Examples (`/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/`)

| File | Source | Purpose |
|------|--------|---------|
| `stdio-config.json` | Copied from contracts/ | STDIO configuration template |
| `sse-config.json` | Copied from contracts/ | SSE configuration template |
| `test-scenarios.json` | Copied from contracts/ | Test scenario definitions |
| `stdio-quickstart.sh` | New (US1) | Unix setup automation |
| `stdio-quickstart.ps1` | New (US1) | Windows setup automation |
| `sse-token-refresh.sh` | New (US2) | Token generation automation |

**Total**: 5 documentation files + 6 example/script files = **11 deliverable files**

---

## Notes

- NO code changes to `src/` directory (documentation-only feature)
- NO tests required (manual verification via test scenarios)
- [P] tasks marked for parallel execution (different files, no dependencies)
- [Story] labels map tasks to user stories for traceability
- Each user story independently deliverable and testable
- Total word count: ~5600 words (within 5000 word per guide constraint from plan.md)
- Commit after each user story phase completion
- Verify all copy-paste examples work before marking tasks complete
- Use absolute paths in all documentation (no relative paths or environment variables)
