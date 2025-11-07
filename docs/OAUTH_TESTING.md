# OAuth Authentication Testing Guide

Complete guide for testing the Hansard MCP Server OAuth authentication flow.

## Overview

The Hansard MCP Server at `https://mcp.simonkennedymp.com.au` uses GitHub OAuth for authentication. This guide covers automated testing of the OAuth flow and MCP endpoints.

## Prerequisites

- Python 3.11+
- Playwright (for browser automation)
- httpx (for HTTP requests)
- GitHub CLI (`gh`) authenticated

## Quick Start

### 1. Run OAuth Flow Automation

The automated OAuth flow script handles the complete authentication process:

```bash
python3 test_oauth_simple.py
```

**What it does:**
1. Generates PKCE challenge/verifier
2. Opens browser to OAuth consent page
3. Clicks "Allow Access" button
4. Handles GitHub login (requires manual login)
5. Captures authorization code
6. Exchanges code for access token
7. Saves token to `/tmp/mcp_oauth_token.json`

**Expected output:**
```
✅ Code Verifier: pGtSk2WOOG1kgqKqg8HyfQrAiLbuC07Hm_9sUKI8IIM
✅ Code Challenge: vr2hLH02ZW-UCAEDemeaPEsA4EuClpGb4BnX1DngNGM

🔗 Authorization URL:
https://mcp.simonkennedymp.com.au/authorize?...

📡 Navigating to authorization endpoint...
✅ Page loaded
✅ On consent page
✅ Found 'Allow Access' button
🖱️  Clicked 'Allow Access'

[Manual GitHub login required if not already logged in]

✅ Got authorization code: ozzqgaH4NHYCSk_QjNlJA__eOC3DAWa8FiAz6I_LRY4
✅ Got access token!

💾 Token saved to: /tmp/mcp_oauth_token.json
```

### 2. Test MCP Endpoint with Token

Once you have a token, test the MCP endpoint:

```bash
python3 test_mcp_jsonrpc.py
```

**What it does:**
1. Loads token from `/tmp/mcp_oauth_token.json`
2. Initializes MCP session
3. Lists available tools
4. Tests search tool with sample query
5. Tests fetch tool (if results available)

**Expected output:**
```
🚀 Testing MCP endpoint with OAuth token

1️⃣  INITIALIZE MCP SESSION
✅ Parsed SSE data:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "serverInfo": {
      "name": "Hansard MCP Server",
      "version": "2.13.0.2"
    }
  }
}

✅ MCP session initialized!

============================================================
✅ ALL TESTS COMPLETE!
============================================================

📊 Summary:
  ✅ OAuth authentication: WORKING
  ✅ MCP session initialization: WORKING
  ✅ Tool listing: WORKING
  ✅ Search tool: WORKING
```

## OAuth Flow Details

### Client Registration

The server supports dynamic client registration:

```bash
curl -X POST https://mcp.simonkennedymp.com.au/register \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "test-client",
    "redirect_uris": ["http://localhost:8080/callback"]
  }'
```

Response includes:
- `client_id` - OAuth client identifier
- `client_secret` - Client secret for token exchange
- `redirect_uris` - Registered callback URLs

### Authorization Flow

1. **Authorization URL** (with PKCE):
   ```
   https://mcp.simonkennedymp.com.au/authorize
     ?response_type=code
     &client_id={CLIENT_ID}
     &redirect_uri={REDIRECT_URI}
     &scope=user
     &code_challenge={CODE_CHALLENGE}
     &code_challenge_method=S256
     &state={STATE}
   ```

2. **Consent Page**:
   - User sees: "test-client wants to access the MCP server Hansard MCP Server"
   - Button: "Allow Access"
   - Redirects to GitHub OAuth for authentication

3. **GitHub Authentication**:
   - User logs in to GitHub (if not already logged in)
   - Approves the GitHub OAuth app
   - Redirects back to consent page

4. **Authorization Code**:
   - Redirects to: `http://localhost:8080/callback?code={CODE}&state={STATE}`
   - Code is single-use and expires after 10 minutes

5. **Token Exchange**:
   ```bash
   curl -X POST https://mcp.simonkennedymp.com.au/token \
     -d "grant_type=authorization_code" \
     -d "code={CODE}" \
     -d "redirect_uri={REDIRECT_URI}" \
     -d "client_id={CLIENT_ID}" \
     -d "client_secret={CLIENT_SECRET}" \
     -d "code_verifier={CODE_VERIFIER}"
   ```

6. **Access Token Response**:
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "token_type": "Bearer",
     "expires_in": 3600,
     "scope": "user"
   }
   ```

## MCP Protocol

### Transport: HTTP + SSE

The server uses Server-Sent Events (SSE) over HTTP for MCP communication:

**Required Headers:**
```
Authorization: Bearer {ACCESS_TOKEN}
Content-Type: application/json
Accept: application/json, text/event-stream
```

### Response Format

Responses are in SSE format:

```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{...}}
```

Parse by:
1. Split response by newlines
2. Find lines starting with `data: `
3. Remove `data: ` prefix
4. Parse remaining text as JSON

### Example MCP Requests

**Initialize Session:**
```json
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "test-client",
      "version": "1.0.0"
    }
  },
  "id": 1
}
```

**List Tools:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "params": {},
  "id": 2
}
```

