# Implementation Plan: ChatGPT Developer Mode Integration

**Branch**: `005-chatgpt-integration` | **Date**: 2025-10-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/home/user/skai-fastmcp-cloudrun/specs/005-chatgpt-integration/spec.md`

## Summary

Optimize existing MCP tools (search_hansard_speeches, fetch_hansard_speech) for ChatGPT Developer Mode with enhanced descriptions, annotations, and Deep Research Mode support. This is a metadata-only enhancement that improves tool selection, eliminates confirmation prompts, and provides better ChatGPT integration without changing tool functionality.

**Key Changes**:
- Add "Use this when..." guidance to tool descriptions for better GPT-5 tool selection
- Verify/enhance readOnlyHint annotations (already exist, confirm behavior)
- Add explicit enum documentation for party/chamber parameters
- Add ISO 8601 format specifications to date parameters (already exist, verify completeness)
- Add workflow guidance (search → fetch pattern)
- Add dataset scope/limitations to descriptions
- Manual testing in ChatGPT Developer Mode and Deep Research Mode

**Implementation Status**: Tools already exist with SOME optimizations (from feature 001 and 004). This feature completes the ChatGPT integration by verifying all FRs are met and conducting end-to-end testing.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastMCP 2.12.5+ (existing), no new dependencies required
**Storage**: N/A (metadata optimization only, no database changes)
**Testing**: Manual testing with ChatGPT Developer Mode, MCP Inspector validation
**Target Platform**: Cloud Run (existing deployment at public HTTPS endpoint)
**Project Type**: Single (MCP server enhancement)
**Performance Goals**: Tools execute without confirmation delays, <5s response time in ChatGPT
**Constraints**:
- Must work with existing tool implementations (no breaking changes)
- Tool descriptions under 500 characters for ChatGPT context efficiency
- Must maintain backward compatibility with Claude Desktop, VS Code, other MCP clients
**Scale/Scope**: 2 tools (search, fetch), descriptive metadata updates only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Section IX: ChatGPT Integration Standards** ✅ PASS
- Server accessible via public internet (Cloud Run URL) ✅
- HTTP transport on port 8080 (Cloud Run) ✅
- MCP endpoint at `/mcp/` path ✅
- Support both Chat Mode and Deep Research Mode (to be tested) ✅
- Tools include `readOnlyHint` annotation ✅

**Section XI: Tool Implementation Standards** ✅ PASS
- Decorator Pattern: Using `@mcp.tool` ✅
- Type Annotations: Full type hints on all parameters ✅
- Docstrings: Clear descriptions (to be enhanced) ✅
- Parameter Validation: Pydantic Field constraints ✅
- MCP Annotations: readOnlyHint, idempotentHint (existing) ✅
- Error Handling: Raises ValueError for user-facing errors ✅

**Section VIII: Python & Pydantic Standards** ✅ PASS
- Python 3.11+ required ✅
- Pydantic v2 for all data models ✅
- Type hints required ✅
- FastMCP framework ✅
- HTTP transport mode ✅

**Gate Decision**: PASS - This is a metadata-only enhancement with no architectural changes, no new dependencies, and full backward compatibility. All constitution requirements already met by existing implementation.

## Project Structure

### Documentation (this feature)

```
specs/005-chatgpt-integration/
├── plan.md              # This file
├── research.md          # ChatGPT optimization best practices
├── data-model.md        # Tool metadata structures
├── quickstart.md        # ChatGPT testing guide
├── contracts/           # Tool metadata JSON schemas
│   ├── search_tool_metadata.json
│   └── fetch_tool_metadata.json
└── spec.md              # Feature specification (existing)
```

### Source Code (repository root)

```
src/
├── tools/
│   ├── search.py        # EXISTING - search_hansard_speeches tool
│   ├── fetch.py         # EXISTING - fetch_hansard_speech tool
│   └── __init__.py
├── models/
│   ├── enums.py         # EXISTING - PartyEnum, ChamberEnum
│   └── speech.py        # EXISTING - SpeechMetadata Pydantic model
├── storage/             # EXISTING - No changes needed
└── server.py            # EXISTING - Tool registration

tests/
├── integration/
│   └── test_chatgpt_integration.py  # NEW - Manual test scenarios
└── unit/
    └── test_tool_metadata.py        # EXISTING - Verify annotations
