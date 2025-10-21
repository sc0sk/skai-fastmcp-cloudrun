# Technical Research: GitHub OAuth Authentication and Docker Deployment

**Feature**: 002-github-oauth-docker
**Date**: 2025-10-21
**Status**: Complete

## Overview

This document consolidates technical research for implementing GitHub OAuth authentication using FastMCP's OAuth Proxy pattern and containerizing the application for Google Cloud Run deployment.

---

## FastMCP OAuth Proxy Architecture

### Decision: GitHubProvider with OAuth Proxy Pattern

**Chosen Approach**: Use FastMCP's `GitHubProvider` class with environment-based configuration for production deployment.

**Official Documentation**:
- OAuth Proxy Pattern: https://gofastmcp.com/servers/auth/oauth-proxy
- GitHub Integration: https://gofastmcp.com/integrations/github
- OAuth Token Security: https://gofastmcp.com/deployment/http#oauth-token-security

**Rationale**:
- FastMCP OAuth Proxy solves the Dynamic Client Registration (DCR) gap between MCP specification and traditional OAuth providers
- GitHub OAuth doesn't support DCR; FastMCP bridges this with a token factory pattern
- Environment-based configuration aligns with Cloud Run secrets management best practices
- Automatic token lifecycle management (encryption, persistence, validation)

**Alternatives Considered**:
1. **Custom OAuth Implementation**: Rejected - reinventing security-critical code is error-prone
2. **Direct Token Validation (JWTVerifier)**: Rejected - doesn't support MCP client dynamic registration
3. **Generic OAuthProxy**: Considered but GitHubProvider provides GitHub-specific optimizations

### Architecture Components

**Three-Phase Flow**:

1. **Registration Phase**:
   - MCP client POSTs to `/register` with client_name, redirect_uris
   - Server returns client_id and fixed upstream credentials
   - Client's dynamic callback URL stored for later forwarding

2. **Authorization Flow**:
   - Client initiates browser-based OAuth flow
   - User reviews consent page (client details, scopes, redirect URI)
   - Dual PKCE parameters generated (client-to-proxy, proxy-to-upstream)
   - GitHub callback handled, tokens exchanged
   - FastMCP issues its own JWT tokens to client

3. **Token Management**:
   - FastMCP JWT tokens (HS256) issued to clients
   - Upstream GitHub tokens encrypted (Fernet: AES-128-CBC + HMAC-SHA256)
   - Two-tier validation: JWT signature + upstream token verification
   - Persistent storage (Redis) enables tokens to survive server restarts

### Environment Variables

**Required (Minimum Viable)**:
```bash
FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.github.GitHubProvider
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=Ov23liAbcDefGhiJkLmN
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=github_pat_11AABBCCDD...
FASTMCP_SERVER_AUTH_GITHUB_BASE_URL=https://mcp.simonkennedymp.com.au
```

**Production (Persistent Tokens)**:
```bash
# Above variables +
JWT_SIGNING_KEY=random-secret-string-for-jwt-signing
TOKEN_ENCRYPTION_KEY=random-secret-string-for-token-encryption
REDIS_HOST=10.x.x.x  # Internal Cloud SQL Redis instance IP
REDIS_PORT=6379
```

**Optional**:
```bash
FASTMCP_SERVER_AUTH_GITHUB_REQUIRED_SCOPES=user,user:email  # Comma-separated
FASTMCP_SERVER_AUTH_GITHUB_REDIRECT_PATH=/auth/callback  # Default shown
FASTMCP_SERVER_AUTH_GITHUB_TIMEOUT=30  # Seconds
```

### Implementation Pattern

**Server Initialization** ([src/server.py](../../src/server.py)):
```python
from fastmcp import FastMCP

# Auth auto-configured from environment variables
mcp = FastMCP(
    name="Australian Hansard RAG",
    # FastMCP reads FASTMCP_SERVER_AUTH and instantiates GitHubProvider
)

@mcp.tool
async def search(query: str) -> dict:
    """Search Hansard speeches (requires authentication)."""
    from fastmcp.server.dependencies import get_access_token

    token = get_access_token()
    user = token.claims.get("login")  # GitHub username

    # Perform search...
    return results
```

