# Quickstart: GitHub OAuth Authentication and Docker Deployment

**Feature**: 002-github-oauth-docker
**Date**: 2025-10-21
**Prerequisites**: Feature 001-hansard-rag-implementation deployed and tested

This guide walks through setting up GitHub OAuth authentication and deploying the Hansard RAG MCP server to Google Cloud Run using Docker.

---

## Prerequisites

### Required Tools
- [x] Docker 24+ with BuildKit enabled
- [x] Google Cloud SDK (`gcloud`) authenticated
- [x] `uv` package manager (for local development)
- [x] GitHub account (for OAuth app registration)
- [x] Access to Google Cloud project with Cloud Run, Secret Manager, and Artifact Registry enabled

### Existing Infrastructure (from Feature 001)
- [x] Cloud SQL PostgreSQL instance with pgvector extension
- [x] Hansard speeches ingested into database (21 speeches, 196 chunks)
- [x] Vertex AI API enabled for embeddings
- [x] Custom domain `mcp.simonkennedymp.com.au` configured with SSL certificate

---

## Part 1: GitHub OAuth App Setup

### 1.1 Create GitHub OAuth App

1. Navigate to GitHub Settings → Developer settings → OAuth Apps
2. Click **"New OAuth App"**
3. Fill in application details:
   - **Application name**: `Australian Hansard RAG MCP Server`
   - **Homepage URL**: `https://mcp.simonkennedymp.com.au`
   - **Authorization callback URL**: `https://mcp.simonkennedymp.com.au/auth/callback`
   - **Application description** (optional): `MCP server for searching Australian Hansard speeches`
4. Click **"Register application"**
5. On the application page:
   - Copy the **Client ID** (e.g., `Ov23liAbcDefGhiJkLmN`)
   - Click **"Generate a new client secret"**
   - Copy the **Client Secret** (e.g., `github_pat_11AABBCCDD...`)
   - ⚠️ **Important**: Store these securely - you won't see the secret again

### 1.2 Store Credentials in Google Secret Manager

```bash
# Store GitHub OAuth credentials
echo -n "Ov23liAbcDefGhiJkLmN" | gcloud secrets create github-client-id \
  --data-file=- \
  --replication-policy=automatic

echo -n "github_pat_11AABBCCDD..." | gcloud secrets create github-client-secret \
  --data-file=- \
  --replication-policy=automatic

# Store JWT signing key (generate random string)
openssl rand -base64 32 | gcloud secrets create jwt-signing-key \
  --data-file=- \
  --replication-policy=automatic

# Store token encryption key (generate random string)
openssl rand -base64 32 | gcloud secrets create token-encryption-key \
  --data-file=- \
  --replication-policy=automatic

# Verify secrets were created
gcloud secrets list
```

### 1.3 Grant Cloud Run Service Account Access to Secrets

```bash
# Get the Cloud Run service account (or create one)
SERVICE_ACCOUNT="hansard-mcp-sa@$(gcloud config get-value project).iam.gserviceaccount.com"

# Grant Secret Manager access
for secret in github-client-id github-client-secret jwt-signing-key token-encryption-key db-password; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"
done
```

---

## Part 2: Docker Containerization

### 2.1 Create Dockerfile

Create `Dockerfile` in the project root:

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
COPY src ./src
COPY scripts ./scripts

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
CMD ["python", "-m", "src.server"]
```

### 2.2 Create .dockerignore

```dockerignore
# Version control
.git
.gitignore

# Python cache
__pycache__
*.py[cod]
.Python

# Virtual environments
venv/
env/
.venv/

# Testing
.pytest_cache/
.coverage
htmlcov/

# IDEs
.vscode/
.idea/
.DS_Store

# Documentation
specs/
docs/
*.md

# Docker
Dockerfile*
docker-compose*.yml
.dockerignore

# Environment files
.env
.env.local
*.pem
*.key

# Data
data/
logs/
*.db

# CI/CD
.github/
```

### 2.3 Update src/server.py for Cloud Run

Add startup configuration at the bottom of [src/server.py](../../../src/server.py):

```python
import os
from fastmcp import FastMCP
from starlette.responses import PlainTextResponse

mcp = FastMCP("Australian Hansard RAG")

# ... existing tools ...

# Health check endpoints
@mcp.custom_route("/health", methods=["GET"])
async def health_check():
    """Liveness probe for Cloud Run."""
    return PlainTextResponse("OK")

