# GitHub OAuth Setup Guide

## Step 1: Create GitHub OAuth App

Go to https://github.com/settings/developers → **OAuth Apps** → **New OAuth App**

### Production OAuth App

| Field | Value |
|-------|-------|
| **Application name** | `Australian Hansard RAG MCP` |
| **Homepage URL** | `https://mcp.simonkennedymp.com.au` |
| **Authorization callback URL** | `https://mcp.simonkennedymp.com.au/auth/callback` |

Click **Register application**.

GitHub will show you:
- ✅ **Client ID**: `Ov23li...` (public, visible)
- ✅ **Generate a new client secret** button - click it to get the secret (only shown once!)

**Copy both values immediately!**

### Development OAuth App (Optional)

For local testing, create a second OAuth App:

| Field | Value |
|-------|-------|
| **Application name** | `Australian Hansard RAG MCP (Dev)` |
| **Homepage URL** | `http://localhost:8080` |
| **Authorization callback URL** | `http://localhost:8080/auth/callback` |

---

## Step 2: Set GitHub Repository Secrets

**Replace the placeholder values below with your real credentials**:

```bash
# Production OAuth credentials (from first OAuth App)
gh secret set GITHUB_OAUTH_CLIENT_ID --body "Ov23liYOUR_REAL_CLIENT_ID_HERE"
gh secret set GITHUB_OAUTH_CLIENT_SECRET --body "YOUR_REAL_CLIENT_SECRET_HERE"

# Production base URL
gh secret set FASTMCP_SERVER_BASE_URL --body "https://mcp.simonkennedymp.com.au"

# OAuth provider configuration
gh secret set FASTMCP_SERVER_AUTH --body "fastmcp.server.auth.providers.github.GitHubProvider"
gh secret set FASTMCP_SERVER_AUTH_GITHUB_REQUIRED_SCOPES --body "user"
```

**Verify secrets were set**:
```bash
gh secret list
```

Expected output:
```
FASTMCP_SERVER_AUTH                          Updated ...
FASTMCP_SERVER_BASE_URL                      Updated ...
GCP_SERVICE_ACCOUNT_KEY                      Updated ...
GITHUB_OAUTH_CLIENT_ID                       Updated ...
GITHUB_OAUTH_CLIENT_SECRET                   Updated ...
```

---

## Step 3: Set Google Cloud Secret Manager (Production Runtime)

**Why Google Cloud Secrets?**
- GitHub Secrets → Used by **GitHub Actions CI/CD** (build/deploy time)
- Google Cloud Secret Manager → Used by **Cloud Run application** (runtime)

### Create Secrets in Google Cloud

```bash
# Set project
export PROJECT_ID="skai-fastmcp-cloudrun"
gcloud config set project $PROJECT_ID

# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Create secrets (replace with your real values)
echo -n "Ov23liYOUR_REAL_CLIENT_ID" | \
    gcloud secrets create fastmcp-github-oauth-client-id \
    --data-file=- \
    --replication-policy="automatic"

echo -n "YOUR_REAL_CLIENT_SECRET" | \
    gcloud secrets create fastmcp-github-oauth-client-secret \
    --data-file=- \
    --replication-policy="automatic"

echo -n "https://mcp.simonkennedymp.com.au" | \
    gcloud secrets create fastmcp-server-base-url \
    --data-file=- \
    --replication-policy="automatic"

# Grant Cloud Run service account access to secrets
export SERVICE_ACCOUNT="hansard-mcp-deployer@skai-fastmcp-cloudrun.iam.gserviceaccount.com"

gcloud secrets add-iam-policy-binding fastmcp-github-oauth-client-id \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding fastmcp-github-oauth-client-secret \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding fastmcp-server-base-url \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
```

### Verify Secrets

```bash
# List secrets
gcloud secrets list

# View secret metadata (not the value)
gcloud secrets describe fastmcp-github-oauth-client-id
gcloud secrets describe fastmcp-github-oauth-client-secret
gcloud secrets describe fastmcp-server-base-url
```

---

## Step 4: Configure Cloud Run to Use Secrets

When deploying to Cloud Run, mount secrets as environment variables:

```bash
gcloud run deploy hansard-mcp-server \
    --image gcr.io/skai-fastmcp-cloudrun/hansard-mcp-server \
    --region us-central1 \
    --set-env-vars FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.github.GitHubProvider \
    --set-env-vars FASTMCP_SERVER_AUTH_GITHUB_REQUIRED_SCOPES=user \
    --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=fastmcp-github-oauth-client-id:latest \
    --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=fastmcp-github-oauth-client-secret:latest \
    --set-secrets=FASTMCP_SERVER_BASE_URL=fastmcp-server-base-url:latest
```

Or in `deployment/cloud-run-config.yaml`:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: hansard-mcp-server
spec:
  template:
    spec:
      containers:
      - image: gcr.io/skai-fastmcp-cloudrun/hansard-mcp-server
        env:
        - name: FASTMCP_SERVER_AUTH
          value: "fastmcp.server.auth.providers.github.GitHubProvider"
        - name: FASTMCP_SERVER_AUTH_GITHUB_REQUIRED_SCOPES
          value: "user"
        - name: FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: fastmcp-github-oauth-client-id
              key: latest
        - name: FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: fastmcp-github-oauth-client-secret
              key: latest
        - name: FASTMCP_SERVER_BASE_URL
          valueFrom:
            secretKeyRef:
              name: fastmcp-server-base-url
              key: latest
```

---

## Step 5: Local Development Setup

Create `.env` file (gitignored, not committed):

```bash
# Copy example
cp .env.example .env

# Edit .env with your DEV OAuth App credentials
nano .env
```

Update these lines in `.env`:
```bash
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=Ov23liYOUR_DEV_CLIENT_ID
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=YOUR_DEV_CLIENT_SECRET
FASTMCP_SERVER_BASE_URL=http://localhost:8080
```

**Test locally**:
```bash
# Load environment
source .env

# Run server with HTTP transport
fastmcp run src/server.py --transport http --port 8080

# Browser should open and redirect to GitHub OAuth
```

---

## Secret Management Summary

| Secret | GitHub Secrets | Google Cloud Secret Manager | Local .env |
|--------|---------------|----------------------------|-----------|
| **Purpose** | CI/CD (GitHub Actions) | Runtime (Cloud Run) | Local dev |
| **Client ID** | `GITHUB_OAUTH_CLIENT_ID` | `fastmcp-github-oauth-client-id` | In `.env` file |
| **Client Secret** | `GITHUB_OAUTH_CLIENT_SECRET` | `fastmcp-github-oauth-client-secret` | In `.env` file |
| **Base URL** | `FASTMCP_SERVER_BASE_URL` | `fastmcp-server-base-url` | In `.env` file |
| **Provider** | `FASTMCP_SERVER_AUTH` | Set as env var | In `.env` file |
| **Scopes** | `FASTMCP_SERVER_AUTH_GITHUB_REQUIRED_SCOPES` | Set as env var | In `.env` file |

---

## Security Best Practices

### ✅ DO
- Use **different OAuth Apps** for dev/prod
- Store secrets in **GitHub Secrets** (for CI/CD)
- Store secrets in **Google Cloud Secret Manager** (for runtime)
- Keep `.env` file local (already in `.gitignore`)
- Rotate OAuth secrets every 90 days
- Use `roles/secretmanager.secretAccessor` (least privilege)

### ❌ DON'T
- Commit OAuth credentials to git
- Share OAuth credentials across environments
- Use same OAuth App for dev and prod
- Store secrets in source code
- Use repository variables for sensitive data (use secrets instead)

---

## Troubleshooting

### "OAuth redirect URI mismatch"
Check that callback URL in GitHub OAuth App matches:
- Production: `https://mcp.simonkennedymp.com.au/auth/callback`
- Dev: `http://localhost:8080/auth/callback`

### "Secret not found" in Cloud Run
Verify Cloud Run service account has `secretmanager.secretAccessor` role:
```bash
gcloud secrets get-iam-policy fastmcp-github-oauth-client-id
```

### "Invalid client_secret"
Regenerate client secret in GitHub OAuth App settings (old secret will be invalidated).

---

**Last Updated**: 2025-10-21
**Project**: skai-fastmcp-cloudrun (666924716777)
