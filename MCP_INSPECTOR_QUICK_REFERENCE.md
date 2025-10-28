# FastMCP Inspector Quick Reference Guide

**Purpose**: Review, test, and validate MCP server tools  
**Status**: ✅ Verified & Working  
**Version**: FastMCP 2.12.5, MCP 1.16.0  

---

## Quick Start: Loading the MCP Inspector

### Step 1: Navigate to Project
```bash
cd /home/user/skai-fastmcp-cloudrun
```

### Step 2: Reload Inspector (Dev Mode)
```bash
# Start the MCP inspector with dev server
DANGEROUSLY_OMIT_AUTH=true uv run fastmcp dev src/server.py
```

**Output** (expected):
```
⚠️  WARNING: Authentication DISABLED (DANGEROUSLY_OMIT_AUTH=true)
✅ Hansard MCP Server initialized with ChatGPT Developer Mode enhancements
   🔍 search_hansard_speeches [read-only]
   📄 fetch_hansard_speech [read-only]
   📝 ingest_hansard_speech [write operation with progress reporting]
```

### Step 3: Access Inspector UI
- Opens automatically at: `http://localhost:5173`
- Browse tools and test them
- Hot-reload enabled for code changes

---

## Alternative: Inspect Without UI

### Just Review Tool Configuration
```bash
DANGEROUSLY_OMIT_AUTH=true uv run fastmcp inspect src/server.py
```

**Output**:
```
Server
  Name:         Hansard MCP Server
  Generation:   2

Components
  Tools:        3
  Prompts:      0
  Resources:    0
  Templates:    0
```

### Full JSON Output (MCP Format)
```bash
DANGEROUSLY_OMIT_AUTH=true uv run fastmcp inspect src/server.py --format mcp
```

### Full JSON Output (FastMCP Format)
```bash
DANGEROUSLY_OMIT_AUTH=true uv run fastmcp inspect src/server.py --format fastmcp
```

---

## Available Tools in Inspector

### 1. search_hansard_speeches

**Type**: Read-only search function

**Parameters**:
- `query` (string, required): Search terms
- `party` (optional): Liberal, Labor, Greens, National, Independent
- `chamber` (optional): REPS or SENATE
- `start_date` (optional): ISO 8601 date (YYYY-MM-DD)
- `end_date` (optional): ISO 8601 date (YYYY-MM-DD)
- `limit` (1-100, default 10): Max results

**Example**:
```json
{
  "query": "climate policy",
  "party": "Liberal",
  "limit": 5
}
```

**Returns**: Array of speech objects with metadata

---

### 2. fetch_hansard_speech

**Type**: Read-only fetch function

**Parameters**:
- `speech_id` (UUID, required): ID from search results

**Example**:
```json
{
  "speech_id": "d9c697e9-e13d-4769-9fbe-ce6cb18f4700"
}
```

**Returns**: Complete speech with full content

---

### 3. ingest_hansard_speech

**Type**: Write operation (modifies database)

**Parameters**:
- Speech data in required format

**Example**:
```json
{
  "speaker": "Simon Kennedy",
  "date": "2025-10-29",
  "content": "Speech text here...",
  "party": "Liberal",
  "chamber": "REPS",
  "topics": ["housing", "immigration"]
}
```

**Returns**: Ingestion confirmation with statistics

---

## Common Inspector Tasks

### Test a Tool
1. Click on tool in inspector
2. Fill in parameters
3. Click "Execute" or "Test"
4. View results

### Check Tool Documentation
1. Inspector shows full tool description
2. Parameters are documented
3. Return type shown
4. Annotations displayed

### Verify Tool Annotations
Look for:
- `readOnlyHint`: Tool doesn't modify data
- `destructiveHint`: Tool changes state
- `idempotentHint`: Safe to retry
- `openWorldHint`: Can handle any input

### Test Error Handling
- Try invalid parameters
- Test missing required fields
- Try non-existent IDs
- Check error messages

### Monitor Performance
- Response time shown
- Database query time tracked
- Memory usage monitored
- Success/failure recorded

---

## Troubleshooting

### Problem: "Authentication DISABLED" Warning
**Cause**: Using DANGEROUSLY_OMIT_AUTH for local dev  
**Solution**: Expected behavior, only for development  
**Production**: OAuth is enforced at https://mcp.simonkennedymp.com.au

### Problem: "Inspector failed to start"
**Cause**: OAuth configuration requires HTTPS  
**Solution**: Use `DANGEROUSLY_OMIT_AUTH=true` flag

### Problem: Database connection errors
**Cause**: Cloud SQL not initialized  
**Solution**: Expected in dev - system shows warnings but continues  
**Note**: Tools will fail at runtime but inspector still loads

### Problem: Tools not showing
**Cause**: Server didn't load properly  
**Solution**: Check console output for errors, restart

### Problem: Changes not reflected
**Cause**: Dev mode not hot-reloading  
**Solution**: Restart the inspector or use inspect command