**Health Check Endpoints**:
```python
from starlette.responses import PlainTextResponse

@mcp.custom_route("/health", methods=["GET"])
async def health_check():
    """Liveness probe for Cloud Run."""
    return PlainTextResponse("OK")

@mcp.custom_route("/ready", methods=["GET"])
async def readiness_check():
    """Readiness probe - verify dependencies."""
    try:
        # Check Redis connection
        await redis_client.ping()
        return PlainTextResponse("READY", status_code=200)
    except Exception as e:
        return PlainTextResponse(f"NOT READY: {str(e)}", status_code=503)
```

### Cloud Run Configuration

**GitHub OAuth App Settings**:
- **Homepage URL**: `https://mcp.simonkennedymp.com.au`
- **Authorization callback URL**: `https://mcp.simonkennedymp.com.au/auth/callback`
  - MUST exactly match `FASTMCP_SERVER_AUTH_GITHUB_BASE_URL + /auth/callback`

**Deployment Command**:
```bash
gcloud run deploy hansard-mcp-server \
  --image=gcr.io/PROJECT_ID/hansard-mcp:latest \
  --region=us-central1 \
  --set-env-vars=FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.github.GitHubProvider \
  --set-env-vars=FASTMCP_SERVER_AUTH_GITHUB_BASE_URL=https://mcp.simonkennedymp.com.au \
  --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=github-client-id:latest \
  --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=github-client-secret:latest \
  --set-secrets=JWT_SIGNING_KEY=jwt-signing-key:latest \
  --set-secrets=TOKEN_ENCRYPTION_KEY=token-encryption-key:latest \
  --no-allow-unauthenticated  # GitHub OAuth handles authentication
```

### Security Considerations

**Token Persistence**:
- **Development**: Ephemeral keys (random on startup) - tokens invalid after restart
- **Production**: Persistent keys in Secret Manager - tokens survive restarts

**Logging Best Practices**:
- ✅ Log authentication events (user login, registration attempts)
- ✅ Log authorization failures
- ✅ Mask sensitive data (tokens, secrets)
- ❌ Never log full access tokens or client secrets

**PKCE Protection**:
- Dual PKCE parameters (client-to-proxy, proxy-to-upstream)
- Protects against authorization code interception
- Automatic forwarding to GitHub (forward_pkce=True by default)

**Consent Mechanism**:
- Explicit user approval required for each new client
- CSRF-protected consent page
- Displays client name, redirect URI, requested scopes

---

## Docker Containerization

### Decision: Multi-Stage Build with python:3.13-slim + uv

**Chosen Approach**: Multi-stage Dockerfile using official Python slim image and uv package manager.

**Rationale**:
- **python:3.13-slim**: Optimal balance (114MB base, glibc compatibility, security updates)
- **Multi-stage build**: 50-70% size reduction (520MB → 270MB)
- **uv package manager**: 10-100x faster than pip, deterministic builds
- **Non-root user**: Security compliance required for Cloud Run CIS benchmarks

**Alternatives Considered**:
1. **python:3.13-alpine**: Rejected - musl libc incompatibility with LangChain/numpy
2. **Distroless runtime**: Considered for advanced optimization but removes debugging tools
3. **Single-stage build**: Rejected - includes unnecessary build tools in runtime (520MB)

### Dockerfile Structure

**Build Stage**:
- Install uv from official image (COPY --from pattern)
- Separate dependency installation from project installation (layer caching)
- Use BuildKit cache mounts for uv cache directory

**Runtime Stage**:
- Fresh python:3.13-slim base
- Create non-root user (appuser:1000)
- Copy only virtual environment from build stage
- Set PATH to use venv binaries directly

**Complete Dockerfile**:
```dockerfile
# ============================================
# Stage 1: Build environment
# ============================================
FROM python:3.13-slim AS build

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Build optimizations
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy dependency files (leverage layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies separately (better caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev

# Copy application code
COPY . .

# Install project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ============================================
# Stage 2: Runtime environment
# ============================================
FROM python:3.13-slim AS runtime

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Runtime environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
RUN chown -R appuser:appuser /app

# Copy virtual environment from build
COPY --from=build --chown=appuser:appuser /app /app

# Switch to non-root user
USER appuser

# Expose Cloud Run port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()"

# Start FastMCP server
CMD ["python", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Cloud Run Integration

**Port Configuration** ([src/server.py](../../src/server.py)):
```python
import os
from fastmcp import FastMCP

mcp = FastMCP("Australian Hansard RAG")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))

    mcp.run(
        transport="streamable-http",  # Cloud Run compatible
        host="0.0.0.0",  # CRITICAL: Must be 0.0.0.0, not 127.0.0.1
        port=port,
        path="/mcp"
    )
