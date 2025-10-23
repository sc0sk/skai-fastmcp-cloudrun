# Quickstart: Gemini CLI + Hansard MCP (Local STDIO)

**Goal**: Connect Google Gemini CLI to your local Hansard MCP server in under 5 minutes.

**Transport**: STDIO (local process communication)
**Use Case**: Local development, testing, offline access

---

## Prerequisites

### 1. Install Google Gemini CLI

**macOS/Linux**:
```bash
# Install Gemini CLI (official installation command)
npm install -g @google/gemini-cli

# Verify installation
gemini --version
```

**Windows**:
```powershell
# Install via npm
npm install -g @google/gemini-cli

# Verify installation
gemini --version
```

**Required Version**: Gemini CLI v1.0.0 or higher

### 2. Install FastMCP and Dependencies

```bash
# Navigate to Hansard MCP project
cd /path/to/skai-fastmcp-cloudrun

# Install Python dependencies (using uv)
uv sync

# Verify FastMCP installation
fastmcp --version
```

**Required Versions**:
- Python 3.11+
- FastMCP 2.14.0+

### 3. Initialize Local Database (Optional)

If you want to test with real data:

```bash
# Initialize SQLite database for local development
python scripts/init_database.py --local

# Load sample Hansard speeches
python scripts/ingest_sample.py
```

---

## Quick Setup (5 Minutes)

### Step 1: Locate Gemini CLI Configuration

Find your Gemini CLI configuration file:

**macOS/Linux**:
```bash
# Configuration file location
~/.config/gemini-cli/config.json

# Create directory if it doesn't exist
mkdir -p ~/.config/gemini-cli
```

**Windows**:
```powershell
# Configuration file location
%APPDATA%\gemini-cli\config.json

# Create directory if it doesn't exist
New-Item -Path "$env:APPDATA\gemini-cli" -ItemType Directory -Force
```

### Step 2: Add Hansard MCP Server Configuration

Open `config.json` in your editor and add the Hansard server configuration:

**Template** (copy-paste ready):

```json
{
  "mcpServers": {
    "hansard": {
      "command": "fastmcp",
      "args": ["run", "src/server.py"],
      "env": {
        "DANGEROUSLY_OMIT_AUTH": "true",
        "DATABASE_URL": "sqlite:///data/hansard.db",
        "PYTHONPATH": "/ABSOLUTE/PATH/TO/skai-fastmcp-cloudrun"
      },
      "description": "Australian Hansard parliamentary speech search"
    }
  }
}
```

**Important**: Replace `/ABSOLUTE/PATH/TO/skai-fastmcp-cloudrun` with your actual project path.

**Example** (macOS):
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

**Example** (Windows):
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

### Step 3: Restart Gemini CLI

```bash
# Restart Gemini CLI to load new configuration
gemini restart

# Or start fresh session
gemini
```

---

## Verification (3 Tests)

### Test 1: Tool Discovery

**Command**: In Gemini CLI, ask:
```
What MCP tools are available from the Hansard server?
```

**Expected Response**:
Gemini should list three tools:
- `hansard_search` - Search parliamentary speeches
- `hansard_fetch` - Retrieve full speech by ID
- `hansard_ingest` - Add new speeches to database

**Success Criteria**: All three tool names appear in response.

### Test 2: Search Query

**Command**: In Gemini CLI, ask:
```
Search Hansard for speeches about climate change policy in the last year.
```

**Expected Response**:
Gemini executes `hansard_search` and returns results including:
- Speaker names
- Speech dates
- Chamber (House/Senate)
- Text excerpts mentioning climate change

**Success Criteria**: At least 1 search result with complete metadata.

**Note**: If database is empty, you'll get zero results. Run `python scripts/ingest_sample.py` first.

### Test 3: Fetch Speech

**Command**: Get a speech ID from Test 2 results, then ask:
```
Fetch the full text of Hansard speech ID [SPEECH_ID].
```

**Expected Response**:
Gemini executes `hansard_fetch` and returns:
- Complete speech text (full transcript)
- Speaker name and party
- Date and time
- Chamber (House of Representatives or Senate)

**Success Criteria**: Full speech text displayed (not just excerpt).

---

## Troubleshooting

### Issue 1: "Cannot find command 'fastmcp'"

