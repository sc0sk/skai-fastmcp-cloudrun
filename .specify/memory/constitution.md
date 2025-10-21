<!--
Sync Impact Report:
Version: 2.5.0 → 2.6.0
Modified Principles: Adopted Google ADK-aligned architecture (LangChain + Vertex AI + Cloud SQL pgvector)
Added Sections: Google ADK rationale, Vertex AI embeddings (768-dim), LangChain integration patterns, Full text retrieval from PostgreSQL, Dual-table schema (speeches + speech_chunks)
Removed Sections: Qdrant Cloud architecture, sentence-transformers local embeddings, Direct pgvector integration
Changed Dependencies: Added LangChain (langchain-google-vertexai, langchain-google-cloud-sql-pg), Added Vertex AI embeddings, Removed sentence-transformers
Templates Requiring Updates: ⚠ pending - plan-template.md, spec-template.md, tasks-template.md, fastmcp.json
Follow-up TODOs: Create fastmcp.json with LangChain deps, update database schemas (768-dim vectors), implement speech ingestion with Vertex AI, build MCP RAG tools with full text retrieval, setup Cloud infrastructure (Redis, Cloud SQL pgvector), create deployment scripts
-->

# skai-fastmcp-cloudrun Constitution

## Core Principles

### I. FastMCP Server-First Architecture

Every feature MUST be designed as a discoverable MCP tool with clear metadata. Tools are the fundamental building blocks of FastMCP servers and MUST be:
- Discoverable via `list_tools()` with descriptive names and documentation
- Tagged with metadata for filtering (FastMCP 2.11.0+)
- Self-contained with explicit input schemas
- Independently testable

**Rationale**: Tool-based architecture ensures discoverability, composability, and clear contracts between clients and servers.

### II. Secure Authentication (NON-NEGOTIABLE)

GitHub OAuth MUST be used for all authentication. Implementation requirements:
- Use `GitHubProvider` for server authentication
- Browser-based OAuth flow for initial client authentication
- Automatic token management and caching
- OAuth Proxy pattern for dynamic client authentication
- User information retrieval from GitHub profile

**Rationale**: GitHub OAuth provides enterprise-grade security with familiar developer experience and automatic token lifecycle management.

### III. Secrets Management (NON-NEGOTIABLE)

Credentials and secrets MUST NEVER be committed to version control. All configuration MUST use:
- Environment variables for all credentials (`FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID`, `FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET`)
- Cloud Run secrets for production deployments
- `.env` files with `.gitignore` enforcement for local development
- HTTPS-only communication for production

**Rationale**: Security breaches from committed credentials are preventable and catastrophic.

### IV. Test-Driven Development (NON-NEGOTIABLE)

TDD is mandatory for all tool development:
1. Write tests defining expected tool behavior
2. Verify tests fail appropriately
3. Implement tool functionality
4. Verify tests pass
5. Refactor while maintaining green tests

Red-Green-Refactor cycle strictly enforced. No tool merges without tests.

**Rationale**: MCP tools define contracts; tests verify contracts before and after implementation.

### V. Structured Result Handling

All tools MUST return `CallToolResult` objects with multiple access methods:
- `.data`: Fully hydrated Python objects with complex type support
- `.content`: Standard MCP content blocks for protocol compliance
- `.structured_content`: Raw JSON data for custom processing
- `.is_error`: Boolean error state indicator

Tools MUST raise `ToolError` exceptions for execution failures with descriptive messages.

**Rationale**: Consistent result structures enable reliable client integration and debugging.

### VI. Cloud Run Production Standards

Production deployments MUST follow Google Cloud Run best practices:
- Container-based deployment with proper health checks
- Environment-based configuration (dev, staging, prod)
- Callback URL configuration for OAuth (`/auth/callback`)
- Automatic HTTPS termination and certificate management
- Proper logging and error reporting to Cloud Logging

**Rationale**: Cloud Run provides scalable, managed infrastructure; proper configuration ensures reliability.

### VII. Progress Transparency (NON-NEGOTIABLE)

Long-running tools (>5 seconds expected) MUST support progress reporting:
- Use `await ctx.report_progress(progress, total)` for client updates
- Report meaningful progress updates (percentage or absolute values)
- Support timeout configuration via `timeout` parameter
- Graceful timeout handling with partial results if applicable
- Multi-stage operations MUST report progress per stage
- Indeterminate operations MAY report progress without total

**Rationale**: User experience requires feedback for operations that don't complete instantly. Progress reporting enables clients to display progress indicators and prevents timeout confusion (FastMCP 2.0+).

### VIII. Python & Pydantic Standards (NON-NEGOTIABLE)

All server code MUST be written in Python using Pydantic for data validation:
- Python 3.11+ required for Cloud Run compatibility
- Pydantic v2 for all data models and tool input schemas
- Type hints required for all functions and methods
- Use `uv` for dependency management (faster than pip)
- FastMCP framework as the MCP server foundation
- HTTP transport mode for ChatGPT compatibility

**Rationale**: Python provides extensive library support; Pydantic ensures type safety and automatic validation; uv provides fast, reproducible builds; HTTP transport enables ChatGPT integration.

### IX. ChatGPT Integration Standards

Servers MUST be compatible with ChatGPT Developer Mode and MCP connectors:
- Server accessible via public internet (Cloud Run or ngrok for dev)
- HTTP transport on standard port (8000 dev, 8080 Cloud Run)
- MCP endpoint at `/mcp/` path
- Support both Chat Mode and Deep Research Mode
- Tools MUST include `readOnlyHint` annotation where applicable

**Rationale**: ChatGPT integration expands server utility; standardized endpoints ensure compatibility; read-only hints improve safety.

### X. MCP JSON Configuration Standards

Servers MUST support standard MCP JSON configuration format for multi-client compatibility:
- Generate configuration using `fastmcp install mcp-json`
- Use absolute file paths in generated configuration
- Support `uv` as the standard package manager
- Include all dependencies in `args` array
- Provide environment variables via `env` object
- Compatible with Claude Desktop, Cursor, VS Code, and other MCP clients

**Rationale**: Standard MCP JSON format enables server distribution across ecosystem; absolute paths ensure reliability; uv provides fast, reproducible dependency management.

### XI. Tool Implementation Standards (NON-NEGOTIABLE)

All tools MUST implement comprehensive standards following FastMCP best practices:

**Core Requirements**:
- **Decorator Pattern**: Use `@mcp.tool` decorator (naked decorator FastMCP 2.7+)
- **Type Annotations**: Full type hints on all parameters and return values for automatic schema generation
- **Docstrings**: Clear, concise descriptions of tool purpose and behavior
- **Parameter Validation**: Use Pydantic Field constraints (ge, le, min_length, pattern)
- **Return Type Annotations**: Enable automatic output schema generation (FastMCP 2.10.0+)
- **Structured Outputs**: Return object-like results (dict, Pydantic models) for automatic structured content
- **Error Handling**: Raise `ToolError` for controlled error messages, mask internal errors in production
- **Async Support**: Use async functions for I/O-bound operations, wrap blocking operations with `anyio.to_thread.run_sync`
- **Context Access**: Use `ctx: Context` parameter for logging, progress, resources, and sampling

**Advanced Capabilities**:
- **Metadata Tags**: Categorize with `tags={"domain", "action", "maturity"}` for filtering
- **MCP Annotations**: Add `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`
- **Icons**: Provide visual identification (FastMCP 2.14.0+)
- **Parameter Exclusion**: Use `exclude_args` for runtime-injected parameters (FastMCP 2.6.0+)
- **Dynamic Management**: Enable/disable tools programmatically, filter by tags
- **Validation Modes**: Use `strict_input_validation` when type safety critical (FastMCP 2.13.0+)
- **Duplicate Handling**: Configure `on_duplicate_tools` behavior (FastMCP 2.1.0+)
- **Tool Removal**: Support dynamic tool removal with `mcp.remove_tool()` (FastMCP 2.3.4+)

**Rationale**: Complete tool implementation standards ensure reliability, type safety, discoverability, and rich client experiences across all MCP clients.

## Authentication & Security Requirements

### GitHub OAuth Configuration (OAuth Proxy Pattern)

FastMCP GitHub integration provides OAuth proxy for dynamic client authentication.

1. **OAuth App Setup** (GitHub Settings):
   - Application name clearly identifies the MCP server purpose
   - Homepage URL: Cloud Run service URL (e.g., `https://zoo-mcp-server-<hash>-ew.a.run.app`)
   - Callback URL: Deployment URL + `/auth/callback`
   - Minimal required scopes (user:email, read:user)
   - Generate Client ID and Client Secret

2. **Environment Variables** (required):
   ```
   FASTMCP_SERVER_AUTH=github
   FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=<client-id>
   FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=<client-secret>
   ```

3. **Optional Configuration**:
   - `FASTMCP_SERVER_AUTH_GITHUB_SCOPES`: Custom OAuth scopes (comma-separated)
   - `FASTMCP_SERVER_AUTH_GITHUB_TIMEOUT`: Auth flow timeout (seconds)

4. **Cloud Run Secrets Integration**:
   Store secrets in Google Secret Manager and reference in Cloud Run:
   ```bash
   gcloud secrets create github-client-id --data-file=-
   gcloud secrets create github-client-secret --data-file=-
   ```

### Credential Storage

- **Local Development**: Use `.env` file (MUST be in `.gitignore`)
- **Cloud Run**: Use Google Secret Manager with secret references in deployment
  ```bash
  gcloud run deploy SERVICE \
    --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=github-client-id:latest \
    --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=github-client-secret:latest
  ```
- **CI/CD**: Use encrypted secrets in GitHub Actions/Cloud Build
- **Never**: Hardcode credentials or commit to repository

### Google Cloud IAM & Authentication

Cloud Run services authentication depends on client type:
- **Internal MCP Clients** (Claude, Gemini): Deploy with `--no-allow-unauthenticated`
  - Use Google Cloud IAM roles for access control
  - Grant `roles/run.invoker` only to authorized principals
  - Authenticate using identity tokens
- **ChatGPT Developer Mode**: May require `--allow-unauthenticated` OR use GitHub OAuth
  - ChatGPT connectors access via public HTTPS URL
  - Optional: Layer GitHub OAuth for user authentication
  - Maintain audit logs for all requests with user context

**Security Trade-off**: Public access for ChatGPT vs IAM-restricted for Claude. Prefer GitHub OAuth when possible.

## MCP Inspector Testing Standards

### MCP Inspector Overview

The MCP Inspector is the standard testing tool for FastMCP server development. It provides both interactive UI and CLI modes for testing and debugging MCP servers.

**Key Components**:
- **MCP Inspector Client (MCPI)**: React-based web UI at http://localhost:6274
- **MCP Proxy (MCPP)**: Node.js proxy server bridging UI to MCP servers

**Supported Transports**:
- **STDIO**: Local process execution (default for `fastmcp dev`)
- **SSE**: Server-Sent Events connection
- **Streamable HTTP**: HTTP-based streaming connection

### Interactive Testing (UI Mode)

**FastMCP Integration**:
```bash
# Recommended: Use fastmcp dev command
fastmcp dev server.py

# Automatically starts MCP Inspector UI
# Opens browser at http://localhost:6274
# Connects via stdio transport
```

