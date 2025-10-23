# Remote SSE Setup Guide

**Goal**: Connect Google Gemini CLI to remote Hansard MCP server on Cloud Run in 15 minutes

**Transport**: SSE (Server-Sent Events over HTTPS)

**Use Case**: Production access, team collaboration, shared cloud database

**Target Time**: 15 minutes from start to verified working setup

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Cloud Run Deployment](#cloud-run-deployment)
3. [Authentication Setup](#authentication-setup)
4. [SSE Configuration](#sse-configuration)
5. [Verification](#verification)
6. [Performance Considerations](#performance-considerations)
7. [Security Best Practices](#security-best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### 1. Deployed Cloud Run Service

**Requirement**: Hansard MCP server must be deployed to Google Cloud Run

**Verify Deployment**:
```bash
# List Cloud Run services
gcloud run services list

# Get service URL
gcloud run services describe hansard-mcp-server \
  --format='value(status.url)'
```

**Expected Output**:
```
https://hansard-mcp-server-PROJECT_ID.a.run.app
```

**If not deployed**, see deployment documentation:
- [/home/user/skai-fastmcp-cloudrun/deployment/](/home/user/skai-fastmcp-cloudrun/deployment/)
- [/home/user/skai-fastmcp-cloudrun/specs/002-github-oauth-docker/](/home/user/skai-fastmcp-cloudrun/specs/002-github-oauth-docker/)

---

### 2. Google Cloud Authentication

**Requirement**: Valid Google Cloud credentials with Cloud Run Invoker permissions

**Verify Authentication**:
```bash
# Check current user
gcloud auth list

# Verify active account
gcloud config get-value account
```

**Required Permissions**:
- `roles/run.invoker` - Permission to invoke Cloud Run services
- Or service allows unauthenticated access (development only)

---

### 3. Network Access

**Requirement**: HTTPS connectivity to Cloud Run endpoint

**Test Connectivity**:
```bash
# Test endpoint accessibility
curl -I https://YOUR-SERVICE-URL.a.run.app/health

# Expected: HTTP/2 200 or 401 (401 means endpoint exists but needs auth)
```

---

### 4. Gemini CLI Installed

**Requirement**: Gemini CLI v1.0.0 or higher

**Verify Installation**:
```bash
gemini --version
```

**If not installed**:
```bash
npm install -g @google/gemini-cli
```

---

## Cloud Run Deployment

### Step 1: Verify Service Status

Check that your Cloud Run service is running and healthy:

```bash
# Get service status
gcloud run services describe hansard-mcp-server \
  --format='json(status.conditions)'

# Check recent logs
gcloud run services logs read hansard-mcp-server --limit=10
```

**Success Indicators**:
- Service status shows `Ready: True`
- No error messages in recent logs
- Health check endpoint returns 200

---

### Step 2: Test Health Endpoint

Verify the service is responding to requests:

```bash
# Generate auth token
TOKEN=$(gcloud auth print-identity-token)

# Test health endpoint
curl -H "Authorization: Bearer $TOKEN" \
  https://YOUR-SERVICE-URL.a.run.app/health

# Expected output: {"status": "healthy"}
```

**If health check fails**, see [Troubleshooting - Service Issues](#service-issues).

---

### Step 3: Check Authentication Requirements

Determine if your service requires authentication:

```bash
# Test unauthenticated access
curl -I https://YOUR-SERVICE-URL.a.run.app/health

# If returns 200: Service allows unauthenticated access
# If returns 401: Service requires authentication (recommended for production)
```

**Recommended Settings**:
- **Development**: Allow unauthenticated access for testing
- **Production**: Require authentication with IAM

---

## Authentication Setup

### Option A: User Identity Token (Recommended for Development)

**Use Case**: Personal development, quick testing, short-term access

**Advantages**:
- Quick setup (one command)
- Uses your Google Cloud credentials
- No service account management

**Disadvantages**:
- Tokens expire in ~1 hour
- Requires manual refresh
- Not suitable for automated workflows

**Generate Token**:
```bash
# Generate identity token
gcloud auth print-identity-token

# Copy the output token for configuration step
```

**Token Expiration**: ~60 minutes

**Refresh Command**:
```bash
# Regenerate token when expired
TOKEN=$(gcloud auth print-identity-token)
echo "New token: $TOKEN"
```

---

### Option B: Service Account Token (Recommended for Production)

**Use Case**: Production deployments, team access, automated workflows

**Advantages**:
- Longer-lived tokens
- Can be automated
- Better audit trail
- Fine-grained permissions

**Disadvantages**:
- More complex setup
- Requires IAM configuration

**Setup Steps**:

**1. Create Service Account**:
```bash
# Create service account for Gemini CLI users
gcloud iam service-accounts create gemini-cli-user \
  --display-name="Gemini CLI User" \
  --description="Service account for Gemini CLI access to Hansard MCP"
```

**2. Grant Cloud Run Invoker Permission**:
```bash
# Grant permission to invoke Cloud Run service
gcloud run services add-iam-policy-binding hansard-mcp-server \
  --member="serviceAccount:gemini-cli-user@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

**3. Generate Token**:
```bash
# Generate service account token
gcloud auth print-identity-token \
  --impersonate-service-account=gemini-cli-user@PROJECT_ID.iam.gserviceaccount.com
```

**4. Token Rotation**:

Set up automated token refresh (see [sse-token-refresh.sh](#automation-script) below).

---

### Option C: No Authentication (Development Only)

**Use Case**: Local development, internal testing, POC deployments

**WARNING**: Do NOT use in production. Exposes service to public internet.

**Deploy Without Authentication**:
```bash
gcloud run deploy hansard-mcp-server \
  --allow-unauthenticated \
  --image=gcr.io/PROJECT_ID/hansard-mcp:latest
```

**Configuration**: Omit `Authorization` header in Gemini CLI config (see below).

---

## SSE Configuration

### Step 1: Locate Gemini CLI Config File

**macOS/Linux**:
```bash
~/.config/gemini-cli/config.json
```

**Windows**:
```powershell
%APPDATA%\gemini-cli\config.json
```

---

### Step 2: Add SSE Configuration

Open `config.json` and add the Hansard server with SSE transport:

**Configuration Template**:

Replace the following placeholders:
- `YOUR-SERVICE-URL`: Your Cloud Run service URL
- `YOUR_TOKEN`: Generated identity token from authentication step

```json
{
  "mcpServers": {
    "hansard": {
      "transport": "sse",
      "url": "https://YOUR-SERVICE-URL.a.run.app",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN",
        "Content-Type": "application/json"
      },
      "timeout": 60,
      "description": "Australian Hansard parliamentary speech search (Cloud Run production)"
    }
  }
}
```

---

### Complete Example

**With Authentication** (Production):
```json
{
  "mcpServers": {
    "hansard": {
      "transport": "sse",
      "url": "https://hansard-mcp-server-my-project-123.a.run.app",
      "headers": {
        "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6ImFiYzEyMyIs...",
        "Content-Type": "application/json"
      },
      "timeout": 60,
      "description": "Australian Hansard parliamentary speech search (Cloud Run production)"
    }
  }
}
```

**Without Authentication** (Development):
```json
{
  "mcpServers": {
    "hansard": {
      "transport": "sse",
      "url": "https://hansard-mcp-dev-my-project-123.a.run.app",
      "timeout": 60,
      "description": "Australian Hansard parliamentary speech search (Cloud Run development)"
    }
  }
}
```

---

### URL Format Explanation

Cloud Run service URLs follow this pattern:
```
https://SERVICE_NAME-PROJECT_ID.REGION.run.app
```

**Example**:
- **Service Name**: `hansard-mcp-server`
- **Project ID**: `my-gcp-project-123`
- **Region**: `us-central1` (encoded as `a` in URL)
- **Full URL**: `https://hansard-mcp-server-my-gcp-project-123.a.run.app`

**Find Your URL**:
```bash
gcloud run services describe hansard-mcp-server --format='value(status.url)'
```

---

### Step 3: Restart Gemini CLI

After saving the configuration:

```bash
# Restart Gemini CLI
gemini restart

# Or start fresh session
gemini
```

---

## Verification

### Test 1: Connection Test (5 seconds)

**Command**: In Gemini CLI, ask:
```
What Hansard tools are available?
```

**Expected Response**:
```
Available Hansard tools:
1. hansard_search - Search Australian parliamentary speeches
2. hansard_fetch - Retrieve full speech text by ID
3. hansard_ingest - Add new speeches to database
```

**Success Criteria**:
- All three tools listed
- No connection errors
- Response time under 5 seconds (cold start may take 10-30 seconds on first request)

---

### Test 2: Remote Query Execution (3-10 seconds)

**Command**: In Gemini CLI, ask:
```
Search Hansard for speeches about climate change
```

**Expected Response**:
Search results from the cloud database with speaker names, dates, and excerpts.

**Success Criteria**:
- Results returned within 3-10 seconds
- Data matches cloud database content
- No authentication errors

---

### Test 3: Performance Verification

**First Query** (Cold Start):
```
Search Hansard for speeches about education policy
```

Expected time: 10-30 seconds (Cloud Run container startup)

**Second Query** (Warm):
```
Search Hansard for speeches about healthcare
```

Expected time: 2-5 seconds (container already running)

**Success Criteria**:
- Cold start completes within 30 seconds
- Warm queries complete within 5 seconds
- No timeout errors

---

## Performance Considerations

### Cold Start Delays

**Issue**: First request after idle period takes 10-30 seconds

**Causes**:
- Cloud Run container startup time
- Database connection initialization
- Model loading for embeddings

**Mitigation**:
```bash
# Keep service warm with minimum instances
gcloud run services update hansard-mcp-server \
  --min-instances=1
```

**Trade-off**: Minimum instances incur costs even when idle.

---

### Query Response Times

**Expected Performance**:

| Operation | Cold Start | Warm |
|-----------|------------|------|
| Tool Discovery | 10-30s | 1s |
| Search Query | 15-30s | 3-5s |
| Fetch by ID | 10-20s | 1-2s |

**Optimization Tips**:
1. Increase `timeout` in config if queries are slow:
   ```json
   "timeout": 120
   ```

2. Monitor Cloud Run metrics:
   ```bash
   gcloud run services describe hansard-mcp-server \
     --format='json(status.latestCreatedRevisionName)'
   ```

3. Check database performance (Cloud SQL):
   ```bash
   gcloud sql operations list --instance=hansard-db
   ```

---

### Timeout Configuration

**Recommended Timeout Settings**:

**Development** (expecting cold starts):
```json
"timeout": 60
```

**Production** (with minimum instances):
```json
"timeout": 30
```

**Large Queries** (complex searches):
```json
"timeout": 120
```

---

## Security Best Practices

### Token Management

**DO**:
- Generate new tokens regularly (daily/weekly)
- Use service accounts for production
- Store tokens securely (not in version control)
- Rotate tokens after team member departure

**DON'T**:
- Commit tokens to Git repositories
- Share tokens via email or chat
- Use personal tokens for production
- Leave tokens in shell history

---

### Token Storage

**Secure Storage Options**:

**1. Environment Variables** (Recommended):
```bash
# Store token in environment
export HANSARD_TOKEN=$(gcloud auth print-identity-token)

# Reference in config (if Gemini CLI supports env vars)
"Authorization": "Bearer ${HANSARD_TOKEN}"
```

**2. Secret Management**:
```bash
# Store in Google Secret Manager
gcloud secrets create gemini-hansard-token \
  --data-file=- <<< "$(gcloud auth print-identity-token)"

# Retrieve when needed
gcloud secrets versions access latest --secret=gemini-hansard-token
```

**3. Automated Refresh Script**:

See [sse-token-refresh.sh](#automation-script) below for automated token rotation.

---

### Credentials Management

**Avoid Hardcoding Tokens**:

**Bad** (token in config file):
```json
"headers": {
  "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6ImFiYzEyMyIs..."
}
```

**Good** (reference to secure storage):
```bash
# Use script to inject token into config
./docs/gemini-cli/examples/sse-token-refresh.sh
```

---

### Production Deployment Checklist

- [ ] Service account created with minimal permissions
- [ ] IAM policy grants `roles/run.invoker` only
- [ ] Authentication required (no `--allow-unauthenticated`)
- [ ] Tokens rotated weekly or automated
- [ ] Config file not committed to version control
- [ ] Audit logging enabled for Cloud Run
- [ ] VPC connector configured (if internal-only access needed)

---

## Troubleshooting

### Service Issues

**Symptom**: Health check fails or service unreachable

**Diagnosis**:
```bash
# Check service status
gcloud run services describe hansard-mcp-server

# Check recent logs
gcloud run services logs read hansard-mcp-server --limit=50

# Verify service is deployed
gcloud run services list | grep hansard
```

**Solutions**:
1. Redeploy service:
   ```bash
   gcloud run deploy hansard-mcp-server \
     --image=gcr.io/PROJECT_ID/hansard-mcp:latest
   ```

2. Check Cloud Run quotas:
   ```bash
   gcloud compute project-info describe --project=PROJECT_ID
   ```

3. Verify database connectivity from Cloud Run

---

### Authentication Errors

**Symptom**: "401 Unauthorized" or "Permission denied"

**Diagnosis**:
```bash
# Test token validity
TOKEN=$(gcloud auth print-identity-token)
curl -H "Authorization: Bearer $TOKEN" \
  https://YOUR-SERVICE-URL.a.run.app/health

# Check IAM permissions
gcloud run services get-iam-policy hansard-mcp-server
```

**Solutions**:

**1. Token Expired**:
```bash
# Regenerate token
TOKEN=$(gcloud auth print-identity-token)
# Update config.json with new token
```

**2. Missing Permissions**:
```bash
# Grant Cloud Run Invoker role
gcloud run services add-iam-policy-binding hansard-mcp-server \
  --member="user:your-email@example.com" \
  --role="roles/run.invoker"
```

**3. Wrong Token Type**:
```bash
# Use identity token (not access token)
gcloud auth print-identity-token  # Correct
gcloud auth print-access-token    # Wrong for Cloud Run
```

---

### Connection Timeout

**Symptom**: "Connection timeout" or "Request timeout after 30s"

**Diagnosis**:
```bash
# Test endpoint manually with verbose output
curl -v -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://YOUR-SERVICE-URL.a.run.app/health

# Check network latency
ping YOUR-SERVICE-URL.a.run.app
```

**Solutions**:

**1. Increase Timeout**:
```json
{
  "mcpServers": {
    "hansard": {
      "timeout": 120
    }
  }
}
```

**2. Set Minimum Instances** (prevent cold starts):
```bash
gcloud run services update hansard-mcp-server --min-instances=1
```

**3. Check Firewall Rules**:
```bash
# Verify no corporate firewall blocking HTTPS
curl -I https://cloud.google.com
```

---

### SSE Connection Drops

**Symptom**: "Connection reset" or "Stream interrupted"

**Diagnosis**:
```bash
# Check Cloud Run logs for errors
gcloud run services logs read hansard-mcp-server --limit=100

# Monitor active connections
gcloud run services describe hansard-mcp-server \
  --format='json(status.traffic)'
```

**Solutions**:

**1. Increase Cloud Run Resources**:
```bash
gcloud run services update hansard-mcp-server \
  --memory=1Gi \
  --cpu=2
```

**2. Check Request Limits**:
```bash
# Cloud Run has 60-minute request limit for streaming
# Use connection pooling or reconnection logic
```

**3. Monitor Cloud Run Metrics**:
```bash
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_count"'
```

---

## Automation Script

Use the provided script to automate token generation and config updates:

**Script**: [/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/sse-token-refresh.sh](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/sse-token-refresh.sh)

**Usage**:
```bash
# Run token refresh script
bash /path/to/skai-fastmcp-cloudrun/docs/gemini-cli/examples/sse-token-refresh.sh

# Set up cron job for automated refresh (every 30 minutes)
crontab -e
# Add line:
# */30 * * * * bash /path/to/sse-token-refresh.sh
```

**Features**:
- Generates new identity token
- Updates Gemini CLI config.json
- Backs up previous config
- Restarts Gemini CLI

---

## Next Steps

### Option 1: Run Test Scenarios

Execute comprehensive tests to verify setup:

**Test Guide**: [test-scenarios.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/test-scenarios.md)

---

### Option 2: Set Up Token Automation

Automate token refresh to avoid manual updates:

```bash
# Copy automation script to local bin
cp docs/gemini-cli/examples/sse-token-refresh.sh ~/bin/hansard-token-refresh
chmod +x ~/bin/hansard-token-refresh

# Set up cron job
crontab -e
# Add: */30 * * * * ~/bin/hansard-token-refresh
```

---

### Option 3: Configure Team Access

Set up service accounts for team members:

```bash
# Create service account per team member
gcloud iam service-accounts create gemini-cli-user-alice

# Grant access
gcloud run services add-iam-policy-binding hansard-mcp-server \
  --member="serviceAccount:gemini-cli-user-alice@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

---

## Support

**Troubleshooting Guide**: [troubleshooting.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md)

**Test Scenarios**: [test-scenarios.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/test-scenarios.md)

**Configuration Examples**: [examples/](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/)

**Cloud Run Deployment**: [/home/user/skai-fastmcp-cloudrun/deployment/](/home/user/skai-fastmcp-cloudrun/deployment/)

---

**Last Updated**: 2025-10-23

**Feature**: 009-gemini-cli-integration

**User Story**: US2 - Remote Cloud Run Integration with SSE Transport