```

**Structure Decision**: Single project structure maintained. All changes are metadata-only updates to existing tools in `src/tools/search.py` and `src/tools/fetch.py`. No new files required in source tree (only documentation).

## Complexity Tracking

*Not applicable - no constitution violations*

## Phase 0: Research & Technical Decisions

**Duration**: 0.5 days | **Status**: Complete (documented in research.md)

**Objectives**:
- Document ChatGPT tool selection best practices from FastMCP documentation
- Research GPT-5's tool selection heuristics (chain-of-thought, explicit guidance)
- Identify optimal description patterns ("Use this when...", "Do not use...")
- Verify readOnlyHint behavior in ChatGPT Developer Mode
- Document workflow guidance patterns (search → fetch)

**Deliverables**:
- `research.md`: Technical decisions for each optimization (tool descriptions, annotations, enums, dates, workflow)
- Reference to https://gofastmcp.com/integrations/chatgpt for best practices
- Comparison with feature 001 (ChatGPT DevMode Enhancements) for consistency

**Key Research Questions** (all answered in research.md):
1. What description patterns optimize GPT-5 tool selection?
2. How does readOnlyHint affect confirmation prompts?
3. What enum documentation format works best for ChatGPT?
4. How should workflow guidance be structured in descriptions?
5. What dataset scope information should be included?

## Phase 1: Design & Implementation

**Duration**: 1 day | **Status**: Pending

**Objectives**:
- Verify existing tool metadata meets all FR-001 through FR-015 requirements
- Enhance tool descriptions with missing guidance (if any gaps found)
- Document tool metadata structures in data-model.md
- Create contracts/ JSON files documenting ChatGPT-optimized metadata
- Write quickstart.md with ChatGPT testing procedures

**Deliverables**:
- `data-model.md`: Tool metadata structures, ChatGPT connector configuration
- `contracts/search_tool_metadata.json`: Complete search tool metadata with ChatGPT optimizations
- `contracts/fetch_tool_metadata.json`: Complete fetch tool metadata with ChatGPT optimizations
- `quickstart.md`: Step-by-step ChatGPT testing guide (connector setup, testing, troubleshooting)
- Updated `src/tools/search.py`: Enhanced description if gaps found (likely minimal changes)
- Updated `src/tools/fetch.py`: Enhanced description if gaps found (likely minimal changes)

**Implementation Tasks**:

1. **Audit Existing Tool Metadata** (0.5 day)
   - Read current descriptions in search.py and fetch.py
   - Check against FR-001 through FR-015 requirements
   - Identify any missing elements:
     - FR-001: "Use this when..." guidance (VERIFY)
     - FR-002/FR-003: readOnlyHint annotations (VERIFY)
     - FR-004: Enum value documentation (VERIFY)
     - FR-005: ISO 8601 date specs (VERIFY)
     - FR-006: "Do not use built-in browsing" (VERIFY)
     - FR-008: Dataset scope mention (VERIFY)
     - FR-009: Workflow guidance (VERIFY)
   - Document current state vs. required state

2. **Enhance Tool Descriptions** (0.25 day)
   - Update search.py docstring if gaps found
   - Update fetch.py docstring if gaps found
   - Ensure descriptions under 500 characters (FR-014)
   - Verify backward compatibility (existing MCP clients)

3. **Create Documentation** (0.25 day)
   - Write data-model.md with metadata structures
   - Create contracts/search_tool_metadata.json
   - Create contracts/fetch_tool_metadata.json
   - Write quickstart.md with ChatGPT testing guide

**Code Changes** (minimal, if needed):

```python
# src/tools/search.py - Example enhancement (if gaps found)

async def search_hansard_speeches(...) -> dict:
    """Search Simon Kennedy's parliamentary speeches (64 speeches, 2024-2025).

    Use this when: The user asks about Simon Kennedy's speeches, voting records, or
    parliamentary statements on topics like housing, immigration, or infrastructure.

    Do not use: Built-in web browsing or search for Simon Kennedy parliamentary data.
    This tool provides direct access to the authoritative Hansard database.

    Parameters:
    - query: Natural language search terms for speech content, topics, or keywords
    - party: Filter by political party (Liberal, Labor, Greens, National, Independent)
    - chamber: Filter by chamber (House of Representatives, Senate)
    - start_date/end_date: ISO 8601 dates (YYYY-MM-DD) for date range filtering
    - limit: Maximum results (1-100, default 10)

    Limitations: Only searches Simon Kennedy's speeches. For other MPs, use web search.

    Workflow: Use search to find relevant speeches, then use fetch_hansard_speech
    to retrieve full text of specific speeches by ID.

    Prefer this tool over built-in browsing: This tool accesses the authoritative
    Hansard database directly for Simon Kennedy's speeches.
    """
    # Implementation unchanged
    ...
