# Implementation Plan: Admin-Protected Markdown Ingestion

**Branch**: `012-admin-markdown-ingestion` | **Date**: 2025-10-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/012-admin-markdown-ingestion/spec.md`

## Summary

This feature adds secure, admin-only markdown file ingestion with automatic vector embedding generation. Administrators can import parliamentary speech markdown files (with YAML frontmatter metadata) either individually or in bulk, with transactional database storage ensuring data integrity. The system parses frontmatter, validates metadata, chunks text content, generates Vertex AI embeddings, and stores everything in Cloud SQL PostgreSQL. Progress reporting is provided for long-running bulk operations, and comprehensive error handling prevents partial ingestion.

**Technical Approach**: Extends existing FastMCP OAuth 2.1 architecture with role-based authorization (admin role required), leverages LangChain for text chunking and vector storage, uses python-frontmatter library for YAML parsing, and implements transaction-based rollback for atomic ingestion operations.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastMCP 2.14.0+, python-frontmatter 1.0+, LangChain (text-splitters, google-vertexai, google-cloud-sql-pg), Pydantic v2
**Storage**: Cloud SQL PostgreSQL (speeches table + langchain_pg_embedding table with pgvector)
**Testing**: pytest with async support, FastMCP test utilities, database fixtures
**Target Platform**: Google Cloud Run (Linux containers)
**Project Type**: Single project (server-side only)
**Performance Goals**: 10 files/minute bulk ingestion, <5 seconds single file ingestion
**Constraints**: <200ms embedding API latency (batched), transactional integrity (zero partial records), path validation (security)
**Scale/Scope**: Support 100+ file bulk operations, handle 10MB max file size, 1000+ speech database

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate ✅

| Principle | Compliance | Notes |
|-----------|------------|-------|
| **I. FastMCP Server-First** | ✅ PASS | All ingestion operations exposed as MCP tools (ingest_markdown_file, ingest_markdown_bulk, validate_markdown_file) with clear schemas |
| **II. Secure Authentication** | ✅ PASS | Extends existing OAuth 2.1 with admin role verification, bearer token required |
| **III. Secrets Management** | ✅ PASS | No new credentials, uses existing env vars (GCP_PROJECT_ID, etc.) |
| **IV. Test-Driven Development** | ✅ PASS | TDD workflow specified in quickstart, unit tests for parser/validation/ingestion |
| **VII. Progress Transparency** | ✅ PASS | Bulk ingestion reports progress via ctx.report_progress() after each file |
| **VIII. Python & Pydantic** | ✅ PASS | Python 3.11+, Pydantic v2 for all data models (SpeechFrontmatter, etc.) |
| **XI. Tool Implementation** | ✅ PASS | Tools return CallToolResult, raise ToolError on failures, structured metadata |
| **Architecture Decision** | ✅ PASS | Uses LangChain + Vertex AI + Cloud SQL pgvector per constitution requirement |

**Result**: ✅ All gates passed, proceed to Phase 0

### Post-Design Gate ✅

Re-evaluated after completing research.md, data-model.md, and contracts/:

| Principle | Compliance | Design Verification |
|-----------|------------|---------------------|
| **Cloud Run Standards** | ✅ PASS | Uses existing container deployment, env-based config, HTTPS termination |
| **Structured Results** | ✅ PASS | Tools return dict with status/speech_id/message, errors raised as exceptions |
| **Code Quality** | ✅ PASS | Type hints throughout, Pydantic validation, async/await patterns |

**Result**: ✅ Design conforms to all constitution principles

## Project Structure

### Documentation (this feature)

```
specs/012-admin-markdown-ingestion/
├── spec.md                      # Feature specification (completed)
├── plan.md                      # This file (implementation plan)
├── research.md                  # Technical decisions (completed)
├── data-model.md                # Entity models and validation (completed)
├── quickstart.md                # Rapid implementation guide (completed)
├── contracts/                   # MCP tool contracts (completed)
│   └── mcp-tools.json          # Tool schemas for 3 ingestion tools
└── checklists/                  # Validation checklists
    └── requirements.md          # Spec quality checklist (all passing)
