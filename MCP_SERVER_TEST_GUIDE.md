# MCP Server Testing Guide

**Server URL:** https://mcp.simonkennedymp.com.au  
**Custom Domain:** mcp.simonkennedymp.com.au  
**Testing Date:** October 31, 2025  
**Latest Revision:** hansard-mcp-server-00092-q77

---

## Deployment Status

✅ **IAM Authentication Enabled**
- `USE_IAM_AUTH=true` set on Cloud Run service
- Service Account: `666924716777-compute@developer.gserviceaccount.com`
- IAM Roles: 
  - ✅ `roles/cloudsql.client`
  - ✅ `roles/cloudsql.instanceUser`

✅ **Code Changes Deployed**
- Vector store enforces IAM DB auth
- Cloud SQL connector uses boolean `enable_iam_auth=True`
- Password env vars no longer passed when IAM mode active

---

## Why Claude CLI Cannot Test Directly

The Hansard MCP server implements **OAuth 2.0 authentication via GitHub** using the FastMCP OAuth proxy. This requires:

1. **Browser-based OAuth flow** - User must authorize via GitHub
2. **OAuth tokens** - Access tokens issued after authorization
3. **Session management** - Tokens must be included in requests

**Claude CLI limitations:**
- Does not support OAuth 2.0 flows for MCP servers
- Cannot authenticate with GitHub and obtain tokens
- Expects stdio or SSE transport without authentication

**Solution:** Use **MCP Inspector** (browser-based UI with OAuth support)

---

## Testing via MCP Inspector (Recommended)

### Step 1: Open MCP Inspector

**Option A: Cloudflare Inspector**
```
https://inspector.cloudflare-mcp.com/?url=https://mcp.simonkennedymp.com.au
```

**Option B: Local Inspector**
```bash
npx @modelcontextprotocol/inspector https://mcp.simonkennedymp.com.au
```

### Step 2: Authenticate via OAuth

1. Inspector will detect OAuth requirement
2. Click "Authorize" or "Connect"
3. Redirected to GitHub OAuth page
4. Authorize the application
5. Redirected back to Inspector with valid token

### Step 3: Test Each Tool

Once connected, test the following tools in order:

#### 1. `get_database_stats`
**Purpose:** Get overview of database contents  
**Parameters:** None required  
**Expected Output:**
```json
{
  "speech_count": <number>,
  "unique_speakers": <number>,
  "earliest_date": "YYYY-MM-DD",
  "latest_date": "YYYY-MM-DD",
  "party_breakdown": { ... }
}
```

**Test Command in Inspector:**
```json
{
  "tool": "get_database_stats",
  "arguments": {}
}
```

**Success Criteria:**
- ✅ Returns statistics without errors
- ✅ No "control characters forbidden" error
- ✅ Logs show "Vector store using IAM DB authentication"

---

#### 2. `search_speeches_by_metadata`
**Purpose:** Search speeches by speaker, party, chamber, date range  
**Parameters:**
- `speaker` (optional): Speaker name (case-insensitive partial match)
- `party` (optional): Political party
- `chamber` (optional): "REPS" or "SENATE"
- `date_from` (optional): ISO date string
- `date_to` (optional): ISO date string
- `limit` (optional): Max results (default: 50)

**Test Command in Inspector:**
```json
{
  "tool": "search_speeches_by_metadata",
  "arguments": {
    "speaker": "minister",
    "limit": 5
  }
}
```

**Expected Output:**
```json
[
  {
    "speech_id": "...",
    "title": "...",
    "speaker": "...",
    "party": "...",
    "chamber": "...",
    "date": "...",
    ...
  }
]
```

**Success Criteria:**
- ✅ Returns matching speeches
- ✅ No database connection errors

---

#### 3. `search_hansard_speeches`
**Purpose:** Semantic vector search across speech text  
**Parameters:**
- `query` (required): Natural language search query
- `k` (optional): Number of results (default: 10)
- `speaker_filter` (optional): Filter by speaker name
- `party_filter` (optional): Filter by party
- `chamber_filter` (optional): Filter by chamber
- `date_from_filter` (optional): Filter by date range start
- `date_to_filter` (optional): Filter by date range end

