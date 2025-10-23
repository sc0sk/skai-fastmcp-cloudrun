# Phase 2: ChatGPT Developer Mode Testing Guide

**Feature**: 005-chatgpt-integration
**Cloud Run URL**: https://hansard-mcp-server-355dd2atrq-uc.a.run.app
**MCP Endpoint**: https://hansard-mcp-server-355dd2atrq-uc.a.run.app/mcp/
**Duration**: 6-8 hours
**Prerequisites**: ChatGPT Pro/Team/Enterprise account

---

## Pre-Testing Checklist

Before beginning testing, verify all prerequisites are met:

- [ ] ChatGPT Pro/Team/Enterprise subscription active (Developer Mode requires paid tier)
- [ ] Cloud Run service accessible (check health endpoint: `curl https://hansard-mcp-server-355dd2atrq-uc.a.run.app/health`)
- [ ] Developer Mode enabled in ChatGPT settings
- [ ] Testing report template ready (TEST-RESULTS-TEMPLATE.md)
- [ ] Timer/stopwatch available for timing measurements
- [ ] Spreadsheet or note-taking tool for tracking test results
- [ ] Browser with ChatGPT access (Chrome, Firefox, Edge, or Safari)

---

## Part 1: Connector Setup (SC-001)

### Step 1.1: Enable Developer Mode

**Objective**: Enable ChatGPT Developer Mode to access MCP connector functionality

**Procedure**:
1. Open ChatGPT at https://chatgpt.com
2. Click your avatar icon (bottom left corner)
3. Select **Settings** from dropdown menu
4. Navigate to **Features** or **Beta** section (varies by account type)
5. Locate **Developer Mode** toggle switch
6. Enable Developer Mode by toggling ON
7. Click **Save** or **Apply** if prompted

**Expected Result**: Toggle turns green/on without errors. Settings page may display message: "Developer Mode enabled"

**Troubleshooting**:
- **Developer Mode not visible**: Verify subscription tier (ChatGPT Pro/Team/Enterprise required)
- **Toggle grayed out**: Contact ChatGPT Team/Enterprise administrator to enable Developer Mode for your account
- **Error message on enable**: Try logging out and back in, or contact OpenAI support

---

### Step 1.2: Create MCP Connector

**Objective**: Connect ChatGPT to Hansard MCP server deployed on Cloud Run

**Success Criteria**: SC-001 - Connection completes in under 2 minutes

**Procedure**:

**Timer Start**: Record current time

1. In Settings, navigate to **Developer Mode** section or **MCP Connectors** subsection
2. Click **+ Add Connector** or **Create Connector** button
3. Fill out connector form with exact values:
   - **Name**: `Hansard Parliamentary Speeches`
   - **URL**: `https://hansard-mcp-server-355dd2atrq-uc.a.run.app/mcp/`
   - **Important**: Include trailing `/mcp/` path
4. Check the **"I trust this provider"** checkbox (REQUIRED for zero confirmations)
5. Click **Save** or **Create Connector**
6. Wait for connection verification (5-30 seconds depending on cold start)

**Timer Stop**: Record total time from step 1 to verification complete

**Expected Results**:
- Connection status shows "Connected" or "Connection successful"
- Connector appears in "Active Connectors" or "My Connectors" list
- Green checkmark or "Online" indicator next to connector name
- No error messages displayed

**Pass Criteria**:
- ✅ Connection time < 2 minutes
- ✅ "Connected successfully" message displayed
- ✅ Connector visible in list

**Fail Criteria**:
- ❌ Connection time > 2 minutes
- ❌ Error message: "Could not reach server"
- ❌ Error message: "Invalid protocol response"
- ❌ Timeout error after 30+ seconds

**Troubleshooting**:

| Error | Cause | Solution |
|-------|-------|----------|
| "Could not reach server" | URL incorrect or server down | Verify URL is exact: `https://hansard-mcp-server-355dd2atrq-uc.a.run.app/mcp/` with trailing slash |
| "Connection timeout" | Cloud Run cold start delay | Wait 30 seconds and retry. Cold starts take 15-30 seconds on first request |
| "Invalid protocol" | Wrong endpoint | Ensure URL ends with `/mcp/` not just base Cloud Run URL |
| "URL must be HTTPS" | Used HTTP | Cloud Run provides HTTPS automatically, ensure `https://` prefix |
| "Server returned error" | Server misconfiguration | Check Cloud Run logs for errors during connection attempt |

**Record**: Connection time in seconds for reporting

---

### Step 1.3: Verify Tool Discovery

**Objective**: Confirm both MCP tools are discoverable and have correct metadata

**Procedure**:
1. Start a **new chat** in ChatGPT (click "New Chat" button)
2. Look for connector dropdown above message input box (may show "No tools" initially)
3. Click connector dropdown to expand available tools list
4. Find **"Hansard Parliamentary Speeches"** in the list
5. Toggle connector **ON** (enable it for this chat session)
6. Observe tools that appear in dropdown or tool panel

**Expected Results**:
- Two tools appear after enabling connector:
  - `search_hansard_speeches` - "Search Australian parliamentary speeches by Simon Kennedy MP"
  - `fetch_hansard_speech` - "Retrieve full text of a specific parliamentary speech"
- Tool descriptions are visible when hovering or expanding tool details
- No error messages like "No tools available" or "Could not load tools"

**Verification Checklist**:
- [ ] search_hansard_speeches visible in tool list
- [ ] fetch_hansard_speech visible in tool list
- [ ] Descriptions match expected text (contain "Simon Kennedy", "parliamentary speeches")
- [ ] No errors displayed in tool panel

**Pass Criteria**:
- ✅ Both tools visible
- ✅ Descriptions present and accurate
- ✅ Tools can be selected/enabled

