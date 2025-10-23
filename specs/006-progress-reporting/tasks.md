# Implementation Tasks: MCP Progress Reporting

**Phase**: Implementation (Ready)
**Branch**: 006-progress-reporting
**Estimated**: 6 hours total (3.75h implementation + 2h testing + 0.75h docs)

## Overview

This document provides an actionable, dependency-ordered task breakdown for implementing MCP progress reporting in the ingest_hansard_speech tool. Tasks follow the phased approach defined in plan.md.

---

## Task Breakdown

### TASK-001: Add progress to ingest tool [Priority: P0, Est: 2h]

**Status**: DONE
**Dependencies**: None
**Files**: `src/tools/ingest.py`

**Requirements**: FR-001, FR-002, FR-003, FR-007, FR-008, FR-009, FR-010, FR-011

**Description**: Modify the ingest_hansard_speech tool to accept Context parameter and report progress through all stages of speech processing. This is the core implementation that establishes the progress reporting pattern.

**Implementation Steps**:

1. Import Context from fastmcp at top of file:
   ```python
   from fastmcp import Context
   from typing import Optional
   ```

2. Add ctx parameter to function signature (currently has speech_data, generate_embeddings):
   ```python
   async def ingest_hansard_speech(
       speech_data: dict = Field(..., description="..."),
       generate_embeddings: bool = Field(True, description="..."),
       ctx: Optional[Context] = None,  # NEW: Progress reporting context
   ) -> dict:
   ```

3. Define progress stage constants at module level (before function):
   ```python
   # Progress stages (percentage ranges)
   STAGE_VALIDATION = (0, 20)
   STAGE_CHUNKING = (20, 40)
   STAGE_EMBEDDING = (40, 70)
   STAGE_VECTOR_STORAGE = (70, 90)
   STAGE_METADATA_STORAGE = (90, 100)
   ```

4. Add progress reporting at start of function (Stage 1: Validation):
   ```python
   if ctx:
       await ctx.report_progress(STAGE_VALIDATION[0], 100)
       await ctx.info("Validating speech data...")
   ```

5. Add validation logic (parse speech_data, check required fields)

6. Report chunking stage (Stage 2):
   ```python
   if ctx:
       await ctx.report_progress(STAGE_CHUNKING[0], 100)
       await ctx.info("Chunking speech text...")
   ```

7. Add chunking logic (use existing chunking utilities or implement)

8. Report embedding stage (Stage 3) and pass ctx to VectorStoreService:
   ```python
   if ctx:
       await ctx.report_progress(STAGE_EMBEDDING[0], 100)
       await ctx.info("Generating embeddings...")

   if generate_embeddings:
       chunk_ids = await vector_store.add_chunks(
           texts=chunk_texts,
           metadatas=chunk_metadatas,
           speech_id=speech_id,
           ctx=ctx  # NEW: Pass context for sub-progress
       )
   ```

9. Report vector storage stage (Stage 4) - handled by VectorStoreService

10. Report metadata storage stage (Stage 5) and pass ctx to MetadataStore:
    ```python
    if ctx:
        await ctx.report_progress(STAGE_METADATA_STORAGE[0], 100)
        await ctx.info("Storing speech metadata...")

    speech_id = await metadata_store.add_speech(speech, ctx=ctx)
    ```

11. Report final completion:
    ```python
    if ctx:
        await ctx.report_progress(100, 100)
        await ctx.info("Speech ingestion complete!")
    ```

12. Update return dict to include speech_id

13. Add @mcp.tool decorator if not present, with exclude_args:
    ```python
    # In src/server.py registration:
    @mcp.tool(exclude_args=["ctx"])
    async def ingest_hansard_speech(...):
    ```

**Acceptance Criteria**:
- Function has ctx: Optional[Context] = None parameter
- Progress reported at 6 distinct milestones (0%, 20%, 40%, 70%, 90%, 100%)
- Stage messages are user-friendly and descriptive
- ctx passed to VectorStoreService.add_chunks() and MetadataStore.add_speech()
- Tool works correctly when ctx=None (backward compatible)
- User-facing info messages accompany each progress update

