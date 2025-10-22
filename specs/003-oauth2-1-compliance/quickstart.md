# Quickstart: OAuth 2.1 Compliance

**Feature**: OAuth 2.1 Compliance
**Date**: 2025-10-22

## Overview

This quickstart guide helps developers test and verify OAuth 2.1 compliance locally and in production.

## Prerequisites

- Python 3.11+
- FastMCP 2.12.5+ installed (`uv pip install fastmcp>=2.12.5`)
- GitHub OAuth App configured (see main project README)
- MCP Inspector for testing (`npx @modelcontextprotocol/inspector`)

## Local Development Setup

### 1. Verify Middleware Implementation

Check that `src/server.py` includes the `OAuthResourceParameterMiddleware` class:

```bash
grep -A 10 "class OAuthResourceParameterMiddleware" src/server.py
```

Expected output:
```python
class OAuthResourceParameterMiddleware(BaseHTTPMiddleware):
    """Middleware to strip RFC 8707 'resource' parameter from OAuth authorize requests."""

    async def dispatch(self, request, call_next):
        if request.url.path == "/authorize" and "resource" in request.query_params:
            # Remove 'resource' parameter...
```

### 2. Start Server Locally

**With Authentication (production mode)**:
```bash
# Set OAuth environment variables
export FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.github.GitHubProvider
export FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=your_client_id
export FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=your_client_secret
export FASTMCP_SERVER_AUTH_GITHUB_BASE_URL=http://localhost:8000

# Start server
PORT=8000 fastmcp dev src/server.py
```

**Without Authentication (local testing)**:
```bash
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py
```

### 3. Launch MCP Inspector

Open a second terminal:

```bash
npx @modelcontextprotocol/inspector
```

Open the URL shown in output (typically `http://localhost:6274`).

### 4. Connect Inspector to Server

In the MCP Inspector UI:
1. Enter server URL: `http://localhost:8000/mcp`
2. Select transport: `HTTP (Streamable)`
3. Click "Connect"

**Expected Behavior**:
- If auth enabled: Browser opens for GitHub OAuth login
- Authorization completes without errors
- Inspector shows available tools (search, fetch)

## Testing OAuth 2.1 Compatibility

### Test 1: Simulate ChatGPT Request

Use `curl` to simulate an OAuth 2.1 request with `resource` parameter:

```bash
curl -v "http://localhost:8000/authorize?response_type=code&client_id=test-client&redirect_uri=http://localhost/callback&state=test-state&code_challenge=test-challenge&code_challenge_method=S256&resource=http://localhost:8000/mcp"
```

**Expected Response**:
- HTTP 401 or redirect to GitHub (depending on session)
- **NOT** HTTP 400 Bad Request

**Verify in logs**:
```
✅ OAuth resource parameter middleware enabled (RFC 8707 compatibility)
```

### Test 2: Verify Backward Compatibility

Test standard OAuth 2.0 request (without `resource` parameter):

```bash
curl -v "http://localhost:8000/authorize?response_type=code&client_id=test-client&redirect_uri=http://localhost/callback&state=test-state&code_challenge=test-challenge&code_challenge_method=S256"
```

**Expected Response**:
- Same behavior as Test 1 (no regression)
- Middleware passes request through unmodified

### Test 3: Run Unit Tests

```bash
pytest tests/unit/test_oauth_middleware.py -v
```

**Expected Tests**:
- `test_strip_resource_parameter` - PASS
- `test_preserve_non_authorize_paths` - PASS
- `test_handle_missing_resource` - PASS
- `test_preserve_other_parameters` - PASS

### Test 4: Run Integration Tests

```bash
pytest tests/integration/test_oauth_flows.py -v
```

**Expected Tests**:
- `test_oauth21_flow` - PASS
- `test_oauth20_backward_compatibility` - PASS
- `test_middleware_performance` - PASS

## Production Deployment

### 1. Build Docker Image

```bash
gcloud builds submit --config=cloudbuild.yaml --project=skai-fastmcp-cloudrun
```