@mcp.custom_route("/ready", methods=["GET"])
async def readiness_check():
    """Readiness probe - verify database connectivity."""
    try:
        from src.storage.vector_store import VectorStoreService
        store = VectorStoreService()
        # Quick connectivity check
        return PlainTextResponse("READY", status_code=200)
    except Exception as e:
        return PlainTextResponse(f"NOT READY: {str(e)}", status_code=503)

# Cloud Run entry point
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",  # CRITICAL: Must be 0.0.0.0, not localhost
        port=port,
        path="/mcp"
    )
```

---

## Part 3: Local Testing

### 3.1 Build Docker Image Locally

```bash
# Enable BuildKit for better caching
export DOCKER_BUILDKIT=1

# Build image
docker build --tag hansard-mcp:latest .

# Verify image size (target: ~270MB)
docker images hansard-mcp:latest
```

### 3.2 Run Container Locally

```bash
# Create .env file for local testing (DO NOT COMMIT)
cat > .env.local <<EOF
GCP_PROJECT_ID=$(gcloud config get-value project)
GCP_REGION=us-central1
CLOUDSQL_INSTANCE=hansard-db
CLOUDSQL_DATABASE=hansard
CLOUDSQL_USER=postgres
DATABASE_PASSWORD=your-local-db-password
VERTEX_AI_LOCATION=us-central1
FASTMCP_SERVER_AUTH_GITHUB_BASE_URL=http://localhost:8080
DANGEROUSLY_OMIT_AUTH=true  # Skip OAuth for local testing
EOF

# Run container
docker run -p 8080:8080 --env-file .env.local hansard-mcp:latest

# Test health endpoint (in another terminal)
curl http://localhost:8080/health
# Expected: OK

curl http://localhost:8080/ready
# Expected: READY
```

### 3.3 Test MCP Endpoint

```bash
# Test MCP tools discovery
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'

# Expected: List of tools (search, fetch, dataset_stats)
```

---

## Part 4: Deploy to Cloud Run

### 4.1 Build and Push to Artifact Registry

```bash
# Set project ID
PROJECT_ID=$(gcloud config get-value project)

# Build and submit to Cloud Build
gcloud builds submit \
  --tag gcr.io/$PROJECT_ID/hansard-mcp:latest \
  --timeout=20m

# Verify image was pushed
gcloud container images list --repository=gcr.io/$PROJECT_ID
```

### 4.2 Deploy to Cloud Run

```bash
PROJECT_ID=$(gcloud config get-value project)
REGION=us-central1
SERVICE_ACCOUNT="hansard-mcp-sa@$PROJECT_ID.iam.gserviceaccount.com"

gcloud run deploy hansard-mcp-server \
  --image=gcr.io/$PROJECT_ID/hansard-mcp:latest \
  --region=$REGION \
  --platform=managed \
  --port=8080 \
  --cpu=2 \
  --memory=2Gi \
  --min-instances=0 \
  --max-instances=10 \
  --concurrency=80 \
  --timeout=300 \
  --service-account=$SERVICE_ACCOUNT \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:hansard-db \
  --set-env-vars=FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.github.GitHubProvider \
  --set-env-vars=FASTMCP_SERVER_AUTH_GITHUB_BASE_URL=https://mcp.simonkennedymp.com.au \
  --set-env-vars=GCP_PROJECT_ID=$PROJECT_ID \
  --set-env-vars=GCP_REGION=$REGION \
  --set-env-vars=CLOUDSQL_INSTANCE=hansard-db \
  --set-env-vars=CLOUDSQL_DATABASE=hansard \
  --set-env-vars=CLOUDSQL_USER=postgres \
  --set-env-vars=VERTEX_AI_LOCATION=$REGION \
  --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=github-client-id:latest \
  --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=github-client-secret:latest \
  --set-secrets=JWT_SIGNING_KEY=jwt-signing-key:latest \
  --set-secrets=TOKEN_ENCRYPTION_KEY=token-encryption-key:latest \
  --set-secrets=DATABASE_PASSWORD=db-password:latest \
  --no-allow-unauthenticated
```

### 4.3 Update Domain Mapping

```bash
# Map custom domain to Cloud Run service
gcloud run domain-mappings create \
  --service=hansard-mcp-server \
  --domain=mcp.simonkennedymp.com.au \
  --region=$REGION

# Verify domain mapping
gcloud run domain-mappings describe mcp.simonkennedymp.com.au \
  --region=$REGION
```

---

## Part 5: Verify Deployment

### 5.1 Test Public Endpoints

```bash
# Test health endpoint (no auth required)
curl https://mcp.simonkennedymp.com.au/health
# Expected: OK