**Direct Inspector Usage**:
```bash
# Quick start with npx
npx @modelcontextprotocol/inspector

# Connect to local server
npx @modelcontextprotocol/inspector node server.py

# Connect to Python server
npx @modelcontextprotocol/inspector python server.py

# Docker mode
docker run --rm --network host -p 6274:6274 -p 6277:6277 \
  ghcr.io/modelcontextprotocol/inspector:latest
```

**UI Features**:
- Interactive server connection management
- Real-time tool exploration and testing
- Resource browsing and inspection
- Prompt template testing
- Request/response debugging
- Server capability discovery

**Testing HTTP Servers**:
```bash
# Start HTTP server manually
fastmcp run server.py --transport http --port 8000

# Open MCP Inspector separately
npx @modelcontextprotocol/inspector

# In UI: Select "Streamable HTTP" transport
# Enter URL: http://localhost:8000/mcp/
# Connect manually
```

**Important**: `fastmcp dev` is STDIO-only. For HTTP/SSE testing, start server manually and connect Inspector separately.

### CLI Mode Testing (Automated)

**Purpose**: Programmatic testing for CI/CD and automation

```bash
# List all tools
npx @modelcontextprotocol/inspector --cli node server.py \
  --method tools/list

# Call specific tool
npx @modelcontextprotocol/inspector --cli python server.py \
  --method tools/call \
  --params '{"name": "my_tool", "arguments": {"x": 5}}'

# List resources
npx @modelcontextprotocol/inspector --cli python server.py \
  --method resources/list

# Read resource
npx @modelcontextprotocol/inspector --cli python server.py \
  --method resources/read \
  --params '{"uri": "resource://example"}'
```

**CLI Options**:
- `--cli`: Enable CLI mode (non-interactive)
- `--method <method>`: MCP protocol method to call
- `--params <json>`: JSON parameters for the method
- `--config <file>`: Configuration file with environment variables
- `--timeout <ms>`: Connection timeout

### Security & Network Binding

**Default Security Behavior**:
- Binds to `localhost` only (no network access)
- Generates random session token per run
- Requires authentication by default
- Safe for local development

**Network Considerations**:
- Never expose Inspector to public network
- Use SSH tunneling for remote debugging
- Docker mode uses `--network host` for localhost binding

### Inspector Configuration

**Environment Variables** (via config file):
```json
{
  "env": {
    "API_KEY": "dev-key",
    "DEBUG": "true"
  },
  "timeout": 30000
}
```

**Usage**:
```bash
npx @modelcontextprotocol/inspector --config inspector-config.json node server.py
```

### Testing Workflow Recommendations

**Development Cycle**:
1. **Write tool** with type hints and docstrings
2. **Run `fastmcp dev server.py`** - opens Inspector automatically
3. **Test in UI** - explore tools, test calls, verify responses
4. **Iterate** - make changes, Inspector reloads server
5. **Write automated tests** - capture behavior in pytest

**HTTP Server Testing**:
1. **Start server**: `fastmcp run server.py --transport http`
2. **Open Inspector**: `npx @modelcontextprotocol/inspector`
3. **Select transport**: "Streamable HTTP"
4. **Enter URL**: `http://localhost:8000/mcp/`
5. **Test manually** in UI
6. **Automate** with CLI mode or client tests

**CI/CD Integration**:
```bash
# In CI pipeline
npm install -g @modelcontextprotocol/inspector

# Test server startup
npx @modelcontextprotocol/inspector --cli python server.py \
  --method tools/list || exit 1

# Test specific tool
npx @modelcontextprotocol/inspector --cli python server.py \
  --method tools/call \
  --params '{"name": "health_check", "arguments": {}}' || exit 1
```

### Inspector vs pytest Testing

**Use MCP Inspector for**:
- Interactive debugging
- Manual exploration
- Visual verification
- Client perspective testing
- Quick prototyping

**Use pytest for**:
- Automated regression testing
- Unit testing
- Integration testing
- Coverage measurement
- CI/CD gates

**Best Practice**: Use both
- Inspector for development and debugging
- pytest for automated quality gates

## Code Quality & Testing Standards

### Tool Testing Requirements

Each tool MUST have:
1. **Unit Tests**: Test tool logic in isolation using pytest
2. **Integration Tests**: Test tool execution via `call_tool()`
3. **Error Tests**: Verify proper `ToolError` exceptions
4. **Schema Tests**: Validate Pydantic input schema enforcement
5. **Result Tests**: Verify `.data`, `.content`, `.structured_content` correctness
6. **Type Tests**: Verify Pydantic model validation and type coercion
7. **Output Schema Tests**: Verify complex type reconstruction (datetime, UUID)
8. **Metadata Tests**: Verify tags and metadata are properly included
9. **Async Tests**: Verify async tools execute correctly
10. **Context Tests**: Verify context access (logging, progress, state)
11. **Dynamic Tests**: Verify enable/disable functionality
12. **Logging Tests**: Verify client logging messages are sent correctly
13. **Icon Tests**: Verify icons are included in tool metadata (if applicable)

**In-Memory Testing** (FastMCP 2.0+):
```python
from fastmcp.testing import test_mcp

async def test_my_tool():
    async with test_mcp(mcp) as client:
        result = await client.call_tool("add", {"a": 5, "b": 3})
        assert result.data == 8

async def test_tool_logging():
    async with test_mcp(mcp) as client:
        # Test client logging
        result = await client.call_tool("analyze_data", {"data": [1, 2, 3]})
        # Verify logs were sent to client
```

### Test Coverage Minimums

- Line coverage: 80% minimum
- Branch coverage: 70% minimum
- All public tool methods: 100% coverage
- Error paths: 100% coverage

### Code Review Gates

All PRs MUST:
- Pass all tests (no exceptions)
- Include test updates for new functionality
- Update tool metadata and descriptions
- Verify no committed secrets (automated scan)
- Document breaking changes with migration guide

## FastMCP CLI Standards (NON-NEGOTIABLE)

All FastMCP servers MUST be developed, tested, and deployed using the FastMCP CLI. The CLI provides standardized workflows for development, testing, client installation, and deployment.

### CLI Commands Overview

| Command | Purpose | Transport | Dependency Management |
|---------|---------|-----------|----------------------|
| `fastmcp run` | Run server directly or proxy remote servers | stdio/http/sse | Local env OR uv subprocess with flags |
| `fastmcp dev` | Run with MCP Inspector for testing | stdio only | Always uv subprocess |
| `fastmcp install` | Install in MCP clients (Claude Code/Desktop/Cursor) | stdio | Isolated uv environment |
| `fastmcp inspect` | Generate server manifest (FastMCP/MCP formats) | N/A | Local environment |
| `fastmcp project prepare` | Create persistent uv project | N/A | Creates uv project |

### Server Entrypoint Patterns

FastMCP supports multiple server entrypoint patterns (FastMCP 2.3.5+):

**1. Inferred Server Instance** (recommended):
```python
# server.py - CLI auto-detects `mcp`, `server`, or `app` variable
from fastmcp import FastMCP
mcp = FastMCP("MyServer")

@mcp.tool
def my_tool(x: int) -> int:
    return x * 2
```
Run with: `fastmcp run server.py`

**2. Explicit Server Entrypoint**:
```python
# server.py - custom variable name
my_custom_server = FastMCP("CustomServer")
```
Run with: `fastmcp run server.py:my_custom_server`

**3. Factory Function** (FastMCP 2.11.2+) - for setup code:
```python
# server.py
async def create_server() -> FastMCP:
    mcp = FastMCP("MyServer")
    # Setup code runs here (not ignored like __main__)
    await configure_tools(mcp)
    return mcp
```
Run with: `fastmcp run server.py:create_server`

**4. Remote Server Proxy**:
```bash
fastmcp run https://example.com/mcp
```

**5. FastMCP Configuration** (FastMCP 2.11.4+):
```bash
# Auto-detects fastmcp.json in current directory
fastmcp run

# Or explicit file
fastmcp run my-config.fastmcp.json
```

**6. MCP Configuration** (runs all servers in config):
```bash
fastmcp run mcp.json
```

**IMPORTANT**: `fastmcp run` ignores `if __name__ == "__main__"` blocks. Use factory functions for setup code.

### Development Workflow with CLI

**Local Development**:
```bash
# Development with MCP Inspector
fastmcp dev server.py

# Development with fastmcp.json
fastmcp dev  # auto-detects

# HTTP development server
fastmcp run server.py --transport http --port 8000

# With dependencies
fastmcp run server.py --with pandas --with requests
```

**Testing & Inspection**:
```bash
# Interactive testing with MCP Inspector (UI mode)
fastmcp dev server.py

# MCP Inspector opens automatically with stdio connection
# UI available at http://localhost:6274

# Direct MCP Inspector usage
npx @modelcontextprotocol/inspector node server.py

# CLI mode for automated testing
npx @modelcontextprotocol/inspector --cli node server.py --method tools/list

# Inspect server capabilities (static analysis)
fastmcp inspect server.py

# Generate FastMCP manifest
fastmcp inspect server.py --format fastmcp -o manifest.json

# Generate MCP protocol manifest
fastmcp inspect server.py --format mcp -o mcp-manifest.json
```

**Client Installation**:
```bash
# Install in Claude Code
fastmcp install claude-code server.py

# Install in Claude Desktop
fastmcp install claude-desktop server.py

# Install in Cursor
fastmcp install cursor server.py

# With dependencies and custom name
fastmcp install claude-desktop server.py \
  --server-name "My Analysis Server" \
  --with pandas --with matplotlib

# With environment variables
fastmcp install claude-code server.py \
  --env API_KEY=secret --env DEBUG=true

# With .env file
fastmcp install cursor server.py --env-file .env

# Generate MCP JSON for distribution
fastmcp install mcp-json server.py --copy
```

**Production Preparation**:
```bash
# Create persistent uv project
fastmcp project prepare fastmcp.json --output-dir ./env

# Run using prepared environment (fast, no dependency installation)
fastmcp run fastmcp.json --project ./env
```

### fastmcp.json Configuration Standard

All projects SHOULD include a `fastmcp.json` configuration file for declarative server management:

```json
{
  "$schema": "https://gofastmcp.com/public/schemas/fastmcp.json/v1.json",
  "source": {
    "path": "server.py",
    "entrypoint": "mcp"
  },
  "environment": {
    "dependencies": ["pandas", "requests", "httpx"],
    "python": "3.11",
    "env_file": ".env"
  },
  "transport": {
    "type": "http",
    "host": "0.0.0.0",
    "port": 8080
  }
}
```

**Benefits**:
- Single command installation: `fastmcp install claude-code`
- Consistent dependency management
- Environment variable loading
- Transport configuration
- CI/CD automation

### CLI Flag Standards

**Environment Management**:
- `--python <version>`: Specify Python version (e.g., 3.11)
- `--with <package>`: Add dependency (repeatable)
- `--with-editable <path>`: Install local package in editable mode
- `--with-requirements <file>`: Load from requirements.txt
- `--project <path>`: Run within uv project directory
- `--skip-env`: Skip uv environment setup (when already in uv env)

**Transport Configuration**:
- `--transport <stdio|http|sse>`: Protocol (default: stdio)
- `--host <host>`: Bind address for HTTP (default: 127.0.0.1)
- `--port <port>`: Bind port for HTTP (default: 8000)
- `--path <path>`: HTTP path (default: /mcp/ or /sse/)

**Debugging**:
- `--log-level <level>`: Set log level (DEBUG, INFO, WARNING, ERROR)
- `--no-banner`: Disable startup banner

