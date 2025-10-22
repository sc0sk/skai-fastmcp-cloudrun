# Quickstart: ChatGPT Developer Mode Enhancements

**Feature**: ChatGPT Developer Mode Enhancements
**Branch**: `001-chatgpt-devmode-enhancements`
**Date**: 2025-10-22

## Prerequisites

- Python 3.11+
- `uv` package manager installed
- FastMCP 2.14.0+ (already in project)
- Git repository cloned and on feature branch
- PostgreSQL Cloud SQL database (already configured)

## Local Development Setup

### 1. Checkout Feature Branch

```bash
git checkout 001-chatgpt-devmode-enhancements
```

### 2. Verify Dependencies

No new dependencies required. FastMCP 2.14.0+ already supports all needed features.

```bash
# Verify FastMCP version
uv pip list | grep fastmcp
# Should show: fastmcp 2.14.0 or higher
```

### 3. Run Development Server

```bash
# Start server with OAuth bypass (local testing)
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

# Server starts on http://localhost:8000
# MCP endpoint: http://localhost:8000/mcp/
```

### 4. Verify Tool Metadata with MCP Inspector

```bash
# In a new terminal, start MCP Inspector
npx @modelcontextprotocol/inspector

# Or use mcp-cli to inspect tools
npx -y mcp-cli sse http://localhost:8000/sse
```

**Expected output for search tool**:
```json
{
  "name": "search_hansard_speeches",
  "description": "Search Simon Kennedy's parliamentary speeches...\n\nUse this when: ...",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": { "type": "string", ... },
      "party": {
        "type": "string",
        "enum": ["Liberal", "Labor", "Greens", "National", "Independent"]
      },
      "chamber": {
        "type": "string",
        "enum": ["House of Representatives", "Senate"]
      },
      ...
    }
  },
  "annotations": {
    "readOnly": true
  }
}
```

## Testing

### Unit Tests

Test tool metadata and parameter validation:

```bash
# Run unit tests for tool metadata
pytest tests/unit/test_tool_metadata.py -v

# Expected tests:
# - test_search_tool_has_readonly_hint
# - test_fetch_tool_has_readonly_hint
# - test_ingest_tool_no_readonly_hint
# - test_party_enum_values
# - test_chamber_enum_values
# - test_date_parameter_validation
```

### Integration Tests

Test MCP protocol serialization:

```bash
# Run integration tests
pytest tests/integration/test_chatgpt_integration.py -v

# Expected tests:
# - test_tool_annotations_in_protocol
# - test_parameter_enums_serialization
# - test_description_formatting
```

### Manual Testing with ChatGPT

1. **Deploy to Cloud Run** (or use ngrok for local testing):
```bash
# Option A: Deploy to Cloud Run
gcloud run deploy hansard-mcp-server --image=gcr.io/PROJECT_ID/hansard-mcp:latest

# Option B: Expose local server with ngrok
ngrok http 8000
```

2. **Configure ChatGPT Developer Mode**:
   - Go to ChatGPT settings → Connectors
   - Add MCP connector with your server URL
   - Complete GitHub OAuth flow

3. **Test tool selection**:
   - Ask: "Find Simon Kennedy's speeches about housing"
   - **Expected**: ChatGPT uses `search_hansard_speeches` tool (not built-in browsing)
   - **Expected**: No confirmation prompt (recognizes `readOnlyHint`)

4. **Test parameter accuracy**:
   - Ask: "Find Labor party speeches from July 2024"
   - **Expected**: Tool call uses `party="Labor"` (exact enum value)
   - **Expected**: Date format is `2024-07-01` (ISO 8601)

## Implementation Checklist

### Phase 1: Enhance Search Tool

- [ ] Add `PartyEnum` and `ChamberEnum` type definitions
- [ ] Update `search_hansard_speeches` function signature with enum parameters
- [ ] Add `@mcp.tool(readOnlyHint=True, icon="🔍")` decorator
- [ ] Enhance description with "Use this when..." guidance
- [ ] Add Pydantic `Field` annotations for date parameters
- [ ] Write unit tests for metadata

### Phase 2: Enhance Fetch Tool

