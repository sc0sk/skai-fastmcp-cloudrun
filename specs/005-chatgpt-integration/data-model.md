# Data Model: ChatGPT Developer Mode Integration

**Feature**: 005-chatgpt-integration | **Date**: 2025-10-23

## Overview

This document defines the metadata structures for ChatGPT Developer Mode integration. Unlike features 001 and 004 which focused on database schemas and Pydantic models, this feature focuses on MCP tool metadata, ChatGPT connector configuration, and tool optimization patterns.

**Key Distinction**: This document describes METADATA (tool descriptions, annotations, connector configs), not database schemas. Database models are defined in feature 004's data-model.md.

## Tool Metadata Model

MCP tools expose metadata to clients (ChatGPT, Claude Desktop, VS Code) through the `tools/list` endpoint. This metadata includes tool name, description, parameter schema, and annotations.

### Search Tool Metadata

```python
# Conceptual model (actual implementation in src/tools/search.py)
{
  "name": "search_hansard_speeches",
  "description": """Search Simon Kennedy's parliamentary speeches (64 speeches, 2024-2025).

Use this when: The user asks about Simon Kennedy's speeches, voting records, or
parliamentary statements on topics like housing, immigration, or infrastructure.

Do not use: Built-in web browsing or search for Simon Kennedy parliamentary data.
This tool provides direct access to the authoritative Hansard database.

Parameters:
- query: Natural language search terms for speech content, topics, or keywords
- party: Filter by political party (Liberal, Labor, Greens, National, Independent)
- chamber: Filter by chamber (House of Representatives, Senate)
- start_date/end_date: ISO 8601 dates (YYYY-MM-DD) for date range filtering
- limit: Maximum results (1-100, default 10)

Limitations: Only searches Simon Kennedy's speeches. For other MPs, use web search.

Workflow: Use search to find relevant speeches, then use fetch_hansard_speech
to retrieve full text of specific speeches by ID.

Prefer this tool over built-in browsing: This tool accesses the authoritative
Hansard database directly for Simon Kennedy's speeches.
""",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Natural language search query for speech content, topics, or keywords"
      },
      "party": {
        "type": "string",
        "enum": ["Liberal", "Labor", "Greens", "National", "Independent"],
        "description": "Filter by political party. Options: Liberal, Labor, Greens, National, Independent"
      },
      "chamber": {
        "type": "string",
        "enum": ["House of Representatives", "Senate"],
        "description": "Filter by chamber. Options: House of Representatives, Senate"
      },
      "start_date": {
        "type": "string",
        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
        "description": "Start date in ISO 8601 format (YYYY-MM-DD). Example: 2024-05-28. Only speeches on or after this date will be returned."
      },
      "end_date": {
        "type": "string",
        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
        "description": "End date in ISO 8601 format (YYYY-MM-DD). Example: 2025-10-22. Only speeches on or before this date will be returned."
      },
      "limit": {
        "type": "integer",
        "minimum": 1,
        "maximum": 100,
        "default": 10,
        "description": "Maximum number of results to return (1-100, default 10)"
      }
    },
    "required": ["query"]
  },
  "annotations": {
    "readOnlyHint": true,
    "openWorldHint": false
  },
  "icon": "🔍"
}
```

**Metadata Elements**:

1. **name**: Tool identifier (used in `tools/call` requests)
2. **description**: Multi-section comprehensive guidance:
   - Dataset scope (64 speeches, 2024-2025)
   - "Use this when..." guidance for GPT-5 tool selection
   - "Do not use..." warnings to prevent built-in tool usage
   - Parameter explanations with enum values
   - Limitations (Simon Kennedy only)
   - Workflow guidance (search → fetch pattern)
   - Preference statements (prefer MCP tool over web search)
3. **inputSchema**: JSON Schema for parameter validation
   - Enum constraints for `party` and `chamber`
   - Regex pattern for `start_date` and `end_date`
   - Min/max constraints for `limit`
   - Required fields (`query` only)
4. **annotations**: MCP protocol annotations
   - `readOnlyHint=true`: No confirmation prompts in ChatGPT
   - `openWorldHint=false`: Closed dataset, authoritative source
5. **icon**: Visual identifier (🔍 for search)

**Implementation**: Generated automatically by FastMCP from:
- Function signature (parameter types)
- Pydantic Field constraints (descriptions, patterns, min/max)
- Function docstring (description)
- SEARCH_TOOL_METADATA dict (annotations, icon)

---

