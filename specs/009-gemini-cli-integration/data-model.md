# Data Model: Google Gemini CLI Integration

**Feature**: 009-gemini-cli-integration
**Date**: 2025-10-23
**Type**: Documentation Entities (not code models)

## Overview

This feature is documentation-only and does not involve database schemas or Pydantic models. The "entities" defined here represent the structure of configuration files and test scenarios that users will work with.

---

## Entity 1: Configuration Profile

**Purpose**: Represents a complete Gemini CLI MCP server configuration for the Hansard server.

**Context**: Users add this configuration to their Gemini CLI settings file to connect to the Hansard MCP server via STDIO (local) or SSE (remote) transport.

### Attributes

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `serverName` | string | Yes | Unique identifier for the MCP server | `"hansard"` |
| `transport` | enum | Yes | Connection transport type | `"stdio"` or `"sse"` |
| `command` | string | Conditional | Command to launch local server (STDIO only) | `"fastmcp"` |
| `args` | array[string] | Conditional | Command arguments (STDIO only) | `["run", "src/server.py"]` |
| `url` | string | Conditional | Remote server endpoint (SSE only) | `"https://hansard-mcp.a.run.app"` |
| `env` | object | Optional | Environment variables | `{"DANGEROUSLY_OMIT_AUTH": "true"}` |
| `headers` | object | Optional | HTTP headers (SSE only) | `{"Authorization": "Bearer TOKEN"}` |
| `timeout` | integer | Optional | Connection timeout in seconds | `30` |
| `description` | string | Optional | User-facing description | `"Australian Hansard search"` |

### Conditional Requirements

**STDIO Transport**:
- MUST include: `command`, `args`
- MAY include: `env`, `timeout`
- MUST NOT include: `url`, `headers`

**SSE Transport**:
- MUST include: `url`
- MAY include: `headers`, `timeout`, `env`
- MUST NOT include: `command`, `args`

### Example: STDIO Configuration

```json
{
  "mcpServers": {
    "hansard": {
      "transport": "stdio",
      "command": "fastmcp",
      "args": ["run", "/home/user/skai-fastmcp-cloudrun/src/server.py"],
      "env": {
        "DANGEROUSLY_OMIT_AUTH": "true",
        "DATABASE_URL": "sqlite:////home/user/data/hansard.db",
        "PYTHONPATH": "/home/user/skai-fastmcp-cloudrun"
      },
      "description": "Local Hansard MCP server (development mode)",
      "timeout": 30
    }
  }
}
```

### Example: SSE Configuration

```json
{
  "mcpServers": {
    "hansard": {
      "transport": "sse",
      "url": "https://hansard-mcp-server-abc123.a.run.app",
      "headers": {
        "Authorization": "Bearer ya29.a0AfB_byC..."
      },
      "description": "Remote Hansard MCP server (production)",
      "timeout": 60
    }
  }
}
```

### Validation Rules

1. `serverName` must be unique within Gemini CLI configuration
2. `transport` must be exactly `"stdio"` or `"sse"`
3. STDIO `command` must be an executable in PATH or absolute path
4. SSE `url` must be valid HTTPS URL (HTTP allowed for localhost only)
5. Environment variable keys must be valid shell variable names
6. `timeout` must be positive integer (default: 30 seconds)

### Configuration Location

- **macOS/Linux**: `~/.config/gemini-cli/config.json`
- **Windows**: `%APPDATA%\gemini-cli\config.json`

---

## Entity 2: Test Scenario

**Purpose**: Represents a verifiable test case to confirm correct Gemini CLI and Hansard MCP server setup.

**Context**: Users execute these test scenarios after configuration to verify the server is reachable, tools are discoverable, and queries return expected results.

### Attributes

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | string | Yes | Unique test identifier | `"test-001"` |
| `name` | string | Yes | Short test name | `"Tool Discovery"` |
| `description` | string | Yes | What this test verifies | `"Verify Hansard tools are discoverable"` |
| `transport` | array[enum] | Yes | Compatible transports | `["stdio", "sse"]` |
| `command` | string | Yes | User instruction for test | `"Ask Gemini to list available tools"` |
| `expectedBehavior` | string | Yes | What should happen | `"Gemini lists 3 Hansard tools"` |
| `successCriteria` | string | Yes | How to verify success | `"Tools include hansard_search, hansard_fetch, hansard_ingest"` |
| `sampleInput` | string | Optional | Example query to run | `"Search for speeches about climate change"` |
| `estimatedTime` | integer | Optional | Expected duration in seconds | `5` |

