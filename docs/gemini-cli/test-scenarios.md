# Test Scenarios Guide

**Purpose**: Verify correct Gemini CLI + Hansard MCP setup with standardized test cases

**Goal**: 100% pass rate for all P1 tests confirms working configuration

**Coverage**: Both STDIO (local) and SSE (remote) transports

---

## Table of Contents

1. [Test Execution Guide](#test-execution-guide)
2. [Test 1: Tool Discovery](#test-1-tool-discovery)
3. [Test 2: Search Query Execution](#test-2-search-query-execution)
4. [Test 3: Fetch Speech by ID](#test-3-fetch-speech-by-id)
5. [Test 4: Ingest New Speech (Optional)](#test-4-ingest-new-speech-optional)
6. [Success Criteria](#success-criteria)

---

## Test Execution Guide

### Before You Begin

**Prerequisites**:
- Gemini CLI configured (STDIO or SSE)
- Database initialized and populated (for meaningful results)
- Gemini CLI running and connected

**Prerequisite Checks**:

```bash
# 1. Verify Gemini CLI is installed
gemini --version

# 2. Verify config exists
ls ~/.config/gemini-cli/config.json  # macOS/Linux
dir %APPDATA%\gemini-cli\config.json  # Windows

# 3. Start Gemini CLI
gemini

# 4. Verify database has data (STDIO only)
sqlite3 /path/to/data/hansard.db "SELECT COUNT(*) FROM speeches;"
```

---

### Recommended Test Order

Execute tests in this order for best results:

1. **Test 1** (Tool Discovery) - Confirms basic connectivity
2. **Test 2** (Search Query) - Confirms database access and search functionality
3. **Test 3** (Fetch by ID) - Confirms individual record retrieval
4. **Test 4** (Ingest) - Optional, local development only

**Estimated Time**: 20 minutes for core tests (1-3)

---

### Success Definition

**Minimum Success**: Tests 1 and 2 pass (Tool Discovery + Search Query)

**Full Success**: Tests 1, 2, and 3 pass

**Complete Success**: All tests pass including optional Test 4

---

## Test 1: Tool Discovery

**Priority**: P1 (Critical)

**Purpose**: Verify that Gemini CLI can discover and list the three Hansard MCP tools

**Transport**: Both STDIO and SSE

**Estimated Time**: 5 seconds

---

### Test Steps

**Step 1**: Open Gemini CLI

```bash
gemini
```

**Step 2**: Ask Gemini about available tools

**Primary Command**:
```
What MCP tools are available from the Hansard server?
```

**Alternative Commands**:
- "List all available Hansard tools"
- "Show me the Hansard MCP capabilities"
- "What can I do with the Hansard server?"

---

### Expected Response

Gemini should respond with a list of three tools and their descriptions:

```
Available Hansard tools:

1. hansard_search - Search Australian parliamentary speeches by keywords, speaker, date, or chamber
2. hansard_fetch - Retrieve full speech text and metadata by speech ID
3. hansard_ingest - Add new speeches to the database
```

**Note**: Exact wording may vary, but all three tool names must appear.

---

### Success Criteria

- [ ] Response includes tool name `hansard_search`
- [ ] Response includes tool name `hansard_fetch`
- [ ] Response includes tool name `hansard_ingest`
- [ ] Each tool has a description explaining its purpose
- [ ] No connection errors or timeout messages
- [ ] Response received within 5 seconds (30 seconds on cold start for SSE)

---

### Common Failures

**Failure 1: "No tools found" or "Server not available"**

**Diagnosis**:
```bash
# STDIO: Test server manually
cd /path/to/skai-fastmcp-cloudrun
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

# SSE: Test endpoint
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://YOUR-SERVICE-URL.a.run.app/health
```

**Solutions**:
- Verify config.json has correct hansard entry
- Check Gemini CLI logs: `~/.config/gemini-cli/logs/mcp.log`
- Restart Gemini CLI: `gemini restart`

See [troubleshooting.md - Connection Issues](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md#connection-issues)

---

**Failure 2: "Connection timeout"**

**Solutions**:
- Increase timeout in config: `"timeout": 60`
- Check network connectivity (SSE)
- Verify server starts successfully (STDIO)

See [troubleshooting.md - Connection Timeout](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md#issue-4-connection-timeout)

---

## Test 2: Search Query Execution

**Priority**: P1 (Critical)

**Purpose**: Verify that `hansard_search` tool executes successfully and returns speech results

**Transport**: Both STDIO and SSE

**Estimated Time**: 10 seconds (3-5 seconds after cold start)

---

### Test Steps

**Step 1**: Ensure database has data

**STDIO**:
```bash
sqlite3 /path/to/data/hansard.db "SELECT COUNT(*) FROM speeches;"
# Should return a number > 0
```

**SSE**: Data should be in Cloud SQL database (verify with deployment team)

If database is empty, load sample data:
```bash
cd /path/to/skai-fastmcp-cloudrun
python scripts/ingest_sample.py
```

---

**Step 2**: Execute search query in Gemini CLI

**Primary Command**:
```
Search Hansard for speeches about climate change policy
```

**Alternative Commands**:
- "Find parliamentary speeches discussing climate change"
- "Search for climate policy debates in Hansard"
- "Show me speeches about renewable energy"
- "Search Hansard for speeches about education"

---

### Expected Response

Gemini should execute `hansard_search` tool and return results with:

```
Found 3 speeches about climate change:

1. Speaker: Hon. Anthony Albanese MP
   Party: Australian Labor Party
   Date: 2023-09-15
   Chamber: House of Representatives
   Excerpt: "...our government is committed to climate action and reducing
            emissions by 43% by 2030..."

2. Speaker: Sen. Penny Wong
   Party: Australian Labor Party
   Date: 2023-08-22
   Chamber: Senate
   Excerpt: "...climate change is the defining challenge of our generation
            and we must act decisively..."

3. Speaker: Hon. Tanya Plibersek MP
   Party: Australian Labor Party
   Date: 2023-07-10
   Chamber: House of Representatives
   Excerpt: "...environmental protection and climate action go hand in hand..."
```

---

### Success Criteria

- [ ] At least 1 search result is returned
- [ ] Each result includes speaker name
- [ ] Each result includes speech date
- [ ] Each result includes chamber (House of Representatives or Senate)
- [ ] Each result includes text excerpt containing search terms
- [ ] No database errors or query failures
- [ ] Response received within 10 seconds

---

### Common Failures

**Failure 1: "Zero results returned"**

**Diagnosis**:
```bash
# Check database has speeches
sqlite3 /path/to/data/hansard.db "SELECT COUNT(*) FROM speeches;"

# Check speeches contain search terms
sqlite3 /path/to/data/hansard.db \
  "SELECT COUNT(*) FROM speeches WHERE content LIKE '%climate%';"
```

**Solutions**:
- Load sample data: `python scripts/ingest_sample.py`
- Try broader search query: "Search for any speeches"
- Verify database connection

See [troubleshooting.md - Data Issues](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md#data-issues)

---

**Failure 2: "Database error" or "Query execution failed"**

**Diagnosis**:
```bash
# Check database integrity
sqlite3 /path/to/data/hansard.db "PRAGMA integrity_check;"

# Check database is not locked
lsof /path/to/data/hansard.db
```

**Solutions**:
- Close other database connections
- Rebuild database if corrupted
- Check file permissions

See [troubleshooting.md - Query Execution Errors](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md#issue-13-query-execution-errors)

---

## Test 3: Fetch Speech by ID

**Priority**: P2 (High)

**Purpose**: Verify that `hansard_fetch` tool retrieves complete speech text by ID

**Transport**: Both STDIO and SSE

**Estimated Time**: 5 seconds

**Prerequisite**: Must complete Test 2 first to obtain a valid speech ID

---

### Test Steps

**Step 1**: Get a speech ID from Test 2 results

From the search results in Test 2, note one of the speech IDs. Speech IDs typically look like:
- `hansard-2023-09-15-reps-12345`
- `speech_12345`
- `12345`

**Example**: If Test 2 showed "Speech ID: hansard-2023-09-15-reps-12345", use that ID.

---

**Step 2**: Execute fetch query in Gemini CLI

**Primary Command** (replace [SPEECH_ID] with actual ID):
```
Fetch the full text of Hansard speech ID hansard-2023-09-15-reps-12345
```

**Alternative Commands**:
- "Get the complete transcript for speech [SPEECH_ID]"
- "Show me the full text of speech [SPEECH_ID]"
- "Retrieve Hansard speech [SPEECH_ID]"

---

### Expected Response

Gemini should execute `hansard_fetch` tool and return:

```
Speech ID: hansard-2023-09-15-reps-12345
Speaker: Hon. Anthony Albanese MP
Party: Australian Labor Party
Date: 2023-09-15 14:30:00
Chamber: House of Representatives
Location: Parliament House, Canberra

Full Text:
Mr. Speaker, I rise today to address this parliament on the critical issue
of climate change and our government's comprehensive plan to achieve net zero
emissions by 2050.

[Several paragraphs of complete speech text continue...]

As I have outlined, our plan for climate action is comprehensive, achievable,
and will position Australia as a leader in the clean energy transition.
I commend this approach to the House.

[End of speech]
```

---

### Success Criteria

- [ ] Response includes complete speech text (not just excerpt)
- [ ] Response includes speech_id matching the requested ID
- [ ] Response includes speaker name and party affiliation
- [ ] Response includes date and time of speech
- [ ] Response includes chamber (House or Senate)
- [ ] Speech text is significantly longer than search excerpt from Test 2
- [ ] No "speech not found" errors
- [ ] Response received within 5 seconds

---

### Common Failures

**Failure 1: "Speech not found" or "Invalid ID"**

**Diagnosis**:
```bash
# Verify speech ID exists in database
sqlite3 /path/to/data/hansard.db \
  "SELECT id, speaker FROM speeches WHERE id = 'SPEECH_ID';"
```

**Solutions**:
- Copy speech ID exactly from Test 2 results (case-sensitive)
- Try different speech ID from search results
- Verify database has speeches: `SELECT COUNT(*) FROM speeches;`

See [troubleshooting.md - Data Issues](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md#data-issues)

---

**Failure 2: "Partial text returned"**

**Diagnosis**: Some Gemini CLI versions may truncate long responses

**Solutions**:
- Ask for specific sections: "Show me the first paragraph"
- Export to file: "Save speech [ID] to file"
- Verify complete text is in database

---

## Test 4: Ingest New Speech (Optional)

**Priority**: P3 (Optional)

**Purpose**: Verify that `hansard_ingest` tool can add a new speech to the database

**Transport**: STDIO only (not recommended for SSE/production)

**Estimated Time**: 5 seconds

**Warning**: This test modifies the database. Only run on local development database.

---

### Test Steps

**Step 1**: Verify STDIO transport and local database

```bash
# Ensure using STDIO (not SSE)
grep -A5 '"hansard"' ~/.config/gemini-cli/config.json | grep -i transport

# Should NOT show "transport": "sse"
```

**If using SSE**, skip this test. Ingestion should be done server-side, not via Gemini CLI.

---

**Step 2**: Execute ingest command in Gemini CLI

**Primary Command**:
```
Ingest a test speech with speaker "John Doe", date "2023-10-23",
chamber "House", and text "This is a test speech about infrastructure funding
and renewable energy projects."
```

**Alternative Format** (JSON):
```
Ingest this speech into Hansard database:
{
  "speaker": "Jane Smith",
  "date": "2023-10-23",
  "chamber": "Senate",
  "party": "Independent",
  "content": "Test speech about education policy and funding."
}
```

---

### Expected Response

Gemini should execute `hansard_ingest` tool and return:

```
Successfully ingested speech into database.

Generated Speech ID: hansard-2023-10-23-house-test-67890

Speech Details:
- Speaker: John Doe
- Date: 2023-10-23
- Chamber: House of Representatives
- Content: This is a test speech about infrastructure funding...

You can now search for this speech or fetch it by ID.
```

---

### Success Criteria

- [ ] Response includes success message
- [ ] Response includes newly generated speech_id
- [ ] Subsequent search for "infrastructure funding" returns the new speech
- [ ] Can fetch new speech by ID using `hansard_fetch`
- [ ] Database record created successfully

---

### Verification

**Step 3**: Verify new speech was added

```bash
# Check database for new speech
sqlite3 /path/to/data/hansard.db \
  "SELECT id, speaker, date FROM speeches ORDER BY date DESC LIMIT 5;"

# Should show new speech at top
```

**Step 4**: Test search for new speech

In Gemini CLI:
```
Search Hansard for speeches about infrastructure funding
```

New speech should appear in results.

---

### Common Failures

**Failure 1: "Permission denied" or "Database locked"**

**Solutions**:
- Verify using STDIO (not SSE)
- Check DANGEROUSLY_OMIT_AUTH is set
- Close other database connections
- Check file permissions: `ls -l /path/to/data/hansard.db`

See [troubleshooting.md - Authentication Issues](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md#authentication-issues)

---

**Failure 2: "Invalid speech format"**

**Solutions**:
- Include all required fields: speaker, date, chamber, content
- Use valid date format: YYYY-MM-DD
- Use valid chamber: "House" or "Senate"

---

## Success Criteria

### Minimum Success (MVP)

**Required Tests**: Test 1 + Test 2

This confirms:
- Gemini CLI can connect to Hansard MCP server
- Tools are discoverable
- Search functionality works
- Database is accessible

**Action if failed**: Review [troubleshooting.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md) and setup guides.

---

### Full Success (Production Ready)

**Required Tests**: Test 1 + Test 2 + Test 3

This confirms:
- Complete CRUD operations (search and fetch)
- Individual record retrieval works
- System ready for production use

**Action if failed**: Check data integrity and ID format.

---

### Complete Success (All Features)

**Required Tests**: Test 1 + Test 2 + Test 3 + Test 4

This confirms:
- Full feature set working
- Write operations successful (local only)
- System fully validated

**Note**: Test 4 is optional and only applies to STDIO transport.

---

## Test Matrix

| Test | Transport | Priority | Time | Database Required |
|------|-----------|----------|------|-------------------|
| 1. Tool Discovery | STDIO, SSE | P1 | 5s | No |
| 2. Search Query | STDIO, SSE | P1 | 10s | Yes |
| 3. Fetch by ID | STDIO, SSE | P2 | 5s | Yes |
| 4. Ingest Speech | STDIO only | P3 | 5s | Yes (writable) |

---

## Troubleshooting Test Failures

### All Tests Fail

**Issue**: Cannot connect to server at all

**Solutions**:
1. Verify config.json is correct
2. Check Gemini CLI logs
3. Test server manually (see setup guides)
4. Restart Gemini CLI

See [troubleshooting.md - Connection Issues](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md#connection-issues)

---

### Test 1 Passes, Test 2 Fails

**Issue**: Connection works but queries fail

**Solutions**:
1. Check database is initialized
2. Verify database has data
3. Check database permissions
4. Try simpler search query

See [troubleshooting.md - Data Issues](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md#data-issues)

---

### Tests 1-2 Pass, Test 3 Fails

**Issue**: Search works but fetch fails

**Solutions**:
1. Verify speech ID format is correct
2. Copy ID exactly from Test 2 results
3. Try different speech ID
4. Check database record exists

See [troubleshooting.md - Query Execution Errors](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md#issue-13-query-execution-errors)

---

## Next Steps

### After Successful Tests

1. **Production Use**: Start using Hansard tools in Gemini CLI for real queries
2. **Team Rollout**: Share configuration with team members
3. **Automation**: Set up token refresh (SSE) or data updates (STDIO)

---

### If Tests Fail

1. **Review Logs**: Check Gemini CLI and server logs for errors
2. **Consult Troubleshooting**: [troubleshooting.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md)
3. **Verify Setup**: Re-follow setup guides:
   - [stdio-setup.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/stdio-setup.md)
   - [sse-setup.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/sse-setup.md)

---

## Test Scenarios JSON

**Complete Test Definitions**: [examples/test-scenarios.json](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/test-scenarios.json)

This JSON file contains detailed test specifications including:
- Expected outputs
- Alternative commands
- Failure debugging steps
- Platform-specific notes

---

**Last Updated**: 2025-10-23

**Feature**: 009-gemini-cli-integration

**User Story**: US3 - Comprehensive Setup Documentation