**Testing**:
```bash
# Manual test via MCP Inspector (see quickstart.md)
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

# Unit test (after TASK-005 complete)
pytest tests/unit/test_progress_reporting.py::test_ingest_with_progress_context -v
```

---

### TASK-002: Add progress to VectorStoreService [Priority: P0, Est: 1h]

**Status**: DONE
**Dependencies**: None (parallel with TASK-001)
**Files**: `src/storage/vector_store.py`

**Requirements**: FR-003, FR-006, FR-010, NFR-001

**Description**: Modify VectorStoreService.add_chunks() to accept optional Context and report granular progress during embedding generation (40-70% range). This provides user feedback during the longest operation stage.

**Implementation Steps**:

1. Import Optional and Context at top of file:
   ```python
   from typing import List, Optional, Dict, Any
   from fastmcp import Context
   ```

2. Add ctx parameter to add_chunks() method signature:
   ```python
   async def add_chunks(
       self,
       texts: List[str],
       metadatas: List[Dict[str, Any]],
       speech_id: str,
       ctx: Optional[Context] = None,  # NEW: Progress reporting
   ) -> List[str]:
   ```

3. Add progress tracking variables at start of method:
   ```python
   if ctx:
       total_chunks = len(texts)
       last_reported_progress = 40.0  # Start of embedding stage
       progress_increment = 30.0 / total_chunks  # 30% range (40-70%)
   ```

4. Add progress reporting loop during embedding generation:
   ```python
   # Inside the loop where embeddings are generated (or before aadd_texts call)
   if ctx:
       current_progress = 40 + (chunk_idx / total_chunks) * 30

       # Report only if progress increased by 5% or more (avoid spam)
       if current_progress - last_reported_progress >= 5.0:
           await ctx.report_progress(current_progress, 100)
           last_reported_progress = current_progress
   ```

5. Report final embedding stage completion before returning:
   ```python
   if ctx:
       await ctx.report_progress(70, 100)  # End of embedding stage
   ```

6. Update docstring to document ctx parameter:
   ```python
   """Add speech chunks to vector store with embeddings.

   Args:
       texts: List of chunk texts
       metadatas: List of metadata dicts (one per chunk)
       speech_id: Parent speech ID (UUID)
       ctx: Optional FastMCP Context for progress reporting

   Returns:
       List of generated chunk IDs
   """
   ```

**Acceptance Criteria**:
- add_chunks() accepts optional ctx parameter
- Progress reported approximately every 10% during embedding (at 45%, 55%, 65%)
- Progress updates throttled to avoid excessive calls (minimum 5% delta)
- Method works correctly when ctx=None (no errors, no behavior change)
- Final 70% progress reported at end of embedding stage
- Progress calculation accurate within ±5% of actual completion

**Testing**:
```python
# Unit test
async def test_vector_store_progress_frequency():
    ctx = MagicMock(spec=Context)
    ctx.report_progress = AsyncMock()

    vector_store = VectorStoreService()
    texts = ["chunk " + str(i) for i in range(30)]  # Enough for multiple updates
    metadatas = [{"speaker": "Kennedy"} for _ in texts]

    await vector_store.add_chunks(texts, metadatas, "speech-123", ctx=ctx)

    # Should report at least 3 times (40%, 55%, 70%)
    assert ctx.report_progress.call_count >= 3

    # Verify progress values are in embedding range (40-70%)
    for call in ctx.report_progress.call_args_list:
        progress = call[0][0]
        assert 40 <= progress <= 70
```

---

### TASK-003: Add progress to MetadataStore [Priority: P1, Est: 30min]

**Status**: DONE
**Dependencies**: None (parallel with TASK-001, TASK-002)
**Files**: `src/storage/metadata_store.py`

**Requirements**: FR-007, FR-010, NFR-001

