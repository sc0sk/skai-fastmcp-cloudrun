# Google Gemini CLI Integration Guide

**Purpose**: Connect Google Gemini CLI to the Hansard MCP server for interactive parliamentary speech search and retrieval.

**Quick Links**:
- [Local STDIO Setup](#local-stdio-setup) (5-10 minutes)
- [Remote SSE Setup](#remote-sse-setup) (15 minutes)
- [Troubleshooting](#troubleshooting)
- [Test Scenarios](#test-scenarios)

---

## Overview

The Hansard MCP server provides three powerful tools for querying Australian parliamentary speeches:

1. **hansard_search** - Search speeches by keywords, speaker, date, or chamber
2. **hansard_fetch** - Retrieve complete speech text by ID
3. **hansard_ingest** - Add new speeches to the database (local only)

This guide helps you connect Google Gemini CLI to the Hansard MCP server using two transport methods:

- **STDIO Transport**: Local development with direct process communication
- **SSE Transport**: Remote access to Cloud Run deployed server

---

## Prerequisites

### Required Software

| Component | Version | Installation |
|-----------|---------|--------------|
| Google Gemini CLI | v1.0.0+ | `npm install -g @google/gemini-cli` |
| Python | 3.11+ | System package manager or python.org |
| FastMCP | 2.14.0+ | Installed via `uv sync` in project |
| uv | Latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

### System Requirements

- **Operating Systems**: Windows 10+, macOS 12+, Linux (Ubuntu 20.04+)
- **Network**: Internet connection for initial setup and Cloud Run SSE access
- **Permissions**: Write access to Gemini CLI config directory

---

## Local STDIO Setup

**Use Case**: Local development, testing, offline access

**Setup Time**: 5-10 minutes

**Transport**: STDIO (direct process I/O)

**Complete Guide**: [stdio-setup.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/stdio-setup.md)

### Quick Start

1. Install prerequisites (Gemini CLI, FastMCP, Python 3.11+)
2. Copy STDIO configuration template to Gemini CLI config:
   - **macOS/Linux**: `~/.config/gemini-cli/config.json`
   - **Windows**: `%APPDATA%\gemini-cli\config.json`
3. Update `PYTHONPATH` to your project directory
4. Restart Gemini CLI: `gemini restart`
5. Verify: Ask Gemini "What Hansard tools are available?"

**Configuration Template**: [examples/stdio-config.json](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/stdio-config.json)

**Automation Scripts**:
- Unix/macOS: [examples/stdio-quickstart.sh](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/stdio-quickstart.sh)
- Windows: [examples/stdio-quickstart.ps1](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/stdio-quickstart.ps1)

---

## Remote SSE Setup

**Use Case**: Production access, team collaboration, shared cloud database

**Setup Time**: 15 minutes

**Transport**: SSE (Server-Sent Events over HTTPS)

**Complete Guide**: [sse-setup.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/sse-setup.md)

### Quick Start

1. Verify Cloud Run service is deployed
2. Generate authentication token: `gcloud auth print-identity-token`
3. Copy SSE configuration template to Gemini CLI config
4. Update `url` with your Cloud Run service URL
5. Update `Authorization` header with generated token
6. Restart Gemini CLI: `gemini restart`
7. Verify: Execute search query and check results

**Configuration Template**: [examples/sse-config.json](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/sse-config.json)

**Automation Script**: [examples/sse-token-refresh.sh](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/sse-token-refresh.sh)

---

## Troubleshooting

**Common Issues**:
- Connection failures (STDIO process not starting, SSE endpoint unreachable)
- Authentication errors (expired tokens, missing credentials)
- Version compatibility (Gemini CLI, FastMCP, Python mismatches)
- Data issues (empty database, query errors)

**Complete Troubleshooting Guide**: [troubleshooting.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md)

### Quick Diagnostics

**STDIO Connection Issues**:
```bash
# Test server manually
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

# Check Gemini CLI logs
cat ~/.config/gemini-cli/logs/mcp.log  # macOS/Linux
type %APPDATA%\gemini-cli\logs\mcp.log  # Windows
```

**SSE Connection Issues**:
```bash
# Verify Cloud Run service is accessible
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://YOUR-SERVICE-URL.a.run.app/health

# Check token validity
gcloud auth print-identity-token --verbosity=debug
```

---

## Test Scenarios

**Purpose**: Verify correct setup with standardized test cases

**Complete Test Guide**: [test-scenarios.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/test-scenarios.md)

**Test Scenarios JSON**: [examples/test-scenarios.json](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/test-scenarios.json)

### Core Tests

| Test | Description | Priority | Time |
|------|-------------|----------|------|
| **Tool Discovery** | Verify Gemini can list all three Hansard tools | P1 | 5 min |
| **Search Query** | Execute hansard_search and get results | P1 | 10 min |
| **Fetch by ID** | Retrieve complete speech text using hansard_fetch | P2 | 5 min |
| **Ingest Speech** | Add new speech to database (local only) | P3 | 5 min |

**Success Criteria**: All P1 tests pass (Tool Discovery + Search Query)

---

## Configuration Examples

All configuration templates are located in the [examples/](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/) directory:

| File | Purpose | Transport |
|------|---------|-----------|
| `stdio-config.json` | Local development configuration | STDIO |
| `sse-config.json` | Remote Cloud Run configuration | SSE |
| `test-scenarios.json` | Test case definitions | Both |
| `stdio-quickstart.sh` | Unix/macOS automated setup | STDIO |
| `stdio-quickstart.ps1` | Windows automated setup | STDIO |
| `sse-token-refresh.sh` | Token generation automation | SSE |

---

## Platform-Specific Notes

### macOS

- Gemini CLI config: `~/.config/gemini-cli/config.json`
- Use absolute paths: `/Users/username/projects/skai-fastmcp-cloudrun`
- Check PATH for fastmcp: `which fastmcp`

### Linux

- Gemini CLI config: `~/.config/gemini-cli/config.json`
- Use absolute paths: `/home/username/skai-fastmcp-cloudrun`
- Check PATH for fastmcp: `which fastmcp`

### Windows

- Gemini CLI config: `%APPDATA%\gemini-cli\config.json`
- Use forward slashes in paths: `C:/Users/Username/Projects/skai-fastmcp-cloudrun`
- PowerShell execution policy: Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` if scripts are blocked
- Check PATH for fastmcp: `where fastmcp`

---

## Version Compatibility

| Component | Minimum Version | Recommended Version | Notes |
|-----------|----------------|---------------------|-------|
| Gemini CLI | v1.0.0 | Latest | Check: `gemini --version` |
| FastMCP | v2.14.0 | v2.14.0+ | OAuth Proxy support required |
| Python | 3.11 | 3.11 or 3.12 | Cloud Run compatible versions |
| uv | - | Latest | Package manager for dependencies |

---

## Support and Resources

### Documentation

- **Local Setup**: [stdio-setup.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/stdio-setup.md)
- **Remote Setup**: [sse-setup.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/sse-setup.md)
- **Troubleshooting**: [troubleshooting.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md)
- **Testing**: [test-scenarios.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/test-scenarios.md)

### Project Resources

- **Project README**: [/home/user/skai-fastmcp-cloudrun/README.md](/home/user/skai-fastmcp-cloudrun/README.md)
- **Feature Specification**: [/home/user/skai-fastmcp-cloudrun/specs/009-gemini-cli-integration/spec.md](/home/user/skai-fastmcp-cloudrun/specs/009-gemini-cli-integration/spec.md)
- **Configuration Contracts**: [/home/user/skai-fastmcp-cloudrun/specs/009-gemini-cli-integration/contracts/](/home/user/skai-fastmcp-cloudrun/specs/009-gemini-cli-integration/contracts/)

### Additional Help

- **Database Setup**: [/home/user/skai-fastmcp-cloudrun/specs/001-hansard-rag-implementation/quickstart.md](/home/user/skai-fastmcp-cloudrun/specs/001-hansard-rag-implementation/quickstart.md)
- **Cloud Run Deployment**: [/home/user/skai-fastmcp-cloudrun/deployment/](/home/user/skai-fastmcp-cloudrun/deployment/)
- **OAuth Configuration**: [/home/user/skai-fastmcp-cloudrun/specs/002-github-oauth-docker/](/home/user/skai-fastmcp-cloudrun/specs/002-github-oauth-docker/)

---

## Next Steps

### For Local Development

1. Complete STDIO setup following [stdio-setup.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/stdio-setup.md)
2. Initialize local database: `python scripts/init_database.py --local`
3. Load sample data: `python scripts/ingest_sample.py`
4. Run test scenarios: Follow [test-scenarios.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/test-scenarios.md)

### For Production Access

1. Deploy to Cloud Run (see deployment docs)
2. Complete SSE setup following [sse-setup.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/sse-setup.md)
3. Configure token refresh automation
4. Run test scenarios against Cloud Run endpoint

---

**Last Updated**: 2025-10-23

**Feature**: 009-gemini-cli-integration

**Status**: Complete
