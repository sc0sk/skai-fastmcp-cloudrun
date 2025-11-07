# Implementation Plan: ChatGPT Developer Mode Enhancements

**Branch**: `001-chatgpt-devmode-enhancements` | **Date**: 2025-10-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-chatgpt-devmode-enhancements/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Enhance the MCP server for optimal ChatGPT Developer Mode integration by adding comprehensive tool annotations (`readOnlyHint`), improved tool descriptions with "Use this when..." guidance, parameter enums for parties and chambers, and explicit tool selection guidance to help GPT-5 choose MCP tools over built-in capabilities. This feature leverages GPT-5's improved instruction following and reasoning capabilities to reduce confirmation prompts, improve tool selection accuracy, and provide better user experience when accessing Simon Kennedy's parliamentary speeches through ChatGPT.

## Technical Context

**Language/Version**: Python 3.11+ (Cloud Run compatibility)
**Primary Dependencies**: FastMCP 2.14.0+ (tool annotations, metadata, icons)
**Storage**: Cloud SQL PostgreSQL with pgvector (existing RAG database, no changes required)
**Testing**: pytest with unit tests for tool metadata validation
**Target Platform**: Cloud Run (HTTP transport for ChatGPT compatibility)
**Project Type**: Single project (MCP server)
**Performance Goals**: No performance impact (metadata-only changes to existing tools)
**Constraints**:
- All changes must be backward compatible with existing MCP clients (Claude Desktop, VS Code)
- Tool function signatures and behavior unchanged (only annotations and descriptions)
- No new dependencies required (FastMCP 2.14.0+ already supports all needed features)
**Scale/Scope**:
- 3 existing tools to enhance (search, fetch, ingest)
- ~20 lines of annotation additions per tool
- Zero database schema changes
- Zero API contract changes (MCP protocol unchanged)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Tool Implementation Standards (XI)
**Status**: ✅ COMPLIANT

All enhancements align with FastMCP Tool Implementation Standards:
- **MCP Annotations**: Feature adds `readOnlyHint: true` to all read-only tools (search, fetch) per constitution requirement
- **Docstrings**: Enhances existing tool docstrings with "Use this when..." guidance and edge case documentation
- **Parameter Validation**: Adds enum definitions for `party` and `chamber` parameters using Pydantic Field
- **Type Annotations**: No changes to existing type hints (already compliant)
- **Icons**: Optional enhancement using FastMCP 2.14.0+ icons for tool identification

**Rationale**: This feature strengthens compliance by making implicit properties (read-only nature) explicit through annotations.

### ChatGPT Integration Standards (IX)
**Status**: ✅ COMPLIANT

Feature directly implements constitution requirements:
- **`readOnlyHint` Annotation**: Constitution requires "Tools MUST include `readOnlyHint` annotation where applicable"
- **HTTP Transport**: No changes to existing HTTP transport on port 8080
- **MCP Endpoint**: No changes to existing `/mcp/` path
- **Public Accessibility**: No changes to Cloud Run deployment

**Rationale**: This feature fulfills the constitution's ChatGPT integration mandate by adding missing `readOnlyHint` annotations.

### Python & Pydantic Standards (VIII)
**Status**: ✅ COMPLIANT

No changes to existing Python/Pydantic architecture:
- Python 3.11+ unchanged
- Pydantic v2 used for enum definitions (already in use)
- Type hints unchanged
- FastMCP 2.14.0+ already supports all required features (no version upgrade needed)

### Test-Driven Development (IV)
**Status**: ✅ COMPLIANT

TDD approach for this feature:
1. **Write tests first**: Unit tests verify tool metadata includes `readOnlyHint`, proper descriptions, enum values
2. **Implement enhancements**: Add annotations and enhanced descriptions to tools
3. **Verify tests pass**: Confirm metadata accessible via MCP protocol
4. **Integration test**: Verify ChatGPT Developer Mode recognizes read-only hints (no confirmation prompts)

**Note**: Since this feature enhances existing tools rather than creating new ones, tests focus on metadata validation rather than functional behavior (which is already tested).

### Gate Decision
**✅ PASSED** - All constitution requirements met. Feature enhances compliance with existing standards (ChatGPT Integration IX, Tool Implementation XI). No violations or exceptions required.

**Proceed to Phase 0: Research**

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/
├── server.py            # FastMCP server entrypoint - tool registration with enhanced annotations
├── tools/               # MCP tools directory
│   ├── search.py       # Search tool - add readOnlyHint, enhanced descriptions, parameter enums
│   ├── fetch.py        # Fetch tool - add readOnlyHint, enhanced descriptions
│   └── ingest.py       # Ingest tool - enhance descriptions (no readOnlyHint - write operation)
├── models/             # Pydantic models (unchanged)
├── storage/            # Vector store integration (unchanged)
└── processing/         # Text chunking (unchanged)

tests/
├── unit/
│   └── test_tool_metadata.py    # NEW: Unit tests for tool annotations and metadata
├── integration/
│   └── test_chatgpt_integration.py  # NEW: Integration tests for ChatGPT Developer Mode
└── fixtures/           # Sample speeches (unchanged)
```

**Structure Decision**: Single project structure (existing). This feature modifies only tool definitions in `src/tools/` and `src/server.py` to add metadata and enhanced descriptions. No new modules or architectural changes required.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

**N/A** - No constitution violations. All gates passed.