### Multi-Client Support Pattern

All servers SHOULD support both stdio (local clients) and HTTP (ChatGPT, remote) transports:

```python
import os

if __name__ == "__main__":
    # Support both stdio (Claude Desktop, Cursor) and HTTP (ChatGPT, Cloud Run)
    transport = "http" if os.getenv("PORT") else "stdio"
    port = int(os.getenv("PORT", 8080)) if transport == "http" else None

    if transport == "http":
        mcp.run(transport="http", port=port)
    else:
        mcp.run()  # stdio
```

### Method Decoration Standards (FastMCP 2.7+)

**NEVER directly decorate methods** - decorators return Tool objects, not functions:

**❌ DON'T DO THIS**:
```python
class MyClass:
    @mcp.tool  # WRONG - my_method is now a Tool, not callable
    def my_method(self, x: int) -> int:
        return x * 2
```

**✅ DO THIS INSTEAD** (register after instance creation):
```python
class MyClass:
    def my_method(self, x: int) -> int:
        return x * 2

# Create instance, then register bound methods
obj = MyClass()
mcp.tool(obj.my_method)
```

**Class Methods**:
```python
class MyClass:
    @classmethod
    def from_string(cls, s: str):
        return cls(s)

# Register after class definition
mcp.tool(MyClass.from_string)
```

**Static Methods** (works but not recommended - register instead):
```python
class MyClass:
    @staticmethod
    def utility(x: int, y: int) -> int:
        return x + y

# Prefer this pattern
mcp.tool(MyClass.utility)
```

**Auto-registration Pattern**:
```python
class ComponentProvider:
    def __init__(self, mcp_instance):
        # Register methods during initialization
        mcp_instance.tool(self.tool_method)
        mcp_instance.resource("resource://data")(self.resource_method)

    def tool_method(self, x: int) -> int:
        return x * 2

    def resource_method(self) -> str:
        return "Resource data"

# Methods automatically registered
provider = ComponentProvider(mcp)
```

### Tool Transformation Standards (FastMCP 2.8.0+)

Tool transformation enables creating enhanced tool variants from existing tools without code duplication:

**Basic Transformation** (metadata changes):
```python
from fastmcp.tools import Tool
from fastmcp.tools.tool_transform import ArgTransform

# Original tool
@mcp.tool
def search(q: str, category: str = "all") -> list[dict]:
    """Generic search."""
    return database.search(q, category)

# Create enhanced variant
product_search = Tool.from_tool(
    search,
    name="find_products",
    description="Search for products in catalog.",
    transform_args={
        "q": ArgTransform(
            name="search_query",
            description="Product name or description to search for"
        )
    }
)
mcp.add_tool(product_search)

# Disable original if needed
search.disable()
```

**Argument Transformations**:
```python
transform_args = {
    "user_id": ArgTransform(
        name="uid",  # Rename
        description="User unique identifier",  # Add description
        required=True  # Make required
    ),
    "api_key": ArgTransform(
        hide=True,  # Hide from LLM
        default=os.environ.get("API_KEY")  # Provide default
    ),
    "timestamp": ArgTransform(
        hide=True,
        default_factory=lambda: datetime.now()  # Dynamic default
    )
}
```

**Behavior Transformation** (validation, pre/post-processing):
```python
from fastmcp.tools.tool_transform import forward

async def validate_positive(x: int, y: int) -> int:
    """Ensure both arguments are positive before calling parent."""
    if x <= 0 or y <= 0:
        raise ValueError("Arguments must be positive")
    # Call parent tool with automatic argument mapping
    return await forward(x=x, y=y)

validated_add = Tool.from_tool(
    add_tool,
    transform_fn=validate_positive
)
```

**Common Patterns**:
1. **Exposing Client Methods**: Wrap API client methods directly as tools
2. **Hiding Internal Parameters**: Hide debug flags, auth tokens, rate limits
3. **Reusable Argument Patterns**: Define shared arg transforms for consistency
4. **Adapting Remote Tools**: Simplify generic remote/OpenAPI tools
5. **Context-Aware Factories**: Generate user-specific tool variants

## Development Workflow

### Tool Development Process

1. **Design**: Define tool name, description, Pydantic input schema, output structure
2. **Test**: Write pytest tests for success cases, error cases, edge cases
3. **Implement**: Build tool in Python following TDD cycle
4. **Validate**: Verify Pydantic model validation works correctly
5. **Document**: Update tool description and usage examples
6. **Review**: Code review with constitution compliance check
7. **Deploy**: Stage deployment → production promotion

### Python Code Standards

**Type Hints** (required for all code):
```python
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class ToolInput(BaseModel):
    param: str = Field(description="Parameter description")
    optional_param: Optional[int] = None

def my_tool(input: ToolInput) -> Dict[str, str]:
    return {"result": input.param}
```

**Pydantic Models**:
- All tool inputs MUST be Pydantic models
- Use `Field()` for descriptions and validation
- Leverage Pydantic validators for complex validation
- Use `BaseModel.model_validate()` for runtime validation

**Code Formatting**:
- Use `black` for code formatting (line length: 100)
- Use `ruff` for linting and import sorting
- Use `mypy` for static type checking

**FastMCP Configuration File**:
Every server SHOULD include a `fastmcp.json` configuration file:
```json
{
  "$schema": "https://gofastmcp.com/public/schemas/fastmcp.json/v1.json",
  "source": {
    "path": "server.py",
    "entrypoint": "mcp"
  },
  "environment": {
    "dependencies": ["package1", "package2"],
    "python": "3.11",
    "env_file": ".env"
  }
}
```

This enables:
- Single command installation: `fastmcp install mcp-json fastmcp.json`
- Consistent dependency management across environments
- Easy distribution to team members
- CI/CD automation

### Server Icon Standards

**Server Icons** (FastMCP 2.14.0+):
```python
from fastmcp import FastMCP
from mcp.types import Icon

mcp = FastMCP(
    name="WeatherService",
    website_url="https://weather.example.com",
    icons=[
        Icon(
            src="https://weather.example.com/icon-48.png",
            mimeType="image/png",
            sizes=["48x48"]
        ),
        Icon(
            src="https://weather.example.com/icon-96.png",
            mimeType="image/png",
            sizes=["96x96"]
        ),
    ]
)
```

**Icon Format Requirements**:
- `src`: URL or data URI to icon image (required)
- `mimeType`: MIME type (e.g., "image/png", "image/svg+xml") (optional)
- `sizes`: Array of size descriptors (e.g., ["48x48"], ["any"]) (optional)

### Tool Decorator Standards

**Basic Tool Definition** (FastMCP 2.7+ naked decorator):
```python
from fastmcp import FastMCP

mcp = FastMCP("My Server")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b
```

**Advanced Tool Definition with Parameters**:
```python
from mcp.types import Icon

@mcp.tool(
    name="custom_name",           # Override function name
    description="Custom desc",     # Override docstring
    tags=["math", "read", "stable"], # Categorization tags
    enabled=True,                  # Enable/disable tool
    annotations={                  # Metadata annotations
        "readOnlyHint": True,
        "custom_key": "custom_value"
    },
    icons=[                       # Tool icons (FastMCP 2.14.0+)
        Icon(src="https://example.com/calculator-icon.png")
    ]
)
def my_tool(param: str) -> str:
    return f"Result: {param}"
```

**Data URI Icons** (embedded icons):
```python
from mcp.types import Icon

svg_icon = Icon(
    src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCI+PHBhdGggZD0iTTEyIDJDNi40OCAyIDIgNi40OCAyIDEyczQuNDggMTAgMTAgMTAgMTAtNC40OCAxMC0xMFMxNy41MiAyIDEyIDJ6Ii8+PC9zdmc+",
    mimeType="image/svg+xml"
)

@mcp.tool(icons=[svg_icon])
def my_tool() -> str:
    """Tool with embedded SVG icon."""
    return "result"
```

**Decorator Return Behavior** (FastMCP 2.7+):
```python
# Decorator returns the Tool object, not the function
tool = @mcp.tool
def add(a: int, b: int) -> int:
    return a + b

# tool is now a Tool instance, not a function
assert isinstance(tool, Tool)
```

### Output Schema Standards

**All tools MUST define Pydantic output schemas** (FastMCP 2.10.0+):

```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class WeatherReport(BaseModel):
    temperature: float = Field(description="Temperature in Celsius")
    timestamp: datetime = Field(description="Measurement time")
    station_id: UUID = Field(description="Weather station identifier")
    humidity: int = Field(ge=0, le=100)

@mcp.tool(output_schema=WeatherReport)
def get_weather(city: str) -> WeatherReport:
    """Get current weather for a city."""
    return WeatherReport(
        temperature=20.5,
        timestamp=datetime.now(),
        station_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        humidity=65
    )
```

**Benefits**:
- FastMCP clients get fully hydrated Python objects in `.data`
- Complex types (datetime, UUID) automatically reconstructed
- Type safety enforced at runtime
- Self-documenting API contracts

**Primitive Wrapping**:
- Non-object returns (int, str, bool) auto-wrapped in `{"result": value}`
- FastMCP clients auto-unwrap for convenience
- Other MCP clients access via `structured_content["result"]`

```python
@mcp.tool
def calculate_sum(a: int, b: int) -> int:
    """Calculate sum of two numbers."""
    return a + b  # FastMCP wraps as {"result": 8}

# Client receives:
result.data  # 8 (auto-unwrapped)
result.structured_content  # {"result": 8}
```

### Advanced Return Patterns

**ToolResult for Full Control**:
```python
from fastmcp import ToolResult

@mcp.tool
def complex_tool(param: str) -> ToolResult:
    """Tool with multiple content types."""
    return ToolResult(
        content=[
            TextContent(text="Analysis complete"),
            ImageContent(data=b"...", mimeType="image/png")
        ],
        structured_output={"status": "success", "count": 42}
    )
```

**Automatic Conversion** (default behavior):
```python
@mcp.tool
def simple_tool(param: str) -> dict:
    """Simple dict return auto-converts to TextContent."""
    return {"result": "value"}  # Auto-converted to MCP content
```

### Async Tool Support

**Use async for I/O-bound operations**:
```python
import httpx

@mcp.tool
async def fetch_data(url: str) -> dict:
    """Fetch data from remote API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

### Context Access

**Access context for logging, progress, LLM sampling, and state**:
```python
from fastmcp import Context

@mcp.tool
async def long_task(param: str, ctx: Context) -> str:
    """Long-running task with full context capabilities."""
    # MCP client logging (sent to client)
    await ctx.debug("Starting task")
    await ctx.info(f"Processing {param}")
    await ctx.warning("Deprecated parameter used")
    await ctx.error("Failed step, retrying")

    # Structured logging with extra data
    await ctx.info(
        f"Processing transaction {param}",
        extra={
            "transaction_id": param,
            "amount": 100.0,
            "currency": "USD"
        }
    )

    # Progress reporting (FastMCP 2.0+)
    await ctx.report_progress(progress=0, total=100)
    await ctx.report_progress(progress=50, total=100)

    # LLM sampling (FastMCP 2.0+)
    response = await ctx.sample(
        messages=f"Analyze this data: {param}",
        system_prompt="You are a data analyst",
        temperature=0.3,
        max_tokens=512
    )
    analysis = response.text

    # Access persistent state
    ctx.state["last_run"] = datetime.now()

    return f"Complete: {analysis}"