**Fail Criteria**:
- ❌ Tools not appearing after enabling connector
- ❌ Only one tool visible
- ❌ Descriptions missing or incorrect

**Troubleshooting**:
- **Tools not appearing**: Refresh ChatGPT page (F5), re-enable connector
- **Connector shows as offline**: Check Cloud Run service is running: `gcloud run services describe hansard-mcp-server`
- **"No tools available"**: Disconnect and reconnect connector in Settings
- **Partial tool list**: Server may have crashed during tools/list request, check Cloud Run logs

---

## Part 2: Chat Mode Testing (FR-002, SC-002, SC-004)

### Test 2.1: Simple Search Without Confirmation

**Objective**: Verify readOnlyHint eliminates confirmation prompts for search tool

**Success Criteria**: SC-002 - Zero confirmation prompts for search tool invocations

**Procedure**:
1. Start new chat with Hansard connector enabled
2. Copy-paste exact query below:

**Test Query**:
```
What has Simon Kennedy said about housing affordability?
```

3. Press Enter and observe ChatGPT's behavior
4. **Critical**: Watch for confirmation prompt before tool execution
5. Measure time from message send to first result token

**Expected Behavior Checklist**:
- [ ] ChatGPT invokes `search_hansard_speeches` automatically
- [ ] **NO confirmation prompt** appears (e.g., "Allow Hansard to access...?")
- [ ] Tool execution starts within 1 second of message send
- [ ] Results appear within 5 seconds total
- [ ] Response includes speech excerpts with metadata (speaker, date, party)
- [ ] Attribution shows "Used Hansard Parliamentary Speeches" (not web browsing)

**Measurements to Record**:
- Confirmation prompts: ____ (MUST be 0)
- Response time: ____ seconds (target: <5 seconds)
- Tool used: search_hansard_speeches / web browsing / other (circle one)
- Number of results returned: ____
- Metadata displayed: Speaker / Date / Party / Chamber (check all present)