```

**Cloud SQL Connection**:
- **Method**: Built-in Cloud SQL connector (langchain-google-cloud-sql-pg)
- **No sidecar needed**: Cloud Run's `--add-cloudsql-instances` flag handles proxy
- **Connection string**: PostgresEngine.afrom_instance() with project_id/region/instance

**Deployment Command**:
```bash
gcloud run deploy hansard-mcp-server \
  --image=gcr.io/PROJECT_ID/hansard-mcp:latest \
  --region=us-central1 \
  --port=8080 \
  --cpu=2 \
  --memory=2Gi \
  --min-instances=0 \
  --max-instances=10 \
  --add-cloudsql-instances=PROJECT_ID:us-central1:hansard-db \
  --service-account=hansard-mcp-sa@PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars=GCP_PROJECT_ID=PROJECT_ID \
  --set-env-vars=CLOUDSQL_INSTANCE=hansard-db \
  --set-secrets=DATABASE_PASSWORD=db-password:latest \
  --no-allow-unauthenticated
```

### Security Hardening

**Non-Root User**:
```dockerfile
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser  # All subsequent commands run as appuser
```

**Secret Management**:
- ❌ Never use ARG/ENV for secrets (persists in image layers)
- ✅ Use Cloud Run `--set-secrets` (runtime injection from Secret Manager)
- ✅ Document expected env vars in Dockerfile (no values)

**.dockerignore** (reduces build context ~50MB → ~5MB):
```dockerignore
.git
.venv
__pycache__
*.pyc
.env
data/
logs/
specs/
.github/
README.md
Dockerfile*
```

### Build Commands

**Local Build**:
```bash
export DOCKER_BUILDKIT=1

docker build \
  --tag hansard-mcp:latest \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  .

# Test locally
docker run -p 8080:8080 \
  -e GCP_PROJECT_ID=PROJECT_ID \
  -e CLOUDSQL_INSTANCE=hansard-db \
  -e DATABASE_PASSWORD=test-password \
  hansard-mcp:latest
```

**Cloud Build**:
```bash
gcloud builds submit \
  --tag gcr.io/PROJECT_ID/hansard-mcp:latest \
  --timeout=20m
```

**Direct Cloud Run Source Deploy**:
```bash
# Automatically detects Dockerfile
gcloud run deploy hansard-mcp-server \
  --source=. \
  --region=us-central1
```

---

## Key Decisions Summary

### OAuth Authentication
- **Provider**: FastMCP GitHubProvider (environment-based config)
- **Storage**: Redis for persistent client registrations and encrypted tokens
- **Secrets**: Google Secret Manager with Cloud Run `--set-secrets`
- **Callback URL**: https://mcp.simonkennedymp.com.au/auth/callback

### Docker Containerization
- **Base Image**: python:3.13-slim (glibc compatibility)
- **Build Pattern**: Multi-stage (50% size reduction)
- **Package Manager**: uv (10-100x faster than pip)
- **Security**: Non-root user (appuser:1000)
- **Port**: 8080 with host="0.0.0.0"

### Cloud Run Deployment
- **Compute**: 2 vCPU, 2Gi memory
- **Scaling**: 0-10 instances (scale-to-zero cost optimization)
- **Connectivity**: Built-in Cloud SQL connector (no sidecar)
- **Health Checks**: /health (liveness), /ready (readiness)
- **Authentication**: GitHub OAuth (--no-allow-unauthenticated)

### Trade-offs Made
1. **Persistent tokens** (Redis) vs **ephemeral** (restart invalidates sessions)
   - Chose persistent for production UX
2. **Alpine** (27MB) vs **slim** (114MB)
   - Chose slim for glibc compatibility with LangChain
3. **OAuth scopes**: Minimal (user, user:email) vs broader
   - Chose minimal following principle of least privilege
4. **Cloud SQL connection**: Sidecar proxy vs built-in connector
   - Chose built-in for simplicity (Cloud Run handles automatically)

---

## References

- [FastMCP Authentication Documentation](https://github.com/jlowin/fastmcp/blob/main/docs/auth.md)
- [FastMCP GitHub Integration Guide](https://github.com/jlowin/fastmcp/blob/main/docs/guides/github-integration.md)
- [Google Cloud Run Docker Best Practices](https://cloud.google.com/run/docs/building/containers)
- [GitHub OAuth Scopes](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps)
- [LangChain Cloud SQL Integration](https://python.langchain.com/docs/integrations/vectorstores/google_cloud_sql_pg)
