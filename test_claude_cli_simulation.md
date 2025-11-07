# Claude Code CLI Testing - Hansard Search Simulation

## Test Setup

**Query**: "Search Hansard for speeches about climate change"

**MCP Server Status**:
- Server: `mcp-prod` → `https://mcp.simonkennedymp.com.au/mcp`
- Configuration: ✅ Present in `~/.claude/.credentials.json`
- Client ID: `c10a614a-f8f6-4d07-9292-63b5ac0ae40d`
- Access Token: ❌ Empty (needs OAuth flow)
- Status: ⚠️ Needs authentication

## Test Results

### Attempt 1: Direct Query
```bash
echo "Search Hansard for speeches about climate change" | claude -p --output-format json
```

**Result**: ❌ **FAILED - Did not use MCP server**

**Actual Behavior**:
- Claude attempted to run local Python commands instead
- Tried to import from `src.server` and `src.tools.search`
- Commands were denied by permission system
- Did not attempt to connect to `mcp-prod` server

**Response**:
> "I need approval to run Python commands that search the database. The Hansard MCP server provides a `search_hansard_speeches` tool that can search for speeches about climate change..."

**Issues**:
1. ❌ Claude did not automatically detect/use the available MCP server
2. ❌ Claude chose local Python execution over MCP tool calls
3. ❌ No OAuth flow was triggered
4. ⚠️ Claude knew about the tool but didn't use it

**Score**: **2/10**
- +1: Identified the correct tool name (`search_hansard_speeches`)
- +1: Understood the query intent
- -8: Completely failed to use the MCP server

### Attempt 2: Explicit MCP Reference
```bash
claude -p "Use the mcp-prod server to search Hansard for speeches about climate change"
```

**Result**: ❌ **FAILED - MCP server not accessible**

**Actual Behavior**:
- Claude reported not having access to mcp-prod tools
- Only saw LangChain documentation MCP server
- Did not attempt OAuth connection

**Response**:
> "I don't have access to the mcp-prod server's tools. The available MCP tool I see is for LangChain documentation, not Hansard speeches."

**Issues**:
1. ❌ MCP server not loaded in Claude's context
2. ❌ OAuth flow not triggered even with explicit reference
3. ❌ Server exists in config but not available to Claude

**Score**: **1/10**
- +1: Correctly identified the issue (no access to server)
- -9: Did not trigger OAuth or attempt connection

## Root Cause Analysis

### Why MCP Server Not Available

1. **OAuth Token Missing**:
   ```json
   "accessToken": "",
   "expiresAt": 0
   ```
   The server requires OAuth but no token is present.

2. **OAuth Flow Not Triggered**:
   - `--print` mode may bypass OAuth flows
   - Interactive mode likely needed to open browser
   - No fallback mechanism for non-interactive auth

3. **Server Discovery Issue**:
   - Server configured in `.credentials.json`
   - But not appearing in available tools
   - May need server restart or explicit activation

### Expected Behavior (Correct Flow)

1. **User asks**: "Search Hansard for speeches about climate change"
2. **Claude detects**: `mcp-prod` server has `search_hansard_speeches` tool
3. **Claude triggers**: OAuth flow if token missing/expired
4. **Browser opens**: User authenticates with GitHub
5. **Token cached**: Access token saved to `.credentials.json`
6. **Tool called**: Claude calls `search_hansard_speeches` with query
7. **Results returned**: Speeches displayed to user

## Manual OAuth Flow Test

### Running OAuth Flow Manually

Since `--print` mode doesn't trigger OAuth, testing with interactive mode:

```bash
# Start interactive session
claude

# Then type:
# "Search Hansard for speeches about climate change using the mcp-prod MCP server"
```

**Expected**:
1. Browser window opens to consent page
2. User clicks "Allow Access"
3. GitHub login (if needed)
4. Token saved to `.credentials.json`
5. Search executes
6. Results displayed

### Using Pre-Generated OAuth Token

Our automated OAuth test already generated a valid token:

```bash
# Token saved at:
cat /tmp/mcp_oauth_token.json

# Contains:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "user"
}
```

**Could manually inject** this token into `.credentials.json`:
```json
"mcpOAuth": {
  "mcp-prod|1e54082a72130e2a": {
    "serverName": "mcp-prod",
    "serverUrl": "https://mcp.simonkennedymp.com.au/mcp",
    "clientId": "c10a614a-f8f6-4d07-9292-63b5ac0ae40d",
    "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expiresAt": 1762480642000
  }
}
```

