# Implementation Plan: Search and Fetch MCP Tools

**Branch**: `004-search-fetch-mcp-tools` | **Date**: 2025-10-23 | **Spec**: [spec.md](./spec.md)

## Summary

Implement two MCP tools (`search_hansard_speeches` and `fetch_hansard_speech`) that provide programmatic access to Australian Hansard parliamentary speeches stored in a vector database. The tools enable semantic search with metadata filtering (party, chamber, date range, speaker) and full speech retrieval with all 29 metadata fields. Implementation uses LangChain PostgresVectorStore for vector similarity search and PostgreSQL metadata store for full speech retrieval.

**Current Status**: ✅ **IMPLEMENTATION COMPLETE** - Tools exist and are functional. This plan documents the existing implementation and identifies remaining documentation/testing work.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastMCP 2.12.5+, LangChain (langchain-google-vertexai, langchain-google-cloud-sql-pg), Pydantic v2  
**Storage**: Cloud SQL PostgreSQL with pgvector extension (LangChain schema: langchain_pg_embedding + speeches metadata table)  
**Testing**: pytest with pytest-asyncio for async tool testing  
**Target Platform**: Cloud Run (containerized deployment), Local development via `fastmcp dev`  
**Project Type**: Single project (MCP server)  
**Performance Goals**: <3s search response (95th percentile), <2s fetch response (95th percentile), 10 concurrent queries  
**Constraints**: Read-only tools (no write operations exposed via MCP), OAuth authentication required in production  
**Scale/Scope**: 64 speeches (628 chunks), designed for 10,000+ speeches

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Compliance Status: PASSED WITH WARNINGS

**I. FastMCP Server-First Architecture**: ✅ PASS
- Tools registered with `@mcp.tool()` decorator
- Tools discoverable via `list_tools()` with metadata
- Self-contained with explicit Pydantic input schemas
- Read-only annotations (`readOnlyHint=True`)

**II. Secure Authentication**: ✅ PASS
- GitHub OAuth configured via `GitHubProvider`
- Browser-based OAuth flow for client authentication
- Development bypass available (`DANGEROUSLY_OMIT_AUTH=true`)

**III. Secrets Management**: ✅ PASS
- All credentials via environment variables
- Google Secret Manager for production
- `.env` files for local development (in .gitignore)
- No credentials in version control

**IV. Test-Driven Development**: ⚠️ WARNING
- Tool tests exist but need expansion for all functional requirements
- Integration tests for search filtering combinations needed
- Error handling tests (invalid speech_id, malformed dates) needed

**V. Structured Result Handling**: ⚠️ WARNING
- Tools return structured dicts (JSON-serializable)
- Error handling with `ValueError` for user-facing errors
- TODO: Convert to `CallToolResult` with `.data`, `.content`, `.is_error` (FastMCP 2.14.0+)

**VI. Cloud Run Production Standards**: ✅ PASS
- Container-based deployment (Dockerfile)
- Health checks configured
- OAuth callback URL configured
- Cloud Logging integration

**VII. Progress Transparency**: ✅ PASS (N/A)
- Search and fetch tools respond <5s (no progress reporting needed)

**VIII. Python & Pydantic Standards**: ✅ PASS
- Python 3.11+ (Cloud Run compatible)
- Pydantic v2 for all data models
- Type hints on all functions
- `uv` for dependency management
- FastMCP framework
- HTTP transport mode

**IX. ChatGPT Integration Standards**: ✅ PASS
- Public internet access via Cloud Run
- HTTP transport on port 8080
- MCP endpoint at `/mcp/`
- `readOnlyHint` annotations on both tools
- Enhanced tool descriptions with "Use this when..." guidance

**X. MCP JSON Configuration Standards**: ⚠️ WARNING
- TODO: Generate MCP JSON configuration with `fastmcp install mcp-json`
- TODO: Document configuration for Claude Desktop, Cursor, VS Code

**XI. Tool Implementation Standards**: ⚠️ WARNING
- ✅ `@mcp.tool` decorator (naked decorator)
- ✅ Type annotations on all parameters
- ✅ Docstrings with clear descriptions
- ✅ Pydantic Field constraints (ge, le, pattern)
- ✅ Async functions for I/O operations
- ✅ ToolAnnotations metadata (readOnlyHint, idempotentHint)
- ⚠️ TODO: Return type annotations for output schema generation (FastMCP 2.10.0+)
- ⚠️ TODO: Tags for categorization (FastMCP 2.11.0+)

### Gate Decision: ✅ PROCEED WITH WARNINGS

