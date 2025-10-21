# Quick Start: Testing GitHub OAuth Flow

This guide walks you through testing the GitHub OAuth authentication with MCP Inspector.

## Prerequisites

- Node.js installed
- GitHub account: `sc0sk` (authorized user)
- Access to: https://mcp.simonkennedymp.com.au

## Step 1: Install MCP Inspector

```bash
npm install -g @modelcontextprotocol/inspector
```

## Step 2: Start MCP Inspector

```bash
mcp-inspector
```

This will open a browser at http://localhost:5173

## Step 3: Configure Connection

In the MCP Inspector UI:

1. Click **"Add Server"**
2. **Server Name:** `Hansard RAG`
3. **Server URL:** `https://mcp.simonkennedymp.com.au/sse`
4. **Transport:** `SSE` (Server-Sent Events)
5. Click **"Connect"**

## Step 4: OAuth Authentication

When you click "Connect", you'll be redirected to:

```
https://github.com/login/oauth/authorize?
  client_id=...
  &redirect_uri=https://mcp.simonkennedymp.com.au/auth/callback
  &scope=user%20user:email
  &state=...
  &code_challenge=...
  &code_challenge_method=S256
```

**Actions:**
1. Click **"Authorize [Your App Name]"** on GitHub
2. You'll be redirected back to MCP Inspector
3. Connection should show as "Connected" with green indicator

## Step 5: Verify Authorization

Check Cloud Run logs for authorization decision:

```bash
gcloud run logs read hansard-mcp-server --region=us-central1 --limit=10
```

**Expected log output (authorized user):**
```
✅ Authorization granted for GitHub user: sc0sk
```

**Expected log output (unauthorized user):**
```
⚠️ Authorization denied for GitHub user: [username]
```

## Step 6: Test MCP Tools

Once connected, you should see available tools in MCP Inspector:

1. **search_speeches** - Search Australian Hansard speeches
2. **fetch_speech_by_id** - Retrieve a specific speech
3. **get_search_stats** - Get database statistics

**Test a search:**
```json
{
  "query": "climate change",
  "limit": 5
}
```

Expected response: List of relevant Hansard speeches

## Testing Unauthorized Access

To test the whitelist is working:

1. **Create a test GitHub account** (not `sc0sk`)
2. Follow Steps 1-4 above
3. Complete GitHub OAuth authorization
4. **Expected result:** 403 Forbidden error

**Error Response:**
```json
{
  "error": "Authorization denied",
  "detail": "User '[username]' is not authorized to access this server",
  "allowed_users": ["sc0sk"]
}
```

## Troubleshooting

### Error: "Failed to connect"
- Check service is running: `curl https://mcp.simonkennedymp.com.au/health`
- Verify OAuth callback URL in GitHub App matches: `https://mcp.simonkennedymp.com.au/auth/callback`

### Error: "Authentication failed"
- Check GitHub OAuth App credentials are correct
- Verify secrets in Google Secret Manager: `gcloud secrets list`
- Check Cloud Run logs: `gcloud run logs read hansard-mcp-server --region=us-central1`

### Error: "403 Forbidden" (authorized user)
- Verify your GitHub username is `sc0sk`
- Check whitelist secret: `gcloud secrets versions access latest --secret=github-allowed-usernames`
- Confirm secret value is `sc0sk` (case-sensitive)

### Connection drops/timeout
- Check Cloud Run min-instances: Should be 0 (cold start may take 5-10 seconds)
- Verify VPC connector: `gcloud compute networks vpc-access connectors describe hansard-vpc-connector --region=us-central1`
- Check Redis connection: `curl https://mcp.simonkennedymp.com.au/ready | jq .checks.redis`

## Adding More Authorized Users

To add users to the whitelist:

```bash
# Current: sc0sk
# Add another user (comma-separated)
echo -n "sc0sk,anotheruser" | gcloud secrets versions add github-allowed-usernames --data-file=-

# Redeploy to pick up new secret version
gcloud run services update hansard-mcp-server \
  --region=us-central1 \
  --update-secrets="GITHUB_ALLOWED_USERNAMES=github-allowed-usernames:latest"
```

## Claude Desktop Integration

To use with Claude Desktop, add to your config:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "hansard-rag": {
      "url": "https://mcp.simonkennedymp.com.au/sse",
      "transport": "sse"
    }
  }
}
```

**Note:** Claude Desktop will handle OAuth flow in a browser window.

## Monitoring OAuth Activity

View recent OAuth events:

```bash
# Authorization decisions
gcloud run logs read hansard-mcp-server --region=us-central1 \
  | grep "Authorization"

# OAuth errors
gcloud run logs read hansard-mcp-server --region=us-central1 \
  | grep -i "oauth\|auth"

# Recent connections
gcloud run logs read hansard-mcp-server --region=us-central1 \
  | grep "GitHub OAuth authentication"
```

## Security Notes

✅ **What's Protected:**
- All MCP tool calls require OAuth authentication
- Username whitelist enforced on every request
- GitHub tokens encrypted in Redis
- JWT tokens signed with RSA-256

❌ **What's NOT Protected (by design):**
- Health endpoints: `/health` and `/ready` (for monitoring)
- OAuth callback: `/auth/callback` (required for OAuth flow)

## Production URLs

- **Service:** https://mcp.simonkennedymp.com.au
- **Health:** https://mcp.simonkennedymp.com.au/health
- **Readiness:** https://mcp.simonkennedymp.com.au/ready
- **MCP SSE:** https://mcp.simonkennedymp.com.au/sse
- **OAuth Callback:** https://mcp.simonkennedymp.com.au/auth/callback

## Support

If you encounter issues:

1. Check service health: `curl https://mcp.simonkennedymp.com.au/health`
2. Review Cloud Run logs: `gcloud run logs tail hansard-mcp-server --region=us-central1`
3. Verify GitHub OAuth App settings at: https://github.com/settings/developers
4. Check infrastructure status: `gcloud run services describe hansard-mcp-server --region=us-central1`

---

**Status:** ✅ Production Ready
**Authorized Users:** sc0sk
**Last Updated:** October 22, 2025