---

## Development Workflow

### 1. Make Code Changes
Edit tool implementation files:
- `src/tools/search.py`
- `src/tools/fetch.py`
- `src/tools/ingest.py`

### 2. Reload Inspector
```bash
# Dev mode auto-reloads or manually restart
DANGEROUSLY_OMIT_AUTH=true uv run fastmcp dev src/server.py
```

### 3. Test Changes
- Use inspector UI to test
- Or use fastmcp inspect command

### 4. Check Logs
Look for:
- ✅ Tool registered
- ⚠️ Warnings (expected for DB in dev)
- ❌ Errors (need to fix)

### 5. Commit Changes
```bash
git add src/tools/
git commit -m "feat: Update tool implementation"
```

---

## Performance Optimization

### Monitor Response Times
1. Open inspector
2. Execute tool
3. Check response time shown
4. Target: < 1 second for most operations

### Database Connection Pooling
- Pre-initialized on server startup
- Check logs for "Vector store initialized"
- Check logs for "Metadata store initialized"

### Vector Search Performance
- Embeddings cached in Cloud SQL
- 768-dimensional Vertex AI embeddings
- pgvector indexes optimized

---

## Best Practices

✅ **DO**:
- Use inspector to test tools before deploying
- Check tool parameters are correctly validated
- Verify return values match documentation
- Monitor performance metrics
- Test error scenarios

❌ **DON'T**:
- Leave DANGEROUSLY_OMIT_AUTH=true in production
- Test with real production data in dev
- Ignore error messages
- Skip documentation updates
- Deploy without testing

---

## Feature 018 Documentation Improvements

### Current State (0.39/1.00)
- Tool descriptions: ✅ Present
- Parameters: ✅ Documented
- Returns: ⚠️ Basic (needs detail)

### Target State (0.80/1.00)
- Tool descriptions: Enhanced with examples
- Parameters: Validated with constraints
- Returns: Complete schemas documented
- Error cases: All documented
- Performance: Baselines documented

### Phase 1: Documentation (This Week)
1. Add complete Returns section to each tool
2. Document all possible error conditions
3. Add example requests/responses
4. Performance expectations

### Phase 2: Testing (Next Week)
1. Async test framework improvements
2. Error scenario testing
3. Data quality validation

### Phase 3: Monitoring (Week After)
1. Compliance dashboard
2. Automated scoring
3. Performance tracking

---

## Related Files

### Inspector Output
- **Review Document**: `FASTMCP_DOCUMENTATION_REVIEW.md`
- **Inspector Results**: Recent run shows all tools verified

### Tool Implementation
- `src/tools/search.py` - Search implementation
- `src/tools/fetch.py` - Fetch implementation
- `src/tools/ingest.py` - Ingest implementation

### Configuration
- `src/server.py` - Server setup and tool registration
- `pyproject.toml` - FastMCP version and dependencies
- `cloudbuild.yaml` - Production deployment config

### Specification
- `specs/018-mcp-tools-quality-improvements/` - Feature roadmap

---

## Command Reference

### Start Inspector
```bash
DANGEROUSLY_OMIT_AUTH=true uv run fastmcp dev src/server.py
```

### Inspect Without UI
```bash
DANGEROUSLY_OMIT_AUTH=true uv run fastmcp inspect src/server.py
```

### Get Full JSON
```bash
DANGEROUSLY_OMIT_AUTH=true uv run fastmcp inspect src/server.py --format mcp
```

### Check Version
```bash
uv run fastmcp version
```

### Stop Server
```bash
Ctrl+C in terminal
```

---

## Success Indicators

✅ **Inspector Loaded**:
- No errors on startup
- All 3 tools listed
- Can execute tools

✅ **Tools Working**:
- search_hansard_speeches returns results
- fetch_hansard_speech returns full speech
- ingest_hansard_speech accepts data

✅ **Documentation Complete**:
- All parameters documented
- Returns documented
- Examples provided

✅ **Production Ready**:
- OAuth enforced at custom domain
- Tools accessible with auth token
- Performance meets targets

---

## Next Steps

1. ✅ Load inspector and verify tools
2. ⏳ Review tool documentation (Feature 018 Phase 1)
3. ⏳ Enhance Returns documentation
4. ⏳ Add example requests/responses
5. ⏳ Build compliance dashboard (Phase 3)

---

**Status**: ✅ Inspector Verified & Ready  
**FastMCP Version**: 2.12.5  
**Tools**: 3/3 Registered  
**Feature 018**: Ready for Phase 1 Implementation  

---

**Quick Commands**:
```bash
# Reload inspector
DANGEROUSLY_OMIT_AUTH=true uv run fastmcp dev src/server.py

# Just inspect
DANGEROUSLY_OMIT_AUTH=true uv run fastmcp inspect src/server.py

# Get JSON
DANGEROUSLY_OMIT_AUTH=true uv run fastmcp inspect src/server.py --format mcp
```