**Symptom**: Gemini CLI reports `Command not found: fastmcp`

**Diagnosis**:
```bash
# Check if fastmcp is in PATH
which fastmcp  # macOS/Linux
where fastmcp  # Windows
```

**Solutions**:
1. Verify FastMCP is installed: `fastmcp --version`
2. Use absolute path to fastmcp in config:
   ```json
   "command": "/home/user/.local/bin/fastmcp"
   ```
3. Add FastMCP to PATH in `env` section:
   ```json
   "env": {
     "PATH": "/home/user/.local/bin:$PATH"
   }
   ```

### Issue 2: "ModuleNotFoundError: No module named 'src'"

**Symptom**: Server fails to start with Python import error

**Diagnosis**:
```bash
# Verify PYTHONPATH is correct
echo $PYTHONPATH  # macOS/Linux
echo %PYTHONPATH%  # Windows
```

**Solutions**:
1. Set `PYTHONPATH` to project root (not `src/` subdirectory):
   ```json
   "env": {
     "PYTHONPATH": "/absolute/path/to/skai-fastmcp-cloudrun"
   }
   ```
2. Verify `src/server.py` exists at correct location
3. Use absolute paths (avoid `~` or `%USERPROFILE%`)

### Issue 3: "No tools available" or Empty Tool List

**Symptom**: Gemini doesn't show Hansard tools

**Diagnosis**:
```bash
# Test server manually
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

# Check for errors in output
```

**Solutions**:
1. Verify server starts without errors
2. Check `DANGEROUSLY_OMIT_AUTH=true` is set (bypasses OAuth in dev)
3. Restart Gemini CLI: `gemini restart`
4. Review Gemini CLI logs for connection errors:
   ```bash
   # macOS/Linux
   cat ~/.config/gemini-cli/logs/mcp.log

   # Windows
   type %APPDATA%\gemini-cli\logs\mcp.log
   ```

---

## Next Steps

### Option 1: Test with Real Data

Load sample Hansard speeches:
```bash
# Download sample data (if not already done)
python scripts/download_sample_data.py

# Ingest into local database
python scripts/ingest_sample.py
```

### Option 2: Configure Remote SSE Connection

For production use with Cloud Run deployment, see:
- **Remote Setup Guide**: `docs/gemini-cli/remote-setup.md`
- **SSE Configuration Example**: `specs/009-gemini-cli-integration/contracts/sse-config.json`

### Option 3: Run Full Test Suite

Execute all verification scenarios:
```bash
# Review test scenarios
cat specs/009-gemini-cli-integration/contracts/test-scenarios.json

# Run each test in Gemini CLI
# (Manual execution - see test-scenarios.json for details)
```

---

## Configuration Reference

### Minimal STDIO Configuration

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

### Full STDIO Configuration (All Options)

```json
{
  "mcpServers": {
    "hansard": {
      "command": "fastmcp",
      "args": ["run", "src/server.py", "--port", "8080"],
      "env": {
        "DANGEROUSLY_OMIT_AUTH": "true",
        "DATABASE_URL": "sqlite:////absolute/path/to/hansard.db",
        "PYTHONPATH": "/absolute/path/to/skai-fastmcp-cloudrun",
        "LOG_LEVEL": "DEBUG"
      },
      "timeout": 30,
      "description": "Australian Hansard parliamentary speech search (local dev)"
    }
  }
}
```

### Environment Variables Explained

| Variable | Required | Purpose | Example |
|----------|----------|---------|---------|
| `DANGEROUSLY_OMIT_AUTH` | Yes (dev) | Bypass OAuth for local testing | `"true"` |
| `DATABASE_URL` | Optional | Database connection string | `"sqlite:///data/hansard.db"` |
| `PYTHONPATH` | Recommended | Python import path | `"/path/to/project"` |
| `LOG_LEVEL` | Optional | Logging verbosity | `"DEBUG"`, `"INFO"` |

---

## Support

**Full Documentation**: `/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/`

**Issues**:
- Connection problems: See `docs/gemini-cli/troubleshooting.md`
- Remote SSE setup: See `docs/gemini-cli/remote-setup.md`
- Database issues: See `docs/database-setup.md`

**Version Compatibility**:
- Gemini CLI: v1.0.0+
- FastMCP: v2.14.0+
- Python: 3.11+
