# Tasks: Update LangChain to 1.0

**Feature**: 001-update-langchain-1-0  
**Created**: 2025-10-25  
**Type**: Dependency Upgrade

## Task Summary

- **Total Tasks**: 16
- **User Stories**: 3 (US1: Seamless Upgrade P1, US2: Backward Compatible Data P1, US3: Updated Documentation P2)
- **Estimated Time**: 2 hours
- **Approach**: Incremental upgrade with continuous validation

---

## Implementation Strategy

**MVP Scope**: User Story 1 (Seamless Upgrade) - Delivers core functionality
- Update dependencies
- Fix imports
- Validate existing tests pass
- ~45 minutes

**Incremental Delivery**:
1. **US1** (P1): Core upgrade - functional compatibility
2. **US2** (P1): Database compatibility validation (can run parallel with US1 tests)
3. **US3** (P2): Documentation updates (final polish)

**Parallel Execution**: Tasks marked [P] can run in parallel (different files, no dependencies)

---

## Phase 1: Setup & Prerequisites (3 tasks)

**Goal**: Prepare environment and capture 0.x baseline behavior for comparison

- [ ] T001 Create feature branch `001-update-langchain-1-0` from main
  - Verify branch created
  - Confirm working directory clean
  - Document current LangChain version: `pip show langchain langchain-google-vertexai langchain-google-cloud-sql-pg`

- [ ] T002 [P] Capture 0.x baseline outputs for regression testing
  - Run `test_tools_direct.py` and capture output
  - Save sample document chunks from current `RecursiveCharacterTextSplitter`
  - Save search results for test query "climate change" (top 5 speech IDs)
  - Document: Create `specs/001-update-langchain-1-0/baseline.md` with outputs

- [ ] T003 [P] Verify dependency compatibility on PyPI
  - Check `langchain>=1.0.0` latest version
  - Check `langchain-text-splitters>=0.3.0` availability  
  - Check `langchain-google-vertexai` has 1.0-compatible version
  - Check `langchain-google-cloud-sql-pg` has 1.0-compatible version
  - Document: Update `research.md` compatibility matrix with actual versions

---

## Phase 2: User Story 1 - Seamless Upgrade (P1) (6 tasks)

**Story Goal**: Upgrade to LangChain 1.0 without breaking existing functionality

**Independent Test**: All existing tests (`test_tools_direct.py`, unit tests) pass with LangChain 1.0

**Acceptance Criteria**:
- ✅ Vector store initializes successfully
- ✅ Text splitter produces identical chunks
- ✅ Embeddings generate with same dimensions
- ✅ Zero test failures

### Dependency Update

- [ ] T101 [US1] Update `pyproject.toml` with LangChain 1.0 dependencies
  - File: `pyproject.toml`
  - Change `langchain` (unpinned) → `langchain>=1.0.0`
  - Add `langchain-text-splitters>=0.3.0`
  - Update `langchain-google-vertexai` to 1.0-compatible version (e.g., `>=2.0.0`)
  - Update `langchain-google-cloud-sql-pg` to 1.0-compatible version (e.g., `>=0.14.0`)
  - Preserve all other dependencies unchanged

### Import Path Updates

- [ ] T102 [P] [US1] Update imports in `src/tools/ingest.py`
  - File: `src/tools/ingest.py`
  - Change: `from langchain.text_splitter import RecursiveCharacterTextSplitter`
  - To: `from langchain_text_splitters import RecursiveCharacterTextSplitter`
  - Verify no other LangChain imports need updating

- [ ] T103 [P] [US1] Update imports in `src/tools/ingest_markdown_file.py`
  - File: `src/tools/ingest_markdown_file.py`
  - Change: `from langchain.text_splitter import RecursiveCharacterTextSplitter`
  - To: `from langchain_text_splitters import RecursiveCharacterTextSplitter`
  - Verify no other LangChain imports need updating

- [ ] T104 [P] [US1] Verify `src/storage/vector_store.py` imports (no changes expected)
  - File: `src/storage/vector_store.py`
  - Confirm: `from langchain_google_cloud_sql_pg import PostgresVectorStore, PostgresEngine`
  - Confirm: `from langchain_google_vertexai import VertexAIEmbeddings`
  - These imports already use 1.0-style packages, no changes needed
  - Document: Note in commit message that vector_store.py unchanged

### Installation & Validation

- [ ] T105 [US1] Install LangChain 1.0 and verify dependency resolution
  - Run: `pip install -e .` in project root
  - Verify no dependency conflicts
  - Verify `pip show langchain` reports version >=1.0.0
  - Verify `langchain-text-splitters` installed
  - Document: If conflicts occur, adjust version pins in pyproject.toml

- [ ] T106 [US1] Run existing test suite and validate compatibility
  - Run: `PYTHONPATH=src:. .venv/bin/python test_tools_direct.py`
  - Expected: All tests pass (search, fetch, bulk ingestion check)
  - Compare output to baseline from T002
  - Verify: Zero "DeprecationWarning" or "FutureWarning" messages
  - If failures: Debug import issues or API changes

---

## Phase 3: User Story 2 - Backward Compatible Data (P1) (4 tasks)

**Story Goal**: Verify existing database vectors remain valid and search results unchanged

**Independent Test**: Query existing speeches and confirm search results match pre-upgrade baseline

**Acceptance Criteria**:
- ✅ No schema migrations triggered
- ✅ Search results identical to 0.x
- ✅ Vector dimensions unchanged (768)

### Database Compatibility Validation

- [ ] T201 [US2] Validate vector store connection with LangChain 1.0
  - Start Cloud SQL proxy: `./scripts/start_cloud_sql_proxy.sh`
  - Run: Python script to connect with `PostgresVectorStore`
  - Verify: Connection succeeds without errors
  - Verify: No "table schema migration" messages in logs
  - Document: Connection logs show no schema changes

