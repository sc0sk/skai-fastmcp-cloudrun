# Local STDIO Setup Guide

**Goal**: Connect Google Gemini CLI to your local Hansard MCP server in 5-10 minutes

**Transport**: STDIO (Standard Input/Output - direct process communication)

**Use Case**: Local development, testing, offline access to Hansard data

**Target Time**: 5-10 minutes from start to verified working setup

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Setup (5 Minutes)](#quick-setup-5-minutes)
3. [Verification (3 Tests)](#verification-3-tests)
4. [Troubleshooting](#troubleshooting)
5. [Configuration Reference](#configuration-reference)
6. [Next Steps](#next-steps)

---

## Prerequisites

### 1. Install Google Gemini CLI

**macOS/Linux**:
```bash
# Install Gemini CLI via npm
npm install -g @google/gemini-cli

# Verify installation
gemini --version
```

**Windows**:
```powershell
# Install Gemini CLI via npm
npm install -g @google/gemini-cli

# Verify installation
gemini --version
```

**Required Version**: Gemini CLI v1.0.0 or higher

**Common Issues**:
- If `npm` is not found, install Node.js first: https://nodejs.org/
- If permission denied, use `sudo npm install -g @google/gemini-cli` (macOS/Linux)

---

### 2. Install FastMCP and Dependencies

```bash
# Navigate to Hansard MCP project directory
cd /path/to/skai-fastmcp-cloudrun

# Install Python dependencies using uv
uv sync

# Verify FastMCP installation
fastmcp --version
```

**Required Versions**:
- Python 3.11+
- FastMCP 2.14.0+
- uv (latest)

**Verify Python Version**:
```bash
python --version  # Should show 3.11 or higher
```

**If FastMCP is not in PATH**:
```bash
# Find FastMCP location
which fastmcp  # macOS/Linux
where fastmcp  # Windows

# Note the absolute path for configuration step
```

---

### 3. Initialize Local Database (Optional)

If you want to test with real Hansard data:

```bash
# Initialize SQLite database for local development
python scripts/init_database.py --local

# Load sample Hansard speeches (recommended for testing)
python scripts/ingest_sample.py
```

**Note**: You can skip this step and use an empty database for initial setup verification. Some test queries will return zero results until data is loaded.

---

## Quick Setup (5 Minutes)

### Step 1: Locate Gemini CLI Configuration File

Find your Gemini CLI configuration directory:

**macOS/Linux**:
```bash
# Configuration file location
~/.config/gemini-cli/config.json

# Create directory if it doesn't exist
mkdir -p ~/.config/gemini-cli

# Verify directory exists
ls -la ~/.config/gemini-cli/
```

**Windows**:
```powershell
# Configuration file location
$env:APPDATA\gemini-cli\config.json

# Create directory if it doesn't exist
New-Item -Path "$env:APPDATA\gemini-cli" -ItemType Directory -Force

# Verify directory exists
dir $env:APPDATA\gemini-cli\
```

---

### Step 2: Add Hansard MCP Server Configuration

Open `config.json` in your text editor and add the Hansard server configuration.

**Quick Command** (macOS/Linux):
```bash
# Open in default editor
nano ~/.config/gemini-cli/config.json
# OR
code ~/.config/gemini-cli/config.json  # If using VS Code
```

**Quick Command** (Windows):
```powershell
# Open in Notepad
notepad "$env:APPDATA\gemini-cli\config.json"
```

---

### Configuration Template (Copy-Paste Ready)

**Replace `/ABSOLUTE/PATH/TO/skai-fastmcp-cloudrun` with your actual project path!**

```json
{
  "mcpServers": {
    "hansard": {
      "command": "fastmcp",
      "args": ["run", "src/server.py"],
      "env": {
        "DANGEROUSLY_OMIT_AUTH": "true",
        "DATABASE_URL": "sqlite:////absolute/path/to/skai-fastmcp-cloudrun/data/hansard.db",
        "PYTHONPATH": "/absolute/path/to/skai-fastmcp-cloudrun"
      },
      "description": "Australian Hansard parliamentary speech search"
    }
  }
}
```

**Important Notes**:
- Use **absolute paths** only (no `~`, `$HOME`, `%USERPROFILE%`)
- SQLite URLs need **4 slashes** for absolute paths: `sqlite:////path/to/file.db`
- Windows paths use **forward slashes**: `C:/Users/Alice/Projects/...`

---

### Platform-Specific Examples

**macOS Example**:
```json
{
  "mcpServers": {
    "hansard": {
      "command": "fastmcp",
      "args": ["run", "src/server.py"],
      "env": {
        "DANGEROUSLY_OMIT_AUTH": "true",
        "DATABASE_URL": "sqlite:////Users/alice/projects/skai-fastmcp-cloudrun/data/hansard.db",
        "PYTHONPATH": "/Users/alice/projects/skai-fastmcp-cloudrun"
      },
      "description": "Australian Hansard parliamentary speech search"
    }
  }
}
```

**Linux Example**:
```json
{
  "mcpServers": {
    "hansard": {
      "command": "fastmcp",
      "args": ["run", "src/server.py"],
      "env": {
        "DANGEROUSLY_OMIT_AUTH": "true",
        "DATABASE_URL": "sqlite:////home/user/skai-fastmcp-cloudrun/data/hansard.db",
        "PYTHONPATH": "/home/user/skai-fastmcp-cloudrun"
      },
      "description": "Australian Hansard parliamentary speech search"
    }
  }
}
```

**Windows Example**:
```json
{
  "mcpServers": {
    "hansard": {
      "command": "fastmcp",
      "args": ["run", "src/server.py"],
      "env": {
        "DANGEROUSLY_OMIT_AUTH": "true",
        "DATABASE_URL": "sqlite:///C:/Users/Alice/Projects/skai-fastmcp-cloudrun/data/hansard.db",
        "PYTHONPATH": "C:/Users/Alice/Projects/skai-fastmcp-cloudrun"
      },
      "description": "Australian Hansard parliamentary speech search"
    }
  }
}
```

---

### Step 3: Restart Gemini CLI

After saving the configuration file, restart Gemini CLI to load the new configuration:

```bash
# Option 1: Restart existing session
gemini restart

# Option 2: Start fresh session
gemini

# Option 3: Force reload configuration
gemini --reload-config
```

**Success Indicator**: Gemini CLI should start without errors. If you see connection errors, check the troubleshooting section below.

---

## Verification (3 Tests)

Run these three tests to confirm your setup is working correctly.

### Test 1: Tool Discovery (5 seconds)

**Purpose**: Verify that Gemini CLI can discover the three Hansard MCP tools

**Command**: In Gemini CLI, ask:
```
What MCP tools are available from the Hansard server?
```

**Alternative Questions**:
- "List all available Hansard tools"
- "Show me the Hansard MCP capabilities"
- "What can I do with the Hansard server?"

**Expected Response**:
Gemini should list three tools with their descriptions:

```
Available Hansard tools:
1. hansard_search - Search Australian parliamentary speeches by keywords
2. hansard_fetch - Retrieve full speech text by ID
3. hansard_ingest - Add new speeches to the database
```

**Success Criteria**:
- All three tool names appear: `hansard_search`, `hansard_fetch`, `hansard_ingest`
- Each tool has a description explaining its purpose
- No connection errors or timeout messages

**If this test fails**, see [Troubleshooting - Issue 3](#issue-3-no-tools-available-or-empty-tool-list).

---

### Test 2: Search Query (10 seconds)

**Purpose**: Verify that `hansard_search` tool executes successfully and returns results

**Command**: In Gemini CLI, ask:
```
Search Hansard for speeches about climate change policy in the last year.
```

**Alternative Questions**:
- "Find parliamentary speeches discussing climate change"
- "Search for climate policy debates in Hansard"
- "Show me speeches about renewable energy"

**Expected Response**:
Gemini executes `hansard_search` and returns results including:
- Speaker names
- Speech dates
- Chamber (House of Representatives or Senate)
- Text excerpts mentioning your search terms

**Example Output**:
```
Found 3 speeches about climate change:

1. Speaker: Hon. Anthony Albanese MP
   Date: 2023-09-15
   Chamber: House of Representatives
   Excerpt: "...our government is committed to climate action and reducing emissions by 43% by 2030..."

2. Speaker: Sen. Penny Wong
   Date: 2023-08-22
   Chamber: Senate
   Excerpt: "...climate change is the defining challenge of our generation..."
```

**Success Criteria**:
- At least 1 search result is returned
- Results include speaker name, date, chamber, and text excerpt
- No database errors or query failures

**Note**: If you get zero results, your database may be empty. Run `python scripts/ingest_sample.py` to load sample data.

**If this test fails**, see [Troubleshooting - Data Issues](#data-issues).

---

### Test 3: Fetch Speech by ID (5 seconds)

**Purpose**: Verify that `hansard_fetch` tool retrieves complete speech text

**Prerequisite**: Complete Test 2 first to obtain a speech ID from search results

**Command**: Get a speech ID from Test 2 results, then ask:
```
Fetch the full text of Hansard speech ID [SPEECH_ID].
```

**Alternative Questions**:
- "Get the complete transcript for speech [SPEECH_ID]"
- "Show me the full text of speech [SPEECH_ID]"
- "Retrieve Hansard speech [SPEECH_ID]"

**Expected Response**:
Gemini executes `hansard_fetch` and returns:
- Complete speech text (full transcript, not just excerpt)
- Speaker name and party affiliation
- Date and time of speech
- Chamber (House of Representatives or Senate)

**Example Output**:
```
Speech ID: hansard-2023-09-15-reps-12345
Speaker: Hon. Anthony Albanese MP (Australian Labor Party)
Date: 2023-09-15 14:30:00
Chamber: House of Representatives

Full Text:
Mr. Speaker, I rise today to address this parliament on the critical issue of climate change and our government's comprehensive plan to achieve net zero emissions by 2050...

[Complete speech text continues for several paragraphs]
```

**Success Criteria**:
- Full speech text displayed (longer than search excerpt)
- Complete metadata (speaker, date, chamber, party)
- Speech ID matches the requested ID

**If this test fails**, see [Troubleshooting - Data Issues](#data-issues).

---

## Troubleshooting

### Issue 1: "Cannot find command 'fastmcp'"

**Symptom**: Gemini CLI reports `Command not found: fastmcp` or `'fastmcp' is not recognized`

**Diagnosis**:
```bash
# Check if fastmcp is in PATH
which fastmcp  # macOS/Linux
where fastmcp  # Windows

# Test FastMCP directly
fastmcp --version
```

**Solution A - Add FastMCP to PATH**:

**macOS/Linux**:
```json
{
  "mcpServers": {
    "hansard": {
      "command": "fastmcp",
      "args": ["run", "src/server.py"],
      "env": {
        "PATH": "/home/user/.local/bin:$PATH",
        "DANGEROUSLY_OMIT_AUTH": "true",
        "PYTHONPATH": "/absolute/path/to/skai-fastmcp-cloudrun"
      }
    }
  }
}
```

**Solution B - Use Absolute Path to FastMCP**:
```json
{
  "mcpServers": {
    "hansard": {
      "command": "/home/user/.local/bin/fastmcp",
      "args": ["run", "src/server.py"],
      "env": {
        "DANGEROUSLY_OMIT_AUTH": "true",
        "PYTHONPATH": "/absolute/path/to/skai-fastmcp-cloudrun"
      }
    }
  }
}
```

**Solution C - Reinstall FastMCP**:
```bash
cd /path/to/skai-fastmcp-cloudrun
uv sync --reinstall
```

---

### Issue 2: "ModuleNotFoundError: No module named 'src'"

**Symptom**: Server fails to start with Python import error:
```
ModuleNotFoundError: No module named 'src'
ImportError: cannot import name 'mcp' from 'src.server'
```

**Diagnosis**:
```bash
# Verify PYTHONPATH points to project root (not src/ subdirectory)
echo $PYTHONPATH  # macOS/Linux
echo %PYTHONPATH%  # Windows

# Verify src/server.py exists
ls /path/to/skai-fastmcp-cloudrun/src/server.py
```

**Solution A - Fix PYTHONPATH**:

Ensure `PYTHONPATH` points to the **project root**, not the `src/` subdirectory:

**Correct**:
```json
"env": {
  "PYTHONPATH": "/home/user/skai-fastmcp-cloudrun"
}
```

**Incorrect**:
```json
"env": {
  "PYTHONPATH": "/home/user/skai-fastmcp-cloudrun/src"
}
```

**Solution B - Use Absolute Paths Only**:

Avoid using `~`, `$HOME`, or `%USERPROFILE%`. Use full absolute paths:

**macOS**: `/Users/alice/projects/skai-fastmcp-cloudrun`
**Linux**: `/home/user/skai-fastmcp-cloudrun`
**Windows**: `C:/Users/Alice/Projects/skai-fastmcp-cloudrun`

**Solution C - Verify File Structure**:
```bash
# Verify project structure
ls -la /path/to/skai-fastmcp-cloudrun/
# Should show: src/, data/, specs/, etc.

ls -la /path/to/skai-fastmcp-cloudrun/src/
# Should show: server.py, models/, tools/, etc.
```

---

### Issue 3: "No tools available" or Empty Tool List

**Symptom**: Gemini CLI reports "No tools found" or doesn't show Hansard tools in the list

**Diagnosis**:
```bash
# Test server manually
cd /path/to/skai-fastmcp-cloudrun
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

# Check for errors in server output
# Server should start without errors and show available tools
```

**Solution A - Verify Server Starts**:

If manual test fails, check for:
- Python import errors (see Issue 2)
- Missing dependencies: `uv sync`
- Database connection errors

**Solution B - Verify DANGEROUSLY_OMIT_AUTH is Set**:

This environment variable bypasses OAuth in development mode:

```json
"env": {
  "DANGEROUSLY_OMIT_AUTH": "true"
}
```

**CRITICAL**: Value must be the string `"true"`, not boolean `true`.

**Solution C - Restart Gemini CLI**:
```bash
# Force restart
gemini restart

# Or quit and restart completely
# Press Ctrl+C to quit, then run 'gemini' again
```

**Solution D - Check Gemini CLI Logs**:

**macOS/Linux**:
```bash
cat ~/.config/gemini-cli/logs/mcp.log
tail -f ~/.config/gemini-cli/logs/mcp.log  # Follow in real-time
```

**Windows**:
```powershell
type $env:APPDATA\gemini-cli\logs\mcp.log
Get-Content $env:APPDATA\gemini-cli\logs\mcp.log -Wait  # Follow in real-time
```

Look for connection errors, timeout messages, or server startup failures.

---

### Data Issues

**Symptom**: Search returns zero results or "no speeches found"

**Diagnosis**:
```bash
# Check if database exists
ls -la /path/to/skai-fastmcp-cloudrun/data/hansard.db

# Check database has data
sqlite3 /path/to/skai-fastmcp-cloudrun/data/hansard.db "SELECT COUNT(*) FROM speeches;"
```

**Solution A - Initialize Database**:
```bash
cd /path/to/skai-fastmcp-cloudrun
python scripts/init_database.py --local
```

**Solution B - Load Sample Data**:
```bash
cd /path/to/skai-fastmcp-cloudrun
python scripts/ingest_sample.py
```

**Solution C - Verify Database URL**:

Ensure `DATABASE_URL` points to the correct file:

```json
"env": {
  "DATABASE_URL": "sqlite:////absolute/path/to/skai-fastmcp-cloudrun/data/hansard.db"
}
```

**Note**: SQLite URLs need **4 slashes** for absolute paths:
- Linux/macOS: `sqlite:////home/user/project/data/hansard.db`
- Windows: `sqlite:///C:/Users/Alice/project/data/hansard.db` (3 slashes because C: has a slash)

---

### Connection Timeout Issues

**Symptom**: Gemini CLI reports "Connection timeout" or "Server not responding"

**Solution A - Increase Timeout**:
```json
{
  "mcpServers": {
    "hansard": {
      "command": "fastmcp",
      "args": ["run", "src/server.py"],
      "timeout": 60,
      "env": { ... }
    }
  }
}
```

**Solution B - Check Server Performance**:
```bash
# Test server manually and observe startup time
time DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py
```

If startup takes more than 10 seconds, check:
- Database size (large databases slow down initialization)
- System resources (CPU, memory)
- Python virtual environment activation

---

## Configuration Reference

### Minimal STDIO Configuration

Bare minimum configuration for local development:

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

This uses default paths and assumes:
- FastMCP is in PATH
- Database is at default location
- Python can find `src/` module

---

### Full STDIO Configuration (All Options)

Complete configuration with all available options:

```json
{
  "mcpServers": {
    "hansard": {
      "command": "fastmcp",
      "args": ["run", "src/server.py", "--port", "8080"],
      "env": {
        "DANGEROUSLY_OMIT_AUTH": "true",
        "DATABASE_URL": "sqlite:////absolute/path/to/skai-fastmcp-cloudrun/data/hansard.db",
        "PYTHONPATH": "/absolute/path/to/skai-fastmcp-cloudrun",
        "LOG_LEVEL": "DEBUG"
      },
      "timeout": 30,
      "description": "Australian Hansard parliamentary speech search (local dev)"
    }
  }
}
```

---

### Environment Variables Explained

| Variable | Required | Purpose | Example |
|----------|----------|---------|---------|
| `DANGEROUSLY_OMIT_AUTH` | Yes (dev) | Bypass OAuth for local testing | `"true"` |
| `DATABASE_URL` | Optional | Database connection string | `"sqlite:///data/hansard.db"` |
| `PYTHONPATH` | Recommended | Python import path to project root | `"/path/to/project"` |
| `LOG_LEVEL` | Optional | Logging verbosity | `"DEBUG"`, `"INFO"`, `"WARNING"` |

**Important**:
- `DANGEROUSLY_OMIT_AUTH` must be the string `"true"`, not boolean `true`
- Never use `DANGEROUSLY_OMIT_AUTH` in production deployments
- `DATABASE_URL` defaults to `sqlite:///data/hansard.db` (relative to project root)

---

### Using Development Mode

For active development with auto-reload, use `dev` instead of `run`:

```json
{
  "mcpServers": {
    "hansard": {
      "command": "fastmcp",
      "args": ["dev", "src/server.py"],
      "env": {
        "DANGEROUSLY_OMIT_AUTH": "true"
      }
    }
  }
}
```

**Benefits**:
- Auto-reload on code changes
- More verbose logging
- Better error messages

**Note**: Development mode may be slower to start.

---

## Next Steps

### Option 1: Load Real Data

Populate your local database with Hansard speeches:

```bash
cd /path/to/skai-fastmcp-cloudrun

# Download sample Hansard data (if not already done)
python scripts/download_sample_data.py

# Ingest into local database
python scripts/ingest_sample.py

# Verify data loaded
sqlite3 data/hansard.db "SELECT COUNT(*) FROM speeches;"
```

---

### Option 2: Configure Remote SSE Connection

For production use with Cloud Run deployment:

**Complete Guide**: [sse-setup.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/sse-setup.md)

**Configuration Template**: [examples/sse-config.json](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/sse-config.json)

---

### Option 3: Run Full Test Suite

Execute all verification scenarios:

**Test Guide**: [test-scenarios.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/test-scenarios.md)

**Test Scenarios JSON**: [examples/test-scenarios.json](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/test-scenarios.json)

---

### Option 4: Automated Setup

Use provided scripts for one-command setup:

**Unix/macOS**:
```bash
bash /path/to/skai-fastmcp-cloudrun/docs/gemini-cli/examples/stdio-quickstart.sh
```

**Windows**:
```powershell
PowerShell.exe -ExecutionPolicy Bypass -File C:\path\to\skai-fastmcp-cloudrun\docs\gemini-cli\examples\stdio-quickstart.ps1
```

---

## Support

**Troubleshooting Guide**: [troubleshooting.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md)

**Test Scenarios**: [test-scenarios.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/test-scenarios.md)

**Configuration Examples**: [examples/](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/)

**Database Setup**: [specs/001-hansard-rag-implementation/quickstart.md](/home/user/skai-fastmcp-cloudrun/specs/001-hansard-rag-implementation/quickstart.md)

---

**Last Updated**: 2025-10-23

**Feature**: 009-gemini-cli-integration

**User Story**: US1 - Local Development with STDIO Transport
