# Tool Metadata Contracts

**Feature**: ChatGPT Developer Mode Enhancements
**Date**: 2025-10-22

## Overview

This directory contains JSON schema contracts defining enhanced tool metadata for ChatGPT Developer Mode integration. These contracts specify tool annotations, parameter schemas, and expected behavior.

## Files

### tool-metadata-schema.json

Complete JSON schema defining:
- **Tool Annotations**: `readOnlyHint`, `idempotentHint`, `destructiveHint`, `openWorldHint`
- **Parameter Enums**: `PartyEnum`, `ChamberEnum`
- **Date Formats**: ISO 8601 pattern validation
- **Tool Definitions**: Enhanced descriptions for `search_hansard_speeches`, `fetch_hansard_speech`, `ingest_hansard_speech`

## Contract Validation

### Unit Tests

Unit tests verify Python tool definitions match these JSON schemas:

```python
def test_search_tool_metadata():
    """Verify search tool has required annotations"""
    tool = mcp.get_tool("search_hansard_speeches")
    assert tool.readOnlyHint == True
    assert tool.icon == "🔍"
    assert "Use this when" in tool.description

def test_party_enum_values():
    """Verify PartyEnum matches contract"""
    from src.tools.search import PartyEnum
    assert get_args(PartyEnum) == ("Liberal", "Labor", "Greens", "National", "Independent")
```

### Integration Tests

MCP Inspector verifies protocol-level serialization:

```bash
# Start server
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

# Inspect tools via MCP protocol
mcp-cli tools list | jq '.tools[] | select(.name == "search_hansard_speeches")'

# Expected output:
{
  "name": "search_hansard_speeches",
  "description": "Search Simon Kennedy's parliamentary speeches...",
  "inputSchema": { ... },
  "annotations": {
    "readOnly": true  // Note: readOnlyHint -> readOnly in MCP protocol
  }
}
```

### ChatGPT Integration Tests

Manual testing with ChatGPT Developer Mode:

1. **No confirmation prompt**: Verify ChatGPT doesn't show confirmation dialog when calling `search_hansard_speeches` or `fetch_hansard_speech`
2. **Tool selection**: Ask "Find Simon Kennedy's speeches about housing" and verify ChatGPT uses MCP tool (not built-in browsing)
3. **Parameter accuracy**: Verify ChatGPT uses exact enum values ("Labor" not "Labour", "House of Representatives" not "House")

## Usage in Implementation

These contracts guide implementation but are NOT runtime artifacts. FastMCP generates equivalent JSON schemas automatically from Python type hints and decorator parameters.

**Python implementation**:
```python
from typing import Literal
from pydantic import Field

PartyEnum = Literal["Liberal", "Labor", "Greens", "National", "Independent"]

@mcp.tool(
    readOnlyHint=True,
    icon="🔍",
    description="Search Simon Kennedy's parliamentary speeches..."
)
async def search_hansard_speeches(
    query: str,
    party: PartyEnum | None = Field(
        None,
        description="Filter by political party. Options: Liberal, Labor, Greens, National, Independent"
    ),
    ...
):
    ...
```

**FastMCP auto-generates** → JSON schema matching `tool-metadata-schema.json`

## Version History

- **1.0.0** (2025-10-22): Initial contract definition for ChatGPT Developer Mode enhancements
