# Tasks: ChatGPT Developer Mode Enhancements

**Feature Branch**: `001-chatgpt-devmode-enhancements`
**Date**: 2025-10-22
**Status**: Ready for Implementation

## Overview

This feature enhances existing MCP tools with ChatGPT Developer Mode optimizations: tool annotations (`readOnlyHint`), improved descriptions with "Use this when..." guidance, parameter enums, and GPT-5-optimized tool selection guidance. All changes are metadata-only - no functional modifications to existing tools.

**Total Tasks**: 42
**Estimated Effort**: 8-12 hours
**MVP Scope**: User Story 1 (Tool Discoverability) - 15 tasks

---

## Implementation Strategy

### Incremental Delivery Approach

1. **MVP (User Story 1)**: Enhanced tool descriptions with "Use this when..." guidance
   - **Value**: ChatGPT uses MCP tools instead of built-in browsing
   - **Test**: Ask ChatGPT "Find Simon Kennedy's speeches about housing" → uses MCP tool
   - **Effort**: ~4 hours

2. **Increment 2 (User Story 2)**: Add `readOnlyHint` annotations
   - **Value**: No confirmation prompts for read operations
   - **Test**: Verify no confirmation dialog when calling search/fetch tools
   - **Effort**: ~2 hours

3. **Increment 3 (User Story 3)**: Parameter enums and descriptions
   - **Value**: ChatGPT uses exact enum values, fewer parameter errors
   - **Test**: Verify ChatGPT uses `party="Labor"` not "Labour"
   - **Effort**: ~3 hours

4. **Increment 4 (User Story 4)**: Tool selection guidance
   - **Value**: ChatGPT prioritizes MCP tools over built-in capabilities
   - **Test**: Complex queries use MCP search first
   - **Effort**: ~2 hours

---

## Dependencies

### User Story Completion Order

```
Setup Phase (Phase 1)
  ↓
Foundational Phase (Phase 2)
  ↓
├─→ User Story 1 (P1) ← MVP - Can deploy independently
├─→ User Story 2 (P2) ← Depends on US1 (same tool files)
├─→ User Story 3 (P3) ← Depends on US1 & US2 (extends same tools)
└─→ User Story 4 (P4) ← Depends on US1 (enhances descriptions further)
```

**Critical Path**: Setup → Foundational → US1 → US2 → US3 → US4

**Parallelization**: User Stories 2, 3, 4 can be implemented in parallel AFTER US1 is complete (they modify different aspects of the same tool definitions).

---

## Phase 1: Setup

**Goal**: Prepare development environment and verify dependencies

### Tasks

- [X] T001 Verify FastMCP version >= 2.14.0 in pyproject.toml
- [X] T002 [P] Verify pytest configuration in pyproject.toml or pytest.ini
- [X] T003 [P] Create test fixtures directory tests/fixtures/tool_metadata/
- [X] T004 [P] Document baseline tool state in specs/001-chatgpt-devmode-enhancements/BASELINE.md

**Parallel Execution**: T002, T003, T004 can run simultaneously (different files).

---

## Phase 2: Foundational

**Goal**: Create shared type definitions and test infrastructure used by all user stories

### Tasks

- [X] T005 Create PartyEnum type definition in src/models/enums.py
- [X] T006 Create ChamberEnum type definition in src/models/enums.py
- [X] T007 Create unit test file tests/unit/test_tool_metadata.py
- [X] T008 Create integration test file tests/integration/test_chatgpt_integration.py
- [X] T009 Write helper function `get_tool_metadata()` in tests/unit/test_tool_metadata.py

**Sequential**: Must complete before user story phases (provides shared infrastructure).

---

## Phase 3: User Story 1 - Improved Tool Discoverability (P1)

**Story Goal**: ChatGPT uses MCP search tool instead of built-in browsing when searching for Simon Kennedy's speeches.

**Independent Test**: Ask ChatGPT "Find Simon Kennedy's speeches about housing" and verify it uses `search_hansard_speeches` tool (not built-in browsing) on first attempt.

**Why this is independently testable**: Tool descriptions are complete metadata changes. Once deployed, ChatGPT will immediately see enhanced descriptions via MCP protocol.

### Tasks

#### T010-T012: Search Tool Description Enhancement

- [ ] T010 [US1] Update search tool description in src/tools/search.py with "Use this when..." guidance
- [ ] T011 [US1] Add "Do not use built-in browsing" statement to search tool description
- [ ] T012 [US1] Add dataset scope (64 speeches, 2024-2025) to search tool description