**Description**: Modify MetadataStore.add_speech() to accept optional Context and report progress during final storage stage (90-100% range). This signals completion to the user.

**Implementation Steps**:

1. Import Optional and Context:
   ```python
   from typing import List, Optional, Dict, Any
   from fastmcp import Context
   ```

2. Add ctx parameter to add_speech() method:
   ```python
   async def add_speech(
       self,
       speech: SpeechMetadata,
       ctx: Optional[Context] = None,  # NEW: Progress reporting
   ) -> str:
   ```

3. Report progress before SQL insert (start of metadata storage stage):
   ```python
   if ctx:
       await ctx.report_progress(90, 100)
       await ctx.info("Storing speech metadata...")
   ```

4. Existing SQL insert logic remains unchanged

5. Report 100% completion after successful insert:
   ```python
   if ctx:
       await ctx.report_progress(100, 100)
       await ctx.info("Speech ingestion complete!")
   ```

6. Ensure 100% is NOT reported if insert fails (let exception propagate)

7. Update docstring:
   ```python
   """Add speech metadata to database.

   Args:
       speech: SpeechMetadata instance
       ctx: Optional FastMCP Context for progress reporting

   Returns:
       Generated speech_id (UUID)

   Raises:
       ValueError: If speech with same content_hash already exists
   """
   ```

**Acceptance Criteria**:
- add_speech() accepts optional ctx parameter
- Progress reported at 90% before SQL insert
- Progress reported at 100% after successful insert
- 100% NOT reported if insert fails (error case)
- Method works correctly when ctx=None
- Info messages clear and final

**Testing**:
```python
async def test_metadata_store_progress():
    ctx = MagicMock(spec=Context)
    ctx.report_progress = AsyncMock()
    ctx.info = AsyncMock()

    store = MetadataStore()
    speech = SpeechMetadata(
        title="Test Speech",
        full_text="Content...",
        speaker="Kennedy",
        party="Liberal",
        chamber="House",
        electorate="Cook",
        state="NSW",
        date=date(2024, 6, 3),
        hansard_reference="Test"
    )

    speech_id = await store.add_speech(speech, ctx=ctx)

    # Verify 90% and 100% reported
    assert ctx.report_progress.call_count == 2
    assert ctx.report_progress.call_args_list[0] == ((90, 100),)
    assert ctx.report_progress.call_args_list[1] == ((100, 100),)
```

---

### TASK-004: Update ingest tool registration [Priority: P0, Est: 15min]

**Status**: DONE
**Dependencies**: TASK-001
**Files**: `src/server.py`

**Requirements**: FR-011, FR-012

**Description**: Ensure ingest_hansard_speech tool is properly registered with FastMCP server with exclude_args for ctx parameter. The tool must be discoverable via MCP Inspector.

**Implementation Steps**:

1. Check if ingest tool is already registered in src/server.py (search for "ingest")

2. If not registered, add import:
   ```python
   from src.tools.ingest import ingest_hansard_speech
   ```

3. Register tool with MCP server using decorator:
   ```python
   @mcp.tool(
       exclude_args=["ctx"],  # Exclude ctx from MCP schema
       destructiveHint=True,  # Write operation
       icon="📝"  # Visual identifier
   )
   async def ingest_hansard_speech(
       speech_data: dict = Field(..., description="..."),
       generate_embeddings: bool = Field(True, description="..."),
       ctx: Optional[Context] = None,
   ) -> dict:
       # Delegate to implementation in src/tools/ingest.py
       from src.tools.ingest import ingest_hansard_speech as ingest_impl
       return await ingest_impl(speech_data, generate_embeddings, ctx)
   ```

   OR (if tool registration uses different pattern):
   ```python
   mcp.add_tool(
       ingest_hansard_speech,
       exclude_args=["ctx"],
       destructiveHint=True,
       icon="📝"
   )
   ```

4. Verify tool appears in MCP Inspector tool list