```

**Client Logging Methods**:
- `await ctx.debug(message, extra=None)`: Debug-level messages
- `await ctx.info(message, extra=None)`: Informational messages
- `await ctx.warning(message, extra=None)`: Warning messages
- `await ctx.error(message, extra=None)`: Error messages
- `await ctx.log(level, message, logger_name=None, extra=None)`: Generic logging

**Progress Reporting Methods** (FastMCP 2.0+):
- `await ctx.report_progress(progress, total=None)`: Report progress to client
  - Percentage: `await ctx.report_progress(progress=75, total=100)`
  - Absolute: `await ctx.report_progress(progress=5, total=10)`
  - Indeterminate: `await ctx.report_progress(progress=files_processed)` (no total)

**LLM Sampling Methods** (FastMCP 2.0+):
- `await ctx.sample(messages, system_prompt=None, temperature=None, max_tokens=512, model_preferences=None)`: Request client LLM to generate text
  - Returns `TextContent` or `ImageContent` with response
  - Requires client support for sampling handlers

**Server-Side Logging** (separate from client logging):
```python
from fastmcp.utilities.logging import get_logger

# Server logs (not sent to client)
logger = get_logger(__name__)
logger.info("Server-side log entry")

# Enable client logging in server logs
to_client_logger = get_logger("fastmcp.server.context.to_client")
to_client_logger.setLevel(logging.DEBUG)
```

### Dynamic Tool Management

**Enable/disable tools programmatically**:
```python
# Define tool as disabled initially
@mcp.tool(enabled=False)
def experimental_feature() -> str:
    return "Experimental"

# Enable later based on configuration
if config.enable_experimental:
    mcp.enable_component(experimental_feature)
```

**Filter by tags**:
```python
# Disable all beta tools
mcp.disable_components_by_tags(["beta"])

# Enable only stable read tools
mcp.enable_components_by_tags(["stable", "read"])
```

### Tool Naming Conventions

- Use descriptive verb-noun format: `create_issue`, `list_repositories`
- Lowercase with underscores (snake_case)
- Prefix with domain if needed: `github_create_issue`
- No abbreviations unless universally understood
- Multi-server contexts: Expect automatic prefixing by client

### Metadata Standards

Tools MUST include metadata tags in `meta._fastmcp.tags` for:
- **Domain**: Primary area (e.g., `github`, `storage`, `compute`)
- **Action**: Operation type (e.g., `read`, `write`, `delete`)
- **Maturity**: Stability level (`stable`, `beta`, `experimental`)

Example:
```python
@mcp.tool(tags=["github", "read", "stable"])
def list_repositories(org: str) -> list[Repository]:
    """List all repositories in an organization."""
    ...
```

### Tool Discovery Requirements

Tools MUST be discoverable with complete metadata:
```python
# Tool must provide:
- name: str                    # Unique tool identifier
- description: str             # Clear, concise description
- inputSchema: dict           # JSON Schema (from Pydantic model)
- meta._fastmcp.tags: list    # Categorization tags
```

Clients can filter by tags:
```python
tools = await client.list_tools()
read_tools = [t for t in tools
              if 'read' in t.meta.get('_fastmcp', {}).get('tags', [])]
```

## Cloud Run Deployment Standards

### Required Google Cloud APIs

Enable these APIs before deployment:
- Cloud Run API (`run.googleapis.com`)
- Artifact Registry API (`artifactregistry.googleapis.com`)
- Cloud Build API (`cloudbuild.googleapis.com`)
- Secret Manager API (`secretmanager.googleapis.com`)

### Container Configuration

**Dockerfile Requirements**:
- **Base Image**: Official Python 3.11+ slim images (`python:3.11-slim`)
- **Dependency Manager**: Use `uv` (faster than pip, reproducible builds)
- **Dependencies**: Pinned versions in `pyproject.toml` or `requirements.txt`
- **Server File**: `server.py` as main entry point with FastMCP tools
- **Port**: Expose port 8080 (Cloud Run default) or configure via `PORT` env var
- **Transport**: HTTP transport for ChatGPT compatibility
- **Health Check**: Optional `/health` endpoint (Cloud Run handles this)
- **User**: Run as non-root user for security
- **Layer Optimization**: Multi-stage builds to minimize image size

**Example Dockerfile Structure**:
```dockerfile
FROM python:3.11-slim
RUN pip install uv
WORKDIR /app
COPY pyproject.toml .
RUN uv pip install --system -r pyproject.toml
COPY server.py .
# Use PORT env var for Cloud Run compatibility
ENV PORT=8080
CMD ["uv", "run", "python", "server.py"]
```

**Example server.py for Multi-Client Compatibility**:
```python
from fastmcp import FastMCP
import os

# Use descriptive name for MCP JSON configs
mcp = FastMCP("My MCP Server")

@mcp.tool(readOnlyHint=True)
def example_tool(param: str) -> dict:
    """Example tool description."""
    return {"result": param}

# Support both stdio (Claude Desktop, Cursor) and HTTP (ChatGPT, Cloud Run)
if __name__ == "__main__":
    # Default to stdio for local MCP clients
    # Use HTTP when PORT env var is set (Cloud Run)
    transport = "http" if os.getenv("PORT") else "stdio"
    port = int(os.getenv("PORT", 8080)) if transport == "http" else None

    if transport == "http":
        mcp.run(transport="http", port=port)
    else:
        mcp.run()  # stdio transport
```

This pattern supports:
- **stdio**: Claude Desktop, Cursor, VS Code (local installations)
- **HTTP**: ChatGPT, Cloud Run deployments

### Deployment Process

**Deployment Command Options**:

*For ChatGPT Integration (public access)*:
```bash
gcloud run deploy <SERVICE_NAME> \
  --source=. \
  --region=<REGION> \
  --allow-unauthenticated \
  --port=8080 \
  --labels=project=fastmcp,env=production,client=chatgpt
```

*For Internal MCP Clients (IAM-restricted)*:
```bash
gcloud run deploy <SERVICE_NAME> \
  --source=. \
  --region=<REGION> \
  --no-allow-unauthenticated \
  --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=github-client-id:latest \
  --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=github-client-secret:latest \
  --labels=project=fastmcp,env=production,client=claude
```

*For Hybrid (ChatGPT + GitHub OAuth)*:
```bash
gcloud run deploy <SERVICE_NAME> \
  --source=. \
  --region=<REGION> \
  --allow-unauthenticated \
  --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=github-client-id:latest \
  --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=github-client-secret:latest \
  --port=8080 \
  --labels=project=fastmcp,env=production,client=chatgpt,auth=github
```

**Deployment Requirements**:
1. Google Cloud project with billing enabled
2. Authenticated gcloud CLI (`gcloud auth login`)
3. Project set (`gcloud config set project PROJECT_ID`)
4. Region configured (`--region` flag or default)
5. Source code ready (Dockerfile or `--source` for Cloud Build)

### Environment Configuration

- **Development**: Local testing with `fastmcp dev` or `uv run python server.py`
- **Staging**: Cloud Run with staging OAuth app, limited access
- **Production**: Cloud Run with production OAuth app, monitoring enabled, IAM restricted

### Service Configuration

**Required Settings**:
- `--no-allow-unauthenticated`: Require authentication for all requests
- `--region`: Specify deployment region (e.g., `us-central1`, `europe-west1`)
- `--labels`: Add identifying labels (e.g., `env=prod`, `project=mcp`)

**Recommended Settings**:
- `--memory`: Allocate sufficient memory (default 512Mi, recommend 1Gi+)
- `--cpu`: Set CPU allocation (default 1, scale as needed)
- `--timeout`: Request timeout (default 300s, max 3600s)
- `--max-instances`: Limit concurrent instances for cost control
- `--min-instances`: Keep warm instances for reduced cold starts

### Monitoring & Observability

**Cloud Logging**:
- Log all tool invocations with user context and timestamp
- Log authentication events (OAuth flows, token validation)
- Structured logging in JSON format for parsing
- Include request IDs for tracing

**Cloud Monitoring**:
- Track tool execution duration (custom metrics)
- Monitor request rates and latency
- Alert on error rates > 5%
- Dashboard for OAuth success/failure rates

**Audit Trail**:
- Maintain logs for all authenticated requests
- Record GitHub user information from OAuth
- Track tool usage patterns per user
- Retention: 30 days minimum, 90 days recommended

## ChatGPT Integration Standards

### MCP Connector Configuration

**Server Requirements for ChatGPT**:
1. **Public Accessibility**: Server MUST be reachable via public HTTPS URL
   - Production: Cloud Run provides automatic HTTPS endpoint
   - Development: Use ngrok or similar tunneling service
2. **Endpoint Path**: FastMCP server MUST be accessible at `/mcp/` path
3. **HTTP Transport**: Use `mcp.run(transport="http", port=8000)` for local dev
4. **Port Configuration**: Cloud Run uses port 8080, dev uses 8000

**ChatGPT Connector Setup** (User-side):
1. Enable Developer Mode in ChatGPT settings
2. Add connector with:
   - Name: Descriptive server name
   - URL: `https://your-server-url.run.app/mcp/`
   - Authentication: Optional (GitHub OAuth recommended)
3. Activate connector explicitly in each chat session

### Chat Mode vs Deep Research Mode

**Chat Mode** (Standard):
- Tools appear as capabilities in chat
- User explicitly invokes tools or agent decides
- All tools available unless annotated with hints
- Return any structured data (dict, list, primitives)

**Deep Research Mode** (Specialized):
- Requires specific tool signatures: `search` and `fetch`
- Systematic information retrieval with citations
- Tool contracts:
  ```python
  @mcp.tool
  def search(query: str) -> list[str]:
      """Returns list of record IDs matching query."""
      return ["id1", "id2", "id3"]

  @mcp.tool
  def fetch(id: str) -> dict:
      """Returns complete record details for given ID."""
      return {"id": id, "content": "...", "metadata": {...}}
  ```

### Tool Annotations

Use `readOnlyHint` for tools that don't modify state:
```python
from fastmcp import FastMCP

mcp = FastMCP("Server Name")

@mcp.tool(readOnlyHint=True)
def get_data(query: str) -> dict:
    """Retrieve data without side effects."""
    return {"result": "..."}
```

**Rationale**: Read-only hints help ChatGPT understand tool safety and usage patterns.

### Development Workflow for ChatGPT Integration

**Local Testing**:
1. Run server locally: `fastmcp dev server.py`
2. Start ngrok tunnel: `ngrok http 8000`
3. Configure ChatGPT connector with ngrok URL + `/mcp/`
4. Test in ChatGPT Developer Mode
5. Iterate on tool implementations

**Production Deployment**:
1. Deploy to Cloud Run (with or without auth based on requirements)
2. Update ChatGPT connector with Cloud Run URL
3. Test authentication flow if using GitHub OAuth
4. Monitor usage in Cloud Logging

## MCP JSON Configuration Standards

### Standard Configuration Format

All FastMCP servers MUST be distributable via standard MCP JSON configuration following the emergent ecosystem standard:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "executable",
      "args": ["arg1", "arg2"],
      "env": {
        "VAR": "value"
      }
    }
  }
}
```

### Configuration Generation

Use `fastmcp install mcp-json` to generate client configurations:

**Basic Generation**:
```bash
fastmcp install mcp-json server.py
```

**With Dependencies**:
```bash
fastmcp install mcp-json server.py \
  --name "Production Server" \
  --with pandas \
  --with requests \
  --env API_KEY=secret
