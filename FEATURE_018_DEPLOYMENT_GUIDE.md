# Feature 018 Production Deployment Guide

**Feature**: 018-mcp-tools-quality-improvements  
**Live Site**: https://mcp.simonkennedymp.com.au  
**Deployment Target**: Google Cloud Run (us-central1)  
**Authentication**: GitHub OAuth2 (Required)  
**Status**: Ready for Production Deployment  

---

## Pre-Deployment Checklist

### 1. Verify Feature 018 Quality Improvements

```bash
# Ensure you're on the feature branch
git checkout 018-mcp-tools-quality-improvements

# Run comprehensive MCP tests
uv run python3 test_mcp_tools_direct.py

# Expected output:
# ✅ Search tool works with proper returns
# ✅ Fetch tool works with proper returns  
# ✅ No breaking changes to functionality
```

### 2. Verify OAuth Configuration in Google Cloud

```bash
# Check that OAuth secrets are stored in Secret Manager
gcloud secrets list | grep github-oauth

# Expected output should show:
# github-oauth-client-id
# github-oauth-client-secret

# If secrets don't exist, create them:
echo -n "YOUR_GITHUB_CLIENT_ID" | gcloud secrets create github-oauth-client-id --data-file=-
echo -n "YOUR_GITHUB_CLIENT_SECRET" | gcloud secrets create github-oauth-client-secret --data-file=-
```

### 3. Verify Current Deployment Status

```bash
# Check current Cloud Run service
gcloud run services describe hansard-mcp-server --region=us-central1

# Check environment variables
gcloud run services describe hansard-mcp-server \
  --region=us-central1 \
  --format='value(spec.template.spec.containers[0].env)'

# Current should show:
# DANGEROUSLY_OMIT_AUTH=true or no auth config
# After deployment should show:
# FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.github.GitHubProvider
# FASTMCP_SERVER_AUTH_GITHUB_BASE_URL=https://mcp.simonkennedymp.com.au
```

### 4. Test Locally with OAuth Disabled (Pre-deployment Testing)

```bash
# Start local MCP server with Feature 018 improvements
cd /home/user/skai-fastmcp-cloudrun
DANGEROUSLY_OMIT_AUTH=true uv run fastmcp dev src/server.py

# In another terminal, test the tools
uv run python3 test_mcp_tools_direct.py

# Expected improvements over baseline:
# Tool Annotations: PASS (✅ proper type annotations)
# Docstring Quality: PASS (✅ complete Returns documentation)
# Error Handling: IMPROVED (now validates actual errors)
# Performance: IMPROVED (accurate async measurement)
# Data Quality: IMPROVED (evaluates real response data)
```

---

## Step 1: Pre-Deployment Testing (30 minutes)

### Run MCP Tool Compliance Tests

```bash
# Start MCP server locally
cd /home/user/skai-fastmcp-cloudrun
DANGEROUSLY_OMIT_AUTH=true uv run fastmcp dev src/server.py &
MCP_PID=$!

# Wait for server to start
sleep 5

# Run comprehensive tests
cat > test_deployment_readiness.py << 'EOF'
#!/usr/bin/env python3
"""
Test MCP tools for production deployment readiness.
Validates Feature 018 quality improvements are working.
"""
import asyncio
import sys
sys.path.insert(0, '/home/user/skai-fastmcp-cloudrun/src')

from tools.search import search_hansard_speeches
from tools.fetch import fetch_hansard_speech

async def test_deployment_readiness():
    """Test that tools are ready for production"""
    print("🔍 Testing MCP Tools for Production Readiness")
    print("=" * 60)
    
    # Test 1: Search tool
    print("\n📌 Test 1: Search Tool")
    try:
        result = await search_hansard_speeches("climate policy", limit=3)
        assert isinstance(result, dict), "Search should return dict"
        assert "results" in result, "Response should have 'results'"
        assert "metadata" in result, "Response should have 'metadata'"
        print("   ✅ Search tool structure valid")
        print(f"   ✅ Found {len(result['results'])} results")
    except Exception as e:
        print(f"   ❌ Search tool failed: {e}")
        return False
    
    # Test 2: Fetch tool
    print("\n📌 Test 2: Fetch Tool")
    try:
        # Use a known speech ID from test results
        result = await fetch_hansard_speech("d9c697e9-e13d-4769-9fbe-ce6cb18f4700")
        assert isinstance(result, dict), "Fetch should return dict"
        assert "speech" in result, "Response should have 'speech'"
        assert result["speech"]["text"], "Speech should have content"
        print("   ✅ Fetch tool structure valid")
        print(f"   ✅ Retrieved speech ({len(result['speech']['text'])} chars)")
    except Exception as e:
        print(f"   ❌ Fetch tool failed: {e}")
        return False
    
    # Test 3: Docstring compliance
    print("\n📌 Test 3: Documentation Compliance")
    search_doc = search_hansard_speeches.__doc__ or ""
    fetch_doc = fetch_hansard_speech.__doc__ or ""
    
    checks = {
        "Search has Returns": "Returns:" in search_doc,
        "Fetch has Returns": "Returns:" in fetch_doc,
        "Search has Use this when": "Use this when" in search_doc,
        "Fetch has Use this when": "Use this when" in fetch_doc,
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
    
    if not all(checks.values()):
        print("   ⚠️  Documentation improvements needed")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All deployment readiness tests passed!")
    print("🚀 Ready for production deployment")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_deployment_readiness())
    sys.exit(0 if success else 1)
EOF

uv run python3 test_deployment_readiness.py

# Stop the local server
kill $MCP_PID
```

