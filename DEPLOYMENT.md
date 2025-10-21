# Production Deployment Guide

This guide covers deploying the Australian Hansard RAG MCP server to Google Cloud Run with GitHub OAuth authentication and username whitelist.

## Prerequisites

- Google Cloud Project with billing enabled
- Cloud Run, Secret Manager, Cloud SQL, Vertex AI APIs enabled
- `gcloud` CLI authenticated
- Docker installed (for local testing)
- GitHub OAuth App created

## Architecture Overview

```
Client (Claude Desktop/MCP Inspector)
    ↓ HTTPS
Cloud Run (hansard-mcp-server)
    ↓ OAuth → GitHub (authentication)
    ↓ JWT → Whitelist (sc0sk authorization)
    ↓ IAM Auth → Cloud SQL PostgreSQL + pgvector
    ↓ API → Vertex AI Embeddings (text-embedding-005)
```

## 1. Secrets Setup

All sensitive configuration is stored in Google Secret Manager:

```bash
# GitHub OAuth credentials (from GitHub OAuth App settings)
echo -n "Ov23li..." | gcloud secrets create github-oauth-client-id --data-file=-
echo -n "..." | gcloud secrets create github-oauth-client-secret --data-file=-

# JWT signing and token encryption keys (generate with scripts/generate_secrets.py)
python3 scripts/generate_secrets.py
echo -n "<generated-jwt-key>" | gcloud secrets create jwt-signing-key --data-file=-
echo -n "<generated-token-key>" | gcloud secrets create token-encryption-key --data-file=-

# Cloud SQL IAM user
echo -n "scott.coleman@aph.gov.au" | gcloud secrets create cloudsql-user --data-file=-

# GitHub username whitelist (comma-separated for multiple users)
echo -n "sc0sk" | gcloud secrets create github-allowed-usernames --data-file=-

# Grant Cloud Run service account access to secrets
SERVICE_ACCOUNT="666924716777-compute@developer.gserviceaccount.com"
for secret in github-oauth-client-id github-oauth-client-secret jwt-signing-key token-encryption-key cloudsql-user github-allowed-usernames; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"
done
```

## 2. Build and Push Docker Image

```bash
# Build using Cloud Build (supports BuildKit for cache mounts)
gcloud builds submit --config=cloudbuild.yaml

# This creates:
# - gcr.io/skai-fastmcp-cloudrun/hansard-mcp:latest
# - gcr.io/skai-fastmcp-cloudrun/hansard-mcp:v002
```

## 3. Deploy to Cloud Run

```bash
gcloud run deploy hansard-mcp-server \
  --image=gcr.io/skai-fastmcp-cloudrun/hansard-mcp:latest \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated \
  --port=8080 \
  --set-env-vars="GCP_PROJECT_ID=skai-fastmcp-cloudrun,GCP_REGION=us-central1,CLOUDSQL_INSTANCE=hansard-db,CLOUDSQL_DATABASE=hansard,VERTEX_AI_LOCATION=us-central1,FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.github.GitHubProvider,FASTMCP_SERVER_AUTH_GITHUB_BASE_URL=https://hansard-mcp-server-666924716777.us-central1.run.app" \
  --set-secrets="CLOUDSQL_USER=cloudsql-user:latest,FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=github-oauth-client-id:latest,FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=github-oauth-client-secret:latest,JWT_SIGNING_KEY=jwt-signing-key:latest,TOKEN_ENCRYPTION_KEY=token-encryption-key:latest,GITHUB_ALLOWED_USERNAMES=github-allowed-usernames:latest" \
  --service-account=666924716777-compute@developer.gserviceaccount.com \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300 \
  --min-instances=0 \
  --max-instances=10 \
  --concurrency=80
```

## 4. Verify Deployment

```bash
# Health check (should return "OK")
curl https://hansard-mcp-server-666924716777.us-central1.run.app/health

# Readiness check (should return JSON with status:"healthy")
curl https://hansard-mcp-server-666924716777.us-central1.run.app/ready

# View logs
gcloud run logs read hansard-mcp-server --region=us-central1 --limit=50
```

## 5. GitHub OAuth Configuration

Update your GitHub OAuth App settings:
- **Authorization callback URL**: `https://hansard-mcp-server-666924716777.us-central1.run.app/auth/callback`
- **Homepage URL**: `https://mcp.simonkennedymp.com.au` (or your custom domain)

## 6. Username Whitelist Management

Only users in the `GITHUB_ALLOWED_USERNAMES` secret can authenticate:

```bash
# View current whitelist
gcloud secrets versions access latest --secret=github-allowed-usernames

# Update whitelist (comma-separated for multiple users)
echo -n "sc0sk,anotheruser" | gcloud secrets versions add github-allowed-usernames --data-file=-

# Redeploy to pick up new secret version
gcloud run services update hansard-mcp-server --region=us-central1 --update-secrets="GITHUB_ALLOWED_USERNAMES=github-allowed-usernames:latest"
```

## 7. Local Development

For local testing without OAuth:

```bash
# Set bypass flag (NEVER use in production)
export DANGEROUSLY_OMIT_AUTH=true

# Run with Docker
docker run -p 8080:8080 \
  -e DANGEROUSLY_OMIT_AUTH=true \
  -e GCP_PROJECT_ID=skai-fastmcp-cloudrun \
  -e CLOUDSQL_INSTANCE=hansard-db \
  hansard-mcp:latest

# Or run directly with uv
PORT=8080 DANGEROUSLY_OMIT_AUTH=true uv run python -m src.server
```

## Security Best Practices

1. **Secrets Storage**: All sensitive data (OAuth credentials, JWT keys, whitelist) in Google Secret Manager
2. **Username Whitelist**: Only `sc0sk` GitHub account can authenticate (configurable via secret)
3. **IAM Authentication**: Cloud SQL uses IAM authentication (no password)
4. **Non-Root Container**: Docker runs as UID 1000 (appuser), not root
5. **HTTPS Only**: Cloud Run enforces HTTPS for all traffic
6. **Minimal Image**: Multi-stage build, Python 3.13-slim base
7. **No Secrets in Code**: All credentials loaded from environment/secrets at runtime

## Monitoring

```bash
# View recent logs
gcloud run logs read hansard-mcp-server --region=us-central1 --tail=100

# Stream logs in real-time
gcloud run logs tail hansard-mcp-server --region=us-central1

# Check authorization decisions
gcloud run logs read hansard-mcp-server --region=us-central1 | grep "Authorization"
```

## Troubleshooting

### Health Check Fails
```bash
# Check container logs
gcloud run logs read hansard-mcp-server --region=us-central1 --limit=100

# Verify secrets are accessible
gcloud run services describe hansard-mcp-server --region=us-central1 --format="get(spec.template.spec.containers[0].env)"
```

### OAuth Flow Fails
- Verify GitHub OAuth App callback URL matches Cloud Run service URL
- Check `FASTMCP_SERVER_AUTH_GITHUB_BASE_URL` matches actual service URL
- Ensure `FASTMCP_SERVER_AUTH` is set to `fastmcp.server.auth.providers.github.GitHubProvider`

### Unauthorized User (403)
- User's GitHub username is not in `GITHUB_ALLOWED_USERNAMES` secret
- Update the secret and redeploy:
  ```bash
  echo -n "sc0sk,newuser" | gcloud secrets versions add github-allowed-usernames --data-file=-
  gcloud run services update hansard-mcp-server --region=us-central1 --update-secrets="GITHUB_ALLOWED_USERNAMES=github-allowed-usernames:latest"
  ```

## Production URLs

- **Service URL**: https://hansard-mcp-server-666924716777.us-central1.run.app
- **Health Check**: https://hansard-mcp-server-666924716777.us-central1.run.app/health
- **Readiness Check**: https://hansard-mcp-server-666924716777.us-central1.run.app/ready
- **OAuth Callback**: https://hansard-mcp-server-666924716777.us-central1.run.app/auth/callback
- **MCP SSE Endpoint**: https://hansard-mcp-server-666924716777.us-central1.run.app/mcp/v1/

## Cost Optimization

Current configuration:
- **Min instances**: 0 (scales to zero when idle)
- **Max instances**: 10
- **Memory**: 2Gi
- **CPU**: 2
- **Concurrency**: 80 requests per instance

Estimated monthly cost (assuming light usage):
- Cloud Run: ~$5-10/month (mostly cold starts + minimal active time)
- Cloud SQL: ~$25/month (db-f1-micro)
- Vertex AI Embeddings: Pay-per-use (~$0.00002/1000 chars)
- Secret Manager: $0.06/secret/month (~$0.36/month for 6 secrets)
- **Total**: ~$30-40/month

## Next Steps

1. **Custom Domain** (optional): Map `mcp.simonkennedymp.com.au` to Cloud Run service
2. **Redis** (recommended for production): Add Cloud Memorystore for persistent OAuth token storage
3. **Monitoring**: Set up Cloud Monitoring alerts for health check failures
4. **Backup**: Schedule Cloud SQL backups
5. **CI/CD**: Automate deployments via GitHub Actions
