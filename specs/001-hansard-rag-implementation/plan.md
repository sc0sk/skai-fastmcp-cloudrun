# Implementation Plan: Australian Hansard RAG MVP

**Branch**: `001-hansard-rag-implementation` | **Date**: 2025-10-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-hansard-rag-implementation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a FastMCP server for semantic search over Australian Hansard parliamentary speeches using Google ADK-aligned architecture (LangChain + Vertex AI + Cloud SQL pgvector). Implements paragraph-aware chunking, 768-dimensional embeddings, and hybrid search with metadata filtering. MVP supports local development with STDIO transport and provides foundation for Cloud Run deployment.

## Technical Context

**Language/Version**: Python 3.11+ (Cloud Run compatible)
**Primary Dependencies**: FastMCP 2.12.2, LangChain (langchain-google-vertexai, langchain-google-cloud-sql-pg), Pydantic v2
**Storage**: Cloud SQL PostgreSQL 15 + pgvector v0.8.0 (768-dim vectors, HNSW indexing)
**Testing**: pytest with >80% coverage target, integration tests with MCP Inspector
**Target Platform**: Google Cloud Run (containerized), local development via STDIO
**Project Type**: Single MCP server project
**Performance Goals**: <500ms search latency (p95), 1 speech/sec ingestion throughput
**Constraints**: Vertex AI quota (768-dim embeddings), Cloud SQL connection limits, paragraph-aware chunking (800 chars)
**Scale/Scope**: MVP with 64 speeches (Simon Kennedy dataset), expandable to 1000+ speeches in production

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. FastMCP Server-First | ✅ PASS | Tools implemented with @mcp.tool decorator, full annotations (readOnlyHint, idempotentHint, openWorldHint) |
| II. GitHub OAuth | ⚠️ DEFERRED | OAuth deferred to v2 per spec, MVP uses local STDIO transport |
| III. Secrets Management | ✅ PASS | .env with .gitignore, DATABASE_PASSWORD in env vars, no secrets in git |
| IV. Test-Driven Development | ⚠️ PARTIAL | Integration tests exist, unit test coverage <80% target |
| V. Structured Result Handling | ✅ PASS | Tools return Dict[str, Any] with structured data, error handling via exceptions |
| VI. Cloud Run Standards | ✅ PASS | Dockerfile ready, environment-based config, health checks planned |
| VII. Progress Transparency | ❌ NOT IMPLEMENTED | Ingestion script doesn't use ctx.report_progress (CLI script, not MCP tool) |
| VIII. Python & Pydantic | ✅ PASS | Python 3.11+, Pydantic v2 models, uv package manager, type hints throughout |
| IX. ChatGPT Integration | ⚠️ PLANNED | HTTP transport not yet configured, STDIO only in MVP |
| X. MCP JSON Config | ⚠️ PLANNED | fastmcp.json not yet generated |
| XI. Separation of Concerns | ✅ PASS | Ingestion via CLI scripts/, MCP tools read-only (search, fetch, stats) |
| XII. Tool Implementation | ✅ PASS | Full docstrings, type annotations, async functions, annotations present |

**Post-Implementation Re-check**: Constitution alignment is strong for MVP. Deferred items (OAuth, ChatGPT, progress reporting) are intentional scope reductions documented in spec.md.

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
skai-fastmcp-cloudrun/
├── src/
│   ├── models/              # Pydantic models (Speech, SearchResult)
│   ├── storage/             # LangChain vector store + metadata store
│   │   ├── embeddings.py    # Vertex AI embedding service
│   │   ├── metadata_store.py # Cloud SQL metadata queries
│   │   └── vector_store.py  # PostgresVectorStore integration
│   ├── processing/          # Text chunking and validation
│   │   ├── chunker.py       # RecursiveCharacterTextSplitter (paragraph-aware)
│   │   └── validators.py    # Speech metadata validation
│   ├── tools/               # MCP tool implementations
│   │   ├── search.py        # Hybrid search with filters
│   │   └── fetch.py         # Speech retrieval + stats
│   └── server.py            # FastMCP entrypoint
├── scripts/
│   ├── ingest_hansard.py    # CLI ingestion (admin operation)
│   ├── init_database.py     # Cloud SQL schema initialization
│   └── setup-cloudsql.sh    # Cloud SQL instance creation
├── tests/
│   ├── unit/                # Component tests (models, chunking)
│   ├── integration/         # E2E MCP tool tests
│   └── fixtures/            # Sample speech data
├── data/
│   └── sk-hansard/          # Simon Kennedy speeches (64 .md files)
├── deployment/              # Cloud Run deployment configs
└── specs/001-hansard-rag-implementation/
    ├── spec.md              # Feature specification
    ├── plan.md              # This file
    ├── research.md          # Google ADK research
    ├── data-model.md        # Database schemas + Pydantic models
    ├── quickstart.md        # Local development setup
    └── contracts/           # MCP tool JSON schemas
```

**Structure Decision**: Single project (Option 1) with FastMCP server. Separation of concerns via:
- **MCP Tools** (`src/tools/`): Read-only query operations exposed to clients
- **CLI Scripts** (`scripts/`): Admin operations for ingestion and setup
- **Storage Layer** (`src/storage/`): LangChain + Cloud SQL integration
- **Processing** (`src/processing/`): Paragraph-aware chunking (800 chars, 150 overlap)

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

No constitution violations requiring justification. Deferred items (OAuth, ChatGPT integration) are intentional MVP scope reductions documented in spec.md.

## Implementation Status

**Phase 0 (Research)**: ✅ COMPLETE
- Google ADK architecture research completed
- LangChain + Vertex AI + Cloud SQL pgvector patterns documented
- Paragraph chunking analysis completed (670 paragraphs, mean 497 chars)

**Phase 1 (Design)**: ✅ COMPLETE
- data-model.md: Dual-table schema (speeches + speech_chunks) with pgvector
- contracts/: MCP tool JSON schemas (search, fetch, dataset_stats)
- quickstart.md: Local development setup with Cloud SQL

**Phase 2 (Implementation)**: 🔄 IN PROGRESS
- ✅ Cloud SQL PostgreSQL instance created (hansard-db)
- ✅ Database schema initialized with pgvector v0.8.0
- ✅ Vector store integration fixed (PostgresEngine, column mapping)
- ✅ 62 speeches ingested into metadata store
- ⏳ Speech chunks + embeddings ingestion pending (0/62 speeches chunked)
- ✅ MCP server running with 3 tools (search, fetch, dataset_stats)
- ⏳ End-to-end testing pending (awaiting chunk data)

**Next Steps**:
1. Complete chunk ingestion with Vertex AI embeddings
2. Test search functionality with real data
3. Run integration tests via MCP Inspector
4. Generate fastmcp.json for MCP client distribution