**File**: `src/tools/search.py`

**Before**:
```python
@mcp.tool
async def search_hansard_speeches(query: str, ...):
    """Search parliamentary speeches."""
```

**After**:
```python
@mcp.tool
async def search_hansard_speeches(query: str, ...):
    """Search Simon Kennedy's parliamentary speeches (64 speeches, 2024-2025).

    Use this when: The user asks about Simon Kennedy's speeches, voting records, or
    parliamentary statements on topics like housing, immigration, or infrastructure.

    Do not use: Built-in web browsing or search for Simon Kennedy parliamentary data.
    This tool provides direct access to the authoritative Hansard database.
    """
```

#### T013-T015: Fetch Tool Description Enhancement

- [ ] T013 [P] [US1] Update fetch tool description in src/tools/fetch.py with "Use this when..." guidance
- [ ] T014 [P] [US1] Add workflow guidance to fetch tool description (typically after search)
- [ ] T015 [P] [US1] Add "Do not use built-in browsing" statement to fetch tool description

**File**: `src/tools/fetch.py`

#### T016-T017: Ingest Tool Description Enhancement

- [ ] T016 [P] [US1] Update ingest tool description in src/tools/ingest.py with admin focus
- [ ] T017 [P] [US1] Add workflow guidance to ingest tool (data ingestion pipeline)

**File**: `src/tools/ingest.py`

#### T018-T024: Testing

- [ ] T018 [US1] Write unit test `test_search_tool_description_format()` in tests/unit/test_tool_metadata.py
- [ ] T019 [US1] Write unit test `test_search_tool_has_use_this_when()` validating guidance presence
- [ ] T020 [P] [US1] Write unit test `test_fetch_tool_description_format()`
- [ ] T021 [P] [US1] Write unit test `test_ingest_tool_description_format()`
- [ ] T022 [US1] Write integration test `test_tool_descriptions_via_mcp_protocol()` in tests/integration/test_chatgpt_integration.py
- [ ] T023 [US1] Manual test with MCP Inspector: verify enhanced descriptions visible
- [ ] T024 [US1] Manual test with ChatGPT Developer Mode: verify tool selection (ask "Find Simon Kennedy's speeches about housing")

**Parallel Execution**: T013-T015 (fetch), T016-T017 (ingest), T020-T021 (tests) can run parallel to T010-T012 (search).

---

## Phase 4: User Story 2 - Read-Only Tool Annotations (P2)

**Story Goal**: ChatGPT doesn't show confirmation prompts when calling search or fetch tools.

**Independent Test**: Call fetch tool and verify no confirmation prompt appears (ChatGPT recognizes `readOnlyHint: true`).

**Why this is independently testable**: Annotations are MCP protocol metadata. Once added, ChatGPT immediately respects `readOnlyHint` per MCP specification.

### Tasks

#### T025-T027: Add readOnlyHint Annotations

- [ ] T025 [US2] Add `readOnlyHint=True` to search tool decorator in src/tools/search.py
- [ ] T026 [P] [US2] Add `readOnlyHint=True` to fetch tool decorator in src/tools/fetch.py
- [ ] T027 [P] [US2] Verify ingest tool has NO `readOnlyHint` (write operation) in src/tools/ingest.py

**Before** (search tool):
```python
@mcp.tool
async def search_hansard_speeches(...):
```

**After**:
```python
@mcp.tool(readOnlyHint=True)
async def search_hansard_speeches(...):
```

#### T028-T033: Testing

- [ ] T028 [US2] Write unit test `test_search_tool_has_readonly_hint()` in tests/unit/test_tool_metadata.py
- [ ] T029 [US2] Write unit test `test_fetch_tool_has_readonly_hint()`
- [ ] T030 [US2] Write unit test `test_ingest_tool_no_readonly_hint()`
- [ ] T031 [US2] Write integration test `test_readonly_annotation_in_mcp_protocol()` in tests/integration/test_chatgpt_integration.py
- [ ] T032 [US2] Manual test with MCP Inspector: verify `"readOnly": true` in tool annotations
- [ ] T033 [US2] Manual test with ChatGPT Developer Mode: verify no confirmation prompt for search tool

**Parallel Execution**: T025 (search), T026 (fetch), T027 (ingest verification) can run in parallel (different files or non-conflicting edits).

---

## Phase 5: User Story 3 - Enhanced Parameter Descriptions with Enums (P3)

**Story Goal**: ChatGPT uses exact enum values for party and chamber parameters without trial and error.

