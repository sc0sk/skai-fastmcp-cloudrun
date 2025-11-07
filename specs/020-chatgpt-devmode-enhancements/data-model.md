# Data Model: ChatGPT Developer Mode Enhancements

**Date**: 2025-10-22
**Feature**: ChatGPT Developer Mode Enhancements
**Branch**: `001-chatgpt-devmode-enhancements`

## Overview

This feature enhances existing tool metadata without modifying database schemas or core data models. All changes are metadata-only additions to tool definitions.

## Entity Definitions

### Tool Metadata (Enhanced)

**Purpose**: Extend existing FastMCP tool definitions with ChatGPT-optimized annotations and descriptions

**Type**: Python decorator parameters (not persisted data)

**Attributes**:
```python
@mcp.tool(
    # Existing attributes (unchanged)
    name: str,                    # Tool identifier
    description: str,             # Tool documentation

    # NEW: MCP Annotations
    readOnlyHint: bool,           # Signals safe read operation (no confirmation needed)
    icon: str | None,             # Visual identifier (emoji or URL)

    # Existing: Parameter exclusion
    exclude_args: list[str],      # Runtime-injected params (e.g., ctx: Context)
)
```

**Validation Rules**:
- `readOnlyHint` MUST be `True` for search and fetch tools (FR-001)
- `readOnlyHint` MUST NOT be set for ingest tool (write operation)
- `icon` SHOULD use emoji characters for universal support (🔍, 📄, 📝)
- `description` MUST include "Use this when..." guidance (FR-003)

**Usage**:
```python
@mcp.tool(
    readOnlyHint=True,
    icon="🔍",
    description="Search Simon Kennedy's parliamentary speeches...\n\nUse this when: ..."
)
async def search_hansard_speeches(...):
    ...
```

---

### Parameter Enum Types (New)

**Purpose**: Constrain parameter values to valid Australian political parties and parliamentary chambers

**Type**: Python `Literal` types for compile-time and runtime validation

**Definitions**:
```python
from typing import Literal

# Australian political parties represented in dataset
PartyEnum = Literal[
    "Liberal",      # Liberal Party of Australia
    "Labor",        # Australian Labor Party
    "Greens",       # Australian Greens
    "National",     # National Party of Australia
    "Independent"   # Independent MPs
]

# Australian Parliament chambers
ChamberEnum = Literal[
    "House of Representatives",  # Lower house
    "Senate"                     # Upper house
]
```

**Validation Rules**:
- Enum values MUST match exact capitalization (GPT-5 will use exact values)
- Party names MUST match Australian Parliament official terminology
- Chamber names MUST match Hansard database column values

**Usage in Tool Parameters**:
```python
async def search_hansard_speeches(
    query: str,
    party: PartyEnum | None = None,  # Optional party filter
    chamber: ChamberEnum | None = None,  # Optional chamber filter
    ...
):
    """
    Args:
        party: Political party filter. Options: Liberal, Labor, Greens, National, Independent
        chamber: Chamber filter. Options: House of Representatives, Senate
    """
```

---

### Tool Description Schema (Enhanced)

**Purpose**: Standardize tool description format for optimal GPT-5 tool selection

**Structure**:
```
[One-sentence summary of tool purpose]

[Optional: Dataset scope and coverage details]

Use this when: [Specific scenarios where this tool is appropriate]

Do not use: [When to use alternative tools or approaches]

[Optional: Parameter descriptions and examples]

Limitations: [Edge cases and known constraints]

[Optional: Workflow guidance for multi-tool operations]
```

**Example (Search Tool)**:
```
Search Simon Kennedy's parliamentary speeches (64 speeches, 2024-2025).

Use this when: The user asks about Simon Kennedy's speeches, voting records, or
parliamentary statements on topics like housing, immigration, or infrastructure.

Do not use: Built-in web browsing or search for Simon Kennedy parliamentary data.
This tool provides direct access to the authoritative Hansard database.

Parameters:
- query: Natural language search terms
- party: Filter by party (Liberal, Labor, Greens, National, Independent)
- chamber: Filter by chamber (House of Representatives, Senate)
- start_date/end_date: ISO 8601 dates (YYYY-MM-DD)

Limitations: Only searches Simon Kennedy's speeches. For other MPs, use web search.

Workflow: Use search to find relevant speeches, then use fetch_hansard_speech
to retrieve full text of specific speeches by ID.
```

