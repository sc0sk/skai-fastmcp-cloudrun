# skai-fastmcp-cloudrun Constitution (Compact v2.6.0)

**Architecture**: Google ADK-aligned (LangChain + Vertex AI text-embedding-004 768-dim + Cloud SQL pgvector)

## Core Principles (NON-NEGOTIABLE)

### I. FastMCP Server-First
- Every feature = discoverable MCP tool
- Tagged metadata, explicit schemas, independently testable
- Use `@mcp.tool` decorator with full type hints

### II. Authentication
- **MVP**: STDIO (local, no auth)
- **Production**: GitHub OAuth (`GitHubProvider`) OR Cloud Run IAM
- Never commit credentials; use `.env` + Secret Manager

### III. Secrets Management
- Environment variables for all credentials
- Cloud Run secrets for production
- `.env` in `.gitignore` for local dev
- HTTPS-only in production

### IV. Test-Driven Development
- Write tests → verify fail → implement → verify pass → refactor
- No tool merges without tests
- Minimum: 80% line coverage, 70% branch coverage

### V. Result Handling
- Return `CallToolResult` with `.data`, `.content`, `.structured_content`
- Raise `ToolError` for failures with descriptive messages
- Async functions for I/O operations

### VI. Cloud Run Standards
- Container deployment with health checks
- Environment-based config (dev/staging/prod)
- OAuth callback at `/auth/callback`
- Cloud Logging integration

### VII. Progress Transparency
- Long tools (>5s) MUST report progress via `ctx.report_progress()`
- Support timeout configuration
- Multi-stage operations report per stage

### VIII. Python & Pydantic
- Python 3.11+, Pydantic v2, type hints required
- `uv` for dependency management
- FastMCP framework, HTTP transport for ChatGPT

### IX. ChatGPT Integration
- Public HTTP endpoint at `/mcp/`
- Port 8000 (dev) or 8080 (Cloud Run)
- `readOnlyHint` annotations on safe tools

### X. MCP JSON Configuration
- Generate with `fastmcp install mcp-json`
- Absolute paths, uv package manager
- Compatible with Claude Desktop/Code/Cursor

### XI. Separation of Concerns
**MCP Tools** (read-only): search, retrieve, analytics (`readOnlyHint: true`)
**CLI Scripts** (write): ingestion, migrations, admin ops
**Rationale**: Security (no file writes), safety, auditability

### XII. Tool Implementation
**Required**:
- `@mcp.tool` decorator, full type hints, clear docstrings
- Pydantic validation, async support, `ctx: Context` access
- Error handling with `ToolError`

**Advanced**:
- Tags, MCP annotations (readOnlyHint, idempotentHint, openWorldHint)
- Icons (2.14.0+), parameter exclusion, dynamic enable/disable

## Google ADK Architecture (v2.6.0)

### Embeddings
- **Model**: Vertex AI `gemini-embedding-001`
- **Dimensions**: 768 (not 384 from sentence-transformers)
- **Integration**: LangChain `VertexAIEmbeddings`

### Vector Storage
- **Database**: Cloud SQL PostgreSQL + pgvector v0.8.0
- **Index**: HNSW (m=24, ef_construction=100)
- **Integration**: LangChain `PostgresVectorStore`

### Database Schema
**Dual-table**:
1. `speeches`: Full text + metadata (speaker, party, chamber, date, hansard_reference)
2. `speech_chunks`: Chunked text + 768-dim vectors + denormalized metadata

### LangChain Integration
- `langchain-google-vertexai` for embeddings
- `langchain-google-cloud-sql-pg` for vector store
- `RecursiveCharacterTextSplitter` (800 chars, 150 overlap)

### Full Text Retrieval
- Store complete speech in `speeches` table
- Reference via `speech_id` foreign key
- MCP tool retrieves from PostgreSQL (not just chunks)

## Testing Standards