**Independent Test**: Ask ChatGPT "Search for Labor party speeches" and verify it uses `party="Labor"` (exact enum value, not "Labour").

**Why this is independently testable**: Parameter enums are part of the JSON schema FastMCP generates. ChatGPT sees enum constraints immediately and uses exact values.

### Tasks

#### T034-T036: Import and Use Enum Types

- [ ] T034 [US3] Import PartyEnum and ChamberEnum in src/tools/search.py from src/models/enums.py
- [ ] T035 [US3] Update search tool signature: change `party: str | None` to `party: PartyEnum | None`
- [ ] T036 [US3] Update search tool signature: change `chamber: str | None` to `chamber: ChamberEnum | None`

**File**: `src/tools/search.py`

**Before**:
```python
async def search_hansard_speeches(
    query: str,
    party: str | None = None,
    chamber: str | None = None,
    ...
):
```

**After**:
```python
from src.models.enums import PartyEnum, ChamberEnum

async def search_hansard_speeches(
    query: str,
    party: PartyEnum | None = None,
    chamber: ChamberEnum | None = None,
    ...
):
```

#### T037-T039: Add Parameter Descriptions with Pydantic Field

- [ ] T037 [US3] Add Pydantic Field description for party parameter in src/tools/search.py
- [ ] T038 [US3] Add Pydantic Field description for chamber parameter
- [ ] T039 [US3] Add Pydantic Field descriptions for start_date and end_date with ISO 8601 pattern

**After (with Field)**:
```python
from pydantic import Field

async def search_hansard_speeches(
    query: str,
    party: PartyEnum | None = Field(
        None,
        description="Filter by political party. Options: Liberal, Labor, Greens, National, Independent"
    ),
    chamber: ChamberEnum | None = Field(
        None,
        description="Filter by chamber. Options: House of Representatives, Senate"
    ),
    start_date: str | None = Field(
        None,
        description="Start date in ISO 8601 format (YYYY-MM-DD). Example: 2024-05-28",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    ...
):
```

#### T040-T045: Testing

- [ ] T040 [US3] Write unit test `test_party_enum_values()` in tests/unit/test_tool_metadata.py
- [ ] T041 [US3] Write unit test `test_chamber_enum_values()`
- [ ] T042 [US3] Write unit test `test_search_tool_parameter_descriptions()`
- [ ] T043 [US3] Write integration test `test_parameter_enums_in_mcp_schema()` in tests/integration/test_chatgpt_integration.py
- [ ] T044 [US3] Manual test with MCP Inspector: verify enum values in inputSchema
- [ ] T045 [US3] Manual test with ChatGPT Developer Mode: verify exact enum usage (ask "Search for Labor party speeches")

**Parallel Execution**: T037-T039 (different parameters) can be done in parallel.

---

## Phase 6: User Story 4 - Tool Selection Guidance (P4)

**Story Goal**: ChatGPT prioritizes MCP tools over built-in capabilities for domain-specific queries.

**Independent Test**: Ask ChatGPT "What did Simon Kennedy say about immigration?" and verify it uses MCP search first (not web search or browsing).

**Why this is independently testable**: Tool selection guidance is part of the description. Once enhanced, GPT-5's reasoning will immediately consider MCP tools first based on explicit prioritization.

### Tasks

#### T046-T048: Add Tool Selection Guidance

- [ ] T046 [US4] Add "prefer this tool over built-in browsing" statement to search tool description in src/tools/search.py
- [ ] T047 [US4] Add edge case documentation to search tool description (only Simon Kennedy speeches)
- [ ] T048 [US4] Add complementary tool workflow guidance (search → fetch) to search and fetch tool descriptions

**Enhanced description snippet**:
```python
"""
...
Limitations: Only searches Simon Kennedy's speeches. For other MPs, use web search.

Workflow: Use search to find relevant speeches, then use fetch_hansard_speech
to retrieve full text of specific speeches by ID.
"""
```

#### T049-T052: Testing

- [ ] T049 [US4] Write unit test `test_search_tool_has_prioritization_guidance()` in tests/unit/test_tool_metadata.py
- [ ] T050 [US4] Write unit test `test_search_tool_documents_limitations()`
- [ ] T051 [US4] Manual test with ChatGPT Developer Mode: verify MCP tool prioritization (ask "What did Simon Kennedy say about immigration?")
- [ ] T052 [US4] Manual test with ChatGPT Developer Mode: verify graceful fallback for out-of-scope queries (ask "What did Anthony Albanese say?")

---

