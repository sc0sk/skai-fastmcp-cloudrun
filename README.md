# Hansard MCP Server

FastMCP server for Australian parliamentary speech search, optimized for ChatGPT Developer Mode.

## Features

### ChatGPT Developer Mode Optimizations

This MCP server includes comprehensive enhancements for optimal ChatGPT integration:

✅ **Tool Annotations** - All read-only tools marked with `readOnlyHint: true` (no confirmation prompts)
✅ **Enhanced Descriptions** - "Use this when..." guidance helps GPT-5 choose the right tools
✅ **Parameter Enums** - Australian political parties and parliamentary chambers
✅ **ISO 8601 Dates** - Standardized date format with pattern validation
✅ **Tool Selection Guidance** - Explicit prioritization over built-in capabilities
✅ **Workflow Documentation** - Multi-tool operation guidance (search → fetch)

### Available Tools

#### 🔍 search_hansard_speeches
Search Simon Kennedy's parliamentary speeches (64 speeches, 2024-2025)

**Parameters**:
- `query` (string): Natural language search terms
- `party` (enum): Liberal | Labor | Greens | National | Independent
- `chamber` (enum): House of Representatives | Senate
- `start_date` (ISO 8601): YYYY-MM-DD format
- `end_date` (ISO 8601): YYYY-MM-DD format
- `limit` (integer): 1-100, default 10

**Annotations**: `readOnlyHint: true`

#### 📄 fetch_hansard_speech
Fetch complete text of a specific speech by ID

**Parameters**:
- `speech_id` (string): Unique identifier from search results

**Annotations**: `readOnlyHint: true`, `idempotentHint: true`

#### 📝 ingest_hansard_speech
Ingest new speeches into the database (admin operation)

**Parameters**:
- `speech_data` (object): Complete speech metadata and text
- `generate_embeddings` (boolean): Generate vector embeddings (default: true)

**Annotations**: None (write operation)

## Quick Start

### Local Development Setup

