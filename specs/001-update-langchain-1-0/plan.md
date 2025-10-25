````markdown
# Implementation Plan: Update LangChain to 1.0

**Branch**: `001-update-langchain-1-0` | **Date**: 2025-10-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-update-langchain-1-0/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Upgrade project from LangChain 0.x to LangChain 1.0 to stay current with security patches and new features. Primary changes involve updating import paths (e.g., `langchain.text_splitter` → `langchain_text_splitters`) and ensuring backward compatibility with existing database vectors. The upgrade must be zero-downtime with no database re-indexing required.

**Technical Approach**: Incremental dependency upgrade with continuous validation against existing test suite and database queries to ensure backward compatibility.

## Technical Context

**Language/Version**: Python 3.11+ (Cloud Run compatibility requirement)  
**Primary Dependencies**: 
- FastMCP 2.14.0+ (MCP server framework)
- LangChain 0.x → 1.0.x (upgrade target)
- langchain-google-vertexai >=2.0.0 (embeddings)
- langchain-google-cloud-sql-pg >=0.14.0 (vector store)
- langchain-text-splitters >=0.3.0 (NEW - text chunking split out)

**Storage**: PostgreSQL via Cloud SQL with pgvector extension (existing schema must remain compatible)  
**Testing**: pytest, pytest-asyncio (existing test suite must pass unchanged)  
**Target Platform**: Google Cloud Run (Linux containers, serverless deployment)  
**Project Type**: Single project (FastMCP server with MCP tools)  
**Performance Goals**: 
- Search latency: <500ms p95 (unchanged from 0.x)
- Embedding generation: <2s per document (unchanged from 0.x)
- Text chunking: Identical output to 0.x (byte-for-byte)

**Constraints**: 
- Zero database downtime (no schema migrations)
- No re-indexing of existing 64+ speeches (backward compatible vectors)
- All existing tests must pass without modification
- No breaking changes to MCP tool interfaces

**Scale/Scope**: 
- 3 Python files require import updates
- 1 config file (pyproject.toml) requires dependency changes
- ~15 lines of code modifications total
- Estimated implementation time: 2 hours

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: ✅ PASS - No formal constitution enforced

**Analysis**: The project constitution file (`.specify/memory/constitution.md`) is template-only with placeholder principles. No actual governance rules are enforced for this project, so there are no constitution gates to pass.

**Note**: If a formal constitution is adopted in the future, this upgrade should be re-evaluated for compliance with principles like:
- Test-First development (existing tests must pass)
- Library-First approach (LangChain is external dependency)
- Observability requirements (logging/monitoring implications)

**Recommendation**: Consider establishing project constitution post-upgrade to guide future development.

## Project Structure

### Documentation (this feature)

```text
specs/001-update-langchain-1-0/
├── spec.md              # Feature specification (COMPLETE)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (TO BE GENERATED)
├── data-model.md        # Phase 1 output (NOT NEEDED - no data model changes)
├── quickstart.md        # Phase 1 output (TO BE GENERATED)
└── contracts/           # Phase 1 output (NOT NEEDED - no API contract changes)
```

### Source Code (repository root)

```text
src/
├── tools/
│   ├── ingest.py                  # MODIFY: Update RecursiveCharacterTextSplitter import
│   ├── ingest_markdown_file.py    # MODIFY: Update RecursiveCharacterTextSplitter import
│   └── [other tools - no changes]
├── storage/
│   ├── vector_store.py            # REVIEW: Verify compatibility (likely no changes)
│   └── [other storage - no changes]
└── [other modules - no changes]

tests/
├── unit/                          # VALIDATE: All tests must pass
├── integration/                   # VALIDATE: Vector store compatibility
└── test_tools_direct.py           # VALIDATE: End-to-end tool functionality

pyproject.toml                     # MODIFY: Update dependency versions

scripts/                           # VALIDATE: Ingestion scripts still work
├── ingest_hansard_markdown.py     # May use affected imports
└── [other scripts - review]
```

**Structure Decision**: Single project structure maintained. Only import path updates and dependency version bumps required. No architectural changes, no new files created (except documentation). The upgrade is purely a dependency migration with backward compatibility preservation.

**Files Requiring Changes**:
1. `src/tools/ingest.py` - Import path update
2. `src/tools/ingest_markdown_file.py` - Import path update  
3. `src/storage/vector_store.py` - Compatibility verification (may need no changes)
4. `pyproject.toml` - Dependency version updates

**Files Requiring Validation** (no code changes):
- All test files
- All ingestion scripts
- MCP server entry point

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**Status**: N/A - No constitution violations detected

Since the project has no formal constitution with enforced principles, there are no violations to track or justify. This section remains empty.

---

## Phase 0: Research & Analysis

**Goal**: Resolve all NEEDS CLARIFICATION items and identify migration path

### Research Tasks

1. **LangChain 1.0 Breaking Changes Analysis**
   - Research: What import paths changed in 1.0?
   - Research: What API changes affect `RecursiveCharacterTextSplitter`?
   - Research: What changes affect `PostgresVectorStore`?
   - Output: Import path mapping table (old → new)

2. **Dependency Compatibility Matrix**
   - Research: Does `langchain-google-vertexai` support LangChain 1.0?
   - Research: Does `langchain-google-cloud-sql-pg` support LangChain 1.0?
   - Research: What versions are compatible?
   - Output: Compatibility matrix with version ranges

3. **Database Schema Compatibility**
   - Research: Does LangChain 1.0 change pgvector table structure?
   - Research: Are existing embeddings compatible?
   - Research: Will migration scripts run automatically?
   - Output: Schema compatibility assessment

4. **Best Practices for LangChain 1.0 Migration**
   - Research: Official migration guide recommendations
   - Research: Common pitfalls and solutions
   - Research: Testing strategies for upgrade validation
   - Output: Migration checklist

**Deliverable**: `research.md` with all findings consolidated

---

## Phase 1: Design & Documentation

**Prerequisites**: research.md complete, all NEEDS CLARIFICATION resolved

### Design Artifacts

1. **Data Model** (SKIP - No changes to data model)
   - Reason: LangChain upgrade doesn't modify database schema or entities
   - Validation: Confirm in research that pgvector tables unchanged

2. **API Contracts** (SKIP - No changes to MCP tool contracts)
   - Reason: MCP tool interfaces remain unchanged (internal implementation only)
   - Validation: Tool signatures in `src/tools/*.py` stay the same

3. **Quickstart Guide** (GENERATE)
   - File: `specs/001-update-langchain-1-0/quickstart.md`
   - Content:
     - How to verify LangChain 1.0 installation
     - How to test backward compatibility
     - How to rollback if issues arise
     - Common troubleshooting scenarios

4. **Agent Context Update** (REQUIRED)
   - Run: `.specify/scripts/bash/update-agent-context.sh copilot`
   - Add: LangChain 1.0 with langchain-text-splitters package
   - Add: Updated import patterns for future reference
   - Preserve: Manual additions between markers

**Deliverables**: 
- `quickstart.md` (migration guide)
- `.github/copilot-instructions.md` (updated)

---

## Phase 2: Implementation Planning (NOT EXECUTED BY /speckit.plan)

**Note**: Phase 2 (task breakdown) is executed by `/speckit.tasks` command, not by `/speckit.plan`.

The tasks.md file will be generated separately with TDD task breakdown organized by user story.

````