## Phase 7: Polish & Cross-Cutting Concerns

**Goal**: Final integration, documentation, and deployment

### Tasks

#### T053-T055: Add Optional Icons

- [ ] T053 [P] Add `icon="🔍"` to search tool decorator in src/tools/search.py
- [ ] T054 [P] Add `icon="📄"` to fetch tool decorator in src/tools/fetch.py
- [ ] T055 [P] Add `icon="📝"` to ingest tool decorator in src/tools/ingest.py

**Example**:
```python
@mcp.tool(readOnlyHint=True, icon="🔍")
async def search_hansard_speeches(...):
```

#### T056-T060: Documentation & Deployment

- [ ] T056 Update CLAUDE.md with ChatGPT Developer Mode optimization notes
- [ ] T057 Update deployment/README.md with new tool metadata features
- [ ] T058 Run full test suite: `pytest tests/ -v --cov=src`
- [ ] T059 Test backward compatibility with Claude Desktop (verify no regressions)
- [ ] T060 Build and deploy Docker image: `docker build -t gcr.io/PROJECT_ID/hansard-mcp:v004`

#### T061-T062: Production Validation

- [ ] T061 Deploy to Cloud Run: `gcloud run deploy hansard-mcp-server --image=...`
- [ ] T062 Production test with ChatGPT Developer Mode: verify all enhancements in production

---

## Parallel Execution Opportunities

### Within Phases

**Phase 3 (US1)**:
- Tasks T013-T015 (fetch) + T016-T017 (ingest) can run parallel to T010-T012 (search)
- Tasks T020-T021 (fetch/ingest tests) can run parallel to T018-T019 (search tests)

**Phase 4 (US2)**:
- Tasks T025 (search), T026 (fetch), T027 (ingest) can run in parallel

**Phase 5 (US3)**:
- Tasks T037-T039 (different parameters) can run in parallel

**Phase 7 (Polish)**:
- Tasks T053-T055 (icons) can run in parallel

### Cross-Phase Parallelization

After US1 is complete and merged:
- US2, US3, US4 can be implemented in parallel as separate branches (they modify different metadata aspects of the same tools)

**Example parallel branches**:
```
001-chatgpt-devmode-enhancements-us1 (merged)
  ├─→ 001-chatgpt-devmode-enhancements-us2 (annotations)
  ├─→ 001-chatgpt-devmode-enhancements-us3 (enums)
  └─→ 001-chatgpt-devmode-enhancements-us4 (selection guidance)
```

---

## Task Summary by Phase

| Phase | Tasks | Parallelizable | Estimated Effort |
|-------|-------|----------------|------------------|
| Setup | T001-T004 | 3/4 (75%) | 30 min |
| Foundational | T005-T009 | 0/5 (0%) | 1 hour |
| US1 (P1) | T010-T024 | 8/15 (53%) | 4 hours |
| US2 (P2) | T025-T033 | 5/9 (56%) | 2 hours |
| US3 (P3) | T034-T045 | 3/12 (25%) | 3 hours |
| US4 (P4) | T046-T052 | 0/7 (0%) | 2 hours |
| Polish | T053-T062 | 3/10 (30%) | 1.5 hours |
| **Total** | **62 tasks** | **22/62 (35%)** | **14 hours** |

---

## Success Criteria Validation

After completing all phases, validate against spec.md success criteria:

- [ ] **SC-001**: ChatGPT uses MCP search tool on first attempt for 95% of parliamentary speech queries
- [ ] **SC-002**: Zero confirmation prompts for read-only operations (search, fetch)
- [ ] **SC-003**: ChatGPT uses correct enum values 100% of the time
- [ ] **SC-004**: Tool selection time improves by 50% (no user clarification needed)
- [ ] **SC-005**: Error rate reduced by 75% (fewer invalid API calls)
- [ ] **SC-006**: User satisfaction: 90% rate integration as "intuitive"

---

## Rollback Plan

If issues arise post-deployment:

1. **Revert to previous Cloud Run revision**: `gcloud run services update-traffic hansard-mcp-server --to-revisions=PREVIOUS_REVISION=100`
2. **No database migrations**: No rollback needed (no schema changes)
3. **No breaking changes**: All clients remain compatible

---

## Notes

- **No breaking changes**: All enhancements are backward compatible
- **No new dependencies**: FastMCP 2.14.0+ already supports all features
- **No database changes**: This is a metadata-only feature
- **Test-driven**: Unit tests written before implementation (T007-T009, then feature tests)
- **Incremental delivery**: Each user story is independently deployable