### MCP Inspector
- **Dev**: `fastmcp dev src/server.py` (auto-opens Inspector)
- **HTTP**: Start server manually, connect Inspector to `http://localhost:8000/mcp/`
- **CLI**: `npx @modelcontextprotocol/inspector --cli python server.py --method tools/list`

### Required Tests
1. Unit tests (pytest)
2. Integration tests (`call_tool()`)
3. Error tests (`ToolError`)
4. Schema tests (Pydantic validation)
5. Result tests (`.data`, `.content`, `.structured_content`)
6. In-memory tests (`test_mcp()`)

### Coverage
- Line: 80% minimum
- Branch: 70% minimum
- Public tools: 100%
- Error paths: 100%

## FastMCP CLI

### Commands
- `fastmcp run`: Run server (stdio/http/sse)
- `fastmcp dev`: Run with Inspector (stdio only)
- `fastmcp install`: Install in MCP clients
- `fastmcp inspect`: Generate manifest
- `fastmcp project prepare`: Create uv project

### Entrypoint Patterns
```python
# Recommended: Auto-detect mcp variable
from fastmcp import FastMCP
mcp = FastMCP("Server Name")

@mcp.tool()
async def my_tool():
    ...
```

## Project Structure

```
src/
├── models/              # Pydantic models
├── storage/             # Database + embeddings
│   ├── vector_store.py  # LangChain PostgresVectorStore
│   ├── metadata_store.py # Speech metadata
│   └── embeddings.py    # Vertex AI wrapper
├── tools/               # MCP tools (search, retrieve)
├── processing/          # Text chunking, parsing
└── server.py            # FastMCP entrypoint

scripts/
├── ingest_hansard.py    # CLI ingestion (not MCP tool)
└── init_database.py     # Schema setup

tests/
├── unit/
├── integration/
└── fixtures/

specs/[###-feature]/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan
├── research.md          # Technical research
├── data-model.md        # Database schemas
├── quickstart.md        # Setup guide
├── contracts/           # API contracts
└── tasks.md             # Task tracking
```

## Quality Gates

**PR Requirements**:
- All tests pass
- Test updates for new functionality
- Updated tool metadata/descriptions
- No committed secrets (automated scan)
- Breaking changes documented

**Code Review**:
- Type hints complete
- Error handling robust
- Progress reporting (if long-running)
- MCP annotations present
- Documentation updated

## Australian Hansard Specifics

### Metadata Requirements
- `speaker`: MP/Senator name
- `party`: Labor, Liberal, Greens, National, Independent, etc.
- `chamber`: "House of Representatives" | "Senate"
- `electorate`: For House members (optional for Senators)
- `state`: NSW, VIC, QLD, SA, WA, TAS, NT, ACT
- `date`: ISO 8601 (YYYY-MM-DD)
- `hansard_reference`: Official citation
- `topic_tags`: List of topics

### MCP Tools
1. **search_speeches**: Hybrid search (vector + metadata filters)
2. **get_speech**: Retrieve full speech by ID
3. **(No ingest tool)**: Use `scripts/ingest_hansard.py` CLI

### Data Source
- Format: Markdown with YAML frontmatter (sk-hansard compatible)
- Verbatim transcripts (no modification)
- Attribution required (Hansard reference)

## Deployment

### Local Development
- Python 3.11+, uv, .env file
- `fastmcp dev src/server.py`
- MCP Inspector for testing

### Cloud Run
- Container with health checks
- GitHub OAuth or IAM auth
- Secret Manager for credentials
- Cloud Logging enabled
- HTTPS-only

### Dependencies
```toml
fastmcp>=2.12.0
langchain-google-vertexai>=0.1.0
langchain-google-cloud-sql-pg>=0.9.0
pydantic>=2.5.0
```

## Version History

- **v2.6.0**: Google ADK architecture (LangChain + Vertex AI + Cloud SQL pgvector)
- **v2.5.0**: Previous (Qdrant + sentence-transformers)