### Example: Tool Discovery Test

```json
{
  "id": "test-001",
  "name": "Tool Discovery",
  "description": "Verify that Gemini CLI can discover the three Hansard MCP tools",
  "transport": ["stdio", "sse"],
  "command": "Ask Gemini: 'What tools are available from the Hansard server?'",
  "expectedBehavior": "Gemini responds with a list of three tools: hansard_search, hansard_fetch, and hansard_ingest",
  "successCriteria": "All three tool names appear in Gemini's response",
  "sampleInput": null,
  "estimatedTime": 5
}
```

### Example: Search Query Test

```json
{
  "id": "test-002",
  "name": "Search Query Execution",
  "description": "Verify that hansard_search tool executes and returns results",
  "transport": ["stdio", "sse"],
  "command": "Ask Gemini: 'Search Hansard for speeches about climate policy'",
  "expectedBehavior": "Gemini executes hansard_search and returns speech results with speaker names, dates, and excerpts",
  "successCriteria": "Results include at least 1 speech with metadata (speaker, date, chamber)",
  "sampleInput": "climate policy",
  "estimatedTime": 10
}
```

### Example: Fetch by ID Test

```json
{
  "id": "test-003",
  "name": "Speech Fetch by ID",
  "description": "Verify that hansard_fetch tool retrieves full speech text",
  "transport": ["stdio", "sse"],
  "command": "Ask Gemini: 'Fetch Hansard speech ID abc-123'",
  "expectedBehavior": "Gemini executes hansard_fetch and returns complete speech text with full metadata",
  "successCriteria": "Response includes speech_id, speaker, date, chamber, and full speech_text",
  "sampleInput": "abc-123",
  "estimatedTime": 5
}
```

### Test Collection Structure

```json
{
  "version": "1.0",
  "testSuite": "Gemini CLI Hansard Integration",
  "scenarios": [
    { "id": "test-001", /* ... */ },
    { "id": "test-002", /* ... */ },
    { "id": "test-003", /* ... */ }
  ]
}
```

### Execution Workflow

1. User completes Gemini CLI configuration (STDIO or SSE)
2. User opens test-scenarios.json reference
3. For each scenario:
   - Execute the `command` in Gemini CLI
   - Observe Gemini's behavior
   - Verify against `successCriteria`
4. All tests pass = setup confirmed working

### Validation Rules

1. `id` must be unique within test collection
2. `transport` must contain at least one of `["stdio", "sse"]`
3. `estimatedTime` must be positive integer (seconds)
4. `successCriteria` must be objectively verifiable (no subjective judgment)

---

## Entity Relationships

```
Configuration Profile ----< Test Scenario
      1                         N

- One Configuration Profile enables execution of multiple Test Scenarios
- Each Test Scenario specifies compatible transports (STDIO, SSE, or both)
- Test Scenarios are independent (can run in any order)
```

**Example**: A user with STDIO Configuration Profile can execute all 3 Test Scenarios because all scenarios support both `"stdio"` and `"sse"` transports.

---

## Non-Code Entities

**Important**: These entities are NOT implemented as Python classes, Pydantic models, or database tables. They are documentation constructs representing:

1. **Configuration Profile** → JSON structure in Gemini CLI config file
2. **Test Scenario** → JSON structure in test-scenarios.json reference file

**Purpose**: Define clear, consistent structure for user-facing configuration and testing artifacts.

---

## Summary

| Entity | Format | Location | Purpose |
|--------|--------|----------|---------|
| Configuration Profile | JSON | `~/.config/gemini-cli/config.json` | Gemini CLI MCP server config |
| Test Scenario | JSON | `specs/009-.../contracts/test-scenarios.json` | Verification test definition |

**Next Phase**: Create quickstart.md and contract example files.