```

**From fastmcp.json** (recommended):
```json
{
  "$schema": "https://gofastmcp.com/public/schemas/fastmcp.json/v1.json",
  "source": {
    "path": "server.py",
    "entrypoint": "mcp"
  },
  "environment": {
    "dependencies": ["pandas", "requests"]
  }
}
```

Then: `fastmcp install mcp-json fastmcp.json`

### Configuration Fields

**Required Fields**:
- `command`: Always `uv` for FastMCP servers
- `args`: Array of arguments passed to uv run, including:
  - `--with fastmcp` (FastMCP dependency)
  - `--with <package>` (additional dependencies)
  - `fastmcp run <absolute-path-to-server.py>`

**Optional Fields**:
- `env`: Environment variables as string key-value pairs
- Server-specific uv options:
  - `--python <version>`: Specify Python version
  - `--project <path>`: Run within project directory
  - `--with-requirements <file>`: Load from requirements.txt

### Client Compatibility

Generated configurations MUST work with:
- **Claude Desktop**: `~/.claude/claude_desktop_config.json`
- **Claude Code**: Workspace `.claude/settings.json`
- **Cursor**: `~/.cursor/mcp.json`
- **VS Code**: Workspace `.vscode/mcp.json`
- **Other MCP clients**: Any client following the standard

### Configuration Best Practices

**1. Use Absolute Paths**:
```json
{
  "command": "uv",
  "args": ["run", "fastmcp", "run", "/home/user/project/server.py"]
}
```

**2. Pin Dependencies**:
```bash
fastmcp install mcp-json server.py \
  --with pandas==2.0.0 \
  --with requests==2.31.0
```

**3. Environment Variables for Secrets**:
```json
{
  "env": {
    "API_KEY": "placeholder-replace-me",
    "DATABASE_URL": "postgresql://localhost/db"
  }
}
```

**4. Use fastmcp.json for Complex Configs**:
```json
{
  "$schema": "https://gofastmcp.com/public/schemas/fastmcp.json/v1.json",
  "source": {
    "path": "server.py",
    "entrypoint": "mcp"
  },
  "environment": {
    "dependencies": ["pandas", "matplotlib", "seaborn"],
    "python": "3.11",
    "env_file": ".env"
  }
}
```

### Distribution Patterns

**Copy to Clipboard**:
```bash
fastmcp install mcp-json server.py --copy
```

**Save to File**:
```bash
fastmcp install mcp-json server.py > mcp-config.json
```

**CI/CD Pipeline**:
```bash
#!/bin/bash
CONFIG=$(fastmcp install mcp-json server.py --name "CI Server")
echo "$CONFIG" | jq '."CI Server".command'
```

**Team Distribution**:
1. Generate config with placeholders: `fastmcp install mcp-json server.py`
2. Document environment variables in README
3. Team members replace placeholders and add to their client

## Tool Operation Standards

### Tool Execution Patterns

**Basic Execution**:
```python
async with client:
    result = await client.call_tool("add", {"a": 5, "b": 3})
    print(result.data)  # 8 (fully hydrated)
```

**Advanced Execution**:
```python
async with client:
    # With timeout
    result = await client.call_tool(
        "long_task",
        {"param": "value"},
        timeout=2.0
    )

    # With progress handler
    result = await client.call_tool(
        "long_task",
        {"param": "value"},
        progress_handler=my_progress_handler
    )
```

### Result Handling Standards

**CallToolResult Properties** (FastMCP exclusive):

1. **`.data`**: Fully hydrated Python objects with complex type support
   - datetime objects (not ISO strings)
   - UUID objects (not string representations)
   - Custom Pydantic models (not dictionaries)
   - Primitive unwrapping for int/str/bool returns

2. **`.content`**: Standard MCP content blocks
   - TextContent, ImageContent, AudioContent
   - Compatible with all MCP servers

3. **`.structured_content`**: Raw JSON data
   - Standard MCP structured output
   - Available from all servers supporting structured outputs

4. **`.is_error`**: Boolean error state

**Usage Pattern**:
```python
from datetime import datetime
from uuid import UUID

result = await client.call_tool("get_weather", {"city": "London"})

# FastMCP reconstructs complete Python objects
weather = result.data  # WeatherReport instance
assert isinstance(weather.timestamp, datetime)
assert isinstance(weather.station_id, UUID)

# Fallback to content blocks if no structured output
if result.data is None:
    for content in result.content:
        if hasattr(content, 'text'):
            print(content.text)
```

### Error Handling Patterns

**Server-Side Error Handling**:
```python
from fastmcp.exceptions import ToolError

@mcp.tool
def risky_tool(param: str) -> str:
    """Tool that may fail."""
    if not param:
        raise ToolError("Parameter cannot be empty")

    try:
        # Risky operation
        result = external_api(param)
        return result
    except Exception as e:
        # Mask internal errors for security
        raise ToolError("Operation failed") from e
```

**Client-Side Error Handling**:

**Exception-Based (Default)**:
```python
from fastmcp.exceptions import ToolError

try:
    result = await client.call_tool("risky_tool", {"param": "value"})
    print("Success:", result.data)
except ToolError as e:
    print(f"Failed: {e}")
```

**Manual Checking**:
```python
result = await client.call_tool(
    "risky_tool",
    {"param": "value"},
    raise_on_error=False
)

if result.is_error:
    print(f"Failed: {result.content[0].text}")
else:
    print(f"Success: {result.data}")
```

**Raw Protocol Access**:
```python
result = await client.call_tool_mcp("tool", {"param": "value"})
# Returns mcp.types.CallToolResult (no automatic deserialization)
```

### Error Masking for Security

**Mask internal errors in production**:
```python
@mcp.tool
def secure_tool(param: str) -> str:
    try:
        # Internal operation
        return sensitive_operation(param)
    except DatabaseError as e:
        # Don't expose database details to clients
        raise ToolError("Operation failed") from e
    except AuthenticationError as e:
        # Don't expose auth details
        raise ToolError("Access denied") from e
```

### Argument Handling Standards

**Simple Arguments**:
```python
await client.call_tool("greet", {"name": "World"})
```

**Complex Arguments**:
```python
await client.call_tool("process_data", {
    "config": {"format": "json", "validate": True},
    "items": [1, 2, 3, 4, 5],
    "metadata": {"source": "api", "version": "1.0"}
})
```

### Progress Reporting Standards

Long-running tools (>5 seconds) MUST use `ctx.report_progress()`:

```python
@mcp.tool
async def long_running_task(param: str, ctx: Context) -> dict:
    """Long-running task with progress reporting."""
    total = 100
    for i in range(total):
        # Report progress to client
        await ctx.report_progress(progress=i, total=total)
        # Do work

    # Report completion
    await ctx.report_progress(progress=total, total=total)
    return {"status": "complete"}
```

**Progress Patterns**:
- **Percentage**: `await ctx.report_progress(progress=75, total=100)`
- **Absolute**: `await ctx.report_progress(progress=5, total=10)`
- **Indeterminate**: `await ctx.report_progress(progress=files_processed)` (no total)
- **Multi-stage**: Report progress per stage with descriptive context logging

## Multi-Server Support

When building multi-server MCP clients:
- Expect automatic tool name prefixing by client
- Design tools for composability across servers
- Document server dependencies explicitly
- Support raw protocol access via `call_tool_mcp()` when needed
- Generate individual MCP JSON configs for each server
- Use unique server names to avoid conflicts

**Multi-Server Tool Naming**:
```python
# Server named "weather"
@mcp.tool
def get_forecast(city: str): ...

# Client calls as:
await client.call_tool("weather_get_forecast", {"city": "London"})
```

## Caching & Performance Standards

### Caching Middleware (Recommended for Production)

Production deployments SHOULD use response caching middleware to improve performance and reduce server load:

**Basic Configuration** (default TTL, in-memory):
```python
from fastmcp.server.middleware.caching import ResponseCachingMiddleware

mcp.add_middleware(ResponseCachingMiddleware())
```

**Default Behavior**:
- Caches `call_tool`, `list_tools`, `read_resource`, `list_prompts`
- In-memory storage with TTL-based expiration
- No event-based cache invalidation
- Global keys for list operations

**Per-Method Configuration**:
```python
from fastmcp.server.middleware.caching import (
    ResponseCachingMiddleware,
    CallToolSettings,
    ListToolsSettings,
    ReadResourceSettings,
    ListPromptsSettings
)

mcp.add_middleware(ResponseCachingMiddleware(
    # Cache tool list for 30 seconds
    list_tools_settings=ListToolsSettings(
        ttl=30,
        enabled=True
    ),

    # Only cache specific tools
    call_tool_settings=CallToolSettings(
        included_tools=["expensive_tool", "rate_limited_api"],
        ttl=300  # 5 minutes
    ),

    # Disable resource caching
    read_resource_settings=ReadResourceSettings(
        enabled=False
    ),

    # Cache prompts for 60 seconds
    list_prompts_settings=ListPromptsSettings(
        ttl=60
    )
))
```

**Production Configuration with Redis**:
```python
from key_value.aio.stores.redis import RedisStore
from fastmcp.server.middleware.caching import ResponseCachingMiddleware

redis_store = RedisStore(
    host="redis.example.com",
    port=6379,
    password=os.environ.get("REDIS_PASSWORD")
)

mcp.add_middleware(ResponseCachingMiddleware(
    cache_storage=redis_store,  # Distributed cache
    list_tools_settings=ListToolsSettings(ttl=60),
    call_tool_settings=CallToolSettings(ttl=300)
))
```

**Cache Settings Options**:
- `enabled`: Enable/disable caching for this method (default: True)
- `ttl`: Time-to-live in seconds (default: varies by method)
- `included_tools`: Whitelist of tool names to cache (call_tool only)
- `excluded_tools`: Blacklist of tool names to skip (call_tool only)
- `cache_storage`: Storage backend (default: in-memory)

**Multi-Server Considerations**:
- List operations use global cache keys
- When sharing storage backend across servers, namespace collections to prevent conflicts
- Consider per-server cache prefixes or separate Redis databases

**Cache Invalidation**:
- TTL-based expiration only (no event-based invalidation)
- Manual invalidation: restart server or flush storage backend
- Choose appropriate TTLs based on data volatility

## Storage Backends & State Management

### Storage Backend Requirements (NON-NEGOTIABLE for Production)

Production deployments MUST use persistent, distributed storage for OAuth tokens and MAY use it for caching:
- **Development**: In-memory storage (default, lost on restart)
- **Single Server**: Disk storage for persistence across restarts
- **Multi-Server/Cloud**: Redis or cloud-native storage (DynamoDB, MongoDB)

**Rationale**: In-memory storage is fast but ephemeral. Production requires persistence for OAuth; distributed cache improves multi-server performance (FastMCP 2.13.0+).

### Redis Storage Backend (Recommended for Production)

**Redis is the recommended storage backend** for Cloud Run and multi-server deployments:

```python
from key_value.aio.stores.redis import RedisStore
from fastmcp.server.auth.providers.github import GitHubProvider
from fastmcp.server.middleware.caching import ResponseCachingMiddleware
import os

# Redis for distributed OAuth token storage
redis_store = RedisStore(
    host="redis.example.com",
    port=6379,
    password=os.environ.get("REDIS_PASSWORD")
)