### Expected Output
```
🔍 Testing MCP Tools for Production Readiness
============================================================

📌 Test 1: Search Tool
   ✅ Search tool structure valid
   ✅ Found 3 results

📌 Test 2: Fetch Tool
   ✅ Fetch tool structure valid
   ✅ Retrieved speech (4727 chars)

📌 Test 3: Documentation Compliance
   ✅ Search has Returns
   ✅ Fetch has Returns
   ✅ Search has Use this when
   ✅ Fetch has Use this when

============================================================
✅ All deployment readiness tests passed!
🚀 Ready for production deployment
```

---

## Step 2: Prepare Deployment (15 minutes)

### Ensure OAuth Secrets are Available

```bash
# Verify GitHub OAuth credentials are stored
gcloud secrets list --filter="name:(github-oauth*)"

# If not found, add them:
# 1. Go to GitHub Settings → Developer Settings → OAuth Apps
# 2. Create new OAuth App with:
#    - Application name: Hansard MCP Server
#    - Homepage URL: https://mcp.simonkennedymp.com.au
#    - Authorization callback URL: https://mcp.simonkennedymp.com.au/auth/callback
# 3. Copy Client ID and Client Secret, then:

echo -n "YOUR_GITHUB_OAUTH_CLIENT_ID" | \
  gcloud secrets create github-oauth-client-id --data-file=-

echo -n "YOUR_GITHUB_OAUTH_CLIENT_SECRET" | \
  gcloud secrets create github-oauth-client-secret --data-file=-

# Grant Cloud Run service account access to secrets
gcloud secrets add-iam-policy-binding github-oauth-client-id \
  --member=serviceAccount:666924716777-compute@developer.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor

gcloud secrets add-iam-policy-binding github-oauth-client-secret \
  --member=serviceAccount:666924716777-compute@developer.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

### Verify Cloud Build Configuration

```bash
# Check that cloudbuild.yaml is updated
git diff HEAD cloudbuild.yaml

# Expected changes:
# - --no-allow-unauthenticated (instead of --allow-unauthenticated)
# - FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.github.GitHubProvider
# - FASTMCP_SERVER_AUTH_GITHUB_BASE_URL=https://mcp.simonkennedymp.com.au
# - Secret references for OAuth credentials
```

---

## Step 3: Deploy to Cloud Run (10 minutes)

### Option A: Deploy via Cloud Build (Recommended)

```bash
# Set project
gcloud config set project skai-fastmcp-cloudrun

# Submit build (automatically triggered by push)
git add -A
git commit -m "feat(018): Deploy MCP Tools Quality Improvements with OAuth

- Enhanced tool documentation with Returns sections
- Async-aware testing framework eliminates coroutine warnings
- OAuth2 authentication enabled and required
- Best practices compliance improved from 0.39 to 0.80+

Feature: 018-mcp-tools-quality-improvements
Closes: MCP Quality Improvements"

git push origin 018-mcp-tools-quality-improvements

# Cloud Build will automatically:
# 1. Build Docker image with Feature 018
# 2. Push to Google Container Registry
# 3. Deploy to Cloud Run with OAuth enabled
# 4. Replace current unauthenticated endpoint

# Monitor build status:
gcloud builds list --limit=5
gcloud builds log <BUILD_ID> --stream
```

### Option B: Deploy via gcloud CLI (Direct)

```bash
# Deploy directly without Cloud Build
gcloud run deploy hansard-mcp-server \
  --source . \
  --region=us-central1 \
  --platform=managed \
  --no-allow-unauthenticated \
  --set-env-vars=\
PYTHONPATH=/app/src,\
FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.github.GitHubProvider,\
FASTMCP_SERVER_AUTH_GITHUB_BASE_URL=https://mcp.simonkennedymp.com.au \
  --set-secrets=\
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=github-oauth-client-id:latest,\
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=github-oauth-client-secret:latest \
  --cpu=2 \
  --memory=2Gi \
  --max-instances=10 \
  --timeout=300 \
  --startup-cpu-boost \
  --vpc-connector=hansard-vpc-connector \
  --vpc-egress=private-ranges-only \
  --add-cloudsql-instances=skai-fastmcp-cloudrun:us-central1:hansard-db-v2 \
  --service-account=666924716777-compute@developer.gserviceaccount.com
```

### Monitor Deployment

```bash
# Watch deployment progress
gcloud run deploy hansard-mcp-server --region us-central1 --status

# Get service details
gcloud run services describe hansard-mcp-server --region=us-central1