- [ ] T202 [US2] Validate existing vector search results match 0.x baseline
  - Run: Search query for "climate change" (limit 5)
  - Compare: Top 5 speech IDs match baseline from T002
  - Compare: Similarity scores are within 0.01 tolerance
  - Verify: Speech text returned is unchanged
  - Document: If results differ, investigate embedding compatibility

- [ ] T203 [P] [US2] Validate text chunking produces identical output
  - File: Create test script `tests/unit/test_text_splitter_compat.py`
  - Test: Chunk sample document (5000 chars) with chunk_size=1000, overlap=200
  - Compare: Chunk count matches baseline
  - Compare: First chunk content matches byte-for-byte
  - Assert: All chunks match baseline from T002

- [ ] T204 [P] [US2] Validate embedding dimensions unchanged
  - Run: Generate embedding for test text "test sample"
  - Verify: Dimension is 768 (VertexAI textembedding-gecko)
  - Verify: Vector values are reasonable (not all zeros, normalized)
  - Document: Embedding generation works identically

---

## Phase 4: User Story 3 - Updated Documentation (P2) (3 tasks)

**Story Goal**: Update documentation to reflect LangChain 1.0 patterns

**Independent Test**: Code comments and docs reference correct 1.0 import paths

**Acceptance Criteria**:
- ✅ Comments show 1.0 import paths
- ✅ README examples work with 1.0
- ✅ No references to deprecated 0.x patterns

### Documentation Updates

- [ ] T301 [P] [US3] Update inline comments in modified files
  - Files: `src/tools/ingest.py`, `src/tools/ingest_markdown_file.py`
  - Update: Comments referencing `RecursiveCharacterTextSplitter`
  - Add: Note about LangChain 1.0 package structure if helpful
  - Verify: Docstrings still accurate

- [ ] T302 [P] [US3] Update agent context with LangChain 1.0 information
  - File: `.github/copilot-instructions.md`
  - Add: "LangChain 1.0 with langchain-text-splitters package"
  - Update: Recent Changes section with Feature 001
  - Document: Import patterns for future reference

- [ ] T303 [P] [US3] Update README.md if LangChain mentioned
  - File: `README.md`
  - Check: Does README reference LangChain usage?
  - Update: If yes, ensure version/import paths match 1.0
  - If no: Skip this task (no changes needed)

---

## Dependencies & Execution Order

### User Story Dependencies

**Independent Stories** (can be implemented in parallel after Phase 1):
- US1 (Seamless Upgrade) → BLOCKING for US2 and US3
  - Must complete T101-T106 before starting US2 or US3
- US2 (Backward Compatible Data) → Can run after US1 completion
- US3 (Updated Documentation) → Can run after US1 completion (or in parallel with US2)

**Recommended Execution Order**:
1. Phase 1 (Setup) - Sequential execution required
2. Phase 2 (US1) - T101 first, then T102-T104 parallel, then T105-T106 sequential
3. Phase 3 (US2) + Phase 4 (US3) - Can run in parallel after Phase 2 complete

### Task Dependencies

**Sequential (must complete in order)**:
- T001 → T002, T003 (setup before baseline)
- T101 → T102-T104 (deps updated before imports)
- T105 → T106 (install before test)
- T201 → T202 (connect before query)

**Parallel Opportunities**:
- T002 [P] and T003 [P] can run together
- T102 [P], T103 [P], T104 [P] can run together (different files)
- T203 [P] and T204 [P] can run together (independent tests)
- T301 [P], T302 [P], T303 [P] can run together (different files)

---

## Success Criteria Validation

### User Story 1 (Seamless Upgrade)
- ✅ **SC-001**: All existing tests pass → Validated in T106
- ✅ **SC-003**: Text splitter identical chunks → Validated in T203
- ✅ **SC-004**: Zero deprecation warnings → Checked in T106
- ✅ **SC-005**: pip install succeeds → Validated in T105

### User Story 2 (Backward Compatible Data)
- ✅ **SC-002**: Search results identical → Validated in T202
- ✅ **FR-004**: No schema migrations → Validated in T201
- ✅ **FR-005**: Embedding dimensions unchanged → Validated in T204

### User Story 3 (Updated Documentation)
- ✅ **Documentation updated** → Completed in T301-T303

---

## Rollback Plan

If critical issues discovered during implementation:

1. **Revert pyproject.toml**: Change `langchain>=1.0.0` back to `langchain<1.0`
2. **Revert imports**: Change `langchain_text_splitters` back to `langchain.text_splitter`
3. **Reinstall**: Run `pip install -e .` to restore 0.x
4. **Document**: Add findings to research.md for future attempt
5. **Branch cleanup**: Keep branch for investigation, don't merge

**Rollback Triggers**:
- T105: Dependency conflicts that can't be resolved
- T106: Existing tests fail due to API incompatibility
- T202: Search results significantly different (database incompatibility)

---

## Notes

**Quick Win**: T101-T106 (US1) can deliver immediate value in ~45 minutes
- Core functionality working with 1.0
- Can merge at this checkpoint if needed

**Testing Approach**:
- Continuous validation after each phase
- Compare against 0.x baseline captured in T002
- Run full test suite at multiple checkpoints (T106, T202)

**Risk Mitigation**:
- Baseline capture (T002) enables easy comparison
- Parallel tasks reduce total execution time
- Independent user stories allow incremental delivery
- Rollback plan provides safety net

**Performance Expectations**:
- Import speed: Slightly faster (modular packages)
- Search latency: Unchanged (database-bound)
- Memory usage: Slightly reduced (fewer dependencies)
