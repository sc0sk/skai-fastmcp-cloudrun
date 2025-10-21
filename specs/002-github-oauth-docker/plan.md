# Implementation Plan: GitHub OAuth Authentication and Docker Deployment

**Branch**: `002-github-oauth-docker` | **Date**: 2025-10-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-github-oauth-docker/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement GitHub OAuth authentication using FastMCP's OAuth Proxy pattern to secure MCP tool access, and containerize the Hansard RAG application for production deployment on Google Cloud Run. This feature adds enterprise-grade security (GitHub OAuth) and production-ready packaging (Docker container) to the existing RAG functionality, with persistent token storage via Redis to survive server restarts and enable horizontal scaling.

**FastMCP Documentation References**:
- OAuth Proxy Pattern: https://gofastmcp.com/servers/auth/oauth-proxy
- GitHub Integration: https://gofastmcp.com/integrations/github
- OAuth Token Security: https://gofastmcp.com/deployment/http#oauth-token-security
- HTTP Deployment: https://gofastmcp.com/deployment/http

## Technical Context

**Language/Version**: Python 3.11+ (Cloud Run compatibility)
**Primary Dependencies**: FastMCP 2.14.0+ (OAuth Proxy, GitHubProvider), Docker (multi-stage builds), Redis client (persistent token storage)
**Storage**: Redis (production OAuth token storage), Google Secret Manager (JWT signing keys, token encryption keys), Cloud SQL PostgreSQL + pgvector (existing RAG data)
**Testing**: pytest (unit/integration), MCP Inspector (interactive testing), Docker Compose (local development environment)
**Target Platform**: Google Cloud Run (Linux containers, managed platform), local Docker for development
**Project Type**: Single project (containerized MCP server)
**Performance Goals**: <500ms authentication validation, <10s container startup (health check), OAuth flow completion <30s
**Constraints**: Non-root container user (security), 512MB memory limit (Cloud Run default), HTTPS-only (production), no secrets in source code or image
**Scale/Scope**: 10-100 concurrent authenticated users, horizontal scaling via Cloud Run (multiple container instances), token persistence across restarts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle Compliance

| Principle | Status | Notes |
|-----------|--------|-------|
| **II. Secure Authentication** | ✅ COMPLIANT | GitHub OAuth via FastMCP GitHubProvider, OAuth Proxy pattern for MCP clients |
| **III. Secrets Management** | ✅ COMPLIANT | Google Secret Manager for keys, environment variables, no hardcoded secrets |
| **IV. Test-Driven Development** | ✅ COMPLIANT | pytest for authentication flow, Docker container tests, integration tests |
| **VI. Cloud Run Production Standards** | ✅ COMPLIANT | Containerized deployment, health checks, HTTPS, environment-based config |
| **VIII. Python & Pydantic Standards** | ✅ COMPLIANT | Python 3.11+, Pydantic v2, uv package manager, FastMCP framework |

### OAuth Token Storage Requirements (Constitution §II)

**Development Mode**:
- In-memory storage (default FastMCP behavior)
- Ephemeral JWT signing keys
- Tokens lost on server restart (acceptable for testing)

**Production Mode** (REQUIRED for Cloud Run):
- ✅ Redis for persistent token storage (`client_storage=RedisStore`)
- ✅ Separate secrets for JWT signing (`jwt_signing_key`) and token encryption (`token_encryption_key`)
- ✅ Keys stored in Google Secret Manager (never in source code)
- ✅ HTTPS enforced (automatic via Cloud Run)
- ✅ Tokens survive server restarts
- ✅ Horizontal scaling support (multiple container instances share Redis)

### Docker Security Requirements (Constitution §VI)

- ✅ Non-root container user (security hardening)
- ✅ No secrets in Docker image (all via environment variables)
- ✅ Health check endpoint for Cloud Run probes
- ✅ Minimal base image (python:3.11-slim)
- ✅ Multi-stage builds for smaller image size (optional optimization)

### Gate Status: **PASS** ✅

All constitution principles are satisfied. Ready to proceed with Phase 0 research.

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
├── models/              # Pydantic models (existing: Speech, SpeechChunk)
├── storage/             # LangChain vector store + metadata store (existing)
├── tools/               # MCP tools (existing: search, fetch, dataset_stats)
├── processing/          # Text chunking (existing)
└── server.py            # FastMCP entrypoint (MODIFY: add OAuth config)

deployment/
├── Dockerfile           # NEW: Container definition
├── docker-compose.yml   # NEW: Local development environment (Redis + server)
├── .dockerignore        # NEW: Exclude .env, .git, etc.
└── healthcheck.py       # NEW: Cloud Run health check endpoint

scripts/
├── init_database.py     # Existing: Database schema initialization
├── ingest_sample.py     # Existing: Sample speech ingestion
└── generate_secrets.py  # NEW: Generate JWT/encryption keys for development

tests/
├── unit/                # Existing: Component tests
├── integration/         # Existing: E2E MCP tool tests
│   ├── test_oauth_flow.py       # NEW: OAuth authentication flow
│   └── test_docker_container.py # NEW: Container startup/health checks
└── fixtures/            # Existing: Sample speeches

.env.example             # MODIFY: Add OAuth and Redis configuration
pyproject.toml           # MODIFY: Add redis-py dependency
```

**Structure Decision**: Single project (Option 1) with Docker containerization. Existing RAG functionality remains unchanged; OAuth and Docker are additive changes to server configuration and deployment infrastructure.

## Complexity Tracking

*No constitution violations to justify. All requirements align with established principles.*