**Call Tool:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "search_hansard_speeches",
    "arguments": {
      "query": "climate change",
      "limit": 5
    }
  },
  "id": 3
}
```

## Claude Code CLI Integration

### Server Configuration

The server is registered as `mcp-prod` in Claude Code CLI:

```bash
# Check server status
claude mcp list

# Expected output:
# mcp-prod: https://mcp.simonkennedymp.com.au/mcp (HTTP) - ⚠ Needs authentication
```

### Triggering OAuth Flow

Claude Code CLI will automatically trigger the OAuth flow when you first use the server:

1. Start a conversation
2. Use any Hansard tool (e.g., "Search Hansard for speeches about climate change")
3. Claude CLI opens browser automatically
4. Complete GitHub login
5. Click "Allow Access"
6. Claude CLI captures token and stores it
7. Server becomes available

After authentication, status changes to:
```
mcp-prod: https://mcp.simonkennedymp.com.au/mcp (HTTP) - ✓ Connected
```

## Available Tools

The MCP server provides these tools:

### 1. search_hansard_speeches
Search Australian parliamentary speeches by keywords, speaker, date, or chamber.

**Parameters:**
- `query` (required): Search keywords
- `limit` (optional): Number of results (default: 10)
- `speaker_name` (optional): Filter by speaker
- `party` (optional): Filter by political party
- `chamber` (optional): "house" or "senate"
- `date_from` (optional): ISO 8601 date (e.g., "2024-01-01")
- `date_to` (optional): ISO 8601 date

**Example:**
```json
{
  "name": "search_hansard_speeches",
  "arguments": {
    "query": "climate change",
    "limit": 5,
    "chamber": "house",
    "date_from": "2024-01-01"
  }
}
```

### 2. fetch_hansard_speech
Retrieve full speech text and metadata by ID.

**Parameters:**
- `speech_id` (required): Speech identifier from search results

**Example:**
```json
{
  "name": "fetch_hansard_speech",
  "arguments": {
    "speech_id": "54321-2024-03-15"
  }
}
```

### 3. ingest_hansard_speech
Add new speeches to the database (development only).

**Parameters:**
- `speech_id` (required): Unique identifier
- `date` (required): ISO 8601 date
- `speaker_name` (required): Speaker's name
- `party` (required): Political party
- `chamber` (required): "house" or "senate"
- `text` (required): Speech content

## Troubleshooting

### Issue: "Needs authentication"

**Cause:** OAuth token not yet obtained or expired

**Fix:**
1. Use server in a Claude conversation to trigger OAuth
2. Or run `python3 test_oauth_simple.py` to get token manually

### Issue: "Missing session ID"

**Cause:** Subsequent requests not maintaining session state

**Fix:**
- MCP protocol requires session management
- Claude Code CLI handles this automatically
- For manual testing, extract session ID from initialize response

### Issue: "invalid_token"

**Cause:** Token expired (1 hour TTL) or invalid

**Fix:**
1. Re-run OAuth flow to get fresh token
2. Check token hasn't been revoked
3. Verify token format (should be JWT)

### Issue: GitHub login required

**Cause:** No active GitHub session in browser

**Fix:**
1. Log in to GitHub when prompted
2. Authorize the GitHub OAuth app
3. Token will be captured automatically

## Files

- `test_oauth_simple.py` - Automated OAuth flow with Playwright
- `test_mcp_jsonrpc.py` - MCP endpoint testing with token
- `/tmp/mcp_oauth_token.json` - Cached OAuth token
- `/tmp/oauth_page1.png` - Screenshot of consent page
- `/tmp/oauth_page2.png` - Screenshot after clicking "Allow Access"

## OAuth Server Metadata

The server exposes standard OAuth metadata endpoints:

```bash
# OAuth authorization server metadata
curl https://mcp.simonkennedymp.com.au/.well-known/oauth-authorization-server

# OAuth protected resource metadata
curl https://mcp.simonkennedymp.com.au/.well-known/oauth-protected-resource/mcp
```

## Security Notes

1. **PKCE Required**: All authorization requests must use PKCE (Proof Key for Code Exchange)
2. **Token Expiry**: Access tokens expire after 1 hour (3600 seconds)
3. **GitHub OAuth**: Uses GitHub as identity provider (feature 010-token-verification)
4. **HTTPS Only**: All endpoints require HTTPS
5. **No Password Storage**: All authentication via OAuth, no passwords stored

## Related Documentation

- [Feature Spec: 010-token-verification](../specs/010-token-verification/spec.md)
- [CLAUDE.md](../CLAUDE.md) - OAuth server configuration
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
- [FastMCP GitHub OAuth](https://docs.fastmcp.com/servers/auth/github)

## Success Criteria

✅ **OAuth flow complete** when:
1. `test_oauth_simple.py` completes without errors
2. Token saved to `/tmp/mcp_oauth_token.json`
3. Token is valid JWT with 1 hour expiry

✅ **MCP endpoint working** when:
1. `test_mcp_jsonrpc.py` shows "MCP session initialized!"
2. Tools list returns 3+ tools
3. Search tool returns results

✅ **Claude Code CLI integration working** when:
1. `claude mcp list` shows `mcp-prod` as "✓ Connected"
2. Can search Hansard in Claude conversations
3. Results include speaker names and dates