# OAuth with Redis token persistence
auth = GitHubProvider(
    client_id=os.environ["GITHUB_CLIENT_ID"],
    client_secret=os.environ["GITHUB_CLIENT_SECRET"],
    base_url="https://your-server.com",
    jwt_signing_key=os.environ["JWT_SIGNING_KEY"],
    token_encryption_key=os.environ["TOKEN_ENCRYPTION_KEY"],
    client_storage=redis_store  # Distributed token storage
)

# Response caching with Redis
mcp.add_middleware(ResponseCachingMiddleware(
    cache_storage=redis_store
))
```

**Redis Installation**:
```bash
pip install 'py-key-value-aio[redis]'
```

### Storage Backend Options

**Available Backends** (via py-key-value-aio):
- **MemoryStore**: In-memory (default, fast, ephemeral)
- **DiskStore**: Local filesystem persistence
- **RedisStore**: Distributed, highly available (recommended)
- **DynamoDBStore**: AWS cloud-native
- **MongoDBStore**: NoSQL document store
- **ElasticsearchStore**: Distributed search and analytics
- **MemcachedStore**: Distributed memory caching
- **RocksDBStore**: Embedded high-performance key-value

**Storage Use Cases**:
1. **OAuth Token Storage**: Store encrypted OAuth client registrations and tokens
2. **Response Caching**: Cache tool calls, resource reads, prompt requests
3. **Client Token Storage**: FastMCP client persists OAuth tokens locally

**Storage Selection Matrix**:

| Backend      | Development | Single Server | Multi-Server | Cloud Native |
|--------------|-------------|---------------|--------------|--------------|
| Memory       | ✅ Best      | ⚠️ Limited    | ❌            | ❌            |
| Disk         | ✅ Good      | ✅ Recommended | ❌            | ⚠️           |
| Redis        | ⚠️ Overkill | ✅ Good        | ✅ Best       | ✅ Best       |
| DynamoDB     | ❌           | ⚠️            | ✅            | ✅ Best (AWS) |

### OAuth Token Security & Persistence

**Production OAuth Token Requirements** (all three required together):
1. **`jwt_signing_key`**: Secret for signing FastMCP JWT tokens (any string, derived via HKDF)
2. **`token_encryption_key`**: Secret for encrypting upstream tokens at rest (distinct from signing key)
3. **`client_storage`**: Persistent storage backend (Redis, DynamoDB, Disk)

**Default Behavior (Development)**:
- Keys are ephemeral (random salt at startup)
- Storage defaults to disk (`~/.config/fastmcp/oauth-proxy-clients/`)
- Tokens survive restarts as long as filesystem accessible
- Clients register once, reconnect seamlessly

**Production Configuration**:
```python
import os
from key_value.aio.stores.redis import RedisStore

auth = GitHubProvider(
    client_id=os.environ["GITHUB_CLIENT_ID"],
    client_secret=os.environ["GITHUB_CLIENT_SECRET"],
    base_url="https://your-server.com",
    # Production token persistence (all three required)
    jwt_signing_key=os.environ["JWT_SIGNING_KEY"],      # Any string!
    token_encryption_key=os.environ["TOKEN_ENCRYPTION_KEY"],  # Distinct secret
    client_storage=RedisStore(...)  # Distributed storage
)
```

**Key Management**:
- Use environment variables for all secrets
- Use distinct secrets for JWT signing vs token encryption
- Rotate keys periodically (invalidates existing tokens)
- Store in Google Secret Manager for Cloud Run

## Authentication & Authorization Standards

### GitHub OAuth Integration (Recommended)

**GitHub OAuth is the standard authentication** for this project:

```python
from fastmcp.server.auth.providers.github import GitHubProvider
import os

auth = GitHubProvider(
    client_id=os.environ["GITHUB_CLIENT_ID"],
    client_secret=os.environ["GITHUB_CLIENT_SECRET"],
    base_url="https://your-server.com",
    redirect_path="/auth/callback",  # Must match GitHub OAuth App config
    required_scopes=["user"],  # GitHub scopes to request
    jwt_signing_key=os.environ.get("JWT_SIGNING_KEY"),  # Production only
    token_encryption_key=os.environ.get("TOKEN_ENCRYPTION_KEY"),  # Production only
    client_storage=redis_store  # Production: use Redis
)

mcp = FastMCP(name="GitHub Secured Server", auth=auth)
```

**GitHub OAuth App Setup Requirements**:
1. Create OAuth App in GitHub Settings → Developer settings
2. **Application name**: Descriptive name users will recognize
3. **Homepage URL**: Your application URL or documentation
4. **Authorization callback URL**: `{base_url}/auth/callback` (exact match required)
5. Save Client ID and Client Secret securely

**Callback URL Configuration**:
- Development: `http://localhost:8000/auth/callback`
- Production: `https://your-server.com/auth/callback` (HTTPS required)
- Must match exactly between GitHub OAuth App and `base_url` + `redirect_path`

### OAuth Proxy Pattern

**OAuth Proxy bridges traditional OAuth providers to MCP clients**:

The OAuth Proxy enables FastMCP servers to authenticate with OAuth providers that don't support Dynamic Client Registration (GitHub, Google, Azure, AWS, Discord, Facebook, most enterprise systems).

**Key Concepts**:
- **Token Factory Pattern**: Proxy issues FastMCP JWT tokens, not provider tokens directly
- **Dual PKCE**: Client-to-proxy and proxy-to-provider PKCE for end-to-end security
- **Consent Protection**: User consent required for each new client (confused deputy mitigation)
- **Token Persistence**: Tokens survive restarts with proper key and storage configuration

**OAuth Proxy Flow**:
1. **Registration**: Client calls `/register`, receives upstream credentials
2. **Authorization**: Client redirects to `/authorize`, proxy shows consent, redirects to provider
3. **Callback**: Provider redirects to proxy, proxy exchanges for tokens, redirects to client
4. **Token Exchange**: Client exchanges code for FastMCP JWT token
5. **Validation**: Proxy validates JWT, looks up encrypted upstream token, validates with provider

**Security Features**:
- **Confused Deputy Protection**: User consent required per client (FastMCP 2.13.0+)
- **PKCE Forwarding**: End-to-end PKCE at both layers (enabled by default)
- **Token Audience**: FastMCP tokens scoped to this server only
- **Token Encryption**: Upstream tokens encrypted at rest (Fernet AES-128-CBC + HMAC-SHA256)
- **Redirect URI Validation**: Optional allowlist for client redirect URIs

### Token Verification Patterns

**Token verification validates bearer tokens** without participating in user authentication:

**JWT Token Verification** (most common):
```python
from fastmcp.server.auth.providers.jwt import JWTVerifier

# JWKS endpoint verification (production)
verifier = JWTVerifier(
    jwks_uri="https://auth.yourcompany.com/.well-known/jwks.json",
    issuer="https://auth.yourcompany.com",
    audience="mcp-production-api",
    required_scopes=["read:data", "write:data"]
)

# HMAC symmetric key verification (internal microservices)
verifier = JWTVerifier(
    public_key="your-shared-secret-key-minimum-32-chars",  # Despite name, accepts HMAC secrets
    issuer="internal-auth-service",
    audience="mcp-internal-api",
    algorithm="HS256"  # or HS384, HS512
)

# Static public key verification (development)
verifier = JWTVerifier(
    public_key=public_key_pem,  # RSA/ECDSA public key
    issuer="https://auth.yourcompany.com",
    audience="mcp-production-api"
)

mcp = FastMCP(name="Protected API", auth=verifier)
```

**Opaque Token Introspection** (RFC 7662):
```python
from fastmcp.server.auth.providers.introspection import IntrospectionTokenVerifier

verifier = IntrospectionTokenVerifier(
    introspection_url="https://auth.yourcompany.com/oauth/introspect",
    client_id="mcp-resource-server",
    client_secret="your-client-secret",
    required_scopes=["api:read", "api:write"]
)

mcp = FastMCP(name="Protected API", auth=verifier)
```

**Static Token Verification** (development only):
```python
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

verifier = StaticTokenVerifier(
    tokens={
        "dev-alice-token": {
            "client_id": "alice@company.com",
            "scopes": ["read:data", "write:data", "admin:users"]
        },
        "dev-guest-token": {
            "client_id": "guest-user",
            "scopes": ["read:data"]
        }
    },
    required_scopes=["read:data"]
)

mcp = FastMCP(name="Development Server", auth=verifier)
```

**Environment-Based Configuration** (FastMCP 2.12.1+):
```bash
# Enable JWT verification via environment
export FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.jwt.JWTVerifier
export FASTMCP_SERVER_AUTH_JWT_JWKS_URI="https://auth.company.com/.well-known/jwks.json"
export FASTMCP_SERVER_AUTH_JWT_ISSUER="https://auth.company.com"
export FASTMCP_SERVER_AUTH_JWT_AUDIENCE="mcp-production-api"
export FASTMCP_SERVER_AUTH_JWT_REQUIRED_SCOPES="read:data,write:data"
```

### Authentication Method Selection

**Choose authentication based on deployment scenario**:

| Scenario | Method | Rationale |
|----------|--------|-----------|
| Public MCP server, user authentication | **OAuth Proxy** (GitHub) | User identity, token persistence, confused deputy protection |
| Internal microservice, shared secret | **JWT Verifier** (HMAC) | Fast, simple, no external dependencies |
| Internal microservice, external IdP | **JWT Verifier** (JWKS) | Automatic key rotation, enterprise integration |
| Legacy OAuth provider tokens | **Introspection Verifier** | RFC 7662 standard, opaque token support |
| Development/testing | **Static Token Verifier** | No infrastructure, instant testing |

### Scope & Authorization Management

**Required vs Valid Scopes**:
- **`required_scopes`**: Minimum scopes needed for authentication to succeed
- **`valid_scopes`**: All possible scopes your provider supports (advertised to clients)

**Scope Configuration**:
```python
# TokenVerifier required_scopes
verifier = JWTVerifier(
    ...,
    required_scopes=["read:user"]  # Minimum required
)

# OAuth Proxy inherits from TokenVerifier + custom valid_scopes
auth = OAuthProxy(
    ...,
    token_verifier=verifier,
    valid_scopes=["read:user", "write:data", "admin:users"]  # All possible
)
```

**Dynamic clients** automatically request `required_scopes` during authorization.

### Transport & Deployment Patterns

**STDIO Transport** (default):
- Command-line tools, Claude Desktop, Cursor, VS Code
- Client spawns server process per session
- No network exposure

**HTTP Transport** (production):
- ChatGPT integration, web services, remote access
- Multiple concurrent clients
- Requires public URL for OAuth callbacks

**Multi-Client Server Pattern**:
```python
import os

# Support both stdio (local) and HTTP (ChatGPT, Cloud Run)
if __name__ == "__main__":
    transport = "http" if os.getenv("PORT") else "stdio"
    port = int(os.getenv("PORT", 8080)) if transport == "http" else None

    if transport == "http":
        mcp.run(transport="http", port=port)
    else:
        mcp.run()  # stdio
```

**Cloud Run Deployment Scenarios**:

1. **ChatGPT Integration** (public access):
   ```bash
   gcloud run deploy --allow-unauthenticated --port=8080
   ```

2. **Internal MCP Clients** (IAM-restricted):
   ```bash
   gcloud run deploy --no-allow-unauthenticated \
     --set-secrets=GITHUB_CLIENT_ID=github-client-id:latest \
     --set-secrets=GITHUB_CLIENT_SECRET=github-client-secret:latest
   ```