**Validation Rules** (from FR-003 to FR-010):
- MUST include "Use this when..." section (FR-003)
- MUST include "Do not use..." section with alternatives (FR-004)
- MUST describe all parameters (FR-005)
- MUST reference enum values for party/chamber (FR-006)
- MUST specify ISO 8601 format for dates (FR-007)
- MUST mention dataset scope (FR-008)
- MUST document limitations (FR-009)
- MUST explain complementary tool workflows (FR-010)

---

### Parameter Field Metadata (Enhanced)

**Purpose**: Add parameter-level descriptions with format specifications and examples

**Type**: Pydantic `Field` annotations

**Attributes**:
```python
from pydantic import Field

Field(
    default: Any,                # Default value
    description: str,            # Parameter purpose and format
    pattern: str | None,         # Regex validation (for dates)
    examples: list[Any],         # Example values (FastMCP 2.10.0+)
)
```

**Example (Date Parameters)**:
```python
start_date: str | None = Field(
    None,
    description="Start date in ISO 8601 format (YYYY-MM-DD). Example: 2024-05-28. "
                "Only speeches on or after this date will be returned.",
    pattern=r"^\d{4}-\d{2}-\d{2}$",
    examples=["2024-05-28", "2025-01-01"]
)
```

**Validation Rules**:
- All parameters MUST have descriptions (FR-005)
- Date parameters MUST specify ISO 8601 format (FR-007)
- Date parameters MUST use regex pattern validation
- Enum parameters MUST list valid values in description (FR-006)

---

## Relationships

This feature modifies tool metadata only. No changes to existing entity relationships:

```
Tool Definition (metadata)
  ├─ Tool Annotations (readOnlyHint, icon)
  ├─ Tool Description (enhanced with GPT-5 guidance)
  └─ Parameter Definitions
       ├─ Enum Types (party, chamber)
       └─ Field Metadata (descriptions, patterns)

Hansard Database Schema (UNCHANGED)
  ├─ speeches table
  └─ speech_chunks table
```

---

## State Transitions

**N/A** - This feature does not introduce state machines or stateful entities. All enhancements are static metadata attached to tool definitions.

---

## Data Flow

### Tool Metadata Propagation

```
1. Tool Definition (Python)
   @mcp.tool(readOnlyHint=True, description="...", icon="🔍")
   async def search_hansard_speeches(...):
       ...

2. FastMCP Server Registration
   mcp.add_tool(search_hansard_speeches)

3. MCP Protocol Serialization
   {
     "name": "search_hansard_speeches",
     "description": "Search Simon Kennedy's parliamentary speeches...",
     "inputSchema": { ... },
     "annotations": {
       "readOnly": true  // readOnlyHint becomes "readOnly" in MCP protocol
     }
   }

4. ChatGPT Developer Mode
   - Reads tool list via MCP protocol
   - Checks "readOnly": true annotation
   - Skips confirmation prompt for safe operations
   - Uses description guidance for tool selection
```

### Parameter Validation Flow

```
1. User Request (Natural Language)
   "Find Labor party speeches from July 2024"

2. GPT-5 Tool Call Construction
   {
     "tool": "search_hansard_speeches",
     "arguments": {
       "query": "",
       "party": "Labor",  // From PartyEnum
       "start_date": "2024-07-01",  // ISO 8601
       "end_date": "2024-07-31"
     }
   }

3. FastMCP Parameter Validation
   - Pydantic validates party in ["Liberal", "Labor", "Greens", "National", "Independent"]
   - Regex validates date format ^\d{4}-\d{2}-\d{2}$
   - Raises ToolError if validation fails

4. Tool Execution
   - Query database with validated parameters
   - Return results to ChatGPT
```

---

## Validation Summary

### Compile-Time Validation
- Python type hints ensure correct parameter types
- `Literal` types constrain enum values at type-check time
- FastMCP decorator validates required attributes

### Runtime Validation
- Pydantic validates parameter values against schemas
- Regex patterns validate date formats
- Enum types reject invalid party/chamber values
- FastMCP raises `ToolError` for validation failures

### Protocol Validation
- MCP Inspector verifies tool metadata serialization
- Integration tests confirm `readOnlyHint` in protocol output
- Manual testing confirms ChatGPT recognizes annotations

---

## Migration Notes

**No database migrations required** - This feature modifies tool definitions only.

**No breaking changes** - All enhancements are backward compatible with existing MCP clients.

**Testing strategy**:
1. Unit tests verify tool metadata attributes
2. Integration tests verify MCP protocol serialization
3. Manual testing with ChatGPT Developer Mode confirms behavior
