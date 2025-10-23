# Troubleshooting Guide

**Purpose**: Resolve common Gemini CLI + Hansard MCP setup issues independently

**Goal**: 80% self-service resolution without external support

**Coverage**: STDIO transport (local) and SSE transport (remote Cloud Run)

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Connection Issues](#connection-issues)
3. [Authentication Issues](#authentication-issues)
4. [Version Compatibility Issues](#version-compatibility-issues)
5. [Data Issues](#data-issues)
6. [Performance Issues](#performance-issues)
7. [Platform-Specific Issues](#platform-specific-issues)

---

## Quick Diagnostics

### Run These Commands First

**Check Gemini CLI Status**:
```bash
gemini --version
gemini status
```

**Check Server Configuration** (STDIO):
```bash
# Test server manually
cd /path/to/skai-fastmcp-cloudrun
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py
```

**Check Service Status** (SSE):
```bash
# Test Cloud Run endpoint
TOKEN=$(gcloud auth print-identity-token)
curl -H "Authorization: Bearer $TOKEN" \
  https://YOUR-SERVICE-URL.a.run.app/health
```

**Check Gemini CLI Logs**:
```bash
# macOS/Linux
tail -f ~/.config/gemini-cli/logs/mcp.log

# Windows
Get-Content $env:APPDATA\gemini-cli\logs\mcp.log -Wait
```

---

## Connection Issues

### Issue 1: "Cannot find command 'fastmcp'"

**Symptom**:
```
Error: Command not found: fastmcp
'fastmcp' is not recognized as an internal or external command
```

**Applies To**: STDIO transport only

**Diagnosis**:
```bash
# Check if fastmcp is in PATH
which fastmcp  # macOS/Linux
where fastmcp  # Windows

# Test FastMCP directly
fastmcp --version
```

**Root Causes**:
1. FastMCP not installed
2. FastMCP not in system PATH
3. Wrong fastmcp executable path in config

**Solutions**:

**Solution 1: Install FastMCP**
```bash
cd /path/to/skai-fastmcp-cloudrun
uv sync
```

**Solution 2: Use Absolute Path**

Update config.json to use full path to fastmcp:

**macOS/Linux**:
```json
{
  "mcpServers": {
    "hansard": {
      "command": "/home/user/.local/bin/fastmcp",
      "args": ["run", "src/server.py"]
    }
  }
}
```

**Windows**:
```json
{
  "mcpServers": {
    "hansard": {
      "command": "C:/Users/Alice/.local/bin/fastmcp.exe",
      "args": ["run", "src/server.py"]
    }
  }
}
```

**Solution 3: Add PATH to Environment**
```json
{
  "mcpServers": {
    "hansard": {
      "command": "fastmcp",
      "env": {
        "PATH": "/home/user/.local/bin:$PATH"
      }
    }
  }
}
```

---

### Issue 2: "STDIO process not starting"

**Symptom**:
```
Error: Failed to start MCP server 'hansard'
Server process exited immediately
```

**Applies To**: STDIO transport only

**Diagnosis**:
```bash
# Run server manually to see actual error
cd /path/to/skai-fastmcp-cloudrun
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

# Check for Python errors
python --version
python -c "import src.server"
```

**Root Causes**:
1. Python import errors (wrong PYTHONPATH)
2. Missing dependencies
3. Database connection failure
4. Python version incompatibility

**Solutions**:

**Solution 1: Fix PYTHONPATH**

Ensure PYTHONPATH points to project root (not src/ subdirectory):

```json
{
  "mcpServers": {
    "hansard": {
      "env": {
        "PYTHONPATH": "/absolute/path/to/skai-fastmcp-cloudrun"
      }
    }
  }
}
```

**Solution 2: Install Missing Dependencies**
```bash
cd /path/to/skai-fastmcp-cloudrun
uv sync --reinstall
```

**Solution 3: Check Python Version**
```bash
python --version  # Must be 3.11 or higher

# If wrong version, specify Python path in config
"command": "/usr/bin/python3.11",
"args": ["-m", "fastmcp", "run", "src/server.py"]
```

---

### Issue 3: "SSE endpoint unreachable"

**Symptom**:
```
Error: Connection timeout to https://SERVICE.a.run.app
Failed to establish SSE connection
Could not reach server
```

**Applies To**: SSE transport only

**Diagnosis**:
```bash
# Test endpoint accessibility
curl -I https://YOUR-SERVICE-URL.a.run.app/health

# Check network connectivity
ping YOUR-SERVICE-URL.a.run.app

# Test with authentication
TOKEN=$(gcloud auth print-identity-token)
curl -H "Authorization: Bearer $TOKEN" \
  https://YOUR-SERVICE-URL.a.run.app/health
```

**Root Causes**:
1. Cloud Run service not deployed or stopped
2. Network/firewall blocking HTTPS
3. Wrong service URL
4. Service in different region with high latency

**Solutions**:

**Solution 1: Verify Service Deployment**
```bash
# Check service exists and is running
gcloud run services list | grep hansard

# Get service status
gcloud run services describe hansard-mcp-server

# Redeploy if needed
gcloud run deploy hansard-mcp-server \
  --image=gcr.io/PROJECT_ID/hansard-mcp:latest
```

**Solution 2: Verify URL**
```bash
# Get correct URL
gcloud run services describe hansard-mcp-server \
  --format='value(status.url)'

# Update config.json with correct URL
```

**Solution 3: Check Firewall/Proxy**
```bash
# Test if HTTPS is blocked
curl -I https://cloud.google.com

# If corporate proxy, configure proxy settings
export HTTPS_PROXY=http://proxy.company.com:8080
```

**Solution 4: Increase Timeout**
```json
{
  "mcpServers": {
    "hansard": {
      "timeout": 120
    }
  }
}
```

---

### Issue 4: "Connection timeout"

**Symptom**:
```
Error: Request timeout after 30 seconds
Connection to server timed out
```

**Applies To**: Both STDIO and SSE

**Diagnosis**:
```bash
# STDIO: Check server startup time
time DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

# SSE: Check Cloud Run cold start time
time curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://YOUR-SERVICE-URL.a.run.app/health
```

**Root Causes**:
1. Server slow to start (large dependencies)
2. Cloud Run cold start delay (10-30s)
3. Network latency
4. Database initialization slow

**Solutions**:

**Solution 1: Increase Timeout in Config**
```json
{
  "mcpServers": {
    "hansard": {
      "timeout": 60
    }
  }
}
```

**Solution 2: Set Minimum Instances** (SSE only)
```bash
# Prevent cold starts by keeping container warm
gcloud run services update hansard-mcp-server --min-instances=1
```

**Solution 3: Optimize Database Connection**
```bash
# Use connection pooling
# Set DATABASE_URL with connection parameters
DATABASE_URL="postgresql://user:pass@host/db?pool_size=5"
```

---

## Authentication Issues

### Issue 5: "Token expired" or "401 Unauthorized"

**Symptom**:
```
Error: 401 Unauthorized
Authentication failed
Token expired or invalid
```

**Applies To**: SSE transport only

**Diagnosis**:
```bash
# Test current token
TOKEN=$(gcloud auth print-identity-token)
curl -H "Authorization: Bearer $TOKEN" \
  https://YOUR-SERVICE-URL.a.run.app/health

# Check token expiration (if jwt CLI available)
jwt decode "$TOKEN" | grep exp
```

**Root Causes**:
1. Identity token expired (typically 1 hour lifetime)
2. Wrong token type used (access token vs identity token)
3. Token for wrong Google Cloud project

**Solutions**:

**Solution 1: Regenerate Token**
```bash
# Generate new identity token
TOKEN=$(gcloud auth print-identity-token)

# Update config.json Authorization header
# Use automation script:
bash /path/to/docs/gemini-cli/examples/sse-token-refresh.sh
```

**Solution 2: Use Correct Token Type**
```bash
# CORRECT for Cloud Run
gcloud auth print-identity-token

# WRONG for Cloud Run
gcloud auth print-access-token  # Don't use this
```

**Solution 3: Automate Token Refresh**
```bash
# Set up cron job to refresh token every 30 minutes
crontab -e
# Add line:
# */30 * * * * bash /path/to/sse-token-refresh.sh
```

---

### Issue 6: "Missing credentials" or "Permission denied"

**Symptom**:
```
Error: Permission denied
Missing IAM permissions
User does not have roles/run.invoker permission
```

**Applies To**: SSE transport only

**Diagnosis**:
```bash
# Check current user
gcloud auth list
gcloud config get-value account

# Check IAM policy for service
gcloud run services get-iam-policy hansard-mcp-server
```

**Root Causes**:
1. User not granted Cloud Run Invoker role
2. Service requires authentication but user is not authorized
3. Wrong Google Cloud project selected

**Solutions**:

**Solution 1: Grant IAM Permission**
```bash
# Grant yourself Cloud Run Invoker permission
gcloud run services add-iam-policy-binding hansard-mcp-server \
  --member="user:your-email@example.com" \
  --role="roles/run.invoker"
```

**Solution 2: Use Service Account**
```bash
# Create service account with access
gcloud iam service-accounts create gemini-cli-user

# Grant permission
gcloud run services add-iam-policy-binding hansard-mcp-server \
  --member="serviceAccount:gemini-cli-user@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Generate token using service account
gcloud auth print-identity-token \
  --impersonate-service-account=gemini-cli-user@PROJECT_ID.iam.gserviceaccount.com
```

**Solution 3: Deploy with Unauthenticated Access** (development only)
```bash
# WARNING: Only for development, not production
gcloud run deploy hansard-mcp-server --allow-unauthenticated
```

---

### Issue 7: "DANGEROUSLY_OMIT_AUTH not working"

**Symptom**:
```
Error: OAuth authentication required
GitHub OAuth not configured
```

**Applies To**: STDIO transport only

**Diagnosis**:
```bash
# Check if environment variable is set correctly
env | grep DANGEROUSLY_OMIT_AUTH

# Test server manually
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py
```

**Root Causes**:
1. Environment variable not set in config
2. Wrong value type (boolean instead of string)
3. Typo in variable name

**Solutions**:

**Solution 1: Use String Value**

**CORRECT**:
```json
{
  "env": {
    "DANGEROUSLY_OMIT_AUTH": "true"
  }
}
```

**WRONG**:
```json
{
  "env": {
    "DANGEROUSLY_OMIT_AUTH": true
  }
}
```

**Solution 2: Verify Environment Variable Name**

Exact spelling required: `DANGEROUSLY_OMIT_AUTH`

Common typos:
- `DANGEROUSLY_OMIT_AUTH` (correct)
- `DANGEROUSLY_SKIP_AUTH` (wrong)
- `SKIP_AUTH` (wrong)

---

## Version Compatibility Issues

### Issue 8: "Gemini CLI version incompatible"

**Symptom**:
```
Error: MCP protocol version mismatch
Unsupported server version
```

**Diagnosis**:
```bash
# Check versions
gemini --version
fastmcp --version
```

**Root Causes**:
1. Gemini CLI version too old (< v1.0.0)
2. FastMCP version too old (< v2.14.0)
3. Protocol changes between versions

**Solutions**:

**Solution 1: Update Gemini CLI**
```bash
npm update -g @google/gemini-cli
gemini --version
```

**Solution 2: Update FastMCP**
```bash
cd /path/to/skai-fastmcp-cloudrun
uv sync --upgrade
fastmcp --version
```

**Solution 3: Check Compatibility Matrix**

| Gemini CLI | FastMCP | Status |
|------------|---------|--------|
| v1.0.0+ | v2.14.0+ | ✓ Compatible |
| v0.9.x | v2.14.0+ | ⚠ Partial |
| < v0.9.0 | Any | ✗ Incompatible |

---

### Issue 9: "Python version incompatible"

**Symptom**:
```
Error: Python 3.11 or higher required
SyntaxError: invalid syntax
ModuleNotFoundError: No module named 'importlib.metadata'
```

**Diagnosis**:
```bash
# Check Python version
python --version
python3 --version

# Check which Python is used
which python
which python3
```

**Root Causes**:
1. Python version < 3.11
2. Multiple Python installations
3. Virtual environment using wrong Python

**Solutions**:

**Solution 1: Install Python 3.11+**
```bash
# macOS (using Homebrew)
brew install python@3.11

# Ubuntu/Debian
sudo apt install python3.11

# Windows
# Download from python.org
```

**Solution 2: Specify Python Path in Config**
```json
{
  "mcpServers": {
    "hansard": {
      "command": "/usr/bin/python3.11",
      "args": ["-m", "fastmcp", "run", "src/server.py"]
    }
  }
}
```

**Solution 3: Create Virtual Environment with Correct Python**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
uv sync
```

---

### Issue 10: "FastMCP version mismatch"

**Symptom**:
```
Error: FastMCP 2.14.0 or higher required
OAuth proxy not available in this version
```

**Diagnosis**:
```bash
# Check FastMCP version
fastmcp --version

# Check installed package version
pip list | grep fastmcp
uv pip list | grep fastmcp
```

**Root Causes**:
1. Old FastMCP version (< 2.14.0)
2. Multiple FastMCP installations
3. Cache not cleared after update

**Solutions**:

**Solution 1: Update FastMCP**
```bash
cd /path/to/skai-fastmcp-cloudrun
uv sync --upgrade-package fastmcp
```

**Solution 2: Reinstall FastMCP**
```bash
uv pip uninstall fastmcp
uv sync --reinstall
```

**Solution 3: Clear Cache**
```bash
uv cache clean
uv sync
```

---

## Data Issues

### Issue 11: "Database not initialized"

**Symptom**:
```
Error: no such table: speeches
Database file not found
sqlite3.OperationalError: no such table
```

**Applies To**: STDIO transport (local database)

**Diagnosis**:
```bash
# Check if database file exists
ls -la /path/to/skai-fastmcp-cloudrun/data/hansard.db

# Check database schema
sqlite3 /path/to/data/hansard.db ".schema"
```

**Root Causes**:
1. Database file doesn't exist
2. Database schema not initialized
3. Wrong database path in config

**Solutions**:

**Solution 1: Initialize Database**
```bash
cd /path/to/skai-fastmcp-cloudrun
python scripts/init_database.py --local
```

**Solution 2: Verify Database URL**

**CORRECT** (4 slashes for absolute path):
```json
{
  "env": {
    "DATABASE_URL": "sqlite:////absolute/path/to/hansard.db"
  }
}
```

**WRONG** (3 slashes - relative path):
```json
{
  "env": {
    "DATABASE_URL": "sqlite:///data/hansard.db"
  }
}
```

**Solution 3: Check File Permissions**
```bash
# Verify file is readable
ls -l /path/to/data/hansard.db

# Fix permissions if needed
chmod 644 /path/to/data/hansard.db
```

---

### Issue 12: "Empty search results" or "No speeches found"

**Symptom**:
```
Search returned 0 results
No speeches match your query
Database appears to be empty
```

**Diagnosis**:
```bash
# Check database has data
sqlite3 /path/to/data/hansard.db "SELECT COUNT(*) FROM speeches;"

# Check specific search
sqlite3 /path/to/data/hansard.db \
  "SELECT COUNT(*) FROM speeches WHERE content LIKE '%climate%';"
```

**Root Causes**:
1. Database is empty (no speeches ingested)
2. Search query too specific
3. Database doesn't contain relevant speeches

**Solutions**:

**Solution 1: Load Sample Data**
```bash
cd /path/to/skai-fastmcp-cloudrun
python scripts/ingest_sample.py
```

**Solution 2: Try Broader Search**

Instead of:
```
Search for speeches about "climate change renewable energy policy 2023"
```

Try:
```
Search for speeches about climate
```

**Solution 3: Verify Database Connection**
```bash
# Test database directly
python -c "
import sqlite3
conn = sqlite3.connect('/path/to/data/hansard.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM speeches')
print('Total speeches:', cursor.fetchone()[0])
conn.close()
"
```

---

### Issue 13: "Query execution errors"

**Symptom**:
```
Error executing query
Database query failed
SQLAlchemy error: ...
```

**Diagnosis**:
```bash
# Check database integrity
sqlite3 /path/to/data/hansard.db "PRAGMA integrity_check;"

# Check for locks
lsof /path/to/data/hansard.db  # macOS/Linux
```

**Root Causes**:
1. Database file corrupted
2. Database locked by another process
3. SQL syntax error in query

**Solutions**:

**Solution 1: Close Other Database Connections**
```bash
# Find processes using database
lsof /path/to/data/hansard.db

# Kill processes if needed
pkill -f "sqlite3.*hansard"
```

**Solution 2: Rebuild Database**
```bash
# Backup existing data
cp data/hansard.db data/hansard.db.backup

# Reinitialize
python scripts/init_database.py --local --force
python scripts/ingest_sample.py
```

**Solution 3: Check Disk Space**
```bash
df -h /path/to/skai-fastmcp-cloudrun/data
```

---

## Performance Issues

### Issue 14: "Slow query responses"

**Symptom**:
```
Query takes more than 10 seconds
Slow response times
```

**Diagnosis**:
```bash
# Time queries manually
time sqlite3 /path/to/data/hansard.db \
  "SELECT * FROM speeches WHERE content LIKE '%climate%' LIMIT 10;"

# Check database size
du -h /path/to/data/hansard.db
```

**Root Causes**:
1. Large database without indexes
2. Complex queries
3. Slow disk I/O
4. Cloud Run cold start (SSE only)

**Solutions**:

**Solution 1: Add Database Indexes**
```bash
# Run database optimization
python scripts/optimize_database.py
```

**Solution 2: Increase Timeout**
```json
{
  "mcpServers": {
    "hansard": {
      "timeout": 120
    }
  }
}
```

**Solution 3: Use Cloud SQL** (for large datasets)

See deployment documentation for Cloud SQL setup.

---

## Platform-Specific Issues

### macOS Issues

**Issue 15: "PATH not found for fastmcp"**

**Solution**:
```bash
# Add to ~/.zshrc or ~/.bash_profile
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.zshrc
```

**Issue 16: "Permission denied when creating config"**

**Solution**:
```bash
# Ensure config directory has correct permissions
chmod 755 ~/.config/gemini-cli
```

---

### Windows Issues

**Issue 17: "PowerShell execution policy blocked"**

**Solution**:
```powershell
# Set execution policy for current user
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or run script with bypass
PowerShell.exe -ExecutionPolicy Bypass -File script.ps1
```

**Issue 18: "Path with spaces causes errors"**

**Solution**:

Use quotes around paths with spaces:

```json
{
  "env": {
    "PYTHONPATH": "C:/Users/John Doe/Projects/skai-fastmcp-cloudrun"
  }
}
```

**Issue 19: "Backslashes in paths"**

**Solution**:

Use forward slashes in JSON config (Windows accepts both):

**CORRECT**:
```json
"PYTHONPATH": "C:/Users/Alice/Projects/skai-fastmcp-cloudrun"
```

**WRONG**:
```json
"PYTHONPATH": "C:\\Users\\Alice\\Projects\\skai-fastmcp-cloudrun"
```

---

### Linux Issues

**Issue 20: "Permission denied for database file"**

**Solution**:
```bash
# Fix file permissions
chmod 644 /path/to/data/hansard.db
chmod 755 /path/to/data

# Fix ownership if needed
chown $USER:$USER /path/to/data/hansard.db
```

**Issue 21: "Cannot connect to X11 display"**

**Solution**:

Not needed for Gemini CLI. If running headless:
```bash
export DISPLAY=:0
```

---

## Still Need Help?

If you've tried the solutions above and still have issues:

1. **Check Logs**:
   - Gemini CLI logs: `~/.config/gemini-cli/logs/mcp.log`
   - Server logs: Run manually with verbose output

2. **Run Test Scenarios**:
   - [test-scenarios.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/test-scenarios.md)
   - Identify which specific test fails

3. **Review Setup Guides**:
   - [stdio-setup.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/stdio-setup.md)
   - [sse-setup.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/sse-setup.md)

4. **Check Configuration Examples**:
   - [examples/stdio-config.json](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/stdio-config.json)
   - [examples/sse-config.json](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/sse-config.json)

---

**Last Updated**: 2025-10-23

**Feature**: 009-gemini-cli-integration

**User Story**: US3 - Comprehensive Setup Documentation