curl https://mcp.simonkennedymp.com.au/ready
# Expected: READY
```

### 5.2 Test OAuth Configuration

```bash
# Check OAuth metadata endpoint
curl https://mcp.simonkennedymp.com.au/.well-known/oauth-authorization-server

# Expected: OAuth server metadata (authorization_endpoint, token_endpoint, etc.)
```

### 5.3 Connect with MCP Client

**Claude Desktop Configuration** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "hansard-rag": {
      "url": "https://mcp.simonkennedymp.com.au/mcp",
      "transport": "streamable-http"
    }
  }
}
```

**Testing Flow**:
1. Restart Claude Desktop
2. MCP client initiates dynamic registration
3. Browser opens to GitHub OAuth consent page
4. User approves access
5. Tokens exchanged, client authenticated
6. Try query: "Search for speeches about climate change"

---

## Part 6: Redis Setup (Optional - For Production Token Persistence)

### 6.1 Create Cloud Memorystore Redis Instance

```bash
# Create Redis instance (basic tier for dev, standard for prod)
gcloud redis instances create hansard-oauth-cache \
  --size=1 \
  --region=$REGION \
  --redis-version=redis_7_0 \
  --tier=basic

# Get Redis host IP
REDIS_HOST=$(gcloud redis instances describe hansard-oauth-cache \
  --region=$REGION \
  --format="value(host)")

# Store in Secret Manager (optional)
echo -n "$REDIS_HOST" | gcloud secrets create redis-host --data-file=-
```

### 6.2 Update Cloud Run Deployment with Redis

```bash
# Redeploy with Redis configuration
gcloud run deploy hansard-mcp-server \
  --image=gcr.io/$PROJECT_ID/hansard-mcp:latest \
  --update-env-vars=REDIS_HOST=$REDIS_HOST \
  --update-env-vars=REDIS_PORT=6379 \
  ... (other flags from 4.2)
```

---

## Troubleshooting

### Issue: Container fails to start

**Symptoms**: Cloud Run shows "Container failed to start" error

**Solutions**:
```bash
# Check Cloud Run logs
gcloud run services logs read hansard-mcp-server --region=$REGION --limit=50

# Common issues:
# 1. Missing environment variables
# 2. Secret Manager permissions
# 3. Port binding (must be 0.0.0.0, not localhost)
```

### Issue: OAuth callback fails

**Symptoms**: "Redirect URI mismatch" error

**Solutions**:
1. Verify GitHub OAuth App callback URL matches exactly: `https://mcp.simonkennedymp.com.au/auth/callback`
2. Check `FASTMCP_SERVER_AUTH_GITHUB_BASE_URL` environment variable
3. Ensure HTTPS (not HTTP) in production

### Issue: Database connection timeout

**Symptoms**: "Could not connect to Cloud SQL" error

**Solutions**:
```bash
# Verify Cloud SQL instance is running
gcloud sql instances describe hansard-db

# Check Cloud Run service account has Cloud SQL Client role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/cloudsql.client"

# Verify --add-cloudsql-instances flag is correct
gcloud run services describe hansard-mcp-server --region=$REGION \
  --format="value(spec.template.spec.containers[0].env)"
```

---

## Next Steps

1. **Monitor Logs**: `gcloud run services logs tail hansard-mcp-server --region=$REGION`
2. **Set Up Alerts**: Configure Cloud Monitoring for error rate, latency, and uptime
3. **Enable Redis**: For production, deploy Cloud Memorystore Redis for token persistence
4. **CI/CD Pipeline**: Set up GitHub Actions for automated builds and deployments
5. **Test Authentication**: Connect multiple MCP clients to verify OAuth flow
6. **Performance Tuning**: Adjust CPU/memory based on actual usage patterns

---

## Quick Reference

**Local Development**:
```bash
# Build and run locally
docker build -t hansard-mcp:latest .
docker run -p 8080:8080 --env-file .env.local hansard-mcp:latest
```

**Deploy to Cloud Run**:
```bash
# One-command deployment (after initial setup)
gcloud builds submit --tag gcr.io/$PROJECT_ID/hansard-mcp:latest && \
gcloud run deploy hansard-mcp-server --image=gcr.io/$PROJECT_ID/hansard-mcp:latest --region=us-central1
```

**View Logs**:
```bash
gcloud run services logs tail hansard-mcp-server --region=us-central1
```

**Rollback Deployment**:
```bash
gcloud run services update-traffic hansard-mcp-server \
  --to-revisions=hansard-mcp-server-00001-abc=100 \
  --region=us-central1
```