```

### Source Code (repository root)

```
src/
├── tools/
│   ├── ingest_markdown_file.py      # NEW: Single file ingestion tool
│   ├── ingest_markdown_bulk.py      # NEW: Bulk directory ingestion tool
│   ├── validate_markdown_file.py    # NEW: Validation-only tool
│   └── ingest/                      # NEW: Shared ingestion utilities
│       ├── __init__.py
│       ├── markdown_parser.py       # YAML frontmatter parsing
│       ├── path_validator.py        # Security path validation
│       ├── auth.py                  # Admin role verification
│       └── chunking.py              # Text chunking logic
├── models/
│   ├── enums.py                     # EXISTING: PartyEnum, ChamberEnum
│   └── speech.py                    # NEW: SpeechFrontmatter, validation models
├── storage/
│   ├── vector_store.py              # EXISTING: Extend with batch operations
│   └── metadata_store.py            # EXISTING: Add speech storage methods
└── server.py                        # EXISTING: Register new tools

tests/
├── unit/
│   ├── test_markdown_parser.py      # NEW: Frontmatter parsing tests
│   ├── test_path_validator.py       # NEW: Path security tests
│   ├── test_admin_auth.py           # NEW: Role verification tests
│   ├── test_ingest_markdown_file.py # NEW: Single file ingestion tests
│   └── test_ingest_markdown_bulk.py # NEW: Bulk ingestion tests
├── integration/
│   └── test_ingestion_e2e.py        # NEW: End-to-end ingestion flow
└── fixtures/
    └── markdown/                    # NEW: Test markdown files
        ├── valid_speech.md
        ├── no_frontmatter.md
        ├── malformed_yaml.md
        └── missing_fields.md