Implementation can proceed. MUST address pending items before production release:
1. Expand test coverage (FR-007 error handling)
2. Generate MCP JSON configuration
3. Add return type annotations (FastMCP 2.10.0+)
4. Add tool tags for categorization (FastMCP 2.11.0+)
5. Consider migrating to CallToolResult (FastMCP 2.14.0+)

## Project Structure

### Documentation (this feature)

```
specs/004-search-fetch-mcp-tools/
├── spec.md              # Feature specification (✅ COMPLETE)
├── plan.md              # This file (✅ COMPLETE)
├── research.md          # Technical research (⏳ PENDING)
├── data-model.md        # Database schemas + Pydantic models (⏳ PENDING)
├── quickstart.md        # Local dev setup (⏳ PENDING)
├── contracts/           # MCP tool contracts (⏳ PENDING)
│   ├── search_hansard_speeches.json
│   └── fetch_hansard_speech.json
└── checklists/
    └── requirements.md  # Specification validation (✅ COMPLETE)
```

### Source Code (repository root)

```
skai-fastmcp-cloudrun/
├── src/
│   ├── models/
│   │   ├── speech.py          # ✅ SpeechMetadata, SpeechDetail Pydantic models
│   │   └── enums.py           # ✅ PartyEnum, ChamberEnum for MCP tools
│   ├── storage/
│   │   ├── vector_store.py    # ✅ LangChain PostgresVectorStore wrapper
│   │   └── metadata_store.py  # ✅ Direct PostgreSQL access for full speeches
│   ├── tools/
│   │   ├── search.py          # ✅ search_hansard_speeches MCP tool
│   │   ├── fetch.py           # ✅ fetch_hansard_speech MCP tool
│   │   └── ingest.py          # ✅ ingest_hansard_speech (CLI/script only)
│   └── server.py              # ✅ FastMCP entrypoint
├── tests/
│   ├── unit/
│   │   ├── test_search_tool.py   # ⏳ PENDING expansion
│   │   ├── test_fetch_tool.py    # ⏳ PENDING expansion
│   │   └── test_models.py
│   ├── integration/
│   │   └── test_mcp_tools.py     # ⏳ PENDING
│   └── fixtures/
│       └── sample_speeches/
├── scripts/
│   ├── populate_hansard_db.py  # ✅ Bulk ingestion script
│   └── init_schema.py           # ✅ Database initialization
├── deployment/
│   ├── Dockerfile          # ✅ Multi-stage build
│   └── cloudbuild.yaml     # ✅ Cloud Build config
└── pyproject.toml          # ✅ Dependencies
```

**Structure Decision**: Single project structure chosen because this is an MCP server with tools, not a web application with frontend/backend. All code resides in `src/` with clear separation: models (data validation), storage (database access), tools (MCP tool implementations), server (FastMCP entrypoint).

## Complexity Tracking

*No constitution violations requiring justification. All warnings are documentation/testing gaps, not architectural violations.*

## Next Steps (for /speckit.tasks)

The `/speckit.plan` workflow has completed. The following artifacts must be created:

1. **research.md** (Phase 0): Document technical decisions
   - LangChain PostgresVectorStore metadata filtering patterns
   - Vertex AI Embeddings usage for queries
   - Speech reconstruction from chunks
   - MCP tool contract formats
   - Error handling strategies

2. **data-model.md** (Phase 1): Document database schemas and Pydantic models
   - SpeechMetadata model (29 fields)
   - SpeechDetail model (with ingestion_timestamp)
   - PartyEnum, ChamberEnum
   - Database tables: speeches, langchain_pg_embedding
   - Relationships and constraints

3. **contracts/** (Phase 1): Generate MCP tool JSON schemas
   - search_hansard_speeches.json (parameters, response format)
   - fetch_hansard_speech.json (parameters, response format)

4. **quickstart.md** (Phase 1): Local development guide
   - Prerequisites (Python, uv, PostgreSQL, gcloud)
   - Environment variable setup
   - Database initialization
   - Sample data ingestion
   - Running the server locally
   - Testing with MCP Inspector

5. **Update CLAUDE.md** (Phase 1): Add feature to agent context
   - Run `.specify/scripts/bash/update-agent-context.sh claude`
   - Add search/fetch tools to active features

6. **Expand test coverage** (Phase 2): Meet constitution requirements
   - Error handling tests (invalid inputs, connection failures)
   - Search filtering combinations (party+chamber, date ranges)
   - Integration tests with live database

7. **Generate MCP JSON config** (Phase 2): Client distribution
   - Run `fastmcp install mcp-json`
   - Document configuration for Claude Desktop, Cursor, VS Code

---

**Implementation Status**: Tools are ✅ **COMPLETE** and functional. Remaining work is documentation and testing. Run `/speckit.tasks` to generate actionable task list.