**Pass Criteria**:
- ✅ 0 confirmation prompts
- ✅ search_hansard_speeches tool invoked (visible in ChatGPT's tool usage indicator)
- ✅ Response time < 5 seconds
- ✅ Results displayed with excerpts and metadata

**Fail Criteria**:
- ❌ Confirmation prompt appeared
- ❌ ChatGPT used web browsing instead of MCP tool
- ❌ Response time > 5 seconds (excluding cold start on first request)
- ❌ No results returned despite valid query

**Troubleshooting**:
- **Confirmation prompt appears**: CRITICAL - Verify "I trust this provider" was checked when creating connector. Disconnect and reconnect with checkbox checked.
- **Web browsing used instead**: Tool description may need enhancement. Try explicit phrasing: "Use the Hansard tool to search for Simon Kennedy's speeches on housing"
- **Slow response**: Check if this is first request (cold start expected). Subsequent requests should be <5 seconds.

---

### Test 2.2: Search with Party Filter

**Objective**: Verify enum parameter handling for party filter

**Test Query**:
```
Show me Liberal Party speeches on immigration
```

**Expected Behavior**:
- [ ] search_hansard_speeches called with `party="Liberal"` (or `party="LP"`)
- [ ] No confirmation prompt
- [ ] Results filtered to Liberal Party only
- [ ] All returned speeches show speaker party as "Liberal"

**Verification Steps**:
1. Send query
2. Check ChatGPT's tool call details (may show in UI or response text)
3. Verify all results show "Liberal" party in metadata
4. Confirm 0 confirmation prompts

**Measurements**:
- Confirmation prompts: ____
- Party parameter value used: ____
- All results Liberal Party: YES / NO
- Number of results: ____

**Pass Criteria**:
- ✅ party parameter uses correct enum value ("Liberal" or "LP")
- ✅ 0 confirmation prompts
- ✅ Results correctly filtered

**Fail Criteria**:
- ❌ Party parameter error (invalid enum value like "liberal" lowercase)
- ❌ Results include non-Liberal speeches
- ❌ Confirmation prompt appeared

---

### Test 2.3: Search with Date Range (ISO 8601)

**Objective**: Verify ChatGPT converts natural language dates to ISO 8601 format

**Test Query**:
```
Find speeches about housing between May 2024 and October 2024
```

**Expected Behavior**:
- [ ] ChatGPT converts "May 2024" to ISO 8601: `start_date="2024-05-01"`
- [ ] ChatGPT converts "October 2024" to ISO 8601: `end_date="2024-10-31"`
- [ ] search_hansard_speeches called with date parameters in correct format
- [ ] Results show dates within specified range

**Verification Steps**:
1. Send query
2. Check tool parameters (if visible in ChatGPT UI)
3. Verify all returned speeches have dates between 2024-05-01 and 2024-10-31
4. Confirm date format is ISO 8601 (YYYY-MM-DD)

**Measurements**:
- start_date parameter: ____
- end_date parameter: ____
- Date format correct (ISO 8601): YES / NO
- All results within range: YES / NO
- Confirmation prompts: ____

**Additional Date Queries to Test** (optional):
- "speeches from last June" → Expected: `2024-06-01` to `2024-06-30`
- "speeches this year" → Expected: `2025-01-01` to `2025-12-31`
- "speeches after May 28, 2024" → Expected: `start_date="2024-05-28"`, no end_date

**Pass Criteria**:
- ✅ Dates converted to ISO 8601 format
- ✅ Results filtered correctly
- ✅ 0 confirmation prompts

**Fail Criteria**:
- ❌ Date format error (e.g., "05/01/2024" instead of "2024-05-01")
- ❌ Results outside specified date range
- ❌ Validation error from server

---

### Test 2.4: Search → Fetch Workflow

**Objective**: Verify multi-tool workflow executes without confirmations

**Success Criteria**: SC-002, SC-003 - Both tools execute without confirmation prompts

**Test Query (Two-Part)**:

**Part 1**:
```
Find speeches about infrastructure and show me the most relevant one
```

**Part 2** (if needed):
```
Show me the full text of that speech
```

**Expected Behavior**:
1. **First**: ChatGPT invokes `search_hansard_speeches` with query="infrastructure"
   - No confirmation prompt for search
   - Returns list of speech excerpts with speech_id values
2. **Second**: ChatGPT automatically or on request invokes `fetch_hansard_speech`
   - Extracts speech_id from search results
   - No confirmation prompt for fetch
   - Returns full speech text (2000-10000 words)
3. **Total confirmations**: 0 for both tools

**Verification Checklist**:
- [ ] search_hansard_speeches executed first
- [ ] 0 confirmation prompts for search
- [ ] fetch_hansard_speech executed second (with valid speech_id)
- [ ] 0 confirmation prompts for fetch
- [ ] Full speech text displayed (check word count > 2000)
- [ ] Metadata included: title, Hansard reference, date, speaker

**Measurements**:
- Total tool calls: ____ (should be 2)
- Confirmation prompts (search): ____
- Confirmation prompts (fetch): ____
- Total confirmations: ____ (MUST be 0)
- Full text displayed: YES / NO
- Hansard reference present: YES / NO

**Pass Criteria**:
- ✅ Both tools called in sequence
- ✅ 0 total confirmation prompts
- ✅ Full text retrieved and displayed
- ✅ ChatGPT correctly extracted speech_id from search results

**Fail Criteria**:
- ❌ Any confirmation prompt for either tool
- ❌ ChatGPT failed to extract speech_id
- ❌ "Speech not found" error with valid speech_id

---

### Test 2.5: Empty Results Handling

**Objective**: Verify graceful handling of zero search results

**Test Query**:
```
What did Simon Kennedy say about cryptocurrency regulation?
```

**Expected Behavior**:
- [ ] search_hansard_speeches returns 0 results (topic unlikely in dataset)
- [ ] ChatGPT explains: "No speeches found matching this topic"
- [ ] ChatGPT mentions dataset scope (Simon Kennedy, 2024-2025)
- [ ] ChatGPT suggests alternative topics or broader search terms
- [ ] No errors displayed to user

**Verification Checklist**:
- [ ] search tool invoked successfully
- [ ] 0 results returned (not an error)
- [ ] User-friendly explanation provided
- [ ] Dataset limitations mentioned
- [ ] Helpful suggestions offered (e.g., "Try searching for 'economic policy' or 'financial regulation'")

**Measurements**:
- Number of results: ____ (should be 0)
- Error message shown: YES / NO
- User-friendly explanation: YES / NO
- Suggestions provided: YES / NO

**Pass Criteria**:
- ✅ 0 results handled gracefully (not treated as error)
- ✅ ChatGPT explains why no results found
- ✅ Helpful suggestions provided

**Fail Criteria**:
- ❌ Error message displayed (e.g., "Tool failed")
- ❌ ChatGPT provides no explanation
- ❌ Technical error details shown to user

---

### Test 2.6: Tool Preference Over Web Search (SC-004)

**Objective**: Verify ChatGPT prefers MCP tool over built-in web search

**Success Criteria**: SC-004 - ChatGPT uses MCP tool ≥ 80% of time for Simon Kennedy queries

**Procedure**: Run 10 different queries related to Simon Kennedy and track which tool ChatGPT uses

**10 Test Queries** (copy-paste each, send separately):

1. `Simon Kennedy housing policy`
2. `Simon Kennedy maiden speech`
3. `Simon Kennedy immigration stance`
4. `Simon Kennedy infrastructure projects`
5. `Simon Kennedy economic views`
6. `Simon Kennedy parliamentary questions`
7. `Simon Kennedy voting record`
8. `Simon Kennedy constituency work`
9. `Simon Kennedy budget responses`
10. `Simon Kennedy foreign affairs`

**For Each Query, Record**:
- Query number: ____
- Tool used: ☐ search_hansard_speeches ☐ Web browsing ☐ Other
- Results relevant: YES / NO
- Attribution shown: ____

**Scoring**:
- ✅ = Used search_hansard_speeches (MCP tool)
- ❌ = Used web browsing or other tool

**Pass Criteria**: ≥ 8/10 (80%) use MCP tool

**Results Table**:

| Query # | Query Text | Tool Used | ✅/❌ |
|---------|------------|-----------|------|
| 1 | Simon Kennedy housing policy | | |
| 2 | Simon Kennedy maiden speech | | |
| 3 | Simon Kennedy immigration stance | | |
| 4 | Simon Kennedy infrastructure projects | | |
| 5 | Simon Kennedy economic views | | |
| 6 | Simon Kennedy parliamentary questions | | |
| 7 | Simon Kennedy voting record | | |
| 8 | Simon Kennedy constituency work | | |
| 9 | Simon Kennedy budget responses | | |
| 10 | Simon Kennedy foreign affairs | | |

**Total Score**: ____/10 (____%)

**Pass Criteria**:
- ✅ Score ≥ 8/10 (80%)
- ✅ MCP tool used for clear parliamentary speech queries

**Fail Criteria**:
- ❌ Score < 8/10
- ❌ ChatGPT defaults to web search for obvious speech-related queries

**Troubleshooting**:
- **Low MCP usage**: Tool descriptions may need "Use this when..." enhancement
- **Web search preferred**: Try explicit phrasings: "Use the Hansard tool to find..."
- **Inconsistent behavior**: Document which query types trigger web search vs MCP tool

---

## Part 3: Deep Research Mode Testing (FR-011, SC-003, SC-006)

### Test 3.1: Comprehensive Policy Analysis

**Objective**: Verify Deep Research Mode produces comprehensive reports with multiple tool calls and citations

**Success Criteria**: SC-003, SC-006 - Deep Research produces reports with 10+ tool calls and proper citations

**Procedure**:

**Step 1**: Switch to Deep Research Mode
1. Click mode selector at top of ChatGPT interface
2. Select **"Deep Research"** mode (may be labeled "Research" or "Deep Research")
3. Verify mode indicator shows "Deep Research" active

**Step 2**: Submit research query

**Research Query**:
```
Analyze Simon Kennedy's housing policy positions over the past year, including key themes, voting patterns, and rhetorical strategies
```

**Step 3**: Monitor ChatGPT's research process
1. Watch "Researching..." panel for tool invocations
2. Count total tool calls made
3. Note variety of search queries used
4. Record how many speeches are fetched for full text

**Expected Behavior**:
1. **Planning Phase**: ChatGPT displays research plan (1-2 minutes)
2. **Multiple Search Queries** (10+ tool calls): ChatGPT searches with varying keywords:
   - "housing affordability"
   - "first home buyers"
   - "rental crisis"
   - "property prices"
   - "housing supply"
   - "urban development"
   - "affordable housing programs"
   - "housing policy"
   - "residential construction"
   - "housing market"
3. **Fetch Full Speeches** (3-5 fetch calls): Most relevant speeches retrieved for detailed analysis
4. **Generate Structured Report** with:
   - Executive summary (2-3 paragraphs)
   - Key themes identified (bulleted list)
   - Evolution over time (chronological analysis)
   - Rhetorical strategies used
   - Voting patterns (if available in speeches)
   - **Citations section** with Hansard references
5. **Response Time**: 2-5 minutes for complete analysis

**Measurements to Record**:
- Total tool calls: ____ (target: ≥ 10)
- search_hansard_speeches calls: ____ (target: ≥ 7)
- fetch_hansard_speech calls: ____ (target: ≥ 3)
- Unique search queries: ____ (measure keyword diversity)
- Confirmation prompts: ____ (MUST be 0)
- Citations present: YES / NO
- Hansard references in citations: YES / NO
- Report structure: Summary / Themes / Citations (check all present)
- Total time: ____ minutes

**Report Quality Checklist**:
- [ ] Executive summary present (2-3 paragraphs)
- [ ] Key themes identified with supporting evidence
- [ ] Chronological analysis (evolution over time)
- [ ] Rhetorical strategies analyzed
- [ ] Direct quotations from speeches included
- [ ] Citations section with Hansard references (e.g., "House Hansard, 3 June 2024, p.245")
- [ ] Markdown formatting (headers, bullets, etc.)
- [ ] Comprehensive (3000+ words)

**Pass Criteria**:
- ✅ Total tool calls ≥ 10
- ✅ 0 confirmation prompts for any tool call
- ✅ Structured report with all required sections
- ✅ Citations present with Hansard references
- ✅ search_hansard_speeches called with diverse keywords
- ✅ Multiple speeches fetched for detailed analysis

**Fail Criteria**:
- ❌ < 10 tool calls (insufficient research depth)
- ❌ Any confirmation prompts during research
- ❌ No citations section
- ❌ Missing Hansard references
- ❌ Report incomplete (missing sections)
- ❌ All searches use same keyword (no diversity)

**Troubleshooting**:
- **< 10 tool calls**: Deep Research Mode may not understand scope. Rephrase with "comprehensive analysis" or "detailed examination"
- **No citations**: Check if fetch_hansard_speech returns hansard_reference field. May need to explicitly request citations in query.
- **Confirmation prompts**: CRITICAL - Indicates readOnlyHint not working. Verify tool annotations.

---

### Test 3.2: Date Range Comparative Analysis

**Objective**: Verify Deep Research Mode can compare speeches across different time periods

**Research Query**:
```
Compare Simon Kennedy's speeches on economic policy from Q2 2024 vs Q3 2024
```

**Expected Behavior**:
1. **Multiple searches with date filters**:
   - Q2 2024: `start_date="2024-04-01"`, `end_date="2024-06-30"`
   - Q3 2024: `start_date="2024-07-01"`, `end_date="2024-09-30"`
2. **Comparative analysis** showing differences between time periods
3. **Chronological ordering** of themes and topics
4. **Identification of shifts** in policy positions or rhetoric

**Measurements**:
- Searches with Q2 date range: ____
- Searches with Q3 date range: ____
- Comparative structure present: YES / NO
- Differences identified: YES / NO
- Total tool calls: ____

**Pass Criteria**:
- ✅ Date ranges correctly applied
- ✅ Comparative analysis structure (Q2 vs Q3)
- ✅ Differences identified and explained
- ✅ ≥ 6 tool calls

**Fail Criteria**:
- ❌ Incorrect date ranges or format errors
- ❌ No comparison (just lists Q2 and Q3 separately)
- ❌ < 6 tool calls

---

### Test 3.3: Multi-Topic Priority Analysis

**Objective**: Verify Deep Research Mode can analyze multiple policy topics

**Research Query**:
```
What are the main policy priorities for Simon Kennedy based on his parliamentary speeches?
```

**Expected Behavior**:
1. **Broad search queries** to identify topics:
   - "policy", "priorities", "focus", "key issues", "main concerns"
2. **Topic clustering**: Housing, immigration, infrastructure, economy, etc.
3. **Frequency analysis**: Which topics appear most often
4. **Summary of priorities** ranked by speech count or emphasis

**Measurements**:
- Total search queries: ____
- Topics identified: ____ (list all)
- Frequency data provided: YES / NO
- Ranking present: YES / NO
- Total tool calls: ____

**Pass Criteria**:
- ✅ Multiple topics identified (≥ 3)
- ✅ Frequency or ranking provided
- ✅ ≥ 8 tool calls
- ✅ Comprehensive coverage of dataset

**Fail Criteria**:
- ❌ Only 1-2 topics identified
- ❌ No frequency analysis
- ❌ < 8 tool calls

---

## Part 4: Performance Validation (SC-005, SC-006)

### Test 4.1: Response Time Measurement

**Objective**: Verify 95% of tool invocations complete within 5 seconds

**Success Criteria**: SC-005 - 95% of requests complete in < 5 seconds

**Procedure**: Measure 20 tool invocations (mix of search and fetch)

**10 Chat Mode Search Queries** (for variety):
1. `housing affordability`
2. `immigration policy`
3. `infrastructure investment`
4. `economic growth`
5. `climate change`
6. `healthcare funding`
7. `education policy`
8. `regional development`
9. `budget surplus`
10. `tax reform`

**10 Random Search + Fetch Workflows**:
- Pick any 10 speeches from above searches and fetch full text

**For Each Query, Record**:
- Query number: ____
- Tool: search / fetch
- Start time: ____ (when Enter pressed)
- End time: ____ (when first result token appears)
- Response time: ____ seconds
- ✅/❌ (✅ if <5 seconds, ❌ if ≥5 seconds)

**Results Table**:

| # | Query | Tool | Start | End | Time (s) | Pass |
|---|-------|------|-------|-----|----------|------|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |
| 6 | | | | | | |
| 7 | | | | | | |
| 8 | | | | | | |
| 9 | | | | | | |
| 10 | | | | | | |
| 11 | | | | | | |
| 12 | | | | | | |
| 13 | | | | | | |
| 14 | | | | | | |
| 15 | | | | | | |
| 16 | | | | | | |
| 17 | | | | | | |
| 18 | | | | | | |
| 19 | | | | | | |
| 20 | | | | | | |

**Scoring**:
- Total queries: 20
- Queries < 5 seconds: ____
- Percentage: ____% (= queries <5s / 20 * 100)

**Pass Criteria**: ≥ 19/20 (95%) complete in < 5 seconds

**Expected Performance**:
- Search queries: 2-4 seconds (vector search + embedding generation)
- Fetch queries: 1-2 seconds (primary key lookup)
- Occasional outliers: 5-10 seconds acceptable for <5% of requests

**Fail Criteria**:
- ❌ < 95% under 5 seconds
- ❌ Consistent 10+ second delays
- ❌ Timeout errors

**Troubleshooting**:
- **Slow searches**: Check Cloud Run logs for database query times. Verify HNSW index exists on embeddings.
- **Slow fetches**: Primary key lookup should be <1s. Check Cloud SQL connection pooling.
- **Timeouts**: Increase Cloud Run request timeout or check database connection limits.

---

### Test 4.2: Cold Start Handling

**Objective**: Document and verify acceptable cold start behavior

**Procedure**:

**Step 1**: Wait for server to go cold
1. Do NOT send any queries for **15 minutes**
2. Verify server is idle (no activity in Cloud Run logs)

**Step 2**: Send first query after idle period

**First Query**:
```
What has Simon Kennedy said about housing?
```

**Measurements**:
- Start time: ____
- First response token time: ____
- Cold start delay: ____ seconds
- Result: PASS / FAIL

**Expected Behavior**:
- First request: 15-30 seconds (cold start - Cloud Run spins up instance)
- Result: Should return valid results despite delay
- No errors or timeouts

**Step 3**: Send second query immediately

**Second Query**:
```
Find speeches on immigration
```

**Measurements**:
- Start time: ____
- Response time: ____ seconds
- Result: PASS / FAIL

**Expected Behavior**:
- Second request: < 5 seconds (instance already warm)

**Pass Criteria**:
- ✅ Cold start delay 15-30 seconds (acceptable)
- ✅ Valid results returned after cold start
- ✅ Subsequent queries < 5 seconds

**Fail Criteria**:
- ❌ Cold start > 60 seconds
- ❌ Timeout or error on first query
- ❌ Subsequent queries still slow (>5s)

**Mitigation Notes**:
- Cold starts are expected behavior for Cloud Run services
- Can be reduced by setting min instances = 1 (keeps one instance warm)
- Document this limitation in user-facing documentation

---

## Part 5: Error Handling Validation (FR-012)

### Test 5.1: Invalid Speech ID

**Objective**: Verify user-friendly error messages for invalid speech IDs

**Procedure**:

**Step 1**: Find a valid speech_id from search
```
Find a speech about housing
```

**Step 2**: Note one speech_id from results (e.g., `550e8400-e29b-41d4-a716-446655440000`)

**Step 3**: Modify speech_id and request fetch

**Test Query**:
```
Fetch speech ID abc123-invalid-xyz-999
```

**Expected Behavior**:
- [ ] ChatGPT receives error from server: "Speech not found: abc123-invalid-xyz-999"
- [ ] ChatGPT displays user-friendly message: "I couldn't find that speech. The speech ID may be incorrect or the speech may no longer be available."
- [ ] No technical stack traces shown to user
- [ ] ChatGPT suggests: "Try searching for speeches first to get valid IDs"

**Verification Checklist**:
- [ ] Error returned by server (not a crash)
- [ ] ChatGPT explains error in natural language
- [ ] No raw error JSON shown to user
- [ ] No stack traces visible
- [ ] Helpful suggestion provided

**Pass Criteria**:
- ✅ User-friendly error explanation
- ✅ No technical details exposed
- ✅ Helpful recovery suggestion

**Fail Criteria**:
- ❌ Raw error JSON displayed
- ❌ Stack trace visible
- ❌ Server crashes or returns 500 error
- ❌ No explanation provided

---

### Test 5.2: Invalid Date Format Handling

**Objective**: Verify ChatGPT auto-corrects date formats or handles validation errors gracefully

**Test Query**:
```
Find speeches from 05/28/2024 to 10/22/2024
```

**Expected Behavior (Option A - Auto-conversion)**:
- [ ] ChatGPT auto-converts to ISO 8601: `start_date="2024-05-28"`, `end_date="2024-10-22"`
- [ ] search_hansard_speeches called with correct format
- [ ] Results returned successfully
- [ ] User sees results, not errors

**Expected Behavior (Option B - Validation error + retry)**:
- [ ] Server returns validation error: "Date must be in ISO 8601 format (YYYY-MM-DD)"
- [ ] ChatGPT retries with corrected format
- [ ] Results returned on second attempt
- [ ] User sees results, not errors

**Verification Checklist**:
- [ ] Date format converted to ISO 8601
- [ ] Results returned successfully
- [ ] No validation errors shown to user
- [ ] Correct date range applied

**Pass Criteria**:
- ✅ Dates converted to ISO 8601
- ✅ Results returned (even if retry needed)
- ✅ User does not see validation errors

**Fail Criteria**:
- ❌ Validation error shown to user without retry
- ❌ Incorrect date format sent to server
- ❌ No results returned due to format issue

---

## Part 6: Success Criteria Validation

This section provides a final checklist to verify all success criteria are met.

### SC-001: Connection Time
- [ ] **PASS**: Connector setup completed in < 2 minutes
- [ ] **PASS**: Tools visible within 30 seconds of enabling connector
- [ ] **FAIL**: Connection took > 2 minutes (record actual time: ____)

**Notes**: ____

---

### SC-002: Zero Confirmation Prompts for Search Tool
- [ ] **PASS**: search_hansard_speeches executed 0 confirmation prompts in all tests
- [ ] **FAIL**: Confirmation prompts appeared (count: ____)

**Test Coverage**:
- Test 2.1: ____
- Test 2.2: ____
- Test 2.3: ____
- Test 2.4: ____
- Test 3.1: ____

**Total Confirmation Prompts Across All Tests**: ____ (MUST be 0)

---

### SC-003: Zero Confirmation Prompts for Fetch Tool
- [ ] **PASS**: fetch_hansard_speech executed 0 confirmation prompts in all tests
- [ ] **FAIL**: Confirmation prompts appeared (count: ____)

**Test Coverage**:
- Test 2.4: ____
- Test 3.1: ____

**Total Confirmation Prompts**: ____ (MUST be 0)

---

### SC-004: Tool Preference Over Web Search
- [ ] **PASS**: ChatGPT uses MCP tool ≥ 80% of time for Simon Kennedy queries
- [ ] **FAIL**: MCP tool usage < 80%

**Test 2.6 Results**:
- MCP tool usage: ____/10 (____%)
- Pass threshold: ≥ 8/10 (80%)

---

### SC-005: Response Times
- [ ] **PASS**: 95% of queries complete in < 5 seconds
- [ ] **FAIL**: < 95% meet target

**Test 4.1 Results**:
- Queries < 5 seconds: ____/20 (____%)
- Pass threshold: ≥ 19/20 (95%)

---

### SC-006: Deep Research Quality
- [ ] **PASS**: Deep Research produces comprehensive reports with 10+ tool calls
- [ ] **PASS**: Citations present with Hansard references
- [ ] **PASS**: Structured format (summary, themes, citations)
- [ ] **FAIL**: Missing required elements (specify: ____)

**Test 3.1 Results**:
- Total tool calls: ____ (target: ≥ 10)
- Citations present: YES / NO
- Hansard references: YES / NO
- Report structure complete: YES / NO

---

### SC-007: Authentication
- [ ] **PASS**: Zero authentication errors (public endpoint)
- [ ] **PASS**: No CORS issues
- [ ] **FAIL**: Authentication errors occurred (count: ____)

**Notes**: ____

---

### SC-008: User Satisfaction (Manual Rating)

Rate your experience with the ChatGPT MCP integration (1-5 scale):

**Tool Usefulness**: ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5
How useful were the Hansard tools for finding parliamentary speech information?

**Result Relevance**: ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5
How relevant were the search results to your queries?

**Ease of Use**: ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5
How easy was it to set up and use the MCP connector?

**Overall Experience**: ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5
Overall, how would you rate the ChatGPT integration?

- [ ] **PASS**: All ratings ≥ 4/5
- [ ] **FAIL**: Any rating < 4/5 (specify which: ____)

**Pass Criteria**: Average ≥ 4.0/5.0 across all categories

---

## Testing Report Template

Use this template to document final results:

```markdown
# ChatGPT Integration Testing Report

**Date**: [YYYY-MM-DD]
**Tester**: [Name]
**Duration**: [Hours]
**Cloud Run URL**: https://hansard-mcp-server-355dd2atrq-uc.a.run.app

---

## Part 1: Connector Setup
- [ ] SC-001 PASS/FAIL: Connection time = ___ seconds (target: <120s)
- **Notes**: ___

---

## Part 2: Chat Mode Testing
- [ ] Test 2.1 PASS/FAIL: Confirmation prompts = ___ (target: 0)
- [ ] Test 2.2 PASS/FAIL: Party filter worked correctly
- [ ] Test 2.3 PASS/FAIL: Date range filter worked (ISO 8601 format)
- [ ] Test 2.4 PASS/FAIL: Workflow (search → fetch) confirmations = ___ (target: 0)
- [ ] Test 2.5 PASS/FAIL: Empty results handled gracefully
- [ ] Test 2.6 PASS/FAIL: Tool preference = ___/10 (___%) (target: ≥80%)

**Chat Mode Summary**: PASS / FAIL
**Notes**: ___

---

## Part 3: Deep Research Mode Testing
- [ ] Test 3.1 PASS/FAIL: Tool calls = ___, Citations present: YES/NO
- [ ] Test 3.2 PASS/FAIL: Date comparison worked
- [ ] Test 3.3 PASS/FAIL: Multi-topic analysis comprehensive

**Deep Research Summary**: PASS / FAIL
**Notes**: ___

---

## Part 4: Performance Validation
- [ ] Test 4.1 PASS/FAIL: Response times = ___/20 under 5s (___%) (target: ≥95%)
- [ ] Test 4.2 PASS/FAIL: Cold start delay = ___ seconds (acceptable: 15-30s)

**Performance Summary**: PASS / FAIL
**Notes**: ___

---

## Part 5: Error Handling
- [ ] Test 5.1 PASS/FAIL: Invalid speech ID handled gracefully
- [ ] Test 5.2 PASS/FAIL: Date format auto-converted or error handled

**Error Handling Summary**: PASS / FAIL
**Notes**: ___

---

## Success Criteria Summary

| SC | Criterion | Target | Actual | PASS/FAIL |
|----|-----------|--------|--------|-----------|
| SC-001 | Connection time | < 2 min | ___ s | |
| SC-002 | Search confirmations | 0 | ___ | |
| SC-003 | Fetch confirmations | 0 | ___ | |
| SC-004 | Tool preference | ≥ 80% | ___% | |
| SC-005 | Response times | ≥ 95% <5s | ___% | |
| SC-006 | Deep Research quality | 10+ calls, citations | ___ | |
| SC-007 | Authentication errors | 0 | ___ | |
| SC-008 | User satisfaction | ≥ 4/5 | ___/5 | |

**Overall Result**: **PASS** / **FAIL**

**Pass Criteria**: All SCs must PASS
**Result**: ___ / 8 SCs passed

---

## Issues Encountered

1. **Issue**: ___
   **Severity**: Critical / Major / Minor
   **Resolution**: ___

2. **Issue**: ___
   **Severity**: Critical / Major / Minor
   **Resolution**: ___

---

## Lessons Learned

- ___
- ___
- ___

---

## Recommendations for Phase 3

1. **Documentation**: ___
2. **Tool Enhancements**: ___
3. **Performance Optimizations**: ___
4. **User Guidance**: ___

---

## Screenshots

(Attach screenshots of):
- Connector setup screen
- Tool discovery panel
- Example search results
- Deep Research report
- Error handling examples

---

## Sign-Off

**Tester Signature**: ___
**Date**: ___
**Ready for Phase 3**: YES / NO
```

---

## Troubleshooting Reference

### Tools Not Appearing in ChatGPT

**Symptoms**:
- Connector shows as "Connected" but no tools in dropdown
- Chat displays "No tools available"
- Tool panel is empty

**Solutions**:
1. **Refresh ChatGPT page**: Press F5 or Ctrl+R to reload
2. **Disconnect and reconnect**: Settings → Developer Mode → Remove connector → Re-add
3. **Verify server is running**: `curl https://hansard-mcp-server-355dd2atrq-uc.a.run.app/health`
4. **Check server logs**: `gcloud logging read "resource.type=cloud_run_revision" --limit 50`
5. **Test tools/list locally**: Use MCP Inspector or curl to verify tools/list endpoint

---

### ChatGPT Uses Web Search Instead of MCP Tool

**Symptoms**:
- Query should use MCP tool, but ChatGPT browses web instead
- Response attribution shows "Browsing" not "Hansard Parliamentary Speeches"
- Generic web results instead of Hansard data

**Solutions**:
1. **Verify tool description**: Check "Use this when..." guidance is present in tool metadata
2. **Try explicit phrasing**: "Use the Hansard tool to search for Simon Kennedy's speeches on..."
3. **Enable connector**: Ensure Hansard connector is toggled ON in tool dropdown for this chat
4. **Check tool selection metrics**: If <80% MCP usage in Test 2.6, descriptions may need enhancement
5. **Rephrase query**: Try "parliamentary speeches" instead of just "speeches"

---

### Confirmation Prompts Appearing

**Symptoms**:
- ChatGPT asks "Allow Hansard Parliamentary Speeches to access...?" before each tool call
- Tools work after clicking "Allow", but require manual confirmation
- readOnlyHint annotation not being respected

**Solutions**:
1. **CRITICAL**: Verify "I trust this provider" checkbox was checked when creating connector
2. **Disconnect and reconnect**: Settings → Remove connector → Re-add with "I trust this provider" checked
3. **Verify tool annotations**: Use MCP Inspector to check `readOnlyHint=true` in tool metadata:
   ```bash
   curl https://hansard-mcp-server-355dd2atrq-uc.a.run.app/mcp/tools/list
   ```
4. **Check ChatGPT settings**: Ensure Developer Mode trust settings are enabled
5. **Report to FastMCP**: If issue persists, this may be a ChatGPT platform bug

---

### Empty Results for Valid Queries

**Symptoms**:
- Query should return results (e.g., "housing" is a common topic)
- Server returns `{"speeches": [], "total_count": 0}`
- No error message, just empty results

**Solutions**:
1. **Check database populated**: `SELECT COUNT(*) FROM speeches;` (should be 64)
2. **Verify vector embeddings**: `SELECT COUNT(*) FROM speech_chunks;` (should be 500+)
3. **Test search locally**: Use MCP Inspector or direct API call to test search
4. **Check embedding generation**: Verify Vertex AI Embeddings API is working
5. **Review query phrasing**: Try alternative keywords ("housing affordability" vs "houses")
6. **Check date filters**: Verify dates are within dataset range (2024-05-28 onwards)

---

### "Speech not found" Error

**Symptoms**:
- Fetch tool returns `ValueError: Speech not found: <speech_id>`
- speech_id came from search results
- Error occurs despite valid-looking UUID

**Solutions**:
1. **Verify speech_id in database**: `SELECT id FROM speeches WHERE id = '<speech_id>';`
2. **Check UUID format**: Ensure speech_id is valid UUID4 format
3. **Test fetch locally**: Use MCP Inspector to test fetch_hansard_speech with same speech_id
4. **Check database connection**: Verify Cloud SQL connection is stable
5. **Review search results**: Confirm speech_id actually came from search response (not user-generated)

---

### Slow Response Times (>5 seconds)

**Symptoms**:
- Consistent delays >5 seconds for search or fetch
- Queries that should be fast are taking 10+ seconds
- Timeouts occurring

**Solutions**:
1. **Check Cloud Run logs**: Look for slow database queries
2. **Verify HNSW index**: `SELECT indexname FROM pg_indexes WHERE tablename = 'speech_chunks';`
3. **Check Cloud SQL performance**: Query times in database should be <1s
4. **Increase Cloud Run resources**: May need more CPU or memory allocation
5. **Monitor cold starts**: First request after idle will be 15-30s (expected)
6. **Check network latency**: Test from different locations

---

### Connection Timeout on First Request

**Symptoms**:
- First connection to MCP server times out after 30+ seconds
- "Could not reach server" error
- Subsequent retries may succeed

**Solutions**:
1. **Expected on cold start**: Cloud Run can take 15-30s to start instance
2. **Wait and retry**: Second attempt should succeed quickly
3. **Increase Cloud Run min instances**: Set to 1 to keep instance warm
4. **Check Cloud Run startup time**: Review logs for container startup duration
5. **Implement health check warmup**: Periodic keep-alive requests to prevent cold starts

---

## Completion Checklist

Use this checklist to ensure all testing is complete:

### Pre-Testing
- [ ] ChatGPT Pro/Team/Enterprise subscription verified
- [ ] Cloud Run service accessible (health check passed)
- [ ] Developer Mode enabled
- [ ] Testing report template ready
- [ ] Timer/stopwatch prepared

### Part 1: Connector Setup
- [ ] Test 1.1: Developer Mode enabled
- [ ] Test 1.2: Connector created and connection time measured
- [ ] Test 1.3: Tools verified in ChatGPT

### Part 2: Chat Mode Testing
- [ ] Test 2.1: Simple search without confirmation
- [ ] Test 2.2: Party filter test
- [ ] Test 2.3: Date range test
- [ ] Test 2.4: Search → Fetch workflow
- [ ] Test 2.5: Empty results handling
- [ ] Test 2.6: Tool preference (10 queries)

### Part 3: Deep Research Mode
- [ ] Test 3.1: Comprehensive policy analysis
- [ ] Test 3.2: Date range comparison
- [ ] Test 3.3: Multi-topic analysis

### Part 4: Performance Validation
- [ ] Test 4.1: Response time measurement (20 queries)
- [ ] Test 4.2: Cold start handling

### Part 5: Error Handling
- [ ] Test 5.1: Invalid speech ID
- [ ] Test 5.2: Invalid date format

### Part 6: Success Criteria Validation
- [ ] SC-001: Connection time verified
- [ ] SC-002: Search confirmation prompts = 0
- [ ] SC-003: Fetch confirmation prompts = 0
- [ ] SC-004: Tool preference ≥ 80%
- [ ] SC-005: Response times ≥ 95% < 5s
- [ ] SC-006: Deep Research quality verified
- [ ] SC-007: No authentication errors
- [ ] SC-008: User satisfaction ≥ 4/5

### Documentation
- [ ] Testing report completed
- [ ] Screenshots captured
- [ ] Issues documented
- [ ] Lessons learned recorded
- [ ] Recommendations for Phase 3 written

---

## Next Steps After Testing

Once all tests are complete and documented:

1. **Review Results**: Analyze all success criteria pass/fail status
2. **Document Issues**: Create detailed issue reports for any failures
3. **Update Specifications**: If tests reveal spec gaps, update spec.md
4. **Prepare for Phase 3**: Begin documentation finalization based on test results
5. **Share Report**: Distribute testing report to stakeholders
6. **Plan Improvements**: Prioritize enhancements based on test findings

---

## Appendix: Sample Queries for Additional Testing

### General Topic Queries
- "What has Simon Kennedy said about the economy?"
- "Find speeches on climate policy"
- "Show me discussions about education funding"
- "Search for speeches mentioning renewable energy"
- "What did Simon Kennedy say about healthcare?"

### Filtered Queries
- "Liberal Party speeches on tax reform"
- "House of Representatives speeches from June 2024"
- "Speeches about infrastructure after July 2024"
- "Find all speeches in the Senate chamber"

### Complex Research Queries
- "Analyze Simon Kennedy's evolving position on climate policy"
- "Compare speeches on economic policy before and after the May 2024 budget"
- "Identify Simon Kennedy's most frequently discussed topics with examples"
- "What are the key differences in Simon Kennedy's rhetoric on housing vs infrastructure?"

### Edge Cases
- "What did Simon Kennedy say about Antarctica?" (expected: no results)
- "Speeches by Malcolm Turnbull" (expected: dataset scope limitation explanation)
- "Speeches from 2010" (expected: date range limitation)
- "Find speeches in French" (expected: no results, English only)

---

**Total Tests**: 13 core tests + 7 success criteria validations
**Estimated Duration**: 6-8 hours
**Next Phase**: Phase 3 - Documentation Finalization

**END OF TESTING GUIDE**