- [ ] Add `@mcp.tool(readOnlyHint=True, icon="📄")` decorator
- [ ] Enhance description with workflow guidance
- [ ] Write unit tests for metadata

### Phase 3: Enhance Ingest Tool

- [ ] Add `@mcp.tool(icon="📝")` decorator (NO `readOnlyHint` - write operation)
- [ ] Enhance description (keep as admin-focused)
- [ ] Write unit tests for metadata

### Phase 4: Integration Testing

- [ ] Test with MCP Inspector (verify protocol serialization)
- [ ] Test with Claude Desktop (verify backward compatibility)
- [ ] Test with ChatGPT Developer Mode (verify `readOnlyHint` recognition)

### Phase 5: Deployment

- [ ] Build Docker image: `docker build -t gcr.io/PROJECT_ID/hansard-mcp:v004 .`
- [ ] Push to GCR: `docker push gcr.io/PROJECT_ID/hansard-mcp:v004`
- [ ] Deploy to Cloud Run: `gcloud run deploy hansard-mcp-server --image=...`
- [ ] Test production deployment with ChatGPT

## Troubleshooting

### Tool metadata not showing in MCP Inspector

**Problem**: Annotations or icons don't appear in tool list

**Solution**:
1. Verify FastMCP version: `uv pip list | grep fastmcp` (must be 2.14.0+)
2. Check tool decorator syntax: `@mcp.tool(readOnlyHint=True, icon="🔍")`
3. Restart dev server: `DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py`

### ChatGPT shows confirmation prompt for read-only tools

**Problem**: ChatGPT asks "Are you sure?" before calling search tool

**Solution**:
1. Verify `readOnlyHint=True` in decorator
2. Check MCP protocol output: `mcp-cli tools list | jq '.tools[] | .annotations'`
3. Confirm annotation serializes as `"readOnly": true` (not `"readOnlyHint"`)
4. Test with latest ChatGPT (older versions may not respect annotations)

### Parameter validation errors

**Problem**: ChatGPT sends invalid party names (e.g., "Labour" instead of "Labor")

**Solution**:
1. Verify enum definition: `PartyEnum = Literal["Liberal", "Labor", ...]`
2. Check parameter description mentions enum values
3. Verify Pydantic validates parameters (add unit test)
4. Improve tool description to be more explicit about exact values

### GPT-5 uses built-in browsing instead of MCP tools

**Problem**: ChatGPT searches web instead of using MCP search tool

**Solution**:
1. Strengthen "Do not use" guidance in description
2. Add more explicit "Use this when" scenarios
3. Verify tool description is comprehensive (GPT-5 reads full description)
4. Test with different phrasings (e.g., "Use the Hansard connector")

## Common Commands

```bash
# Start dev server (local testing, no auth)
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

# Start dev server (with GitHub OAuth)
PORT=8080 fastmcp dev src/server.py

# Run all tests
pytest tests/ -v --cov=src --cov-report=term-missing

# Run only metadata tests
pytest tests/unit/test_tool_metadata.py -v

# Inspect tools via MCP CLI
npx -y mcp-cli sse http://localhost:8000/sse

# Build and deploy
docker build -t gcr.io/PROJECT_ID/hansard-mcp:v004 .
docker push gcr.io/PROJECT_ID/hansard-mcp:v004
gcloud run deploy hansard-mcp-server --image=gcr.io/PROJECT_ID/hansard-mcp:v004
```

## Next Steps

After implementing this feature:

1. **Update CLAUDE.md**: Add ChatGPT Developer Mode optimization to active technologies
2. **Update README**: Document new tool annotations and parameter enums
3. **Create PR**: Merge feature branch to main with comprehensive description
4. **Monitor ChatGPT usage**: Check Cloud Run logs for tool usage patterns

## References

- [Feature Specification](spec.md)
- [Implementation Plan](plan.md)
- [Research Notes](research.md)
- [Data Model](data-model.md)
- [Tool Contracts](contracts/)
- [FastMCP Tool Annotations](https://docs.fastmcp.com/concepts/tools#annotations)
- [GPT-5 Documentation](https://platform.openai.com/docs/guides/latest-model)
- [MCP Specification](https://modelcontextprotocol.io/)