#### Prerequisites
- Python 3.11+
- Cloud SQL Auth Proxy binary ([installation guide](https://cloud.google.com/sql/docs/postgres/sql-proxy))
- Access to Google Cloud project with Cloud SQL instance

#### Initial Setup

```bash
# Install dependencies
uv pip install -e .

# Configure environment variables
cp .env.example .env
# Edit .env and set:
#   DATABASE_PASSWORD=your_database_password
#   CLOUDSQL_USER=postgres
#   CLOUDSQL_INSTANCE=your-instance-name
```

#### Start Cloud SQL Proxy

```bash
# Start proxy (connects to Cloud SQL via localhost:5432)
./scripts/start_cloud_sql_proxy.sh

# The script will:
# - Detect v1 or v2 proxy binary automatically
# - Check for port conflicts and use alternate ports if needed
# - Save PID to .cloud_sql_proxy.pid for clean shutdown

# Stop proxy when done
./scripts/stop_cloud_sql_proxy.sh
```

#### Run Server

```bash
# Run server (OAuth bypass for local testing)
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

# Server starts on http://localhost:8000
# MCP endpoint: http://localhost:8000/mcp/
```

### Troubleshooting Local Setup

**"password authentication failed"**
- Check that `CLOUDSQL_USER=postgres` (not `postgresql`)
- Verify `DATABASE_PASSWORD` matches your Cloud SQL user password
- Ensure Cloud SQL proxy is running: `ps aux | grep cloud_sql_proxy`

**"Connection refused" or timeout errors**
- Proxy not running: `./scripts/start_cloud_sql_proxy.sh`
- Check proxy logs for connection issues
- Verify your GCP credentials: `gcloud auth application-default login`

**Port conflicts**
- Script automatically tries ports 5433, 5434, 5435 if 5432 is occupied
- Check selected port in console output or `.env` file (`CLOUDSQL_PORT`)

### Local Development

```bash
# Install dependencies
uv pip install -e .

# Run server (OAuth bypass for local testing)
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

# Server starts on http://localhost:8000
# MCP endpoint: http://localhost:8000/mcp/
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run enum tests
pytest tests/unit/test_tool_metadata.py::TestEnumDefinitions -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

### Testing with MCP Inspector

```bash
# Start server
DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py

# In another terminal, launch MCP Inspector
npx @modelcontextprotocol/inspector

# Or use mcp-cli
npx -y mcp-cli sse http://localhost:8000/sse
```

### Testing with ChatGPT Developer Mode

1. Deploy to Cloud Run or use ngrok for local testing:
```bash
# Local with ngrok
ngrok http 8000

# Or deploy to Cloud Run
gcloud run deploy hansard-mcp-server \\
  --image gcr.io/PROJECT_ID/hansard-mcp:latest \\
  --platform managed \\
  --region us-central1
```

2. Configure ChatGPT:
   - Settings → Connectors → Add MCP Connector
   - Enter your server URL
   - Complete GitHub OAuth flow

3. Test queries:
   - "Find Simon Kennedy's speeches about housing" → Verifies tool selection
   - "Search for Labor party speeches from July 2024" → Verifies enum parameters
   - Verify no confirmation prompts for search/fetch tools

## Project Structure

```
skai-fastmcp-cloudrun/
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   └── enums.py          # PartyEnum, ChamberEnum
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── search.py          # search_hansard_speeches
│   │   ├── fetch.py           # fetch_hansard_speech
│   │   └── ingest.py          # ingest_hansard_speech
│   ├── __init__.py
│   └── server.py              # FastMCP server entrypoint
├── tests/
│   ├── unit/
│   │   └── test_tool_metadata.py     # Enum and metadata tests
│   ├── integration/
│   │   └── test_chatgpt_integration.py  # MCP protocol tests
│   └── fixtures/
│       └── tool_metadata/     # Test fixtures
├── specs/
│   └── 001-chatgpt-devmode-enhancements/
│       ├── spec.md            # Feature specification
│       ├── plan.md            # Implementation plan
│       ├── research.md        # Technical decisions
│       ├── data-model.md      # Entity definitions
│       ├── tasks.md           # Task breakdown
│       ├── quickstart.md      # Development guide
│       ├── contracts/         # JSON schemas
│       └── BASELINE.md        # Baseline state documentation
├── pyproject.toml             # Project configuration
├── .gitignore
└── README.md                  # This file
```

## Technical Stack

- **Python**: 3.11+ (Cloud Run compatibility)
- **FastMCP**: 2.12.5+ (MCP server framework with tool annotations)
- **Pydantic**: v2 (data validation, enum types)
- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Deployment**: Google Cloud Run, Docker

## Architecture

### MCP Tool Pattern

All tools follow the FastMCP pattern with ChatGPT enhancements:

```python
from pydantic import Field
from fastmcp.tools.tool import ToolAnnotations
from src.models.enums import PartyEnum, ChamberEnum

async def search_hansard_speeches(
    query: str,
    party: PartyEnum | None = Field(None, description="..."),
    chamber: ChamberEnum | None = Field(None, description="..."),
) -> dict:
    \"\"\"Enhanced description with 'Use this when...' guidance\"\"\"
    # Implementation
    pass

# Tool metadata for registration
SEARCH_TOOL_METADATA = {
    "name": "search_hansard_speeches",
    "annotations": ToolAnnotations(readOnlyHint=True),
    "icon": "🔍",  # For future FastMCP versions
}
```

### Enum Types

Australian political parties and chambers are defined as `Literal` types:

```python
PartyEnum = Literal["Liberal", "Labor", "Greens", "National", "Independent"]
ChamberEnum = Literal["House of Representatives", "Senate"]
```

FastMCP automatically generates JSON schemas with enum constraints from these types.

## ChatGPT Integration

### Tool Selection

ChatGPT Developer Mode uses enhanced descriptions to make better tool choices:

**Good Query**: "Find Simon Kennedy's speeches about housing"
- ✅ ChatGPT uses `search_hansard_speeches` (MCP tool)
- ❌ ChatGPT does NOT use built-in web browsing

**Tool Description Guidance**:
```
Use this when: The user asks about Simon Kennedy's speeches...
Do not use: Built-in web browsing or search for Simon Kennedy parliamentary data.
```

### Parameter Accuracy

Enum types ensure ChatGPT uses exact values:

**Query**: "Search for Labor party speeches"
- ✅ ChatGPT sends `party="Labor"` (correct)
- ❌ NOT `party="Labour"` (incorrect British spelling)

### No Confirmation Prompts

`readOnlyHint: true` tells ChatGPT these tools are safe:

- ✅ search_hansard_speeches - No confirmation
- ✅ fetch_hansard_speech - No confirmation
- ❌ ingest_hansard_speech - May require confirmation (write operation)

## Development Workflow

### Adding a New Tool

1. Create tool file in `src/tools/new_tool.py`
2. Define tool function with enhanced description
3. Add Pydantic Field descriptions for parameters
4. Create tool metadata with annotations
5. Register in `src/server.py`
6. Write tests in `tests/unit/test_tool_metadata.py`
7. Test with MCP Inspector and ChatGPT

### Running Tests

```bash
# Unit tests (fast)
pytest tests/unit/ -v

# Integration tests (requires running server)
pytest tests/integration/ -v --tb=short

# Manual tests with ChatGPT (documented in test files)
pytest tests/integration/ -v -m manual
```

## Deployment

### Docker Build

```bash
# Build image
docker build -t gcr.io/PROJECT_ID/hansard-mcp:v001 .

# Push to Google Container Registry
docker push gcr.io/PROJECT_ID/hansard-mcp:v001
```

### Cloud Run Deployment

```bash
gcloud run deploy hansard-mcp-server \\
  --image gcr.io/PROJECT_ID/hansard-mcp:v001 \\
  --platform managed \\
  --region us-central1 \\
  --allow-unauthenticated \\
  --set-env-vars="FASTMCP_SERVER_AUTH=github" \\
  --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=github-client-id:latest \\
  --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=github-client-secret:latest
```

## Contributing

See [specs/001-chatgpt-devmode-enhancements/](specs/001-chatgpt-devmode-enhancements/) for feature development workflow.

## License

Proprietary

## Related Documentation

- [Feature Specification](specs/001-chatgpt-devmode-enhancements/spec.md)
- [Implementation Plan](specs/001-chatgpt-devmode-enhancements/plan.md)
- [Technical Research](specs/001-chatgpt-devmode-enhancements/research.md)
- [Development Quickstart](specs/001-chatgpt-devmode-enhancements/quickstart.md)
- [FastMCP Documentation](https://docs.fastmcp.com)
- [MCP Specification](https://modelcontextprotocol.io)