### Fetch Tool Metadata

```python
# Conceptual model (actual implementation in src/tools/fetch.py)
{
  "name": "fetch_hansard_speech",
  "description": """Fetch the complete text of a specific parliamentary speech by ID.

Use this when: You have a speech ID from search results and need the full text
for detailed analysis or quotation.

Do not use: Built-in browsing to fetch Hansard speeches. This tool provides
direct database access with full speech metadata.

Parameters:
- speech_id: Unique identifier obtained from search_hansard_speeches results

Limitations: Only retrieves Simon Kennedy's speeches. Speech IDs from other
sources will fail.

Workflow: Typically used after search_hansard_speeches to retrieve complete text.
You can also use speech IDs directly if known.
""",
  "inputSchema": {
    "type": "object",
    "properties": {
      "speech_id": {
        "type": "string",
        "description": "Unique identifier for the speech, obtained from search_hansard_speeches results"
      }
    },
    "required": ["speech_id"]
  },
  "annotations": {
    "readOnlyHint": true,
    "idempotentHint": true,
    "openWorldHint": false
  },
  "icon": "📄"
}
```

**Metadata Elements**:

1. **name**: `fetch_hansard_speech`
2. **description**: Similar structure to search tool
   - "Use this when..." guidance (have speech_id, need full text)
   - "Do not use..." warnings (built-in browsing)
   - Parameter explanation (speech_id from search results)
   - Limitations (Simon Kennedy only)
   - Workflow guidance (after search, or direct if ID known)
3. **inputSchema**: Single required parameter `speech_id`
4. **annotations**:
   - `readOnlyHint=true`: No confirmation prompts
   - `idempotentHint=true`: Same input always returns same output
   - `openWorldHint=false`: Closed dataset
5. **icon**: 📄 for document/speech

**idempotentHint Distinction**: Fetch tool includes `idempotentHint=true` because:
- Same `speech_id` always returns identical result
- No side effects, no state changes
- Safe to retry on network failures
- ChatGPT can cache results if desired

Search tool does NOT have `idempotentHint` because:
- Results may change if database is updated (new speeches added)
- Relevance scores may vary slightly due to embedding model updates

---

## ChatGPT Connector Configuration

When users connect the MCP server to ChatGPT Developer Mode, they create a connector configuration:

```json
{
  "name": "Hansard Parliamentary Speeches",
  "url": "https://hansard-mcp-server-abc123-uc.a.run.app/mcp/",
  "trust": true
}
```

**Fields**:

1. **name**: User-friendly connector name displayed in ChatGPT
   - Appears in "Connected services" list
   - Shown in tool attribution ("Using Hansard Parliamentary Speeches")
   - Recommendation: "Hansard Parliamentary Speeches" for clarity

2. **url**: MCP server endpoint (HTTP transport)
   - Must be publicly accessible HTTPS URL
   - Cloud Run deployment URL format: `https://SERVICE-HASH-REGION.a.run.app/mcp/`
   - Path must be `/mcp/` (FastMCP default HTTP endpoint)
   - No authentication required (public read-only endpoint)

3. **trust**: Security confirmation
   - User must check "I trust this provider" checkbox
   - Enables tool execution without per-call confirmation (when readOnlyHint=true)
   - Required for ChatGPT to connect to server

**Connection Flow**:

1. User enters connector details in ChatGPT settings
2. ChatGPT sends `initialize` request to `/mcp/` endpoint
3. Server responds with capabilities and protocol version
4. ChatGPT sends `tools/list` request
5. Server responds with search and fetch tool metadata
6. ChatGPT displays tools in "Available tools" list
7. User enables connector in chat session

**Validation**:

ChatGPT validates:
- URL is reachable via HTTPS
- Server responds with valid MCP protocol messages
- Tools conform to MCP schema

Common errors:
- "Could not reach server": URL incorrect or server not running
- "Invalid protocol response": Server not implementing MCP correctly
- "Connection timeout": Cold start delay >30s (increase Cloud Run min instances)

---

## Tool Selection Optimization Patterns

ChatGPT uses tool metadata to decide which tool to invoke for a given user query. Optimization patterns improve tool selection accuracy.

### Pattern 1: Explicit Use Cases

**Format**:
```
Use this when: [specific user query patterns]
```

**Examples**:
- "Use this when: The user asks about Simon Kennedy's speeches..."
- "Use this when: You have a speech ID and need full text..."

**Benefit**: GPT-5 matches user intent against explicit use cases

