# Technical Research: Google Gemini CLI Integration

**Feature**: 009-gemini-cli-integration
**Date**: 2025-10-23
**Status**: Phase 0 Complete

## Overview

This document captures technical decisions for creating Gemini CLI integration documentation and configuration templates. All decisions prioritize user clarity, copy-paste readability, and alignment with Gemini CLI's native configuration patterns.

---

## Decision 1: Documentation Format and Structure

**Context**: Users need clear, actionable guides for configuring Gemini CLI to connect to the Hansard MCP server via STDIO (local) and SSE (remote) transports.

**Options Considered**:

1. **Single comprehensive guide** - All setup instructions in one document
2. **Separate guides per transport** - Local vs remote setup in distinct files
3. **Tutorial-style walkthrough** - Step-by-step with screenshots
4. **Reference documentation** - Technical specifications only

**Decision**: Separate guides per transport type (Option 2)

**Rationale**:
- Users typically need only one transport type (local dev OR remote production)
- Reduces cognitive load by focusing each guide on a single use case
- Allows different detail levels (local = quickstart, remote = full setup)
- Easier to maintain and update independently

**Implementation**:
```
docs/gemini-cli/
├── README.md           # Navigation and overview
├── local-setup.md      # STDIO quickstart (5 minutes)
├── remote-setup.md     # SSE Cloud Run setup (15 minutes)
└── troubleshooting.md  # Common issues (both transports)
```

**Format**: Markdown with syntax-highlighted code blocks for copy-paste commands.

---

## Decision 2: Configuration File Format (JSON vs YAML)

**Context**: Gemini CLI configuration needs example files for STDIO and SSE transports. Must choose between JSON and YAML formats.

**Options Considered**:

1. **JSON** - Native JavaScript Object Notation
2. **YAML** - Human-readable data serialization
3. **TOML** - Tom's Obvious Minimal Language
4. **Both JSON and YAML** - Provide examples in both formats

**Decision**: JSON format (Option 1)

**Rationale**:
- Gemini CLI natively uses JSON for configuration files
- JSON is strict (catches syntax errors immediately)
- No whitespace ambiguity (YAML's main pitfall)
- Widely supported across tools and editors
- Copy-paste reliability (no indentation issues)

**Example Structure**:
```json
{
  "mcpServers": {
    "hansard": {
      "command": "fastmcp",
      "args": ["run", "src/server.py"],
      "env": {
        "DANGEROUSLY_OMIT_AUTH": "true"
      }
    }
  }
}
```

**Trade-offs**:
- Less human-readable than YAML (acceptable for config files)
- No comments in standard JSON (use JSON5 style with explanatory text above)

---

## Decision 3: Testing Scenario Design

**Context**: Users need verification tests to confirm correct Gemini CLI setup. Tests must be executable, self-validating, and cover core functionality.

**Options Considered**:

1. **Manual test checklist** - Written steps users follow
2. **Shell script tests** - Automated bash/zsh scripts
3. **JSON test scenarios** - Structured test definitions with manual execution
4. **Interactive test tool** - Custom Python script for validation

**Decision**: JSON test scenarios with manual execution (Option 3)

**Rationale**:
- Structured format ensures consistency (description, command, expected output)
- User executes in Gemini CLI (tests real integration, not mocked)
- Platform-independent (no shell script compatibility issues)
- Easy to extend (add new scenarios without code changes)
- Self-documenting (includes success criteria in test definition)

**Test Scenario Structure**:
```json
{
  "scenarios": [
    {
      "id": "test-001",
      "name": "Tool Discovery",
      "description": "Verify Hansard MCP tools are discoverable",
      "command": "List available MCP tools",
      "expectedBehavior": "Gemini displays hansard_search, hansard_fetch, hansard_ingest",
      "successCriteria": "All three Hansard tools appear in tool list"
    }
  ]
}
```

**Coverage**: 3 core scenarios (discovery, search, fetch)

---

## Decision 4: STDIO vs SSE Transport Setup Patterns

**Context**: Gemini CLI supports multiple MCP transport types. Must document configuration patterns for local STDIO and remote SSE connections.

**Options Considered**:

1. **STDIO only** - Simplify by supporting only local development
2. **SSE only** - Cloud-first approach, no local setup
3. **Both STDIO and SSE** - Full flexibility for local and remote
4. **WebSocket transport** - Alternative real-time protocol

**Decision**: Both STDIO and SSE (Option 3)

**Rationale**:
- STDIO enables fast local development (no network, no auth complexity)
- SSE enables team collaboration via shared Cloud Run deployment
- Different use cases warrant different transports (dev vs prod)
- FastMCP supports both natively (no custom implementation needed)

**STDIO Pattern** (Local Development):
```json
{
  "mcpServers": {
    "hansard": {
      "command": "fastmcp",
      "args": ["run", "src/server.py"],
      "env": {
        "DANGEROUSLY_OMIT_AUTH": "true",
        "DATABASE_URL": "sqlite:///data/hansard.db"
      }
    }
  }
}
```

**SSE Pattern** (Remote Cloud Run):
```json
{
  "mcpServers": {
    "hansard": {
      "url": "https://hansard-mcp-server-PROJECT_ID.a.run.app",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

**Key Differences**:
- STDIO: Launches local process, direct I/O communication
- SSE: HTTP connection to remote endpoint, server-sent events stream
- STDIO: No authentication needed (local trust)
- SSE: Requires authentication token (Cloud Run security)

---

## Decision 5: Troubleshooting Guide Organization

**Context**: Users encounter setup issues (connection failures, auth errors, version mismatches). Need systematic troubleshooting approach.

**Options Considered**:

1. **FAQ format** - Question and answer pairs
2. **Error code reference** - Lookup table by error code
3. **Categorized symptoms** - Group by problem type (connection, auth, version)
4. **Decision tree** - Flowchart-style diagnostic guide

**Decision**: Categorized symptoms with diagnostic commands (Option 3)

**Rationale**:
- Users describe symptoms, not error codes (more intuitive)
- Categories map to common failure modes (connection, auth, data)
- Diagnostic commands enable self-service debugging
- Solutions are actionable (commands to run, not just explanations)

**Troubleshooting Structure**:
```markdown
## Connection Issues

### Symptom: "Cannot connect to MCP server"

**Diagnosis**:
```bash
# Verify server is running
ps aux | grep fastmcp

# Check port availability
netstat -an | grep 8080
```

**Solutions**:
1. Verify FastMCP is installed: `fastmcp --version`
2. Check server.py path is correct
3. Review server logs for errors
```

**Categories**:
1. **Connection Issues** - Server not reachable (STDIO process, SSE endpoint)
2. **Authentication Issues** - OAuth failures, token expired, missing credentials
3. **Version Compatibility** - Gemini CLI version, FastMCP version, Python version
4. **Data Issues** - Database not initialized, empty results, query errors

**Format**: Symptom → Diagnosis → Solutions (commands, not prose)

---

## Research Summary

| Decision | Choice | Impact |
|----------|--------|--------|
| Documentation Format | Separate guides per transport | Reduces cognitive load, easier maintenance |
| Configuration Format | JSON | Native Gemini CLI format, copy-paste reliability |
| Testing Scenarios | JSON with manual execution | Structured, extensible, platform-independent |
| Transport Support | Both STDIO and SSE | Covers local dev and remote production |
| Troubleshooting | Categorized symptoms | Self-service debugging, actionable solutions |

**Next Phase**: Create design artifacts (data-model.md, quickstart.md, contract files)