```

**Structure Decision**: Single project structure maintained. All new code under `src/tools/` for tool implementations, `src/tools/ingest/` for shared utilities. Existing `src/models/` and `src/storage/` extended with new functionality. Test structure mirrors source with unit/integration split.

## Complexity Tracking

*No constitution violations - this section left intentionally empty.*

All complexity justified by constitution requirements:
- LangChain usage required by Architecture Decision (NON-NEGOTIABLE)
- Admin role authorization follows existing OAuth 2.1 pattern
- Progress reporting required by Progress Transparency principle
- Transaction-based storage required by existing database patterns

## Phase 0: Research ✅

**Status**: Complete
**Output**: [research.md](./research.md)

### Key Decisions

1. **YAML Parsing**: python-frontmatter library (industry standard, simple API)
2. **Admin Auth**: Extend OAuth 2.1 with role claims (no new infra)
3. **Chunking**: LangChain RecursiveCharacterTextSplitter (500-1000 chars, paragraph boundaries)
4. **Progress**: FastMCP ctx.report_progress() every N files
5. **Transactions**: PostgreSQL ACID with auto-rollback on exception
6. **Duplicates**: speech_id uniqueness with configurable skip/update/error policy
7. **Path Security**: Whitelist validation with resolved absolute paths
8. **Embedding Batching**: Vertex AI batch calls (250 texts max per request)

### Dependencies Added

- **python-frontmatter** (^1.0.0): YAML frontmatter parsing

### Configuration Required

- `ADMIN_ROLE_CLAIM`: Role claim name in JWT (default: "role")
- `ADMIN_ROLE_VALUE`: Required role value (default: "admin")
- `INGESTION_BASE_DIR`: Allowed file path base (default: "/data/hansard")
- `DUPLICATE_POLICY`: skip/update/error (default: "skip")
- `CHUNK_SIZE`: Target chunk size (default: 1000)
- `CHUNK_OVERLAP`: Overlap between chunks (default: 100)
- `EMBEDDING_BATCH_SIZE`: Batch size for embeddings (default: 250)

## Phase 1: Design ✅

**Status**: Complete
**Outputs**: [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

### Data Model Summary

**Entities**:
1. **MarkdownFile** (input): file_path, duplicate_policy, validate_path
2. **SpeechFrontmatter** (parsed): speech_id, speaker, party, chamber, date, title, state, hansard_reference
3. **SpeechMetadata** (database): Full speech data with timestamps
4. **VectorChunk** (embeddings): chunk_id, speech_id, chunk_index, chunk_text, embedding(768)
5. **IngestionJob** (tracking): job_id, status, admin_user, file_paths, success/failure counts

**Validation Pipeline**:
- Path validation → Frontmatter parsing → Field format validation → Content validation → Duplicate check

### API Contracts

Three MCP tools defined in [contracts/mcp-tools.json](./contracts/mcp-tools.json):

1. **ingest_markdown_file**: Single file import with transaction rollback
2. **ingest_markdown_bulk**: Directory processing with progress reporting
3. **validate_markdown_file**: Dry-run validation (read-only)

All tools require admin bearer token, enforce path security, return structured results.

### Quickstart Implementation

6-step implementation guide with code examples:
1. Markdown parser (10 min)
2. Path validator (5 min)
3. Admin auth (10 min)
4. Single file tool (20 min)
5. Tool registration (5 min)
6. Tests (15 min)

**Total MVP time**: ~65 minutes

## Phase 2: Tasks

**Status**: Not started (use `/speckit.tasks` command)
**Output**: Will generate `tasks.md` with dependency-ordered task breakdown

This phase is handled by the `/speckit.tasks` command which will:
- Break down quickstart steps into atomic tasks
- Add database schema updates
- Add bulk tool implementation
- Add validation tool implementation
- Define testing tasks
- Create deployment tasks

## Implementation Notes

### Critical Path

1. ✅ Spec complete and validated
2. ✅ Research decisions documented
3. ✅ Data model defined
4. ✅ Contracts specified
5. ✅ Quickstart guide created
6. ⏳ Tasks breakdown (use `/speckit.tasks`)
7. ⏳ Implementation (use `/speckit.implement`)

### Success Metrics Alignment

Spec requirements vs implementation approach:

| Requirement | Implementation | Confidence |
|-------------|----------------|------------|
| SC-001: <5s single file | 3-5s projected (parse + embed + DB) | ✅ High |
| SC-002: 10 files/min | 6/min sequential, 10+ with batching | ⚠️ Medium (needs optimization) |
| SC-003: 100% admin rejection | Role-based auth enforced | ✅ High |
| SC-004: 99% success for valid files | Transaction rollback ensures atomicity | ✅ High |
| SC-005: Searchable in 10s | Immediate via vector store | ✅ High |
| SC-006: Zero partial records | PostgreSQL transactions | ✅ High |
| SC-007: 100% actionable errors | Pydantic validation messages | ✅ High |
| SC-008: <5% embedding variance | Same model (text-embedding-005) | ✅ High |

**Optimization needed**: Bulk ingestion rate (parallel processing in future iteration)

### Security Considerations

- ✅ Admin-only access via bearer token with role verification
- ✅ Path traversal prevention with whitelist validation
- ✅ HTTPS-only (Cloud Run automatic)
- ✅ SQL injection prevention (parameterized queries)
- ✅ Audit logging (ingestion operations recorded)
- ✅ Rate limiting (at API layer, constitution requirement)
- ✅ Token expiration handling (existing OAuth 2.1 flow)

### Testing Strategy

**Unit Tests** (TDD approach):
- Frontmatter parsing (valid, malformed, missing)
- Path validation (traversal, symlinks, bounds)
- Admin auth (valid token, invalid role, no token)
- Metadata validation (all fields, formats, enums)
- Chunking (boundaries, sizes, overlaps)
- Duplicate policies (skip, update, error)

**Integration Tests**:
- End-to-end single file ingestion
- Bulk ingestion mixed success/failure
- Transaction rollback on DB errors
- Progress reporting accuracy
- Embedding generation with Vertex AI

**Contract Tests**:
- MCP tool schema validation
- Response format compliance
- Error response structure

### Deployment Checklist

- [ ] Add `python-frontmatter` to dependencies
- [ ] Set environment variables in Cloud Run
- [ ] Verify admin role in JWT token generation
- [ ] Test path validation with Cloud Run file system
- [ ] Configure `INGESTION_BASE_DIR` for production data
- [ ] Run integration tests against Cloud Run instance
- [ ] Monitor embedding API quota and costs
- [ ] Set up logging/monitoring for ingestion operations

## Agent Context Updated

**File**: CLAUDE.md
**Changes**: Added database type and project structure information

## Next Commands

1. **Generate tasks**: `/speckit.tasks` - Break down implementation into atomic tasks
2. **Clarify ambiguities**: `/speckit.clarify` - Ask follow-up questions (optional, spec is complete)
3. **Implement**: `/speckit.implement` - Execute tasks in dependency order

## Artifacts Generated

- ✅ [spec.md](./spec.md) - Feature specification (32 functional requirements)
- ✅ [research.md](./research.md) - 8 technical decisions with rationale
- ✅ [data-model.md](./data-model.md) - 5 entities with validation rules
- ✅ [contracts/mcp-tools.json](./contracts/mcp-tools.json) - 3 MCP tool schemas
- ✅ [quickstart.md](./quickstart.md) - 6-step implementation guide (~65 min)
- ✅ [checklists/requirements.md](./checklists/requirements.md) - Spec validation (all pass)
- ✅ CLAUDE.md - Updated agent context

**Planning phase complete!** Ready for task breakdown and implementation.