5. Verify ctx parameter does NOT appear in tool schema (check MCP Inspector tool details)

**Acceptance Criteria**:
- Tool registered with FastMCP server
- exclude_args=["ctx"] specified
- destructiveHint=True set (write operation)
- Tool visible in MCP Inspector
- ctx parameter NOT in MCP tool schema
- Tool callable via MCP clients

**Testing**:
```bash
# Start server
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

# Open MCP Inspector
npx @modelcontextprotocol/inspector

# Verify:
# 1. Tool "ingest_hansard_speech" appears in tool list
# 2. Tool schema shows speech_data and generate_embeddings parameters
# 3. Tool schema does NOT show ctx parameter
# 4. Tool can be invoked successfully
```

---

### TASK-005: Write unit tests [Priority: P1, Est: 1h]

**Status**: DONE
**Dependencies**: TASK-001, TASK-002, TASK-003
**Files**: `tests/unit/test_progress_reporting.py` (NEW)

**Requirements**: FR-005, FR-011, NFR-001, SC-005, SC-007

**Description**: Create comprehensive unit tests for progress reporting logic to verify correct behavior with and without Context, accurate percentage calculations, and proper error handling.

**Implementation Steps**:

1. Create new test file `tests/unit/test_progress_reporting.py`

2. Implement test fixtures:
   ```python
   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from fastmcp import Context
   from datetime import date

   @pytest.fixture
   def mock_context():
       ctx = MagicMock(spec=Context)
       ctx.report_progress = AsyncMock()
       ctx.info = AsyncMock()
       return ctx

   @pytest.fixture
   def sample_speech_data():
       return {
           "title": "Test Speech",
           "speaker": "Simon Kennedy",
           "party": "Liberal",
           "chamber": "House of Representatives",
           "electorate": "Cook",
           "state": "NSW",
           "date": "2024-06-03",
           "hansard_reference": "House Hansard, 3 June 2024",
           "text": "Mr Speaker, this is a test speech..." * 50  # Long enough to chunk
       }
   ```

3. Implement test cases:

   **Test 1: Ingest with progress context**
   ```python
   @pytest.mark.asyncio
   async def test_ingest_with_progress_context(mock_context, sample_speech_data):
       """Verify progress reported at correct milestones when ctx provided."""
       result = await ingest_hansard_speech(
           speech_data=sample_speech_data,
           generate_embeddings=True,
           ctx=mock_context
       )

       # Verify result
       assert result["status"] == "success"

       # Verify progress calls made
       assert mock_context.report_progress.call_count >= 5

       # Verify progress sequence
       calls = mock_context.report_progress.call_args_list
       assert calls[0][0][0] == 0  # Start at 0%
       assert calls[-1][0][0] == 100  # End at 100%

       # Verify all progress values in range 0-100
       for call in calls:
           assert 0 <= call[0][0] <= 100
   ```

   **Test 2: Ingest without progress context**
   ```python
   @pytest.mark.asyncio
   async def test_ingest_without_progress_context(sample_speech_data):
       """Verify tool works correctly when ctx=None (backward compatibility)."""
       result = await ingest_hansard_speech(
           speech_data=sample_speech_data,
           generate_embeddings=True,
           ctx=None
       )

       # Should complete successfully without errors
       assert result["status"] == "success"
   ```

   **Test 3: Vector store progress frequency**
   ```python
   @pytest.mark.asyncio
   async def test_vector_store_progress_frequency(mock_context):
       """Verify embedding stage reports progress at reasonable intervals."""
       vector_store = VectorStoreService()
       texts = [f"Chunk {i}" for i in range(30)]
       metadatas = [{"speaker": "Kennedy", "chunk_index": i} for i in range(30)]

       await vector_store.add_chunks(texts, metadatas, "speech-123", ctx=mock_context)

       # Should report at least 3 times in embedding range (40-70%)
       assert mock_context.report_progress.call_count >= 3

       # Verify no progress spam (not every chunk)
       assert mock_context.report_progress.call_count < len(texts)
   ```

   **Test 4: Progress percentages accurate**
   ```python
   @pytest.mark.asyncio
   async def test_progress_percentages_accurate(mock_context, sample_speech_data):
       """Verify progress percentages match expected stages."""
       await ingest_hansard_speech(
           speech_data=sample_speech_data,
           ctx=mock_context
       )

       calls = [call[0][0] for call in mock_context.report_progress.call_args_list]

       # Verify stage boundaries present
       assert 0 in calls  # Validation start
       assert any(15 <= p <= 25 for p in calls)  # Chunking start (~20%)
       assert any(35 <= p <= 45 for p in calls)  # Embedding start (~40%)
       assert any(65 <= p <= 75 for p in calls)  # Storage start (~70%)
       assert any(85 <= p <= 95 for p in calls)  # Metadata start (~90%)
       assert 100 in calls  # Completion
   ```

   **Test 5: Final progress always 100%**
   ```python
   @pytest.mark.asyncio
   async def test_final_progress_always_100(mock_context, sample_speech_data):
       """Verify 100% progress reported on successful completion."""
       result = await ingest_hansard_speech(
           speech_data=sample_speech_data,
           ctx=mock_context
       )

       assert result["status"] == "success"

       # Last progress call must be 100%
       last_call = mock_context.report_progress.call_args_list[-1]
       assert last_call[0][0] == 100
   ```

   **Test 6: Progress not called on error**
   ```python
   @pytest.mark.asyncio
   async def test_progress_not_called_on_error(mock_context):
       """Verify 100% NOT reported when operation fails."""
       invalid_data = {"invalid": "missing required fields"}

       with pytest.raises(ValueError):
           await ingest_hansard_speech(
               speech_data=invalid_data,
               ctx=mock_context
           )

       # Progress may be called (validation stage), but NOT 100%
       calls = [call[0][0] for call in mock_context.report_progress.call_args_list]
       assert 100 not in calls
   ```