### 2. Deploy to Cloud Run

```bash
gcloud run deploy hansard-mcp-server \
  --image gcr.io/skai-fastmcp-cloudrun/hansard-mcp:latest \
  --region us-central1 \
  --project=skai-fastmcp-cloudrun
```

### 3. Verify Deployment

Check Cloud Run logs for middleware initialization:

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=hansard-mcp-server" \
  --limit=10 \
  --format=json \
  | jq -r '.[] | select(.textPayload | contains("OAuth resource parameter middleware")) | .textPayload'
```

**Expected Output**:
```
✅ OAuth resource parameter middleware enabled (RFC 8707 compatibility)
```

### 4. Test ChatGPT Integration

1. Open ChatGPT (Plus/Team/Enterprise account required)
2. Navigate to GPT Editor → Configure
3. Add Action:
   - Authentication: OAuth
   - Client ID: (from GitHub OAuth App)
   - Authorization URL: `https://your-server.run.app/authorize`
   - Token URL: `https://your-server.run.app/token`
4. Save and Test

**Expected Behavior**:
- Authorization flow completes successfully
- ChatGPT can invoke MCP tools (search, fetch)
- No 400 Bad Request errors in Cloud Run logs

## Troubleshooting

### Issue: 400 Bad Request on /authorize

**Symptoms**: Authorization requests fail with HTTP 400

**Diagnosis**:
```bash
# Check if middleware is loaded
gcloud logging read "resource.type=cloud_run_revision AND textPayload=~'OAuth resource parameter middleware'" --limit=1
```

**Solution**: Verify middleware is added before OAuth provider initialization in `src/server.py`

### Issue: Middleware Not Stripping Parameter

**Symptoms**: Still seeing 400 errors with `resource` parameter

**Diagnosis**:
- Check middleware order: `OAuthResourceParameterMiddleware` must be added FIRST
- Verify path matching: Should target `/authorize` endpoint specifically

**Solution**: Review middleware `dispatch()` method and path condition

### Issue: OAuth 2.0 Clients Broken

**Symptoms**: Standard OAuth clients fail after adding middleware

**Diagnosis**:
```bash
pytest tests/integration/test_oauth_flows.py::test_oauth20_backward_compatibility -v
```

**Solution**: Middleware should only modify requests with `resource` parameter; check conditional logic

## Performance Monitoring

### Check Middleware Latency

Monitor Cloud Run request latency before/after deployment:

```bash
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_latencies" AND resource.labels.service_name="hansard-mcp-server"' \
  --format=json
```

**Expected**: <10ms increase in authorization request latency

### Load Testing (Optional)

Use Apache Bench to stress-test authorization endpoint:

```bash
ab -n 100 -c 10 "http://localhost:8000/authorize?client_id=test&resource=http://example.com"
```

**Expected**: Consistent latency, no errors

## Rollback Procedure

If issues arise in production:

1. **Deploy Previous Revision**:
   ```bash
   gcloud run services update-traffic hansard-mcp-server \
     --to-revisions=hansard-mcp-server-00051-lv7=100 \
     --region=us-central1
   ```

2. **Verify Rollback**:
   ```bash
   gcloud run revisions list --service=hansard-mcp-server --region=us-central1
   ```

3. **Check Traffic Distribution**:
   - Should show 100% traffic to previous revision
   - New revision remains available for testing

## Next Steps

- Monitor Cloud Run logs for OAuth 2.1 requests
- Track authorization success rate metrics
- Update CLAUDE.md with OAuth 2.1 support documentation
- Consider contributing middleware upstream to FastMCP (optional)

## References

- [FastMCP GitHub OAuth Docs](https://gofastmcp.com/servers/auth/github)
- [OAuth 2.1 Specification](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-11)
- [RFC 8707: Resource Indicators](https://datatracker.ietf.org/doc/html/rfc8707)
- [Starlette Middleware Guide](https://www.starlette.io/middleware/)
