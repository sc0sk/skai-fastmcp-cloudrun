# skai-fastmcp-cloudrun Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-22

## Active Technologies
- Python 3.11+ (Cloud Run compatibility) + FastMCP 2.14.0+ (tool annotations, metadata, icons) (001-chatgpt-devmode-enhancements)
- Python 3.11+ + FastMCP 2.12.5+, LangChain (langchain-google-vertexai, langchain-google-cloud-sql-pg), Pydantic v2 (004-search-fetch-mcp-tools)
- Cloud SQL PostgreSQL with pgvector extension (LangChain schema: langchain_pg_embedding + speeches metadata table) (004-search-fetch-mcp-tools)
- Python 3.11+ + FastMCP 2.12.5+ (existing), no new dependencies required (005-chatgpt-integration)
- N/A (metadata optimization only, no database changes) (005-chatgpt-integration)
- Python 3.11+ (Cloud Run compatibility requirement) + PyJWT (JWT validation), cryptography (RSA/ECDSA keys), httpx (HTTP introspection), Pydantic v2 (schemas), FastMCP 2.12.0+ (auth provider framework) (010-token-verification)
- N/A (stateless token validation, no persistent storage required) (010-token-verification)
- Python 3.11+ (Cloud Run compatibility) + FastMCP 2.13.0, py-key-value-aio 0.2.8+, cryptography 41.0.0+ (022-fastmcp-oauth-persistence)
- Cloud SQL PostgreSQL with existing `oauth_clients` table (022-fastmcp-oauth-persistence)

## Project Structure
```
src/
tests/
```

## Commands
cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style
Python 3.11+ (Cloud Run compatibility): Follow standard conventions