# Expected output:
# Status: READY
# Traffic 100% to latest revision
# Authentication: REQUIRED
```

---

## Step 4: Post-Deployment Validation (20 minutes)

### Test OAuth is Enforced

```bash
# 1. Try accessing without authentication (should fail)
curl https://mcp.simonkennedymp.com.au/mcp

# Expected: 401 Unauthorized or OAuth redirect

# 2. Verify MCP tools are accessible
# Use Claude MCP CLI or MCP Inspector with GitHub OAuth token

# Get list of tools (requires authentication)
curl -H "Authorization: Bearer YOUR_GITHUB_TOKEN" \
  https://mcp.simonkennedymp.com.au/mcp/tools

# Expected response:
# {
#   "tools": [
#     {
#       "name": "search_hansard_speeches",
#       "description": "Search parliamentary speeches...",
#       "inputSchema": {...}
#     },
#     {
#       "name": "fetch_hansard_speech",
#       "description": "Retrieve full speech content...",
#       "inputSchema": {...}
#     }
#   ]
# }
```

### Test MCP Tool Functionality

```bash
# Test search tool through authenticated endpoint
curl -X POST \
  -H "Authorization: Bearer YOUR_GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"call_tool","params":{"name":"search_hansard_speeches","arguments":{"query":"climate policy","limit":3}}}' \
  https://mcp.simonkennedymp.com.au/mcp

# Expected: Search results with proper structure

# Test fetch tool
curl -X POST \
  -H "Authorization: Bearer YOUR_GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"call_tool","params":{"name":"fetch_hansard_speech","arguments":{"speech_id":"d9c697e9-e13d-4769-9fbe-ce6cb18f4700"}}}' \
  https://mcp.simonkennedymp.com.au/mcp

# Expected: Full speech content
```

### Check Cloud Run Logs

```bash
# View recent logs
gcloud run services logs read hansard-mcp-server \
  --region=us-central1 \
  --limit=50

# Expected log entries:
# ✅ Server initialized with ChatGPT Developer Mode enhancements
# ✅ GitHub OAuth authentication enabled
# ✅ search_hansard_speeches registered
# ✅ fetch_hansard_speech registered

# Check for errors
gcloud run services logs read hansard-mcp-server \
  --region=us-central1 \
  --limit=100 | grep -i "error\|warning"
```

---

## Rollback Plan (If Needed)

### Quick Rollback to Previous Deployment

```bash
# Get previous revisions
gcloud run revisions list --service=hansard-mcp-server --region=us-central1

# Rollback to previous stable version
gcloud run services update-traffic hansard-mcp-server \
  --region=us-central1 \
  --to-revisions=<PREVIOUS_REVISION_ID>=100

# Verify rollback
gcloud run services describe hansard-mcp-server --region=us-central1 | grep "URL:"
```

---

## Post-Deployment Checklist

- [ ] Deployment completed successfully (gcloud shows READY)
- [ ] OAuth authentication is enforced (no --allow-unauthenticated)
- [ ] GitHub OAuth secrets are configured and accessible
- [ ] MCP tools are accessible with valid GitHub OAuth token
- [ ] Search tool returns results with proper format
- [ ] Fetch tool retrieves full speech content
- [ ] Documentation improvements are visible in tool descriptions
- [ ] No errors in Cloud Run logs
- [ ] Live site is responding: https://mcp.simonkennedymp.com.au
- [ ] All tests passing on production deployment

---

## Maintenance & Monitoring

### Monitor Production Health

```bash
# Set up continuous monitoring
gcloud monitoring metrics-descriptors create \
  --display-name="MCP Tools - Search Queries" \
  --metric-kind=DELTA \
  --value-type=INT64 \
  custom.googleapis.com/mcp_search_queries

# View metrics in Cloud Console:
# https://console.cloud.google.com/monitoring

# Or via CLI:
gcloud monitoring time-series list \
  --filter='resource.type="cloud_run_revision"'
```

### Update Procedures

For future Feature updates:
1. Create feature branch (e.g., `019-mcp-new-feature`)
2. Make changes and test locally
3. Update this deployment guide if needed
4. Commit and push to trigger Cloud Build
5. Monitor deployment via `gcloud builds log`
6. Validate post-deployment via test suite

---

## Support & Troubleshooting

### Common Issues

**Issue**: OAuth token expired
```bash
# Refresh your GitHub OAuth token and try again
# Tokens expire after 8 hours by default
```

**Issue**: Secret not found
```bash
# Verify secrets exist and service account has access
gcloud secrets list
gcloud secrets get-iam-policy github-oauth-client-id
```

**Issue**: Cloud Run deployment fails
```bash
# Check Cloud Build logs
gcloud builds log <BUILD_ID> --stream

# Check service account permissions
gcloud projects get-iam-policy skai-fastmcp-cloudrun \
  --flatten="bindings[].members" \
  --filter="bindings.members:666924716777-compute@*"
```

---

**Deployment Date**: 2025-10-28  
**Feature**: 018-mcp-tools-quality-improvements  
**Status**: Ready for Production  
**Live URL**: https://mcp.simonkennedymp.com.au