3. **Hybrid** (ChatGPT + GitHub OAuth):
   ```bash
   gcloud run deploy --allow-unauthenticated \
     --set-secrets=GITHUB_CLIENT_ID=github-client-id:latest \
     --set-secrets=GITHUB_CLIENT_SECRET=github-client-secret:latest \
     --port=8080
   ```

## Project-Specific: Speech RAG Server Architecture

### Project Overview

This project implements a **Retrieval-Augmented Generation (RAG) server** for searching and analyzing speeches with rich metadata using FastMCP on Google Cloud Run.

**Primary Use Case**: Enable AI assistants (Claude, ChatGPT, Cursor) to search, retrieve, and analyze historical speeches with semantic understanding and metadata filtering.

### Architecture Decision (NON-NEGOTIABLE)

**RECOMMENDED ARCHITECTURE: Google ADK-Aligned Stack**

This architecture follows Google's Agent Development Kit (ADK) patterns, which use LangChain for production agent systems.

**Technology Stack**:
- **Compute**: Google Cloud Run (FastMCP server)
- **Vector Database**: Cloud SQL PostgreSQL with pgvector extension (v0.8.0)
- **Embeddings**: Vertex AI textembedding-gecko@003 (768 dimensions)
- **Framework**: LangChain (Google ADK standard)
- **Cache**: Cloud Memorystore for Redis
- **Secrets**: Google Secret Manager
- **CI/CD**: Cloud Build + Artifact Registry

**Monthly Cost**: $100-150/month
- Cloud SQL PostgreSQL: $60-110 (db-custom-2-7680, 20GB SSD)
- Cloud Memorystore Redis: $36 (1GB)
- VPC Connector: $10
- Vertex AI Embeddings: ~$2/month (query costs only, ~1000 searches/month)
  - Initial ingestion: ~$1,500 one-time (5,000 speeches × 12k chars/speech)

**Performance**:
- Vector search: 100-200ms p95 (pgvector HNSW)
- Metadata queries: <20ms (PostgreSQL)
- Embedding generation: 50-100ms (Vertex AI API)
- Concurrent users: 10-50 (auto-scaling)

**Why This Architecture (Rationale)**:

1. **Google ADK Alignment** ✅
   - Google's own Agent Development Kit uses LangChain
   - Battle-tested in production Google agents
   - Native integrations: Vertex AI + Cloud SQL
   - Future-proof: aligns with Google's agent ecosystem

2. **100% Google Cloud** ✅
   - Single vendor (unified billing, IAM, support)
   - No external services (Qdrant, OpenAI, etc.)
   - Enterprise compliance requirements met
   - Cloud SQL pgvector (managed PostgreSQL extension)

3. **Single Database for Everything** ✅
   - Vectors (pgvector 768-dim embeddings)
   - Metadata (speaker, party, chamber, date)
   - Full text (complete speech transcripts)
   - ACID transactions across all data

4. **Superior Embeddings** ✅
   - Vertex AI textembedding-gecko (768 dims) vs sentence-transformers (384 dims)
   - Higher quality semantic search
   - Native Google Cloud integration
   - No container memory overhead (API-based)

5. **LangChain Ecosystem** ✅
   - `langchain-google-vertexai` (embeddings)
   - `langchain-google-cloud-sql-pg` (vector store)
   - Proven RAG patterns and abstractions
   - Extensive documentation and community

6. **Full Text Retrieval** ✅
   - PostgreSQL stores complete speech transcripts
   - Vector search returns chunk text + full speech retrieval
   - No external lookups required
   - Single query retrieves vectors + metadata + full text

**Architecture Trade-offs**:

| Factor | This Architecture | Alternative (Qdrant + sentence-transformers) |
|--------|-------------------|---------------------------------------------|
| **Google ADK Aligned** | ✅ Yes (LangChain standard) | ❌ No |
| **Embedding Quality** | 🥇 Vertex AI (768 dims) | Good (384 dims) |
| **Initial Ingestion Cost** | $1,500 one-time | Free |
| **Monthly Query Cost** | $2/month | Free |
| **Vector Search Speed** | 100-200ms | <50ms |
| **Monthly Infrastructure** | $100-150 | $72 |
| **100% Google Cloud** | ✅ Yes | ❌ No (Qdrant external) |
| **Single Database** | ✅ Yes | ❌ No (2 databases) |
| **Framework** | LangChain | Minimal deps |

**Decision**: Accept higher cost ($1,500 initial + $100/month) for Google ecosystem alignment and superior embeddings

### Infrastructure Specifications

#### 1. Cloud Run (FastMCP Server)

```yaml
Configuration:
  CPU: 1 vCPU
  Memory: 512 MB (Vertex AI embeddings via API - no local model)
  Min instances: 0 (scale to zero)
  Max instances: 10
  Concurrency: 80 requests/container
  Timeout: 300s (5 minutes)
  Region: us-central1
Cost: ~$10-15/month
```

**Justification**: Low memory footprint since embeddings generated via Vertex AI API (no in-container model). FastMCP server handles routing and LangChain orchestration only.

#### 2. Cloud SQL PostgreSQL with pgvector (Vector Database + Metadata + Full Text)

```yaml
Configuration:
  Instance: db-custom-2-7680 (2 vCPU, 7.5GB RAM)
  Storage: 20GB SSD
  Version: PostgreSQL 15
  Extensions: vector (pgvector 0.8.0)
  Dimensions: 768 (Vertex AI textembedding-gecko)
  Index: HNSW (m=16, ef_construction=64)
  Backups: Automated daily
  High Availability: No (add in production: +$50/month)
  Region: us-central1
  Connection Pooling: Enabled (PgBouncer)
Cost: ~$60-110/month
Capacity: 50,000 speeches (~250k chunks after splitting)
```

**Justification**: Single database for vectors, metadata, and full speech text. pgvector 0.8.0 provides HNSW indexing for fast vector search. LangChain integration via `langchain-google-cloud-sql-pg`.

#### 3. Cloud Memorystore for Redis

```yaml
Configuration:
  Tier: Basic (non-HA)
  Memory: 1 GB
  Version: Redis 7.0
  Network: Private IP (VPC)
  Region: us-central1
Cost: ~$36/month
```

**Justification**: Required for OAuth token persistence across Cloud Run instances. Provides response caching for frequent queries (TTL-based).

#### 4. Database Schema (PostgreSQL + pgvector + LangChain)
```sql
-- Enable pgvector extension
CREATE EXTENSION vector;

-- Speakers reference table
CREATE TABLE speakers (
  speaker_id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  party TEXT NOT NULL,
  chamber TEXT NOT NULL,
  state TEXT NOT NULL,
  electorate TEXT
);

-- Full speeches (complete transcripts)
CREATE TABLE speeches (
  speech_id UUID PRIMARY KEY,
  speaker_id INTEGER REFERENCES speakers(speaker_id),
  title TEXT NOT NULL,
  full_text TEXT NOT NULL,  -- ⭐ Complete speech text for retrieval
  date DATE NOT NULL,
  hansard_reference TEXT,
  source_url TEXT,
  word_count INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Speech chunks with vector embeddings (for semantic search)
CREATE TABLE speech_chunks (
  chunk_id UUID PRIMARY KEY,
  speech_id UUID NOT NULL REFERENCES speeches(speech_id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  chunk_text TEXT NOT NULL,
  embedding vector(768),  -- ⭐ Vertex AI embeddings (768 dimensions)

  -- Denormalized metadata for fast filtering (no joins during search)
  speaker TEXT NOT NULL,
  party TEXT NOT NULL,
  chamber TEXT NOT NULL,
  state TEXT NOT NULL,
  date DATE NOT NULL,

  -- Topic flags (ChromaDB limitation workaround)
  topic_economy BOOLEAN DEFAULT FALSE,
  topic_healthcare BOOLEAN DEFAULT FALSE,
  topic_climate BOOLEAN DEFAULT FALSE,
  topic_immigration BOOLEAN DEFAULT FALSE,
  topic_education BOOLEAN DEFAULT FALSE,
  topic_foreign_policy BOOLEAN DEFAULT FALSE,
  topic_infrastructure BOOLEAN DEFAULT FALSE,

  hansard_reference TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- HNSW index for fast vector search
CREATE INDEX ON speech_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- B-tree indexes for metadata filtering
CREATE INDEX idx_speech_chunks_speaker ON speech_chunks(speaker);
CREATE INDEX idx_speech_chunks_party ON speech_chunks(party);
CREATE INDEX idx_speech_chunks_date ON speech_chunks(date);
CREATE INDEX idx_speech_chunks_chamber ON speech_chunks(chamber);
```

**Performance Tuning**:
```sql
-- Increase work memory for better vector index builds
ALTER DATABASE hansard SET maintenance_work_mem = '2GB';

-- Optimize parallel workers for vector search
ALTER DATABASE hansard SET max_parallel_workers_per_gather = 4;

-- Enable connection pooling (Cloud SQL built-in PgBouncer)
```

**Python Integration (LangChain + Vertex AI)**:
```python
from fastmcp import FastMCP
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_cloud_sql_pg import PostgresEngine, PostgresVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field
from typing import List, Optional
import os

# Initialize FastMCP server
mcp = FastMCP("Australian Hansard RAG")

# Initialize Vertex AI embeddings (768 dimensions)
embeddings = VertexAIEmbeddings(
    model_name="textembedding-gecko@003",
    project=os.environ["GCP_PROJECT_ID"]
)

# Initialize Cloud SQL PostgreSQL engine
engine = await PostgresEngine.afrom_instance(
    project_id=os.environ["GCP_PROJECT_ID"],
    region="us-central1",
    instance=os.environ["CLOUDSQL_INSTANCE"],
    database="hansard"
)

# Initialize vector store with pgvector
vector_store = await PostgresVectorStore.create(
    engine=engine,
    table_name="speech_chunks",
    embedding_service=embeddings,
    metadata_columns=[
        "speaker", "party", "chamber", "state", "date",
        "topic_economy", "topic_healthcare", "topic_climate",
        "hansard_reference", "speech_id"
    ]
)

# Text splitter for chunking speeches
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=700,
    chunk_overlap=100,
    separators=["\n\n", "\n", ". ", " ", ""]
)

class SpeechSearchResult(BaseModel):
    """Search result from Australian Hansard."""
    speech_id: str = Field(description="UUID of the speech")
    speaker: str = Field(description="MP/Senator name")
    party: str = Field(description="Political party")
    chamber: str = Field(description="House of Representatives or Senate")
    excerpt: str = Field(description="Relevant text excerpt (500 chars)")
    full_text: str = Field(description="⭐ Complete speech transcript")
    relevance_score: float = Field(description="Semantic similarity (0-1)")
    hansard_reference: str = Field(description="Official Hansard reference")
    date: str = Field(description="Speech date (ISO 8601)")

@mcp.tool
async def search_speeches(
    query: str,
    party: Optional[str] = None,
    chamber: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = 10,
    ctx: Context = None
) -> List[SpeechSearchResult]:
    """
    Search Australian Hansard speeches using semantic search + metadata filtering.

    Returns complete speech transcripts along with relevant excerpts.
    """

    # Build metadata filter
    filters = {}
    if party:
        filters["party"] = party
    if chamber:
        filters["chamber"] = chamber
    if topic and topic.lower() in ["economy", "healthcare", "climate"]:
        filters[f"topic_{topic.lower()}"] = True

    # Perform hybrid search (vector similarity + metadata filtering)
    chunk_results = await vector_store.asimilarity_search_with_score(
        query=query,
        k=limit,
        filter=filters if filters else None
    )

    # Retrieve full speech text for each result
    results = []
    for doc, score in chunk_results:
        speech_id = doc.metadata["speech_id"]

        # Fetch full speech from speeches table
        full_speech = await engine.execute(
            "SELECT full_text FROM speeches WHERE speech_id = $1",
            [speech_id]
        )

        results.append(SpeechSearchResult(
            speech_id=speech_id,
            speaker=doc.metadata["speaker"],
            party=doc.metadata["party"],
            chamber=doc.metadata["chamber"],
            excerpt=doc.page_content[:500],  # Chunk excerpt
            full_text=full_speech[0]["full_text"],  # ⭐ Complete speech
            relevance_score=score,
            hansard_reference=doc.metadata["hansard_reference"],
            date=doc.metadata["date"]
        ))

    return results

@mcp.tool
async def get_speech_full_text(
    speech_id: str,
    ctx: Context = None
) -> str:
    """
    Retrieve complete transcript of a speech by ID.

    Use this after search_speeches to get full untruncated text.
    """
    result = await engine.execute(
        "SELECT full_text FROM speeches WHERE speech_id = $1",
        [speech_id]
    )

    if not result:
        raise ValueError(f"Speech {speech_id} not found")

    return result[0]["full_text"]
```

