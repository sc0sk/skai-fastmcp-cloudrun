# skai-fastmcp-cloudrun Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-21

## Active Technologies
- FastMCP 2.14.0+ (MCP server framework)
- LangChain (Google ADK alignment): langchain-google-vertexai, langchain-google-cloud-sql-pg
- Vertex AI Embeddings: gemini-embedding-001 (768 dimensions)
- Cloud SQL PostgreSQL + pgvector v0.8.0 (HNSW indexing)
- Python 3.11+ with Pydantic v2
- uv (package manager)
- Python 3.11+ + FastMCP 2.14.0+, LangChain (langchain-google-vertexai, langchain-google-cloud-sql-pg), Vertex AI Embeddings, Pydantic v2 (001-hansard-rag-implementation)
- Cloud SQL PostgreSQL with pgvector (production), SQLite (local dev for metadata), dual-table schema (speeches + speech_chunks) (001-hansard-rag-implementation)
- Python 3.11+ (Cloud Run compatibility) + FastMCP 2.14.0+ (OAuth Proxy, GitHubProvider), Docker (multi-stage builds), Redis client (persistent token storage) (002-github-oauth-docker)
- Redis (production OAuth token storage), Google Secret Manager (JWT signing keys, token encryption keys), Cloud SQL PostgreSQL + pgvector (existing RAG data) (002-github-oauth-docker)

## Project Structure
```
skai-fastmcp-cloudrun/
├── src/
│   ├── models/              # Pydantic models
│   ├── storage/             # LangChain vector store integration
│   ├── tools/               # MCP tools (ingest, search, retrieve)
│   ├── processing/          # Text chunking
│   └── server.py            # FastMCP entrypoint
├── tests/
│   ├── unit/                # Component tests
│   ├── integration/         # E2E MCP tool tests
│   └── fixtures/            # Sample speeches
├── data/                    # Local development data
├── deployment/              # Cloud Run configs
└── specs/001-hansard-rag-implementation/
    ├── spec.md              # Feature specification
    ├── research.md          # Technical research (Google ADK)
    ├── data-model.md        # Database schemas + Pydantic models
    ├── quickstart.md        # Local dev setup
    └── contracts/           # MCP tool contracts (JSON)
```

## Commands
```bash
# Development
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py  # Local dev (OAuth bypass)
PORT=8080 fastmcp dev src/server.py                   # HTTP mode (for testing)

# OAuth secrets generation
python3 scripts/generate_secrets.py   # Generate JWT_SIGNING_KEY and TOKEN_ENCRYPTION_KEY

# Testing
pytest tests/ -v --cov=src --cov-report=term-missing

# Database setup
python scripts/init_database.py       # Initialize Cloud SQL schema
python scripts/ingest_sample.py       # Load sample speeches

# Docker (local development)
docker build -t hansard-mcp:latest .  # Build Docker image
docker compose -f deployment/docker-compose.yml up  # Run with Redis

# Deployment
docker build -t gcr.io/PROJECT_ID/hansard-mcp:latest .
docker push gcr.io/PROJECT_ID/hansard-mcp:latest
gcloud run deploy hansard-mcp-server --image=gcr.io/PROJECT_ID/hansard-mcp:latest
```

## Code Style
- Async-first: All tools use async/await
- Type hints: Required for all functions (Pydantic models)
- Error handling: Raise ToolError with user-friendly messages
- Global resources: Use FastMCP lifespan for connection pooling
- Constitution compliance: Follow .specify/memory/constitution.md v2.6.0

## Recent Changes
- 002-github-oauth-docker: Implemented GitHub OAuth authentication and Docker deployment
  - OAuth Proxy pattern: GitHubProvider with PKCE, JWT signing, token encryption
  - Multi-stage Docker build: Python 3.13-slim, non-root user (UID 1000), health checks
  - Health check endpoints: /health (liveness), /ready (readiness with DB/Redis checks)
  - Development bypass: DANGEROUSLY_OMIT_AUTH=true for local testing
  - Production token storage: Redis with encrypted GitHub tokens
  - docker-compose.yml: Local dev environment with Redis service
- 001-hansard-rag-implementation: Added (Australian Hansard RAG MVP)
  - Google ADK architecture: LangChain + Vertex AI + Cloud SQL pgvector
  - Dual-table schema: speeches (full text) + speech_chunks (768-dim vectors)
  - HNSW indexing (m=24, ef_construction=100)
  - Context integration: Progress reporting, logging in search/fetch tools

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