4. Run tests and verify >90% coverage:
   ```bash
   pytest tests/unit/test_progress_reporting.py -v --cov=src/tools/ingest --cov=src/storage
   ```

**Acceptance Criteria**:
- All 6 test cases implemented and passing
- Tests use mocked Context (no real MCP infrastructure needed)
- Tests verify progress with and without ctx
- Tests verify progress percentage accuracy
- Tests verify error handling (no 100% on failure)
- Test coverage >90% for progress reporting code

---

### TASK-006: Manual testing with MCP Inspector [Priority: P0, Est: 1h]

**Status**: TODO
**Dependencies**: TASK-001, TASK-004
**Testing Procedure**: Follow quickstart.md testing section

**Description**: Perform end-to-end manual testing with MCP Inspector to validate user experience, progress bar behavior, and success criteria SC-001 through SC-009.

**Testing Steps**:

1. **Setup**:
   ```bash
   # Terminal 1: Start MCP server
   cd /home/user/skai-fastmcp-cloudrun
   DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

   # Terminal 2: Start MCP Inspector
   npx @modelcontextprotocol/inspector
   ```

2. **Connect to server**:
   - Open browser to http://localhost:5173 (MCP Inspector)
   - Click "Connect to server"
   - Enter server URL (typically http://localhost:8000/mcp/)
   - Verify connection successful

3. **Verify tool registration**:
   - Check tool list includes "ingest_hansard_speech"
   - Click on tool to view schema
   - Verify parameters: speech_data (dict), generate_embeddings (bool)
   - Verify ctx parameter NOT visible in schema

4. **Prepare test data**:
   ```json
   {
     "title": "Budget Speech 2024",
     "speaker": "Simon Kennedy",
     "party": "Liberal",
     "chamber": "House of Representatives",
     "electorate": "Cook",
     "state": "NSW",
     "date": "2024-06-03",
     "hansard_reference": "House Hansard, 3 June 2024",
     "text": "Mr Speaker, I rise to speak on the Budget measures announced yesterday. This government has delivered a responsible Budget that balances fiscal prudence with necessary investments in health, education, and infrastructure. The measures we are implementing will support working families while maintaining our commitment to economic management..."
   }
   ```

5. **Execute tool and observe progress**:
   - Paste test data into speech_data field
   - Set generate_embeddings to true
   - Click "Execute Tool"
   - **Observe** (verify all SC criteria):
     - Progress bar appears within 1 second (SC-001)
     - Progress bar shows 0% initially
     - Progress updates smoothly through stages
     - Stage messages display: "Validating speech...", "Chunking text...", "Generating embeddings...", "Storing speech..."
     - Progress percentages visible: ~0%, ~20%, ~40%, ~55%, ~70%, ~90%, ~100%
     - Progress bar reaches 100% at completion
     - Success message appears
     - No errors in console

6. **Verify result**:
   - Check tool response includes speech_id
   - Status should be "success"
   - Total execution time 8-12 seconds (typical)

7. **Test without progress support** (optional):
   - Use Claude Desktop or Python script without progressToken
   - Verify tool executes successfully without errors
   - Verify no progress-related exceptions

8. **Performance measurement**:
   - Run tool 3 times
   - Measure execution time with progress reporting
   - Compare to baseline (should add <100ms / <1%)

**Success Criteria Validation**:
- ✅ SC-001: First progress update within 1 second
- ✅ SC-002: Progress percentages accurate within ±5%
- ✅ SC-003: At least 5 distinct progress updates
- ✅ SC-004: Progress visible in MCP Inspector
- ✅ SC-005: Works with and without progressToken
- ✅ SC-007: Zero crashes or errors
- ✅ SC-008: Stage messages clear and accurate
- ✅ SC-009: Overhead <100ms (<1% of 8-12 second operation)

**Documentation**: Record observations in quickstart.md testing section

---

### TASK-007: Create documentation [Priority: P2, Est: 45min]

**Status**: TODO
**Dependencies**: TASK-001 through TASK-006
**Files**:
- `specs/006-progress-reporting/quickstart.md` (NEW)
- `CLAUDE.md` (UPDATE)
- `specs/006-progress-reporting/checklists/requirements.md` (NEW)

**Description**: Create comprehensive documentation for developers to test progress reporting and add progress to other tools.

**Implementation Steps**:

1. **Create quickstart.md**:
   ```markdown
   # Quickstart: Testing MCP Progress Reporting

   ## Prerequisites
   - FastMCP 2.0+ server running
   - MCP Inspector installed (npx @modelcontextprotocol/inspector)
   - Sample speech data prepared

   ## Testing with MCP Inspector

   ### 1. Start Server
   [Step-by-step from TASK-006]

   ### 2. Connect to Server
   [Instructions...]

   ### 3. Execute Ingest Tool
   [Sample data and expected behavior...]

   ### 4. Observe Progress
   - Expected stages and percentages
   - Expected timing (8-12 seconds)
   - Expected messages

   ## Adding Progress to Other Tools

   ### Pattern
   [Code example showing ctx parameter, exclude_args, report_progress calls]

   ### Best Practices
   - Report at meaningful milestones (5-10% intervals)
   - Use user-friendly stage messages
   - Always report 100% on success
   - Never report 100% on error
   - Pass ctx to service layers for sub-progress

   ## Troubleshooting

   ### Progress not appearing
   - Check MCP Inspector version (2.0+ required)
   - Verify progressToken being sent
   - Check server logs for errors

   ### Progress jumps or stalls
   - Verify percentage calculations correct
   - Check for missing progress calls
   - Ensure progress always moves forward

   ### Tool errors
   - Verify ctx parameter optional (Optional[Context] = None)
   - Check exclude_args in tool registration
   - Ensure progress doesn't block on errors
   ```

2. **Update CLAUDE.md**:
   Add to "Recent Changes" section:
   ```markdown
   - 006-progress-reporting: Implemented MCP progress reporting for long-running operations
     - Progress reporting for ingest_hansard_speech tool
     - Multi-stage progress (Validation, Chunking, Embedding, Storage)
     - Context.report_progress() API integration
     - Graceful degradation when progressToken not supported
     - Reusable pattern for future long-running tools
     - Constitution Section VII compliance (Progress Transparency)
   ```

3. **Create requirements checklist** (`checklists/requirements.md`):
   ```markdown
   # Requirements Validation Checklist

   ## Functional Requirements
   - [ ] FR-001: Ingest tool reports progress during processing
   - [ ] FR-002: Progress includes percentage 0-100
   - [ ] FR-003: Multi-stage operations report per stage
   - [ ] FR-004: Works with progressToken
   - [ ] FR-005: No errors without progressToken
   - [ ] FR-006: Updates at meaningful milestones only
   - [ ] FR-007: Always reports 100% on success
   - [ ] FR-008: User-friendly stage descriptions
   - [ ] FR-009: All >5 second operations report progress
   - [ ] FR-010: Uses Context.report_progress() API
   - [ ] FR-011: Completes successfully regardless of progress support
   - [ ] FR-012: Testable via MCP Inspector

   ## Success Criteria
   - [ ] SC-001: First update within 1 second
   - [ ] SC-002: Percentages accurate within ±5%
   - [ ] SC-003: At least 5 distinct updates for >5s operations
   - [ ] SC-004: Visible in MCP Inspector
   - [ ] SC-005: Works with/without progressToken, zero errors
   - [ ] SC-006: User satisfaction 4/5+ "always knew what was happening"
   - [ ] SC-007: Zero crashes from progress code
   - [ ] SC-008: Stage messages clear (100% user identification)
   - [ ] SC-009: Overhead <100ms (<1% of operation time)
   ```

**Acceptance Criteria**:
- quickstart.md enables new developer to test progress in <10 minutes
- CLAUDE.md updated with feature summary
- Requirements checklist created with all FRs and SCs
- All documentation reviewed for clarity and accuracy

---

## Task Dependencies

```
TASK-001 (ingest tool)
  ├─→ TASK-004 (tool registration) ─→ TASK-006 (manual testing)
  ├─→ TASK-002 (VectorStoreService) ─┐
  └─→ TASK-003 (MetadataStore) ──────┴─→ TASK-005 (unit tests)

TASK-006 (manual testing) ─→ TASK-007 (documentation)
TASK-005 (unit tests) ─────→ TASK-007 (documentation)
```

## Execution Order

**Parallel Phase** (can work simultaneously):
1. TASK-001 (ingest tool - 2h)
2. TASK-002 (VectorStoreService - 1h)
3. TASK-003 (MetadataStore - 30min)

**Sequential Phase 1**:
4. TASK-004 (tool registration - 15min) - requires TASK-001

**Validation Phase** (parallel):
5. TASK-005 (unit tests - 1h) - requires TASK-001, TASK-002, TASK-003
6. TASK-006 (manual testing - 1h) - requires TASK-001, TASK-004

**Final Phase**:
7. TASK-007 (documentation - 45min) - requires all tasks complete

**Total Estimated Time**: 6 hours
**Critical Path**: TASK-001 → TASK-004 → TASK-006 → TASK-007

---

## Definition of Done

**Feature Complete When**:
- ✅ All 7 tasks marked complete
- ✅ All unit tests passing (TASK-005)
- ✅ All success criteria validated via MCP Inspector (TASK-006)
- ✅ All functional requirements implemented
- ✅ Documentation complete and reviewed (TASK-007)
- ✅ No regressions in existing tool functionality
- ✅ Code reviewed and approved
- ✅ Feature branch merged to main

**Ready for Production When**:
- ✅ Feature complete (above)
- ✅ Integration tests passing
- ✅ Performance validated (<1% overhead)
- ✅ Deployed to staging and tested
- ✅ User acceptance testing complete (SC-006 validated)