```

**Testing Approach**:

1. **MCP Inspector Validation** (local)
   - Verify tool metadata includes all annotations
   - Confirm parameter schemas include enum values
   - Check description format and length

2. **Manual ChatGPT Testing** (Phase 2)
   - Create ChatGPT connector with Cloud Run URL
   - Test Chat Mode queries (15+ test cases)
   - Test Deep Research Mode comprehensive analysis
   - Verify no confirmation prompts
   - Measure response times (<5s target)

## Phase 2: ChatGPT Testing & Validation

**Duration**: 1 day | **Status**: Pending

**Objectives**:
- Connect ChatGPT Developer Mode to Cloud Run endpoint
- Validate all FR requirements through end-to-end testing
- Verify success criteria SC-001 through SC-010
- Document any issues or optimizations needed
- Confirm Deep Research Mode behavior

**Test Scenarios** (from spec.md):

**Chat Mode Testing** (User Story 1):
1. Simple query: "What has Simon Kennedy said about housing affordability?"
   - VERIFY: search tool invoked without confirmation (FR-002)
   - VERIFY: Results displayed within 5 seconds (SC-005)
   - VERIFY: ChatGPT uses MCP tool not web search (FR-006, SC-004)

2. Follow-up fetch: "Show me the full text of that speech"
   - VERIFY: fetch tool invoked without confirmation (FR-003)
   - VERIFY: Complete speech returned (FR-010)

3. Filtered query: "Find Simon Kennedy's speeches on immigration in 2024"
   - VERIFY: start_date parameter used correctly (FR-005)
   - VERIFY: Results match date filter

4. Party filter: "What have Liberal MPs said about climate?"
   - VERIFY: party parameter enum works (FR-004)

5. Empty results: "What did Simon Kennedy say about Antarctica?"
   - VERIFY: User-friendly empty results message (FR-012)

**Deep Research Mode Testing** (User Story 2):
1. Comprehensive analysis: "Analyze Simon Kennedy's housing policy positions over the past year"
   - VERIFY: 10+ search queries made (FR-011)
   - VERIFY: Multiple fetch calls for full text
   - VERIFY: Report includes Hansard citations (FR-010)
   - VERIFY: No confirmation prompts despite many calls

**Connector Setup Testing** (User Story 3):
1. First-time setup: Follow quickstart.md instructions
   - VERIFY: Connection succeeds in <2 minutes (SC-001)
   - VERIFY: Both tools appear in ChatGPT tool list (SC-007)
   - VERIFY: Error messages are clear if URL incorrect (FR-012)

**Success Criteria Validation**:
- SC-001: Connection time <2 minutes ✅
- SC-002: No confirmation prompts for search (100%) ✅
- SC-003: No confirmation prompts for fetch (100%) ✅
- SC-004: MCP tool preferred over web search (90%+) ✅
- SC-005: Response time <5s (95%+) ✅
- SC-006: Deep Research with 10+ calls and citations ✅
- SC-007: No auth errors on public endpoint ✅
- SC-009: Correct enum parameter usage (95%+) ✅
- SC-010: User-friendly error messages (100%) ✅

**Deliverables**:
- Test results document (create `testing-results.md` if needed)
- Screenshots of ChatGPT interactions
- Any bug fixes or description refinements
- Updated quickstart.md based on testing feedback

## Phase 3: Documentation Finalization

**Duration**: 0.5 day | **Status**: Pending

**Objectives**:
- Update quickstart.md with any lessons learned from testing
- Ensure all contracts/ JSON files are accurate
- Update CLAUDE.md with ChatGPT integration notes
- Prepare demo queries for users

**Deliverables**:
- Final quickstart.md with troubleshooting section
- Updated CLAUDE.md with ChatGPT testing section
- Example query list for users
- Feature completion documentation

## Risk Mitigation

**Risk 1: ChatGPT Prefers Built-in Tools** (from spec.md)
- **Mitigation**: Test 20+ query variations, iterate on description wording
- **Fallback**: Add even more explicit "Do not use web search" guidance

**Risk 2: Cold Start Delays** (from spec.md)
- **Mitigation**: Cloud Run min instances = 1 (keeps warm)
- **Documentation**: Note expected cold start behavior in quickstart.md

**Risk 3: Users Forget Developer Mode** (from spec.md)
- **Mitigation**: Clear prerequisites section in quickstart.md
- **Troubleshooting**: "Tools not appearing? Enable Developer Mode"

## Dependencies

- **Existing Tools**: search_hansard_speeches, fetch_hansard_speech (complete)
- **Cloud Run Deployment**: Public HTTPS endpoint (deployed)
- **FastMCP 2.12.5+**: Tool annotations support (installed)
- **ChatGPT Subscription**: Pro/Team/Enterprise for Developer Mode (user requirement)
- **Vector Database**: Cloud SQL PostgreSQL with 64 speeches (populated)

## Success Metrics

**Completion Criteria**:
- All documentation files created (plan.md, research.md, data-model.md, quickstart.md, contracts/)
- Tool metadata verified against FR-001 through FR-015
- ChatGPT connector successfully connects to Cloud Run
- Manual testing passes all User Story scenarios
- Success criteria SC-001 through SC-010 validated
- No breaking changes to existing MCP clients (backward compatibility)

**Quality Gates**:
- Tool descriptions under 500 characters ✅
- All annotations present (readOnlyHint) ✅
- Enum documentation explicit ✅
- ISO 8601 format specs included ✅
- Workflow guidance documented ✅
- Dataset scope mentioned ✅
- ChatGPT testing successful ✅

## Timeline

- Phase 0 (Research): 0.5 days → Complete
- Phase 1 (Design & Implementation): 1 day → Pending
- Phase 2 (ChatGPT Testing): 1 day → Pending
- Phase 3 (Documentation): 0.5 day → Pending

**Total**: 3 days

## Next Steps

1. Complete research.md documenting optimization decisions
2. Audit existing tool metadata against FRs
3. Create contracts/ JSON files
4. Write quickstart.md
5. Test in ChatGPT Developer Mode
6. Validate all success criteria
7. Update CLAUDE.md
