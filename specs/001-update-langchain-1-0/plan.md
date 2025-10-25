# Implementation Plan: Update LangChain to 1.0

**Branch**: `001-update-langchain-1-0` | **Date**: 2025-10-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-update-langchain-1-0/spec.md`

## Summary

Upgrade the Hansard MCP server from LangChain 0.x to 1.0 to maintain compatibility with the latest LangChain ecosystem. This is a dependency upgrade requiring import path updates and API compatibility verification. The primary goal is zero functional changes while adopting the new package structure (`langchain-text-splitters`, etc.).

**Key Requirement**: Backward compatibility with existing database vectors - no re-indexing of the 64+ speeches currently stored.

## Technical Context

**Language/Version**: Python 3.11+ (Cloud Run requirement)  
**Primary Dependencies**: 
- LangChain 0.x → 1.0.x (core upgrade)
- `langchain-google-vertexai` (Vertex AI embeddings)
- `langchain-google-cloud-sql-pg` (PostgreSQL vector store)
- `langchain-text-splitters` (new package for text splitting in 1.0)
- FastMCP 2.14.0+ (unchanged)

**Storage**: PostgreSQL via Cloud SQL with pgvector extension  
**Testing**: pytest, pytest-asyncio  
**Target Platform**: Google Cloud Run (Linux containers)  
**Project Type**: Single project (Python server)  
**Performance Goals**: Same as current (< 500ms p95 for search, < 2s for ingestion)  
**Constraints**: Zero database downtime, no re-indexing required, backward compatible  
**Scale/Scope**: 3 Python files affected, ~15 lines of code changes (imports + minor API updates)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: PASS (No violations)

The project constitution is template-only with no enforced principles. This upgrade:
- Maintains existing architecture (no new patterns)
- Uses standard dependency upgrade workflow
- Preserves all existing tests and contracts
- No complexity additions

## Project Structure

### Documentation (this feature)

```text
specs/001-update-langchain-1-0/
├── spec.md              # Feature specification (✅ complete)
├── plan.md              # This file (🔄 in progress)
├── research.md          # Migration guide findings
└── tasks.md             # TDD task breakdown (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── storage/
│   ├── vector_store.py          # ✏️  Update imports, test compatibility
│   └── embeddings.py            # ✅  No changes (wrapper unchanged)
├── tools/
│   ├── ingest.py                # ✏️  Update RecursiveCharacterTextSplitter import
│   └── ingest_markdown_file.py  # ✏️  Update RecursiveCharacterTextSplitter import
└── server.py                    # ✅  No changes

tests/
├── test_tools_direct.py         # 🧪  Run to verify compatibility
└── unit/                        # 🧪  Add specific 1.0 compatibility tests

pyproject.toml                    # ✏️  Pin langchain>=1.0.0
```

**Files to Modify**: 3 Python files, 1 config file  
**Lines of Code**: ~15 LOC (mostly import statements)  
**Testing Strategy**: Run existing tests + add 1.0-specific validation

## Phase 0: Research & Compatibility Analysis

### Research Tasks

1. **LangChain 1.0 Migration Guide**
   - Task: Review official LangChain 0.x → 1.0 migration documentation
   - Key Focus: Import path changes, deprecated APIs, breaking changes
   - Output: `research.md` with specific changes needed for this project

2. **Google Integration Compatibility**
   - Task: Verify `langchain-google-vertexai` and `langchain-google-cloud-sql-pg` support 1.0
   - Check PyPI for compatible versions
   - Test version resolution with `pip install --dry-run`
   - Output: Compatible version constraints for `pyproject.toml`

3. **Text Splitter API Changes**
   - Task: Document `RecursiveCharacterTextSplitter` changes between 0.x and 1.0
   - Verify chunk size, overlap, separators behave identically
   - Output: Test cases to validate chunking behavior

4. **Vector Store Schema Compatibility**
   - Task: Verify `PostgresVectorStore` in 1.0 uses same table schema as 0.x
   - Check for automatic migrations or schema changes
   - Output: Database compatibility checklist

### Compatibility Matrix

| Component | 0.x Version | 1.0 Version | Breaking Changes? | Notes |
|-----------|-------------|-------------|-------------------|-------|
| `langchain-core` | 0.x | >=1.0.0 | Yes | Import paths changed |
| `langchain-text-splitters` | N/A (in core) | >=0.3.0 | Yes | New package |
| `langchain-google-vertexai` | ? | >=2.0.0 | TBD | Research needed |
| `langchain-google-cloud-sql-pg` | ? | >=0.14.0 | TBD | Research needed |

## Phase 1: Import Path Migration

###Step-by-Step Migration Plan

**Step 1: Update `pyproject.toml`**
```toml
dependencies = [
    "langchain>=1.0.0",
    "langchain-text-splitters>=0.3.0",  # NEW: split from core
    "langchain-google-vertexai>=2.0.0",  # Update to 1.0-compatible
    "langchain-google-cloud-sql-pg>=0.14.0",  # Update to 1.0-compatible
    # ... rest unchanged
]
```

**Step 2: Update Import Statements**

| File | Old Import | New Import |
|------|-----------|------------|
| `src/tools/ingest.py` | `from langchain.text_splitter import RecursiveCharacterTextSplitter` | `from langchain_text_splitters import RecursiveCharacterTextSplitter` |
| `src/tools/ingest_markdown_file.py` | `from langchain.text_splitter import RecursiveCharacterTextSplitter` | `from langchain_text_splitters import RecursiveCharacterTextSplitter` |
| `src/storage/vector_store.py` | ✅ Already using `langchain_google_*` packages | No changes needed |

**Step 3: API Compatibility Checks**

- Verify `RecursiveCharacterTextSplitter` constructor signature unchanged
- Confirm `chunk_size`, `chunk_overlap`, `separators` parameters work identically
- Test `split_text()` produces same chunks for test document

**Step 4: Vector Store Validation**

- Connect to existing database with LangChain 1.0
- Run similarity search on existing vectors
- Verify no schema migrations triggered
- Confirm vector dimensions unchanged (768 for VertexAI)

## Phase 2: Testing & Validation

### Test Strategy

**Unit Tests** (New):
- `tests/unit/test_langchain_1_0_compat.py`
  - Test import paths resolve correctly
  - Test text splitter produces expected chunks
  - Test embedding dimensions match 0.x

**Integration Tests** (Existing):
- `test_tools_direct.py` - Must pass without modification
- `test_mcp_tools.py` - End-to-end MCP tool validation

**Regression Tests**:
- Capture chunk output from 0.x for sample document
- Compare 1.0 chunk output - must be identical
- Query existing database speeches - results must match

### Rollback Plan

If issues discovered:
1. Revert `pyproject.toml` to pin `langchain<1.0`
2. Revert import changes
3. Document blocking issues for future retry

## Success Metrics

- ✅ All existing tests pass with LangChain 1.0
- ✅ Text chunking produces identical output
- ✅ Vector search returns same results
- ✅ Zero deprecation warnings in logs
- ✅ Cloud Run deployment succeeds

## Risk Assessment

**Low Risk**:
- Import path changes only (no logic changes)
- Strong backward compatibility guarantees from LangChain team
- Can revert easily if issues found

**Medium Risk**:
- Google integration packages may lag 1.0 support
- Mitigation: Check PyPI before starting

**Mitigation Strategy**:
- Test in isolated virtualenv first
- Validate with existing database before deploying
- Keep rollback commit ready
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