**Key Features**:
1. ✅ **LangChain Integration**: Uses `langchain-google-vertexai` + `langchain-google-cloud-sql-pg`
2. ✅ **Vertex AI Embeddings**: 768-dim textembedding-gecko (superior quality)
3. ✅ **Full Text Retrieval**: `search_speeches` returns both chunk excerpt AND complete speech
4. ✅ **Hybrid Search**: Vector similarity + metadata filtering (party, chamber, topics)
5. ✅ **Google ADK Aligned**: Follows Google's agent development patterns

#### 5. VPC Networking

```yaml
Configuration:
  Serverless VPC Access Connector:
    Throughput: 200-300 Mbps
    IP Range: 10.8.0.0/28
    Region: us-central1
Cost: ~$10/month
```

**Justification**: Required for Cloud Run → Redis private IP communication.

#### 6. Secrets & CI/CD

```yaml
Secret Manager:
  - GITHUB_CLIENT_ID
  - GITHUB_CLIENT_SECRET
  - JWT_SIGNING_KEY
  - TOKEN_ENCRYPTION_KEY
  - QDRANT_API_KEY
  - QDRANT_URL
  - REDIS_PASSWORD
  - DATABASE_URL
Cost: <$1/month

Cloud Build + Artifact Registry:
  Free tier: 120 build-minutes/day
Cost: FREE
```

### Speech Processing Pipeline Standards

#### Chunking Strategy (NON-NEGOTIABLE)

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,        # ~2-3 paragraphs per chunk
    chunk_overlap=150,     # 15-20% overlap for context preservation
    separators=["\n\n", "\n", ". ", " ", ""],  # Semantic boundaries
    length_function=len,
)
```

**Rationale** (based on 2025 RAG best practices):
- 800 chars preserves speech context (complete thoughts)
- 150 char overlap prevents losing meaning at boundaries
- Semantic separators maintain speech structure

#### Embedding Model (NON-NEGOTIABLE)

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
# Dimensions: 384
# Speed: ~50ms per chunk on 1 vCPU
# Quality: Optimized for semantic similarity
```

**Alternative** (if quality issues): `BAAI/bge-large-en-v1.5` (1024 dims, slower but better quality)

#### Metadata Schema (NON-NEGOTIABLE)

```python
speech_metadata = {
    # Core identification
    "speech_id": str,           # UUID v4
    "title": str,               # Speech title
    "speaker": str,             # Speaker name
    "date": str,                # ISO 8601 (YYYY-MM-DD)

    # Context
    "event": Optional[str],     # "State of the Union", "Inaugural Address"
    "location": Optional[str],  # "Washington, DC"
    "audience": Optional[str],  # "Congress", "Public"
    "topic_tags": List[str],    # ["economy", "healthcare", "foreign_policy"]

    # Speech structure
    "chunk_index": int,         # Position in speech (0-based)
    "total_chunks": int,        # Total chunks for this speech
    "section": Optional[str],   # "introduction", "body", "conclusion"

    # Quality/metrics
    "word_count": int,
    "sentiment": Optional[float],     # -1.0 to 1.0 (optional analysis)
    "key_phrases": Optional[List[str]],  # Extracted topics

    # Source
    "source_url": Optional[str],
    "transcript_quality": str,  # "verbatim", "edited", "summary"
}
```

**Storage Distribution**:
- **Qdrant**: `chunk_text`, `embedding`, `speech_id`, `speaker`, `date`, `topic_tags`, `chunk_index`
- **PostgreSQL**: Full speech text, all metadata, relational tables (speakers, events, topics)

### MCP Tools Specification

The following tools MUST be implemented as core functionality:

#### 1. Hybrid Search (Primary Tool)

```python
@mcp.tool(tags=["search", "rag", "stable"])
async def search_speeches(
    query: str,
    speaker: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    topics: Optional[List[str]] = None,
    top_k: int = 10,
    ctx: Context = None
) -> List[SpeechResult]:
    """
    Hybrid search combining semantic similarity with metadata filtering.

    Uses vector search (Qdrant HNSW) + metadata filters + Redis caching.
    """
```

#### 2. Get Speech by ID

```python
@mcp.tool(tags=["retrieve", "rag", "stable"], readOnlyHint=True)
async def get_speech(
    speech_id: str,
    include_context: bool = False,
    ctx: Context = None
) -> SpeechDetail:
    """
    Retrieve complete speech by ID with optional surrounding context.
    """
```

#### 3. Metadata Filtering

```python
@mcp.tool(tags=["filter", "metadata", "stable"], readOnlyHint=True)
async def filter_speeches(
    speaker: Optional[str] = None,
    event: Optional[str] = None,
    date_range: Optional[Tuple[str, str]] = None,
    topics: Optional[List[str]] = None,
    limit: int = 50
) -> List[SpeechMetadata]:
    """
    Filter speeches by metadata without semantic search.
    """
```

#### 4. List Speakers

```python
@mcp.tool(tags=["metadata", "stable"], readOnlyHint=True)
async def list_speakers(
    limit: int = 100
) -> List[Speaker]:
    """
    List all speakers with speech counts.
    """
```

#### 5. Semantic Search (Advanced)

```python
@mcp.tool(tags=["search", "advanced", "beta"])
async def semantic_search(
    text: str,
    similarity_threshold: float = 0.7,
    top_k: int = 20,
    rerank: bool = False
) -> List[SpeechResult]:
    """
    Pure semantic vector search without metadata filtering.
    Optional cross-encoder reranking for higher quality.
    """
```

### Data Flow Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ INGESTION PIPELINE (One-time or scheduled)                   │
└──────────────────────────────────────────────────────────────┘
Speech Text (raw)
   │
   ├─> RecursiveCharacterTextSplitter (800 chars, 150 overlap)
   │   └─> Chunks with position metadata
   │
   ├─> sentence-transformers/all-MiniLM-L6-v2
   │   └─> Embeddings (384 dimensions)
   │
   ├─> Metadata Extraction & Validation (Pydantic)
   │   └─> {speaker, date, topic_tags, event, etc.}
   │
   └─> Parallel Storage:
       ├─> Qdrant.upsert({embedding, chunk_text, metadata})
       └─> PostgreSQL.insert({full_text, metadata, relations})

┌──────────────────────────────────────────────────────────────┐
│ SEARCH REQUEST FLOW (Real-time)                              │
└──────────────────────────────────────────────────────────────┘
MCP Client (Claude/Cursor/ChatGPT)
   │
   └─> FastMCP Server (Cloud Run)
       │
       ├─> Redis Cache Check
       │   ├─> HIT: Return cached results (<10ms)
       │   └─> MISS: Continue to vector search
       │
       ├─> Generate Query Embedding
       │   └─> sentence-transformers (in-memory, ~50ms)
       │
       ├─> Qdrant Hybrid Search
       │   ├─> Vector similarity (HNSW index, <50ms)
       │   ├─> Metadata filtering (speaker, date, topics)
       │   └─> Top-K results with scores
       │
       ├─> PostgreSQL Enrichment (optional)
       │   └─> Full speech text, additional context
       │
       ├─> Cache Results in Redis (TTL: 300s)
       │
       └─> Return MCP Response
           └─> Structured results with citations
```

### Capacity Planning

| Scale | Speeches | Chunks | Vectors | Qdrant Tier | PostgreSQL | Monthly Cost |
|-------|----------|--------|---------|-------------|------------|--------------|
| **Prototype** | 1,000 | 15,000 | 15,000 | Free (1GB) | 10GB | ~$47/month |
| **Production v1** | 10,000 | 150,000 | 150,000 | Paid (5GB) | 20GB | ~$72/month |
| **Scale** | 100,000 | 1.5M | 1.5M | Paid (20GB) | 50GB | ~$180/month |

**Current Target**: Production v1 (10,000 speeches)

### Performance Requirements

- **Search Latency**: <100ms p95 (uncached), <20ms p95 (cached)
- **Embedding Generation**: <100ms per chunk
- **Availability**: 99.5% (Cloud Run SLA)
- **Concurrent Users**: 10-50 (auto-scaling)
- **Cache Hit Rate**: >60% for common queries

### Testing Requirements (Speech RAG Specific)

In addition to standard FastMCP testing, the following MUST be tested:

1. **Search Quality Tests**:
   - Semantic similarity accuracy (manual golden dataset)
   - Metadata filtering correctness
   - Ranking quality (top results relevance)
   - Edge cases (empty queries, malformed filters)

2. **Performance Tests**:
   - Search latency (p50, p95, p99)
   - Embedding generation speed
   - Cache hit rates
   - Concurrent request handling

3. **Data Pipeline Tests**:
   - Chunking boundary preservation
   - Embedding consistency
   - Metadata extraction accuracy
   - Duplicate detection

4. **Integration Tests**:
   - End-to-end ingestion → search
   - Multi-filter combinations
   - MCP client compatibility (Claude, Cursor)
   - OAuth flow with GitHub

## Governance

This constitution supersedes all other development practices and documentation.

### Amendment Process

1. Propose amendment with rationale and impact analysis
2. Review with team/stakeholders
3. Update constitution with semantic version bump:
   - **MAJOR**: Breaking changes to principles or governance
   - **MINOR**: New principles or material expansions
   - **PATCH**: Clarifications, typos, non-semantic fixes
4. Update all dependent templates and documentation
5. Communicate changes to all developers

### Compliance Verification

- All PRs MUST verify constitution compliance
- Code reviews MUST check for principle violations
- Quarterly constitution review for relevance
- Automated checks for secret detection and test coverage

### Version Control

Constitution changes MUST be tracked in git with clear commit messages:
- Format: `docs: amend constitution to vX.Y.Z (summary of changes)`
- Include sync impact report in PR description
- Tag constitutional releases

**Version**: 2.5.0 | **Ratified**: 2025-10-21 | **Last Amended**: 2025-10-21