**Test Command in Inspector:**
```json
{
  "tool": "search_hansard_speeches",
  "arguments": {
    "query": "climate change policy",
    "k": 5
  }
}
```

**Expected Output:**
```json
[
  {
    "chunk_text": "...",
    "score": 0.85,
    "metadata": {
      "speaker": "...",
      "party": "...",
      "chamber": "...",
      "date": "...",
      "speech_id": "..."
    }
  }
]
```

**Success Criteria:**
- ✅ Returns semantically relevant results
- ✅ No "Failed to create vector extension" error
- ✅ No "control characters forbidden" error
- ✅ Similarity scores between 0.0 and 1.0

---

#### 4. `get_speech_by_id`
**Purpose:** Retrieve full speech details by ID  
**Parameters:**
- `speech_id` (required): Speech identifier (integer or string)

**Test Command in Inspector:**
```json
{
  "tool": "get_speech_by_id",
  "arguments": {
    "speech_id": "1"
  }
}
```

**Expected Output:**
```json
{
  "speech_id": "1",
  "title": "...",
  "full_text": "...",
  "speaker": "...",
  "party": "...",
  "chamber": "...",
  "date": "...",
  "hansard_reference": "...",
  ...
}
```

**Success Criteria:**
- ✅ Returns complete speech object
- ✅ All fields populated correctly

---

#### 5. `ingest_markdown_file`
**Purpose:** Parse and ingest Hansard markdown files into database  
**Parameters:**
- `file_path` (required): Path to markdown file
- `source_url` (optional): Source URL for attribution

**Test Command in Inspector:**
```json
{
  "tool": "ingest_markdown_file",
  "arguments": {
    "file_path": "/path/to/hansard.md",
    "source_url": "https://example.com/hansard.md"
  }
}
```

**Expected Output:**
```json
{
  "speeches_processed": 5,
  "speeches_ingested": 5,
  "speeches_skipped": 0,
  "errors": []
}
```

**Success Criteria:**
- ✅ Processes markdown correctly
- ✅ Creates speech records in database
- ✅ Creates vector embeddings
- ✅ No duplicate detection issues

---

#### 6. `bulk_ingest_markdown_files`
**Purpose:** Ingest multiple markdown files using glob patterns  
**Parameters:**
- `directory` (required): Base directory path
- `pattern` (required): Glob pattern (e.g., "*.md", "**/*.md")
- `recursive` (optional): Search subdirectories (default: false)

**Test Command in Inspector:**
```json
{
  "tool": "bulk_ingest_markdown_files",
  "arguments": {
    "directory": "/data/hansard",
    "pattern": "*.md",
    "recursive": true
  }
}
```

**Expected Output:**
```json
{
  "files_processed": 10,
  "total_speeches_ingested": 50,
  "total_speeches_skipped": 5,
  "files_with_errors": 0,
  "processing_time_seconds": 45.2
}
```

**Success Criteria:**
- ✅ Finds all matching files
- ✅ Processes each file successfully
- ✅ Reports accurate statistics

---

## Verification Checklist

### OAuth & Connectivity
- [ ] MCP Inspector successfully connects to server
- [ ] GitHub OAuth flow completes without errors
- [ ] Valid access token obtained
- [ ] Server responds to authenticated requests

### Database Authentication (IAM)
- [ ] No "control characters forbidden" errors
- [ ] No "invalid-encoding" errors
- [ ] Logs show "Vector store using IAM DB authentication"
- [ ] No password authentication fallback

### Tools Functionality
- [ ] `get_database_stats` - Returns statistics
- [ ] `search_speeches_by_metadata` - Returns filtered results
- [ ] `search_hansard_speeches` - Semantic search works
- [ ] `get_speech_by_id` - Retrieves full speech
- [ ] `ingest_markdown_file` - Ingests single file
- [ ] `bulk_ingest_markdown_files` - Ingests multiple files

### Performance
- [ ] Tool responses complete within 30 seconds
- [ ] Vector search returns results in < 5 seconds
- [ ] No timeout errors
- [ ] No connection pool exhaustion

### Error Handling
- [ ] Invalid parameters return clear error messages
- [ ] Missing required parameters are detected
- [ ] Database errors are caught and reported
- [ ] OAuth errors provide helpful guidance