## Recent Changes
- 022-fastmcp-oauth-persistence: Added Python 3.11+ (Cloud Run compatibility) + FastMCP 2.13.0, py-key-value-aio 0.2.8+, cryptography 41.0.0+
- 020-fix-cloudrun-db-auth: Added Cloud Run IAM authentication tracking for Cloud SQL PostgreSQL connections
- 012-admin-markdown-ingestion: Added [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

<!-- MANUAL ADDITIONS START -->

## Cloud Run IAM Authentication (Feature 020)

### IAM Detection for Cloud SQL

The `CloudSQLEngine` class ([src/storage/cloud_sql_engine.py](src/storage/cloud_sql_engine.py)) implements 3-tier IAM user detection for Cloud SQL PostgreSQL connections:

**Detection Priority**:
1. **Metadata Service** (Cloud Run) - Primary method for production
   - Endpoint: `http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email`
   - Header: `Metadata-Flavor: Google`
   - Returns: Service account email (e.g., `666924716777-compute@developer.gserviceaccount.com`)

2. **Application Default Credentials (ADC)** - Local development
   - Method: `google.auth.default()`
   - Attribute: `credentials.service_account_email` or `credentials._service_account_email`
   - Filters: Rejects "default" placeholder value

3. **Gcloud Config** - Fallback for local development
   - Command: `gcloud config get-value account`
   - Returns: User or service account email from gcloud config

4. **Fallback** - Legacy default (not recommended)
   - Value: `"postgres"` (requires password authentication)
   - Marked as invalid (`iam_valid = False`)

### Tracking Properties

The `CloudSQLEngine` class exposes read-only properties for debugging and validation:

```python
engine_mgr = CloudSQLEngine(...)

# Check IAM detection status
print(engine_mgr.detected_iam_user)    # Service account email
print(engine_mgr.detection_method)     # "METADATA_SERVICE" | "ADC_CREDENTIALS" | "GCLOUD_CONFIG" | "FALLBACK"
print(engine_mgr.iam_valid)            # True if valid email detected, False for "default" or "postgres"
```

### Testing IAM Detection

**Unit Tests** (Cloud Run environment):
```bash
# Mock metadata service and ADC
pytest tests/test_cloud_run_iam_auth.py -v
# Tests: metadata service detection, "default" rejection, logging
```

**Integration Tests** (Local environment):
```bash
# Requires valid ADC or gcloud config
pytest tests/test_local_iam_auth.py -v
# Tests: ADC detection, gcloud fallback (skipped - requires Connector mock)
```

**Cloud Run Validation**:
```bash
# Debug endpoint shows IAM detection status
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://hansard-mcp-server-666924716777.us-central1.run.app/debug/iam-user
```

### Best Practices

1. **Always use IAM authentication** (no password storage):
   ```python
   engine_mgr = CloudSQLEngine(
       project_id="...",
       region="...",
       instance="...",
       database="...",
       user=None,        # Triggers IAM auth
       password=None,
   )
   ```

2. **Check detection status** in debug/troubleshooting:
   ```python
   if not engine_mgr.iam_valid:
       print(f"Warning: IAM detection failed, using {engine_mgr.detected_iam_user}")
       print(f"Detection method: {engine_mgr.detection_method}")
   ```

3. **Environment-specific detection**:
   - Cloud Run: Metadata service (automatic, most reliable)
   - Local: ADC via `gcloud auth application-default login`
   - CI/CD: Service account key file (set `GOOGLE_APPLICATION_CREDENTIALS`)

### Common Issues

**Issue**: `detected_iam_user = "default"` in Cloud Run
- **Cause**: ADC returning placeholder instead of actual email
- **Fix**: Metadata service takes priority (working as expected)

**Issue**: `iam_valid = False`
- **Cause**: No valid IAM credentials found
- **Fix**: Run `gcloud auth application-default login` or ensure Cloud Run service account has permissions

**Issue**: `FATAL: role "..." does not exist` in database
- **Cause**: Database user not created for service account email
- **Fix**: Run `CREATE USER "email@..." WITH LOGIN;` and `GRANT` permissions

### Documentation

- **Specification**: [specs/020-fix-cloudrun-db-auth/spec.md](specs/020-fix-cloudrun-db-auth/spec.md)
- **Implementation Plan**: [specs/020-fix-cloudrun-db-auth/plan.md](specs/020-fix-cloudrun-db-auth/plan.md)
- **Testing Guide**: [specs/020-fix-cloudrun-db-auth/quickstart.md](specs/020-fix-cloudrun-db-auth/quickstart.md)
- **Implementation Checklist**: [specs/020-fix-cloudrun-db-auth/checklists/implementation.md](specs/020-fix-cloudrun-db-auth/checklists/implementation.md)

<!-- MANUAL ADDITIONS START (preserved from above) -->

## Claude Code CLI Integration

### Installing Hansard MCP Server

To use the Hansard MCP server with Claude Code CLI, register it using the `claude mcp add` command:

```bash
claude mcp add hansard-mcp \
  -e PYTHONPATH=src \
  -e DANGEROUSLY_OMIT_AUTH=true \
  -e GCP_PROJECT_ID=skai-fastmcp-cloudrun \
  -e GCP_REGION=us-central1 \
  -e CLOUDSQL_INSTANCE=hansard-db-v2 \
  -e CLOUDSQL_DATABASE=hansard \
  -e CLOUDSQL_USER=fastmcp-server \
  -- uv run --project /home/user/skai-fastmcp-cloudrun fastmcp run src/server.py:mcp
```

This configuration:
- Installs the server with STDIO transport (local execution)
- Uses `uv run` with the project directory for dependency management
- Sets required environment variables for Cloud SQL access
- Enables OAuth bypass for local development (`DANGEROUSLY_OMIT_AUTH=true`)

### Managing MCP Servers

```bash
# List installed servers
claude mcp list

# Remove the server
claude mcp remove hansard-mcp

# View configuration
cat ~/.claude.json
```

### Available Tools

Once installed, Claude Code CLI can access:
- `search_hansard_speeches` - Semantic search with metadata filtering
- `fetch_hansard_speech` - Retrieve full speech by ID
- `ingest_hansard_speech` - Add new speeches to database

## Google Gemini CLI Integration

### Documentation

Complete setup guides for connecting Google Gemini CLI to the Hansard MCP server:

- **Overview**: [/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/README.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/README.md)
- **Local STDIO Setup**: [/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/stdio-setup.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/stdio-setup.md) (5-10 minutes)
- **Remote SSE Setup**: [/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/sse-setup.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/sse-setup.md) (15 minutes)
- **Troubleshooting**: [/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/troubleshooting.md)
- **Test Scenarios**: [/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/test-scenarios.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/test-scenarios.md)

### Quick Setup (Local STDIO)

**Prerequisites**: Gemini CLI v1.0.0+, FastMCP 2.14.0+, Python 3.11+

**Configuration** (`~/.config/gemini-cli/config.json`):
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

**Restart Gemini CLI**: `gemini restart`

### Quick Setup (Remote SSE)

**Prerequisites**: Cloud Run deployment, gcloud CLI authentication

**Configuration** (`~/.config/gemini-cli/config.json`):
```json
{
  "mcpServers": {
    "hansard": {
      "transport": "sse",
      "url": "https://hansard-mcp-server-PROJECT_ID.a.run.app",
      "headers": {
        "Authorization": "Bearer $(gcloud auth print-identity-token)",
        "Content-Type": "application/json"
      },
      "timeout": 60,
      "description": "Australian Hansard parliamentary speech search (Cloud Run)"
    }
  }
}
```

**Token Refresh Automation**:
```bash
# Run automation script
bash /home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/sse-token-refresh.sh

# Set up cron job for auto-refresh (every 30 minutes)
crontab -e
# Add: */30 * * * * bash /path/to/sse-token-refresh.sh
```

### Configuration Examples

All configuration templates and automation scripts:

- [/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/stdio-config.json](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/stdio-config.json)
- [/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/sse-config.json](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/sse-config.json)
- [/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/stdio-quickstart.sh](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/stdio-quickstart.sh) (Unix/macOS automation)
- [/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/stdio-quickstart.ps1](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/stdio-quickstart.ps1) (Windows automation)
- [/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/sse-token-refresh.sh](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/sse-token-refresh.sh) (Token automation)
- [/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/test-scenarios.json](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/examples/test-scenarios.json)

### Available Tools

Once configured, Gemini CLI can access:
- `hansard_search` - Search Australian parliamentary speeches by keywords, speaker, date, or chamber
- `hansard_fetch` - Retrieve full speech text and metadata by ID
- `hansard_ingest` - Add new speeches to the database (local development only)

### Verification

**Test tool discovery**:
```
What Hansard tools are available?
```

**Test search**:
```
Search Hansard for speeches about climate change
```

**Test fetch**:
```
Fetch the full text of Hansard speech ID [SPEECH_ID]
```

See [test-scenarios.md](/home/user/skai-fastmcp-cloudrun/docs/gemini-cli/test-scenarios.md) for complete test suite.

<!-- MANUAL ADDITIONS END -->
