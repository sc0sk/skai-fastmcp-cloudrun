# Quickstart: ChatGPT Developer Mode Integration Testing

**Feature**: 005-chatgpt-integration | **Date**: 2025-10-23

## Overview

This guide provides step-by-step instructions for testing the Hansard MCP server with ChatGPT Developer Mode. It focuses on ChatGPT-specific setup and testing procedures. For general server deployment and development setup, see [feature 004 quickstart](../004-search-fetch-mcp-tools/quickstart.md).

**Prerequisites**:
- ChatGPT Pro, Team, or Enterprise subscription (Developer Mode is not available on free tier)
- MCP server deployed to Cloud Run with public HTTPS endpoint
- Cloud Run URL (e.g., `https://hansard-mcp-server-abc123-uc.a.run.app`)

## Step 1: Enable ChatGPT Developer Mode

Developer Mode must be enabled before you can connect MCP servers to ChatGPT.

1. Open ChatGPT (https://chatgpt.com)
2. Click your profile icon (bottom left)
3. Select **Settings**
4. Navigate to **Features** section
5. Find **Developer Mode** toggle
6. Enable Developer Mode
7. Click **Save**

**Troubleshooting**:
- **Developer Mode not visible**: Verify you have ChatGPT Pro/Team/Enterprise subscription (not free tier)
- **Toggle disabled**: Contact your ChatGPT Team/Enterprise admin to enable Developer Mode for your account

---

## Step 2: Create MCP Connector

Connect ChatGPT to the Hansard MCP server deployed on Cloud Run.

1. In ChatGPT Settings, navigate to **Developer Mode** section
2. Click **Add Connector**
3. Enter connector details:
   - **Name**: `Hansard Parliamentary Speeches`
   - **URL**: `https://YOUR-CLOUD-RUN-URL/mcp/`
     - Replace `YOUR-CLOUD-RUN-URL` with your actual Cloud Run service URL
     - Example: `https://hansard-mcp-server-abc123-uc.a.run.app/mcp/`
     - **Important**: Include trailing `/mcp/` path
4. Check **"I trust this provider"** checkbox
   - This enables tool execution without per-call confirmation prompts
   - Combined with `readOnlyHint=true` annotation, tools execute immediately
5. Click **Save**

**Connection Verification**:
- ChatGPT sends `initialize` request to server
- Server responds with protocol version and capabilities
- ChatGPT displays **"Connected successfully"** message
- Connector appears in "Connected services" list

**Troubleshooting**:

| Error | Cause | Solution |
|-------|-------|----------|
| "Could not reach server" | URL incorrect or server not running | Verify Cloud Run URL is correct, test with `curl https://YOUR-URL/mcp/` |
| "Invalid protocol response" | Server not implementing MCP correctly | Check server logs in Cloud Run console for errors |
| "Connection timeout" | Cold start delay >30s | Increase Cloud Run min instances to 1, or wait and retry |
| "URL must be HTTPS" | Used HTTP instead of HTTPS | Cloud Run provides HTTPS automatically, ensure URL starts with `https://` |
| "Path not found" | Missing `/mcp/` path | Append `/mcp/` to Cloud Run URL |

**Example Valid URLs**:
- ✅ `https://hansard-mcp-server-abc123-uc.a.run.app/mcp/`
- ✅ `https://mcp.simonkennedymp.com.au/mcp/` (custom domain)
- ❌ `https://hansard-mcp-server-abc123-uc.a.run.app` (missing `/mcp/`)
- ❌ `http://localhost:8080/mcp/` (HTTP not HTTPS, local dev only)

---

## Step 3: Enable Connector in Chat

Connectors must be explicitly enabled in each chat session.

1. Start a new chat in ChatGPT
2. Click the **connector dropdown** (above message input box)
3. Find **"Hansard Parliamentary Speeches"** in the list
4. Toggle the connector **ON** (checkmark appears)
5. Verify tools appear in dropdown:
   - `search_hansard_speeches`
   - `fetch_hansard_speech`

**Troubleshooting**:
- **Connector not in list**: Verify connector was saved successfully in Settings
- **Tools not appearing**: Click connector to refresh tool list, or disconnect and reconnect
- **"No tools available"**: Server may not be running, check Cloud Run status

---

## Step 4: Test Chat Mode

Test basic ChatGPT interaction with MCP tools to verify tool selection, parameter handling, and response quality.

### Test Case 1: Simple Search Query

**User Query**:
```
What has Simon Kennedy said about housing affordability?
```

**Expected Behavior**:
1. ChatGPT invokes `search_hansard_speeches` tool
2. Parameters: `{"query": "housing affordability"}`
3. **No confirmation prompt** (due to `readOnlyHint=true`)
4. Results displayed within **5 seconds**
5. ChatGPT uses **MCP tool** instead of web browsing (verify in response attribution)

**Success Criteria**:
- ✅ Tool invoked without user confirmation
- ✅ Results returned with speech excerpts and metadata
- ✅ ChatGPT displays speaker, date, party, chamber
- ✅ Response attributes data to "Hansard Parliamentary Speeches" connector

**If ChatGPT uses web search instead**:
- Check tool description includes "Use this when..." guidance
- Verify "Do not use built-in browsing" statement is present
- Try rephrasing: "Search the Hansard database for Simon Kennedy's speeches on housing"

---

### Test Case 2: Search with Filters

**User Query**:
```
Find Simon Kennedy's speeches on immigration in 2024
```

**Expected Behavior**:
1. ChatGPT invokes `search_hansard_speeches`
2. Parameters: `{"query": "immigration", "start_date": "2024-01-01", "end_date": "2024-12-31"}`
3. GPT-5 converts "in 2024" to ISO 8601 date range
4. Results filtered by date

**Success Criteria**:
- ✅ `start_date` and `end_date` parameters use ISO 8601 format (YYYY-MM-DD)
- ✅ All returned speeches have dates within 2024
- ✅ No validation errors on date format

**Alternative Phrasings to Test**:
- "speeches from last June" → `start_date: "2024-06-01", end_date: "2024-06-30"`
- "speeches this year" → `start_date: "2025-01-01", end_date: "2025-12-31"`
- "speeches after May 28, 2024" → `start_date: "2024-05-28"`

---

### Test Case 3: Enum Parameter Filtering

**User Query**:
```
What have Liberal MPs said about climate change?
```

**Expected Behavior**:
1. ChatGPT invokes `search_hansard_speeches`
2. Parameters: `{"query": "climate change", "party": "Liberal"}`
3. Results filtered to Liberal party
4. All results are Simon Kennedy speeches (dataset limitation)

**Success Criteria**:
- ✅ `party` parameter uses exact enum value: `"Liberal"` (not "liberal" or "Liberal Party")
- ✅ No validation errors on party parameter
- ✅ Results mention dataset limitation (only Simon Kennedy speeches available)

**Enum Values to Test**:
- `"Liberal"` ✅
- `"Labor"` ✅
- `"Greens"` ✅
- `"National"` ✅
- `"Independent"` ✅
- Chamber: `"House of Representatives"` ✅
- Chamber: `"Senate"` ✅

---

### Test Case 4: Search → Fetch Workflow

**User Query** (two-part):
1. "What did Simon Kennedy say about housing?"
2. "Show me the full text of that speech"

**Expected Behavior**:
1. **First query**: ChatGPT invokes `search_hansard_speeches`
   - Returns speech excerpts with `speech_id` values
2. **Second query**: ChatGPT invokes `fetch_hansard_speech`
   - Extracts `speech_id` from previous search results
   - Parameters: `{"speech_id": "550e8400-e29b-41d4-a716-446655440000"}`
   - Returns full speech transcript

**Success Criteria**:
- ✅ ChatGPT remembers `speech_id` from search results
- ✅ Fetch tool invoked without confirmation
- ✅ Full text displayed (2000-10000 words)
- ✅ Metadata included: title, Hansard reference, date, word count

**Alternative Workflow**:
```
User: "Find speeches on infrastructure investment"
ChatGPT: [displays search results]
User: "Get the full text of the top result"
ChatGPT: [fetches using speech_id from top search result]
```

---

### Test Case 5: Empty Results Handling

**User Query**:
```
What did Simon Kennedy say about Antarctica?
```

**Expected Behavior**:
1. ChatGPT invokes `search_hansard_speeches`
2. Parameters: `{"query": "Antarctica"}`
3. Server returns: `{"speeches": [], "total_count": 0, "query": "Antarctica"}`
4. ChatGPT displays user-friendly message

**Success Criteria**:
- ✅ No error thrown (empty results are valid)
- ✅ ChatGPT explains no matching speeches found
- ✅ ChatGPT mentions dataset limitation (Simon Kennedy only, 2024-2025)
- ✅ ChatGPT suggests alternative search terms or offers to use web search for other MPs

---

## Step 5: Test Deep Research Mode

Deep Research Mode demonstrates multi-tool workflows and comprehensive data analysis.

1. Switch to **Deep Research Mode** in ChatGPT
   - Click mode selector (top of chat)
   - Select "Deep Research"
2. Enter research task:

**Research Query**:
```
Analyze Simon Kennedy's housing policy positions over the past year, including key themes, rhetorical strategies, and voting patterns.
```

**Expected Behavior**:
1. ChatGPT plans research workflow (visible in "Researching..." panel)
2. Makes **10+ search queries** with varying keywords:
   - "housing affordability"
   - "first home buyers"
   - "rental crisis"
   - "property prices"
   - "housing supply"
   - "urban development"
   - "affordable housing programs"
3. Identifies relevant speeches from search results
4. **Fetches full text** of 3-5 most relevant speeches
5. Analyzes patterns: key themes, rhetorical strategies, evolution over time
6. Generates comprehensive report with:
   - Summary section
   - Key themes (bullet points)
   - Analysis of rhetorical strategies
   - Timeline of policy positions
   - **Citations section with Hansard references**

**Success Criteria**:
- ✅ 10+ tool invocations (search + fetch) without user confirmation
- ✅ All tools execute within 5 seconds each
- ✅ No confirmation prompts despite 10+ calls (readOnlyHint behavior)
- ✅ Report includes direct quotations from speeches
- ✅ Citations use `hansard_reference` field (e.g., "House Hansard, 3 June 2024, p.245")
- ✅ Report organized with clear sections and markdown formatting

**Alternative Research Queries**:
- "Compare Simon Kennedy's positions on immigration policy before and after May 2024"
- "Identify Simon Kennedy's most frequently discussed topics in 2024 with supporting quotes"
- "Analyze how Simon Kennedy frames infrastructure investment arguments"

---

## Step 6: Verify Tool Behavior

Confirm all ChatGPT integration requirements are met.

### Confirmation Prompts (FR-002, FR-003)

**Test**: Invoke both tools 10 times each in single chat session

**Expected**: Zero confirmation prompts ("Allow tool to access...?")

**If prompts appear**:
- Verify `readOnlyHint=true` in tool metadata (use MCP Inspector)
- Confirm "I trust this provider" checkbox was checked when creating connector
- Disconnect and reconnect connector

### Tool Selection Accuracy (FR-001, FR-006, SC-004)

**Test**: 20+ query variations to measure MCP tool vs web search usage

**Success Criteria**: 90%+ queries use MCP tool when appropriate

**Example Queries** (should use MCP tool):
- "What has Simon Kennedy said about housing?"
- "Find Simon Kennedy's speeches on immigration"
- "Show me Simon Kennedy's maiden speech"
- "What did Simon Kennedy say about the budget?"

**Example Queries** (should use web search - out of scope):
- "What has Malcolm Turnbull said about housing?" (different MP)
- "What did Simon Kennedy do before politics?" (not parliamentary speeches)
- "When was Simon Kennedy elected?" (biographical data, not speeches)

**If MCP tool usage <90%**:
- Review tool descriptions for "Use this when..." clarity
- Verify "Do not use built-in browsing" statement is present
- Test more explicit phrasings: "Search the Hansard database for..."

### Enum Parameter Auto-Completion (FR-004, SC-009)

**Test**: Use party and chamber filters 10+ times

**Expected**: ChatGPT uses exact enum values, no validation errors

**Success Criteria**: 95%+ correct enum usage

**Common Errors to Check**:
- ❌ `"liberal"` (lowercase) → Should be `"Liberal"`
- ❌ `"Liberal Party"` → Should be `"Liberal"`
- ❌ `"House"` → Should be `"House of Representatives"`

### Date Format Handling (FR-005, SC-009)

**Test**: Natural language date queries

**Expected**: GPT-5 converts to ISO 8601 format automatically

**Examples**:
- "last June" → `"2024-06-01"`, `"2024-06-30"`
- "this year" → `"2025-01-01"`, `"2025-12-31"`
- "after May 28, 2024" → `"2024-05-28"`
- "before Christmas 2024" → `"2024-12-25"`

**Success Criteria**: 95%+ correct ISO 8601 conversions, no validation errors

---

## Step 7: Performance Validation

Measure response times and confirm performance targets.

### Response Time (SC-005)

**Test**: 20 search queries, 20 fetch queries

**Target**: 95% of requests complete within 5 seconds

**Measurement**:
1. Note timestamp when query sent
2. Note timestamp when results displayed
3. Calculate: `response_time = display_time - query_time`

**Expected**:
- Search: 2-4 seconds (vector search + metadata enrichment + embedding generation)
- Fetch: 1-2 seconds (primary key lookup)
- Cold start (first request after idle): 15-30 seconds (acceptable)

**If >5s consistently**:
- Check Cloud Run logs for slow database queries
- Verify Cloud Run min instances = 1 (reduces cold starts)
- Check network latency (Cloud Run region vs ChatGPT region)

### Cold Start Mitigation (Risk 2)

**Test**: Leave server idle for 15 minutes, then send query

**Expected**: First request takes 15-30 seconds (cold start), subsequent requests <5s

**Mitigation**:
- Set Cloud Run min instances = 1 (keeps one instance warm)
- Document cold start behavior in connector description
- Implement health check endpoint for periodic keep-alive pings

---

## Troubleshooting

### Tools Not Appearing in ChatGPT

**Symptoms**:
- Connector shows as connected, but no tools in dropdown
- Chat says "No tools available"

**Solutions**:
1. Disconnect and reconnect connector
2. Refresh ChatGPT page (F5)
3. Check server is running: `curl https://YOUR-URL/mcp/`
4. Verify server logs show `tools/list` request received
5. Use MCP Inspector to test `tools/list` locally

### ChatGPT Uses Web Search Instead of MCP Tool

**Symptoms**:
- Query should use MCP tool, but ChatGPT browses web instead
- Response attributes data to "Browsing" not "Hansard Parliamentary Speeches"

**Solutions**:
1. Verify tool description includes "Use this when..." guidance
2. Add explicit "Do not use built-in browsing" statement
3. Try more explicit phrasing: "Search the Hansard database for Simon Kennedy's speeches on..."
4. Check tool selection accuracy (should be 90%+ for in-scope queries)

### Confirmation Prompts Appearing

**Symptoms**:
- ChatGPT asks "Allow Hansard Parliamentary Speeches to access...?" before each tool call
- Tools work after approval, but require manual confirmation

**Solutions**:
1. Verify "I trust this provider" checkbox was checked when creating connector
2. Disconnect connector, reconnect, and re-check "I trust this provider"
3. Use MCP Inspector to verify `readOnlyHint=true` in tool metadata:
   ```bash
   DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py
   # In Inspector: Tools tab → search_hansard_speeches → View metadata
   # Confirm: "annotations": {"readOnlyHint": true}
   ```

### Empty Results for Valid Queries

**Symptoms**:
- Query should return results (e.g., "housing" is mentioned in speeches)
- Server returns `{"speeches": [], "total_count": 0}`

**Solutions**:
1. Check database is populated: `python scripts/check_database.py`
2. Verify vector store has embeddings: `SELECT COUNT(*) FROM speech_chunks;`
3. Test search locally with MCP Inspector
4. Check embedding generation is working (Vertex AI Embeddings API)
5. Review server logs for vector search errors

### "Speech not found" Error

**Symptoms**:
- Fetch tool returns `ValueError: Speech not found: <speech_id>`
- `speech_id` came from search results

**Solutions**:
1. Verify `speech_id` matches speeches in database
2. Check for database schema mismatch (UUID format)
3. Ensure speeches table populated: `SELECT COUNT(*) FROM speeches;`
4. Test fetch locally: `await metadata_store.get_speech(speech_id)`

---

## Example Test Session

Complete end-to-end test workflow:

```
# Setup
1. Enable Developer Mode in ChatGPT Settings
2. Create connector: "Hansard Parliamentary Speeches"
3. URL: https://hansard-mcp-server-abc123-uc.a.run.app/mcp/
4. Trust provider: ✅
5. Save connector

# Chat Mode Test
User: "What has Simon Kennedy said about housing affordability?"
ChatGPT: [Invokes search_hansard_speeches]
→ ✅ No confirmation prompt
→ ✅ Results within 5 seconds
→ ✅ Displays 10 speech excerpts with metadata
→ ✅ Attribution: "Hansard Parliamentary Speeches"

User: "Show me the full text of the first speech"
ChatGPT: [Invokes fetch_hansard_speech with speech_id from search results]
→ ✅ No confirmation prompt
→ ✅ Full text returned (3500 words)
→ ✅ Hansard reference: "House Hansard, 3 June 2024, p.245"

User: "Find speeches on immigration from 2024"
ChatGPT: [Invokes search_hansard_speeches with date filters]
→ ✅ Parameters: {"query": "immigration", "start_date": "2024-01-01", "end_date": "2024-12-31"}
→ ✅ ISO 8601 date format
→ ✅ Results filtered correctly

# Deep Research Test
[Switch to Deep Research Mode]
User: "Analyze Simon Kennedy's housing policy positions over the past year"
ChatGPT: [Researching...]
→ Search: "housing affordability" (10 results)
→ Search: "first home buyers" (7 results)
→ Search: "rental crisis" (5 results)
→ Search: "property prices" (8 results)
→ Fetch: speech_id_1 (full text)
→ Fetch: speech_id_2 (full text)
→ Fetch: speech_id_3 (full text)
→ ✅ 10+ tool invocations, no confirmation prompts
→ ✅ Generated comprehensive report with citations
→ ✅ Citations include Hansard references

# Validation
✅ All tools executed without confirmation prompts (100%)
✅ Response times <5s (95%+)
✅ MCP tool used over web search (90%+)
✅ Enum parameters validated correctly (95%+)
✅ Date formats converted to ISO 8601 (95%+)
```

---

## Next Steps

After successful ChatGPT testing:

1. **Document Results**: Create `testing-results.md` with:
   - Test execution logs
   - Success criteria validation
   - Screenshots of ChatGPT interactions
   - Any issues encountered and resolutions

2. **Update CLAUDE.md**: Add ChatGPT testing section:
   ```markdown
   # ChatGPT Testing
   DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py  # Local dev

   # ChatGPT Developer Mode Setup
   1. Enable Developer Mode in Settings
   2. Add Connector: https://YOUR-CLOUD-RUN-URL/mcp/
   3. Trust provider
   4. Test queries: "What did Simon Kennedy say about housing?"
   ```

3. **User Documentation**: Prepare example queries for users:
   - Simple searches: topic queries
   - Filtered searches: party, chamber, date ranges
   - Deep research: comprehensive policy analysis

4. **Feature Completion**: Mark feature 005 as complete in project tracking

---

## References

- **FastMCP ChatGPT Integration**: https://gofastmcp.com/integrations/chatgpt
- **ChatGPT Developer Mode Docs**: https://help.openai.com/articles/chatgpt-developer-mode
- **MCP Protocol**: https://modelcontextprotocol.io/
- **Feature 004 Quickstart**: /home/user/skai-fastmcp-cloudrun/specs/004-search-fetch-mcp-tools/quickstart.md
- **Feature Spec**: /home/user/skai-fastmcp-cloudrun/specs/005-chatgpt-integration/spec.md
- **Cloud Run Documentation**: https://cloud.google.com/run/docs
