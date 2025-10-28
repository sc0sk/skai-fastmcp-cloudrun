# Production Deployment Instructions for Feature 018

## Current Status
- **Branch**: `018-mcp-tools-quality-improvements` (active)
- **Changes**: 20+ modified files, 49 untracked (specs + deployment docs)
- **Status**: Ready for production deployment
- **Target**: mcp.simonkennedymp.com.au with GitHub OAuth required

---

## Quick Start: Deploy in 3 Steps

### Step 1: Verify Prerequisites ✅

```bash
cd /home/user/skai-fastmcp-cloudrun

# Verify gcloud is configured
gcloud config get-value project
# Expected output: skai-fastmcp-cloudrun

# Verify OAuth secrets exist in Secret Manager
gcloud secrets list | grep github-oauth

# If secrets are missing, create them now:
# gcloud secrets create github-oauth-client-id --data-file=-
# gcloud secrets create github-oauth-client-secret --data-file=-
```

### Step 2: Dry-Run Deployment 🧪

```bash
# Make deployment script executable
chmod +x deploy_feature_018.sh

# Execute dry-run (NO CHANGES TO PRODUCTION)
./deploy_feature_018.sh --dry-run

# Review the output to verify:
# ✅ Feature branch is correct
# ✅ OAuth secrets found
# ✅ Deployment parameters look right
# ✅ Service URL is mcp.simonkennedymp.com.au
```

### Step 3: Deploy to Production 🚀

```bash
# Execute actual deployment
./deploy_feature_018.sh --deploy

# Script will:
# 1. Verify feature branch
# 2. Check OAuth secrets in Secret Manager
# 3. Build Docker image
# 4. Push to Container Registry
# 5. Deploy to Cloud Run with OAuth enabled
# 6. Output new service URL

# Wait for deployment to complete (~3-5 minutes)
```

---

## Manual Deployment (If Script Not Available)

```bash
# Set environment variables
export PROJECT_ID="skai-fastmcp-cloudrun"
export REGION="us-central1"
export SERVICE_NAME="hansard-mcp-server"
export IMAGE_URL="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Build Docker image
docker build -t ${IMAGE_URL}:latest .

# Push to Container Registry
docker push ${IMAGE_URL}:latest

# Deploy to Cloud Run with OAuth
gcloud run deploy ${SERVICE_NAME} \
  --region=${REGION} \
  --image=${IMAGE_URL}:latest \
  --platform=managed \
  --no-allow-unauthenticated \
  --set-env-vars="FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.github.GitHubProvider,FASTMCP_SERVER_AUTH_GITHUB_BASE_URL=https://mcp.simonkennedymp.com.au" \
  --set-secrets="FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=github-oauth-client-id:latest,FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=github-oauth-client-secret:latest" \
  --vpc-connector=hansard-vpc-connector \
  --ingress=all
```

---

## Post-Deployment Validation ✅

### 1. Test Authentication (Must Fail for Public Access)

```bash
# Unauthenticated request should get 401
curl -i https://mcp.simonkennedymp.com.au/mcp
# Expected: 401 Unauthorized or OAuth redirect
```

### 2. Check Cloud Run Status

```bash
# Verify service is READY
gcloud run services describe hansard-mcp-server --region=us-central1

# Expected output should show:
# Status: Ready
# Revisions:  100% --> NEW_REVISION_ID (latest)
```

### 3. Monitor Initial Logs

```bash
# Watch logs in real-time
gcloud run services logs read hansard-mcp-server \
  --region=us-central1 \
  --limit=50 \
  --follow

# Expected:
# ✅ "Server initialized with ChatGPT Developer Mode enhancements"
# ✅ "GitHub OAuth authentication enabled"
# ✅ "search_hansard_speeches registered"
# ✅ "fetch_hansard_speech registered"
```

### 4. Verify OAuth is Working

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe hansard-mcp-server --region=us-central1 --format='value(status.url)')

# Try to access (should redirect to GitHub OAuth or show 401)
curl -i "$SERVICE_URL/mcp"

# Visit in browser: $SERVICE_URL
# Should prompt for GitHub OAuth login
```

---

## Rollback if Needed 🔄

```bash
# Get list of recent revisions
gcloud run revisions list \
  --service=hansard-mcp-server \
  --region=us-central1 \
  --limit=5

# Find the previous working revision (before this deployment)
# Then redirect traffic back:
gcloud run services update-traffic hansard-mcp-server \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION_ID=100

# Verify rollback
curl https://mcp.simonkennedymp.com.au/mcp
```

---

## What Changed in This Deployment

### Configuration Changes
- ✅ Authentication enforcement: `--no-allow-unauthenticated`
- ✅ OAuth provider configured: `GitHubProvider`
- ✅ Base URL set: `https://mcp.simonkennedymp.com.au`
- ✅ Secrets mounted for OAuth credentials

### Code Changes
- ✅ MCP tools updated with Returns documentation (planned in Feature 018)
- ✅ Async testing framework designed (implementation in progress)
- ✅ Best practices compliance targeted at 0.80/1.00 (from 0.39/1.00)

### Documentation Updates
- ✅ README.md: Added Feature 018 reference and live site URL
- ✅ FEATURE_018_DEPLOYMENT_GUIDE.md: Comprehensive deployment guide
- ✅ FEATURE_018_DEPLOYMENT_CHECKLIST.md: Pre/post deployment checklist
- ✅ specs/018-mcp-tools-quality-improvements/: Complete feature specification
- ✅ .github/copilot-instructions.md: Updated with Feature 018 info

---

## Key Information

### Service Details
- **Service Name**: hansard-mcp-server
- **Region**: us-central1
- **Public URL**: https://mcp.simonkennedymp.com.au
- **Authentication**: GitHub OAuth (required)
- **Database**: Cloud SQL PostgreSQL (hansard-db-v2)

### OAuth Configuration
- **Provider**: GitHub OAuth2
- **Base URL**: https://mcp.simonkennedymp.com.au
- **Secrets Required**:
  - github-oauth-client-id
  - github-oauth-client-secret
- **Environment Variable**: FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.github.GitHubProvider

### MCP Tools
- **search_hansard_speeches**: Search political speeches by keywords
- **fetch_hansard_speech**: Retrieve full text of specific speech
- **ingest_hansard_speech**: Import new speech data

---

## Monitoring & Support

### Cloud Run Console
https://console.cloud.google.com/run/detail/us-central1/hansard-mcp-server

### Cloud Run Logs
```bash
gcloud run services logs read hansard-mcp-server --region=us-central1 --limit=100
```

### Secret Manager
```bash
# List OAuth secrets
gcloud secrets list | grep github-oauth

# Rotate secrets if needed
gcloud secrets versions add github-oauth-client-id --data-file=-
```

---

## Next Steps After Successful Deployment

1. **Implement Feature 018 Improvements** (3 phases):
   - Phase 1 (2h): Documentation enhancements - add Returns sections
   - Phase 2 (2-3h): Async testing framework - proper tool validation
   - Phase 3 (1-2h): Compliance dashboard - automated scoring

2. **Communicate Deployment**:
   - Update team on new authentication requirement
   - Share Feature 018 implementation roadmap
   - Document OAuth GitHub App setup for users

3. **Monitor Production**:
   - Watch logs for 24 hours
   - Check performance metrics
   - Monitor error rates

---

**Ready to Deploy? Execute: `./deploy_feature_018.sh --deploy`**
