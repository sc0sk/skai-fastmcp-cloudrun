# Research: ChatGPT Developer Mode Enhancements

**Date**: 2025-10-22
**Feature**: ChatGPT Developer Mode Enhancements
**Branch**: `001-chatgpt-devmode-enhancements`

## Overview

This research document covers technical decisions for enhancing the MCP server's ChatGPT Developer Mode integration through tool annotations, improved descriptions, and parameter enhancements. All decisions leverage existing FastMCP 2.14.0+ capabilities and GPT-5 model characteristics.

## Research Topics

### 1. FastMCP Tool Annotations for ChatGPT

**Decision**: Use `readOnlyHint: true` for all read-only tools (search, fetch)

**Rationale**:
- FastMCP 2.14.0+ supports MCP tool annotations per [MCP specification](https://modelcontextprotocol.io/legacy/concepts/tools#available-tool-annotations)
- ChatGPT Developer Mode respects `readOnlyHint` to skip confirmation prompts for safe operations
- Annotations are metadata-only changes with zero functional impact on existing tools
- Compatible with all MCP clients (Claude Desktop, VS Code, ChatGPT)

**Implementation**:
```python
@mcp.tool(
    readOnlyHint=True,  # Signals safe read operation to ChatGPT
    description="..."
)
async def search_hansard_speeches(...):
    ...
```

**Alternatives Considered**:
1. **Custom metadata fields**: Rejected because `readOnlyHint` is standard MCP protocol
2. **Description-only approach**: Rejected because ChatGPT specifically checks `readOnlyHint` annotation
3. **Per-client configuration**: Rejected because annotations work across all MCP clients

**References**:
- MCP Tool Annotations: https://modelcontextprotocol.io/legacy/concepts/tools#available-tool-annotations
- FastMCP Tool Decorator: https://docs.fastmcp.com/concepts/tools
- Constitution Section XI: Tool Implementation Standards

---

### 2. GPT-5 Tool Selection Guidance

**Decision**: Add explicit "Use this when..." guidance and "Do not use built-in browsing" statements in tool descriptions

**Rationale**:
- GPT-5 uses chain-of-thought reasoning for tool selection
- Clear, explicit guidance leverages GPT-5's improved instruction following
- GPT-5 has multiple built-in tools (browse, search, python) that may compete with MCP tools
- Explicit prioritization guidance helps the model make better tool selection decisions

**Implementation Pattern**:
```python
description = """
Search Simon Kennedy's parliamentary speeches (64 speeches, 2024-2025).

Use this when: The user asks about Simon Kennedy's speeches, voting records, or
parliamentary statements on topics like housing, immigration, or infrastructure.

Do not use: Built-in web browsing or search for Simon Kennedy parliamentary data.
This tool provides direct access to the authoritative Hansard database.

Limitations: Only searches Simon Kennedy's speeches. For other MPs, use web search.
"""
```

**Alternatives Considered**:
1. **Generic descriptions**: Rejected because GPT-5 performs better with explicit guidance
2. **Negative examples only**: Rejected because positive "Use this when" guidance is more effective
3. **Minimal descriptions**: Rejected because GPT-5's reasoning benefits from comprehensive context

**References**:
- GPT-5 Documentation: Improved instruction following and reasoning
- GPT-5 Prompting Best Practices: https://cookbook.openai.com/examples/gpt-5/gpt-5_prompting_guide
- Feature Spec Section: GPT-5 Considerations

---

### 3. Parameter Enums for Australian Political Parties

**Decision**: Use Pydantic `Literal` types for `party` and `chamber` parameters with enum definitions

**Rationale**:
- Australian political parties have stable, well-defined names (Liberal, Labor, Greens, National, Independent)
- Enums prevent parameter errors and guide GPT-5 to use exact values
- Pydantic `Literal` provides type safety and automatic validation
- FastMCP automatically generates JSON schema with enum constraints from `Literal` types

**Implementation**:
```python
from typing import Literal

PartyEnum = Literal["Liberal", "Labor", "Greens", "National", "Independent"]
ChamberEnum = Literal["House of Representatives", "Senate"]

@mcp.tool(readOnlyHint=True)
async def search_hansard_speeches(
    query: str,
    party: PartyEnum | None = None,  # Automatic enum validation
    chamber: ChamberEnum | None = None,
    ...
):
    """
    Search Simon Kennedy's parliamentary speeches.

    Args:
        query: Search terms
        party: Political party filter. Options: Liberal, Labor, Greens, National, Independent
        chamber: Chamber filter. Options: House of Representatives, Senate
    """
    ...
```

**Alternatives Considered**:
1. **String parameters with descriptions only**: Rejected because enums provide type safety
2. **Custom Pydantic models**: Rejected as overkill for simple enums
3. **JSON schema annotations**: Rejected because Pydantic `Literal` generates schemas automatically

**References**:
- Pydantic Literal Types: https://docs.pydantic.dev/latest/concepts/types/#literal-types
- FastMCP Parameter Validation: Constitution Section XI
- Australian Parliament: https://www.aph.gov.au/

---

### 4. Date Format Specifications

**Decision**: Use ISO 8601 date format (YYYY-MM-DD) with parameter descriptions

**Rationale**:
- ISO 8601 is unambiguous and internationally recognized
- GPT-5 can reliably convert natural language dates to ISO 8601
- Consistent with existing database schema (PostgreSQL date fields)
- FastMCP automatically validates ISO 8601 strings when type hint is `str` with pattern validation

**Implementation**:
```python
from pydantic import Field

@mcp.tool(readOnlyHint=True)
async def search_hansard_speeches(
    query: str,
    start_date: str | None = Field(
        None,
        description="Start date in ISO 8601 format (YYYY-MM-DD). Example: 2024-05-28",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    end_date: str | None = Field(
        None,
        description="End date in ISO 8601 format (YYYY-MM-DD). Example: 2025-10-22",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    ...
):
    ...
```

**Alternatives Considered**:
1. **Python `datetime` type**: Rejected because FastMCP JSON serialization prefers strings
2. **Natural language dates**: Rejected because validation is complex and error-prone
3. **Unix timestamps**: Rejected because less human-readable than ISO 8601

**References**:
- ISO 8601: https://en.wikipedia.org/wiki/ISO_8601
- Pydantic Field Patterns: https://docs.pydantic.dev/latest/concepts/fields/
- Constitution Section XI: Parameter Validation

---

### 5. Tool Icons for Visual Identification

**Decision**: Add tool icons using FastMCP 2.14.0+ icon support (optional enhancement)

**Rationale**:
- FastMCP 2.14.0+ supports tool icons for visual identification in MCP clients
- Icons improve tool discoverability in ChatGPT Developer Mode
- Minimal implementation effort (single parameter in tool decorator)
- Backward compatible (clients without icon support ignore this field)

**Implementation**:
```python
@mcp.tool(
    readOnlyHint=True,
    icon="🔍",  # Search icon
    description="..."
)
async def search_hansard_speeches(...):
    ...

@mcp.tool(
    readOnlyHint=True,
    icon="📄",  # Document icon
    description="..."
)
async def fetch_hansard_speech(...):
    ...
```

**Alternatives Considered**:
1. **No icons**: Rejected because icons improve UX with minimal cost
2. **Custom icon URLs**: Rejected because emoji icons are simpler and universally supported
3. **Material Design icons**: Rejected because FastMCP icon support uses simple strings

**References**:
- FastMCP 2.14.0 Release Notes: Icon support for tools
- Constitution Section XI: Icons for visual identification

---

### 6. Backward Compatibility with Existing MCP Clients

**Decision**: All enhancements must maintain full backward compatibility with Claude Desktop, VS Code, and other MCP clients

**Rationale**:
- Annotations are optional metadata; clients without support ignore them
- Enhanced descriptions improve UX for all clients, not just ChatGPT
- Enum parameters use standard Pydantic types (no custom serialization)
- Tool function signatures unchanged (only decorator parameters modified)

**Testing Strategy**:
1. Unit tests verify metadata present in tool definitions
2. Integration tests with MCP Inspector verify protocol compliance
3. Manual testing with Claude Desktop confirms backward compatibility
4. ChatGPT Developer Mode testing confirms `readOnlyHint` recognition

**Alternatives Considered**:
1. **ChatGPT-specific builds**: Rejected because single codebase is easier to maintain
2. **Feature flags**: Rejected because annotations are backward compatible by design
3. **Separate tool definitions**: Rejected as unnecessary duplication

**References**:
- MCP Protocol Specification: Optional tool annotations
- FastMCP Compatibility: Works with all MCP clients
- Constitution Section I: Tool-based architecture for discoverability

---

### 7. Complementary Tool Workflow Documentation

**Decision**: Add workflow guidance in tool descriptions explaining multi-tool operations

**Rationale**:
- GPT-5's reasoning benefits from understanding tool relationships
- Search → Fetch is a common workflow (find speeches, then get full text)
- Explicit workflow documentation helps GPT-5 plan multi-step operations
- Reduces user frustration by suggesting logical next steps

**Implementation Pattern**:
```python
# In search tool description
"""
...
Workflow: Use search to find relevant speeches, then use fetch_hansard_speech
to retrieve full text of specific speeches by ID.
"""

# In fetch tool description
"""
...
Workflow: Typically used after search_hansard_speeches to retrieve complete text.
You can also use speech IDs directly if known.
"""
```

**Alternatives Considered**:
1. **No workflow documentation**: Rejected because users and models benefit from guidance
2. **Separate workflow documentation file**: Rejected because in-tool docs are more discoverable
3. **Code comments only**: Rejected because MCP tool descriptions are user-facing

**References**:
- GPT-5 Reasoning Guide: Multi-step planning with tools
- Feature Spec FR-010: Complementary tool workflows
- Constitution Section I: Tool discoverability

---

## Summary

All research decisions align with existing FastMCP 2.14.0+ capabilities and constitution requirements. No new dependencies, no breaking changes, no architecture modifications required. Implementation is straightforward metadata and description enhancements to existing tools.

### Key Takeaways

1. **Annotations**: `readOnlyHint: true` for search and fetch tools
2. **Descriptions**: "Use this when..." guidance with explicit prioritization
3. **Parameters**: Pydantic `Literal` enums for party and chamber
4. **Dates**: ISO 8601 format with pattern validation
5. **Icons**: Optional emoji icons for visual identification
6. **Compatibility**: Full backward compatibility with all MCP clients
7. **Workflows**: Explicit documentation of tool relationships

### No Open Questions

All technical decisions are fully specified. No further research or clarifications needed before proceeding to Phase 1 (Design & Contracts).