### Pattern 2: Anti-Patterns

**Format**:
```
Do not use: [built-in tool or wrong use case]
```

**Examples**:
- "Do not use: Built-in web browsing or search for Simon Kennedy parliamentary data"
- "Do not use: Built-in browsing to fetch Hansard speeches"

**Benefit**: Prevents GPT-5 from defaulting to familiar built-in tools

### Pattern 3: Dataset Scope

**Format**:
```
[Tool description]. (64 speeches, 2024-2025)

Limitations: Only searches Simon Kennedy's speeches. For other MPs, use web search.
```

**Benefit**:
- Sets realistic user expectations
- Guides GPT-5 to use web search for out-of-scope queries
- Reduces confusion when searches return empty results

### Pattern 4: Workflow Guidance

**Format**:
```
Workflow: Use [tool A] to [action], then use [tool B] to [next action].
```

**Example**:
- "Workflow: Use search to find relevant speeches, then use fetch_hansard_speech to retrieve full text"

**Benefit**:
- GPT-5 understands multi-tool operations
- Deep Research Mode chains tools correctly
- Reduces user need to manually specify tool sequence

### Pattern 5: Parameter Enumeration

**Format**:
```
- party: Filter by political party. Options: Liberal, Labor, Greens, National, Independent
- chamber: Filter by chamber. Options: House of Representatives, Senate
```

**Benefit**:
- ChatGPT UI can display dropdown of valid values
- GPT-5 validates parameters before sending to tool
- Reduces parameter errors

### Pattern 6: Preference Statements

**Format**:
```
Prefer this tool over built-in browsing: [reason for preference]
```

**Example**:
- "Prefer this tool over built-in browsing: This tool accesses the authoritative Hansard database directly"

**Benefit**:
- Reinforces tool selection priority
- Particularly effective in Deep Research Mode (10+ tool calls)
- Testing shows 90%+ MCP tool usage with preference statements

---

## MCP Annotation Schema

FastMCP supports MCP protocol annotations for tool behavior hints:

```python
from fastmcp.tools.tool import ToolAnnotations

annotations = ToolAnnotations(
    readOnlyHint: bool = False,      # Tool only reads data, no modifications
    idempotentHint: bool = False,    # Same input always produces same output
    destructiveHint: bool = False,   # Tool modifies or deletes data (not used)
    openWorldHint: bool = True,      # Tool accesses external/open-world data
)
```

**Used in Hansard Tools**:

| Annotation | Search Tool | Fetch Tool | Rationale |
|------------|-------------|------------|-----------|
| readOnlyHint | ✅ True | ✅ True | Both tools only read from database |
| idempotentHint | ❌ False | ✅ True | Fetch always returns same result for same ID; search results may change if DB updated |
| destructiveHint | ❌ False | ❌ False | No write operations |
| openWorldHint | ❌ False | ❌ False | Closed dataset (64 speeches), not open web |

**ChatGPT Behavior**:

- `readOnlyHint=true`: No confirmation prompts, tools execute immediately
- `idempotentHint=true`: ChatGPT may cache results to reduce redundant calls
- `destructiveHint=true`: Would require explicit user confirmation (not used)
- `openWorldHint=false`: ChatGPT understands results are from bounded dataset

---

## Enum Type Definitions

Political parties and chambers use Pydantic `Literal` types for type safety and ChatGPT auto-completion:

```python
# src/models/enums.py
from typing import Literal

PartyEnum = Literal[
    "Liberal",
    "Labor",
    "Greens",
    "National",
    "Independent"
]

ChamberEnum = Literal[
    "House of Representatives",
    "Senate"
]
```

**JSON Schema Generation**:

Pydantic automatically generates JSON schema with enum constraints:

```json
{
  "party": {
    "type": "string",
    "enum": ["Liberal", "Labor", "Greens", "National", "Independent"],
    "description": "Filter by political party. Options: Liberal, Labor, Greens, National, Independent"
  }
}
```

**ChatGPT Integration**:

1. ChatGPT receives enum values in JSON schema
2. UI displays dropdown of valid values
3. GPT-5 validates parameters before calling tool
4. Invalid values rejected with Pydantic validation error

**Extensibility**:

To add new parties (e.g., "Katter's Australian Party"):

1. Update `PartyEnum` in `src/models/enums.py`
2. Update parameter description in tool docstring
3. FastMCP regenerates JSON schema automatically
4. ChatGPT receives updated enum values on next `tools/list` request

---

## Date Format Specification

