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
- 012-admin-markdown-ingestion: Added [if applicable, e.g., PostgreSQL, CoreData, files or N/A]
- 011-mcp-oauth21-security: Added Python 3.11+ (Cloud Run compatibility)
- 010-token-verification: Added Python 3.11+ (Cloud Run compatibility requirement) + PyJWT (JWT validation), cryptography (RSA/ECDSA keys), httpx (HTTP introspection), Pydantic v2 (schemas), FastMCP 2.12.0+ (auth provider framework)

<!-- MANUAL ADDITIONS START -->

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