---

## Checking Logs

### View Cloud Run Logs
```bash
gcloud run services logs read hansard-mcp-server \
  --region us-central1 \
  --project skai-fastmcp-cloudrun \
  --limit 50
```

### Filter for IAM Auth Messages
```bash
gcloud run services logs read hansard-mcp-server \
  --region us-central1 \
  --project skai-fastmcp-cloudrun \
  --limit 100 \
  | grep -i "IAM\|authentication\|vector store"
```

### Look for Errors
```bash
gcloud run services logs read hansard-mcp-server \
  --region us-central1 \
  --project skai-fastmcp-cloudrun \
  --limit 100 \
  | grep -i "error\|exception\|failed"
```

---

## Expected Log Messages (Success)

When tools are called successfully, you should see:

```
INFO: Vector store using IAM DB authentication via Cloud SQL Connector
INFO: Similarity search query: climate change policy, k=5
INFO: Found 5 matching chunks
```

**No errors related to:**
- ❌ "control characters forbidden"
- ❌ "invalid-encoding"
- ❌ "password authentication failed"
- ❌ "Failed to create vector extension"

---

## Troubleshooting

### Issue: "control characters forbidden: invalid-encoding"
**Status:** ✅ FIXED (as of revision 00092-q77)  
**Solution:** IAM authentication now enforced; password credentials not used

### Issue: "Failed to create vector extension"
**Possible Causes:**
1. pgvector extension not installed in database
2. IAM user lacks CREATE EXTENSION privilege

**Solution:**
```bash
# Enable pgvector as postgres superuser
export POSTGRES_PASSWORD="your-postgres-password"
python3 enable_pgvector_postgres.py
```

### Issue: OAuth authentication fails
**Possible Causes:**
1. GitHub OAuth app not properly configured
2. Callback URL mismatch
3. Client credentials invalid

**Solution:**
1. Check GitHub OAuth app settings
2. Verify callback URL: `https://mcp.simonkennedymp.com.au/oauth/callback`
3. Verify client ID/secret in Cloud Run secrets

### Issue: Tool timeouts
**Possible Causes:**
1. Database connection pool exhausted
2. Long-running vector search queries
3. Cold start delay

**Solution:**
1. Check database connection settings
2. Reduce `k` parameter in vector searches
3. Wait for service warm-up (first request may be slow)

---

## Alternative Testing Methods

### Using curl (Basic Connectivity Only)

Test OAuth endpoints (no authentication required):
```bash
# OAuth metadata
curl -s https://mcp.simonkennedymp.com.au/.well-known/oauth-authorization-server | jq

# Protected resource metadata
curl -s https://mcp.simonkennedymp.com.au/.well-known/oauth-protected-resource | jq

# Health check (if available)
curl -s https://mcp.simonkennedymp.com.au/health
```

### Using MCP Python Client (Advanced)

For automated testing, use the FastMCP Python client with OAuth:
```python
from fastmcp import FastMCP
# Note: Requires implementing OAuth token acquisition flow
# See test_mcp_prod_tools.py for reference
```

---

## Next Steps After Testing

1. **If all tests pass:**
   - ✅ Mark deployment as production-ready
   - ✅ Update documentation with confirmed functionality
   - ✅ Remove password env vars: `./tools/remove_db_password_envs.sh`

2. **If vector search fails:**
   - Run `enable_pgvector_postgres.py` to enable extension
   - Verify IAM user has database privileges
   - Check logs for specific error messages

3. **If OAuth issues persist:**
   - Review GitHub OAuth app configuration
   - Verify callback URLs match exactly
   - Check client credentials in secrets

---

## Documentation References

- **IAM Auth Fix Summary:** `IAM_AUTH_FIX_SUMMARY.md`
- **Deployment Guide:** `DEPLOYMENT_GUIDE.md`
- **FastMCP Documentation:** https://github.com/jlowin/fastmcp
- **MCP Protocol Spec:** https://modelcontextprotocol.io/

---

## Contact & Support

For issues or questions:
- Check logs: `gcloud run services logs read hansard-mcp-server`
- Review error messages in MCP Inspector
- Consult `IAM_AUTH_FIX_SUMMARY.md` for troubleshooting steps