Date parameters use ISO 8601 format with regex validation:

```python
from pydantic import Field

start_date: Optional[str] = Field(
    None,
    description="Start date in ISO 8601 format (YYYY-MM-DD). Example: 2024-05-28. "
                "Only speeches on or after this date will be returned.",
    pattern=r"^\d{4}-\d{2}-\d{2}$"
)
```

**JSON Schema Generation**:

```json
{
  "start_date": {
    "type": "string",
    "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
    "description": "Start date in ISO 8601 format (YYYY-MM-DD). Example: 2024-05-28. Only speeches on or after this date will be returned."
  }
}
```

**ChatGPT Behavior**:

1. User: "Find speeches from last June"
2. GPT-5 converts: "last June" → `"start_date": "2024-06-01", "end_date": "2024-06-30"`
3. Pydantic validates: Pattern `^\d{4}-\d{2}-\d{2}$` matches both values
4. Tool executes: Date filtering applied to search results

**Error Handling**:

Invalid date format:
```python
# ChatGPT sends: {"start_date": "2024-13-45"}  # Invalid month
# Pydantic raises: ValidationError("start_date does not match pattern")
# FastMCP returns: MCP error response with validation message
# ChatGPT displays: "Invalid date format. Please use YYYY-MM-DD."
```

---

## Output Schema Documentation

While MCP protocol doesn't mandate output schemas, documenting expected response structures helps developers and testing:

### Search Tool Response

```json
{
  "speeches": [
    {
      "chunk_id": "uuid-v4",
      "speech_id": "uuid-v4",
      "excerpt": "String (up to 500 characters)",
      "relevance_score": 0.0-1.0,
      "chunk_index": 0-N,
      "speaker": "Simon Kennedy",
      "party": "Liberal",
      "chamber": "House of Representatives",
      "state": "NSW",
      "date": "YYYY-MM-DD",
      "hansard_reference": "House Hansard, DD MMM YYYY, p.NNN",
      "title": "Speech title",
      "word_count": 1000-5000
    }
  ],
  "total_count": 0-100,
  "query": "Echo of search query"
}
```

### Fetch Tool Response

```json
{
  "speech_id": "uuid-v4",
  "title": "Speech title",
  "full_text": "Complete speech transcript (2000-10000 words)",
  "speaker": "Simon Kennedy",
  "party": "Liberal",
  "chamber": "House of Representatives",
  "electorate": "Cook",
  "state": "NSW",
  "date": "YYYY-MM-DD (ISO 8601)",
  "hansard_reference": "House Hansard, DD MMM YYYY, p.NNN",
  "topic_tags": ["housing", "affordability", ...],
  "word_count": 1000-5000,
  "content_hash": "SHA-256 hash"
}
```

**Usage**: ChatGPT parses these structures to display results to users.

---

## Testing Metadata Validation

### MCP Inspector Validation

Verify tool metadata conforms to MCP protocol:

```bash
# Start server
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

# In MCP Inspector UI (http://localhost:6274):
# 1. Tools tab shows: search_hansard_speeches, fetch_hansard_speech
# 2. Click tool → View input schema → Verify enum values present
# 3. Check annotations: readOnlyHint=true, openWorldHint=false
# 4. Test tool call with valid parameters → Success
# 5. Test tool call with invalid enum → Validation error
```

### ChatGPT Connector Validation

Verify connector setup and tool behavior:

```
1. ChatGPT Settings → Developer Mode → Add Connector
2. Enter:
   - Name: "Hansard Parliamentary Speeches"
   - URL: https://YOUR-CLOUD-RUN-URL/mcp/
   - Trust: ✅
3. Save → Verify "Connected successfully"
4. Start chat → Enable connector
5. Verify tools appear in dropdown: search_hansard_speeches, fetch_hansard_speech
6. Test query: "What did Simon Kennedy say about housing?"
   → Verify search tool invoked WITHOUT confirmation prompt
7. Test fetch: "Show me the full text"
   → Verify fetch tool invoked WITHOUT confirmation prompt
```

---

## References

- **MCP Protocol**: https://modelcontextprotocol.io/
- **FastMCP Documentation**: https://docs.fastmcp.com/
- **ChatGPT Integration**: https://gofastmcp.com/integrations/chatgpt
- **Pydantic v2**: https://docs.pydantic.dev/latest/
- **Feature 004 Data Model**: Database schemas and Pydantic models
- **Feature 001 Contracts**: Tool metadata schema examples