## Comparison: Expected vs Actual

### Expected Response (with working MCP)

```
I'll search Hansard for speeches about climate change using the search tool.

[Calls: search_hansard_speeches(query="climate change", limit=5)]

Found 5 speeches about climate change:

1. **Anthony Albanese** (Labor, House of Representatives)
   Date: 2024-03-15
   "...we must take decisive action on climate change..."
   Relevance: 0.89

2. **Adam Bandt** (Greens, House of Representatives)
   Date: 2024-03-10
   "...climate change is the greatest threat..."
   Relevance: 0.85

3. **Peter Dutton** (Liberal, House of Representatives)
   Date: 2024-02-20
   "...our climate change policies balance..."
   Relevance: 0.82

[etc.]

Would you like to see the full text of any of these speeches?
```

**Score**: **10/10**
- ✅ Uses MCP server
- ✅ Calls correct tool
- ✅ Returns actual data
- ✅ Formats nicely
- ✅ Offers follow-up

### Actual Response (without MCP)

```
I need approval to run Python commands that search the database...
Would you like me to proceed with the search?
```

**Score**: **2/10**
- ❌ No MCP usage
- ❌ No data returned
- ❌ Asks permission for wrong approach
- ⚠️ Understands intent but wrong execution

## Scoring Summary

| Criterion | Expected | Actual | Score | Weight |
|-----------|----------|--------|-------|--------|
| **Tool Discovery** | Finds `search_hansard_speeches` in mcp-prod | Didn't check MCP servers | 0/10 | 20% |
| **OAuth Handling** | Triggers OAuth flow if needed | No OAuth attempted | 0/10 | 20% |
| **Tool Execution** | Calls MCP tool with correct params | Tried local Python instead | 0/10 | 25% |
| **Data Retrieval** | Returns actual Hansard speeches | No data retrieved | 0/10 | 20% |
| **Response Quality** | Formats results with metadata | Generic permission request | 2/10 | 15% |

### **Overall Score: 0.4/10** (4%)

## Issues Identified

### Critical Issues
1. ❌ **MCP server not discovered** - Server in config but not available to Claude
2. ❌ **OAuth flow not triggered** - No authentication attempt even when needed
3. ❌ **Wrong execution path** - Chose local Python over MCP tools

### Moderate Issues
4. ⚠️ **Non-interactive mode limitation** - `--print` may not support OAuth
5. ⚠️ **No fallback mechanism** - Should fall back to MCP when local Python denied

### Minor Issues
6. ℹ️ **Tool awareness** - Claude knows the tool exists but can't access it
7. ℹ️ **Helpful error** - Explains what's needed (though doesn't execute it)

## Recommendations

### For Immediate Testing

1. **Use Interactive Mode**:
   ```bash
   claude
   # Then type: "Search Hansard for climate change"
   ```
   This should trigger OAuth properly.

2. **Inject OAuth Token**:
   - Copy token from `/tmp/mcp_oauth_token.json`
   - Update `.credentials.json` with valid token
   - Retry query

3. **Check Server Status**:
   ```bash
   claude mcp list
   # Should show: mcp-prod - ⚠ Needs authentication
   ```

### For Production Use

1. **OAuth Automation**:
   - Add OAuth flow to `claude mcp add` command
   - Support headless OAuth for CI/CD
   - Cache tokens with proper refresh

2. **MCP Tool Prioritization**:
   - Prefer MCP tools over local execution
   - Surface MCP tools more prominently
   - Better error messages when MCP unavailable

3. **Non-Interactive OAuth**:
   - Support device flow for headless auth
   - Pre-authenticate option
   - Service account mode

## Conclusion

**The test failed completely** because:
1. OAuth token is missing
2. Claude CLI doesn't trigger OAuth in `--print` mode
3. MCP server exists but isn't available to Claude

**To fix**:
1. Use interactive mode to complete OAuth
2. Or manually inject the OAuth token we generated
3. Then retry the query

**OAuth automation is working** (proven by `test_oauth_simple.py`), but **Claude CLI integration needs OAuth token to be present** before it can use the MCP server.

The OAuth flow itself scores **10/10** (fully working), but the **Claude CLI integration scores 0/10** (not working in non-interactive mode).
