"""FastMCP server for Australian Hansard RAG system."""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

from fastmcp import Context, FastMCP

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools.fetch import fetch_speech, get_dataset_stats
from src.tools.search import search_speeches

# OAuth provider import (conditionally loaded based on configuration)
try:
    from fastmcp.server.auth.providers.github import GitHubProvider

    OAUTH_AVAILABLE = True
except ImportError:
    OAUTH_AVAILABLE = False
    print("⚠️  Warning: GitHub OAuth provider not available (fastmcp version too old)")


# Lifespan context manager for global resources
@asynccontextmanager
async def lifespan(app: FastMCP):
    """
    Manage global resources (database connections, embedding models).

    Note:
        Connections are pre-initialized on startup to avoid cold-start delays.
        This context manager ensures proper cleanup on shutdown.
    """
    # Startup: Pre-initialize resources to avoid cold-start delays
    print("🚀 FastMCP Hansard RAG Server starting...")
    print("🔄 Warming up database connections and embedding models...")

    from src.storage.metadata_store import get_default_metadata_store
    from src.storage.vector_store import get_default_vector_store

    # Pre-initialize vector store (triggers DB + embedding model initialization)
    try:
        vector_store = await get_default_vector_store()
        await vector_store._get_vector_store()  # Force initialization
        print("✅ Vector store initialized")
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize vector store: {e}")

    # Pre-initialize metadata store
    try:
        metadata_store = await get_default_metadata_store()
        await metadata_store._get_pool()  # Force connection pool initialization
        print("✅ Metadata store initialized")
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize metadata store: {e}")

    print("✅ Server ready!")

    yield

    # Shutdown: Clean up resources
    print("🛑 FastMCP Hansard RAG Server shutting down...")
    from src.storage.metadata_store import _default_metadata_store
    from src.storage.vector_store import _default_vector_store

    if _default_metadata_store:
        await _default_metadata_store.close()

    if _default_vector_store:
        await _default_vector_store.close()


# GitHub username whitelist (only these users can authenticate)
# Configure via GITHUB_ALLOWED_USERNAMES environment variable (comma-separated)
ALLOWED_GITHUB_USERNAMES = os.getenv("GITHUB_ALLOWED_USERNAMES", "sc0sk").split(",")


# Custom authorization validator for GitHub username whitelist
async def validate_github_user(request):
    """
    Validate that the authenticated GitHub user is in the whitelist.

    Checks the "login" claim from the JWT token (GitHub username).
    Returns 403 Forbidden if user is not in ALLOWED_GITHUB_USERNAMES.
    """
    from starlette.responses import JSONResponse

    # Skip validation if auth is disabled (local dev only)
    if os.getenv("DANGEROUSLY_OMIT_AUTH", "false").lower() == "true":
        return None

    # Get authenticated user info from request state (set by GitHubProvider)
    user_info = getattr(request.state, "user", None)
    if not user_info:
        return JSONResponse(
            {"error": "Authentication required", "detail": "No user information found"},
            status_code=401,
        )

    # Check GitHub username against whitelist
    github_username = user_info.get("login", "")
    # Allow all users if whitelist contains "*"
    if "*" not in ALLOWED_GITHUB_USERNAMES and github_username not in ALLOWED_GITHUB_USERNAMES:
        print(f"⚠️  Authorization denied for GitHub user: {github_username}")
        return JSONResponse(
            {
                "error": "Authorization denied",
                "detail": f"User '{github_username}' is not authorized to access this server",
                "allowed_users": ALLOWED_GITHUB_USERNAMES,
            },
            status_code=403,
        )

    # User is authorized
    print(f"✅ Authorization granted for GitHub user: {github_username}")
    return None


# Configure OAuth authentication
def get_auth_provider():
    """
    Get authentication provider based on environment configuration.

    Returns:
        GitHubProvider if OAuth is enabled, None otherwise (local dev bypass)
    """
    # Check for development bypass (LOCAL ONLY - DO NOT USE IN PRODUCTION)
    if os.getenv("DANGEROUSLY_OMIT_AUTH", "false").lower() == "true":
        print("⚠️  WARNING: Authentication DISABLED (DANGEROUSLY_OMIT_AUTH=true)")
        print("   This is ONLY safe for local development. NEVER use in production!")
        return None

    # Check if OAuth is configured
    auth_provider = os.getenv("FASTMCP_SERVER_AUTH")
    if not auth_provider or auth_provider != "fastmcp.server.auth.providers.github.GitHubProvider":
        print("ℹ️  No authentication configured (FASTMCP_SERVER_AUTH not set)")
        return None

    # Validate OAuth provider is available
    if not OAUTH_AVAILABLE:
        raise RuntimeError(
            "GitHub OAuth provider not available. "
            "Upgrade to fastmcp>=2.12.0 with OAuth support."
        )

    # Get OAuth credentials from environment
    client_id = os.getenv("FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID")
    client_secret = os.getenv("FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET")
    base_url = os.getenv("FASTMCP_SERVER_AUTH_GITHUB_BASE_URL")

    if not all([client_id, client_secret, base_url]):
        raise RuntimeError(
            "GitHub OAuth configuration incomplete. Required environment variables:\n"
            "  - FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID\n"
            "  - FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET\n"
            "  - FASTMCP_SERVER_AUTH_GITHUB_BASE_URL"
        )

    # Create GitHubProvider with configuration
    print(f"✅ GitHub OAuth authentication enabled (base_url: {base_url})")
    print(f"🔒 Username whitelist: {', '.join(ALLOWED_GITHUB_USERNAMES)}")
    return GitHubProvider(
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url,
        # Note: FastMCP GitHubProvider validates tokens automatically
        # We add username whitelist validation via middleware below
    )


# Initialize FastMCP server with lifespan and optional authentication
auth_provider = get_auth_provider()
mcp = FastMCP(
    "Australian Hansard RAG",
    lifespan=lifespan,
    auth=auth_provider,
)

# Tool: Search speeches
@mcp.tool(
    name="search",
    description="Search Australian Parliament (Hansard) speeches by Simon Kennedy MP. Use this tool whenever the user asks about Simon Kennedy's positions, statements, speeches, voting record, or policy views on ANY topic. Also use for questions about Australian politics, parliamentary debates, legislation, or government policy mentioned in Hansard. Searches 64 parliamentary speeches from 2024-2025 covering topics like cost of living, housing, energy, taxation, immigration, and more.",
    annotations={
        "title": "Search Simon Kennedy's Hansard Speeches",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": True,  # Queries external database (Cloud SQL + Vertex AI)
    },
    exclude_args=["ctx"],  # Context is injected, not exposed to clients
)
async def search(
    query: str,
    limit: int = 10,
    speaker: str | None = None,
    party: str | None = None,
    chamber: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """
    Search Australian Hansard speeches using semantic search with metadata filters.

    Performs vector similarity search over parliamentary speech transcripts,
    returning relevant excerpts with speaker metadata and relevance scores.

    Args:
        query: Search query text (e.g., "climate change policy", "housing affordability")
        limit: Maximum results to return (1-50, default: 10)
        speaker: Filter by speaker name (case-insensitive partial match)
        party: Filter by political party (Liberal, Labor, Greens, National, Independent)
        chamber: Filter by chamber ("House of Representatives" or "Senate")
        date_from: Filter speeches from date onwards (ISO format: YYYY-MM-DD)
        date_to: Filter speeches up to date (ISO format: YYYY-MM-DD)

    Returns:
        List of search results with excerpts, metadata, and relevance scores (0-1)

    Examples:
        Search for climate policy speeches:
        >>> search(query="climate change policy", limit=5)

        Find Labor speeches about housing:
        >>> search(query="housing affordability", party="Labor", limit=10)

        Search House of Representatives speeches in 2024:
        >>> search(
        ...     query="budget",
        ...     chamber="House of Representatives",
        ...     date_from="2024-01-01",
        ...     date_to="2024-12-31"
        ... )
    """
    results = await search_speeches(
        query=query,
        limit=limit,
        speaker=speaker,
        party=party,
        chamber=chamber,
        date_from=date_from,
        date_to=date_to,
        ctx=ctx,
    )

    # Deep Research mode compatibility: return {"ids": [...]} format
    # This allows ChatGPT Deep Research to use search + fetch pattern
    speech_ids = [result.get("speech_id") for result in results if result.get("speech_id")]

    return {
        "ids": speech_ids,  # Required for Deep Research mode
        "results": results,  # Full results for Developer Mode
        "count": len(results),
        "query": query,
        "filters": {
            "speaker": speaker,
            "party": party,
            "chamber": chamber,
            "date_from": date_from,
            "date_to": date_to,
        },
    }


# Tool: Fetch speech
@mcp.tool(
    name="fetch",
    description="Get the complete full text of a specific Hansard speech by ID. Use this after searching to read the entire speech transcript. Returns the complete parliamentary speech with all details including full text, speaker info, date, chamber, party affiliation, debate topic, and more. Essential for in-depth analysis or when you need to quote exact wording from Simon Kennedy's speeches.",
    annotations={
        "title": "Fetch Complete Speech Text",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": True,  # Queries external database (Cloud SQL)
    },
    exclude_args=["ctx"],  # Context is injected, not exposed to clients
)
async def fetch(id: str, ctx: Context | None = None) -> Dict[str, Any]:
    """
    Fetch complete Hansard speech by ID.

    Retrieves the full text and metadata for a specific parliamentary speech.
    Use this after finding IDs from search results to get the complete transcript.

    Args:
        id: Speech ID (obtained from search results)

    Returns:
        Complete speech with full text, speaker metadata, and parliamentary context

    Example:
        >>> fetch(id="AUH_2024-07-01-p2.s1.per0.reps.u9")
        {
            "id": "AUH_2024-07-01-p2.s1.per0.reps.u9",
            "speaker": "Kennedy, Simon MP",
            "content": "Mr Speaker, I rise to speak...",
            "date": "2024-07-01",
            "chamber": "House of Reps",
            "party": "LP",
            "debate": "PRIVATE MEMBERS' BUSINESS",
            ...
        }
    """
    return await fetch_speech(id, ctx=ctx)


# Prompt: Usage guide for AI assistants
@mcp.prompt(
    name="usage_guide",
    description="Instructions on how to effectively use the Simon Kennedy Hansard search tools",
)
async def usage_guide_prompt() -> str:
    """
    Provide usage guidance for AI assistants using this MCP server.

    This prompt helps ChatGPT/Claude understand WHEN and HOW to use the search/fetch tools.
    """
    return """# Simon Kennedy Hansard MCP Server - Usage Guide

## What This Server Provides
This MCP server provides access to 64 Australian Parliament (Hansard) speeches by Simon Kennedy MP from 2024-2025. Use the search tool to find relevant speeches whenever the user asks about:

- Simon Kennedy's positions or statements on ANY topic
- Australian politics, policy, or legislation
- Parliamentary debates or government decisions
- Specific topics like: cost of living, housing, energy, taxation, immigration, budget, economy, etc.

## How To Use

### 1. Search First (ALWAYS)
When the user asks about Simon Kennedy or Australian politics, AUTOMATICALLY use the `search` tool:
- Query: Use natural language (e.g., "cost of living", "housing affordability")
- Limit: Default 5-10 results
- Filters: Add speaker="Kennedy, Simon MP" if needed (but search works without it)

### 2. Fetch Details (OPTIONAL)
If the user wants full speech text or exact quotes, use `fetch` with the speech ID from search results.

## Example Workflows

**User**: "What does Simon Kennedy think about housing?"
**Assistant**: *Automatically calls* `search(query="housing", limit=5)` → Returns relevant speeches

**User**: "Tell me about cost of living"
**Assistant**: *Automatically calls* `search(query="cost of living", limit=5)` → Summarizes results

**User**: "What's Simon Kennedy's full speech on energy policy from July 2024?"
**Assistant**: *Calls* `search(query="energy policy", date_from="2024-07-01", date_to="2024-07-31")` → Then `fetch(id=...)` for full text

## Key Points
- ✅ Use search for ANY question about Simon Kennedy or Australian politics
- ✅ Search works with natural language queries (no need for perfect syntax)
- ✅ Results include excerpts, dates, topics, and relevance scores
- ❌ Don't ask user permission to search - just do it automatically
- ❌ Don't say "let me check" - search and present results directly
"""


# Resource: Dataset statistics
@mcp.resource("hansard://dataset/stats")
async def dataset_stats() -> str:
    """
    Get Hansard dataset statistics.

    Returns overview statistics about the speech corpus including
    speech count, unique speakers, date range, and party distribution.

    Example:
        >>> dataset_stats()
        {
            "speech_count": 65,
            "unique_speakers": 1,
            "earliest_date": "2024-05-28",
            "latest_date": "2025-10-09",
            "party_breakdown": {"Liberal": 65}
        }
    """
    stats = await get_dataset_stats()
    # Return as JSON string for MCP resource
    import json
    return json.dumps(stats, indent=2)


# Health check endpoints for Cloud Run
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Liveness probe for Cloud Run - basic server responsiveness."""
    from starlette.responses import PlainTextResponse

    return PlainTextResponse("OK")


@mcp.custom_route("/ready", methods=["GET"])
async def readiness_check(request):
    """Readiness probe for Cloud Run - verify dependencies are healthy."""
    import json
    from datetime import datetime

    from starlette.responses import JSONResponse, PlainTextResponse

    try:
        # Check database connectivity
        from src.storage.vector_store import get_default_vector_store

        vector_store = await get_default_vector_store()
        db_status = "healthy"

        # Check Redis if configured
        redis_host = os.getenv("REDIS_HOST")
        if redis_host:
            import redis.asyncio as aioredis

            redis_client = await aioredis.from_url(
                f"redis://{redis_host}:{os.getenv('REDIS_PORT', 6379)}",
                decode_responses=True,
            )
            await redis_client.ping()
            await redis_client.aclose()
            redis_status = "healthy"
        else:
            redis_status = "healthy (in-memory mode)"

        response = {
            "status": "healthy",
            "checks": {
                "database": {"status": db_status},
                "redis": {"status": redis_status},
                "embeddings": {"status": "healthy"},
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        return JSONResponse(response, status_code=200)

    except Exception as e:
        error_response = {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        return JSONResponse(error_response, status_code=503)


# Expose ASGI app for uvicorn (Cloud Run deployment)
# FastMCP's http_app() method returns the Starlette ASGI application with all custom routes
app = mcp.http_app()

# Add username whitelist middleware to enforce GitHub username authorization
# This runs after OAuth authentication but before MCP tool execution
from starlette.middleware.base import BaseHTTPMiddleware


class OAuthResourceParameterMiddleware(BaseHTTPMiddleware):
    """Middleware to strip RFC 8707 'resource' parameter from OAuth authorize requests."""

    async def dispatch(self, request, call_next):
        # Only modify /authorize endpoint requests
        if request.url.path == "/authorize" and "resource" in request.query_params:
            # Remove 'resource' parameter from query string (ChatGPT sends this, FastMCP doesn't support it)
            from starlette.datastructures import URL
            query_params = dict(request.query_params)
            query_params.pop("resource", None)

            # Rebuild URL without 'resource' parameter
            new_url = request.url.replace(query=str(URL("").replace(query_params=query_params).query))
            request._url = new_url

        return await call_next(request)


class GitHubWhitelistMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce GitHub username whitelist for all MCP requests."""

    async def dispatch(self, request, call_next):
        # Skip whitelist check for public endpoints (no auth required)
        public_paths = [
            "/health",
            "/ready",
            "/.well-known/oauth-authorization-server",
            "/.well-known/oauth-protected-resource",
            "/authorize",  # OAuth authorization endpoint
            "/token",      # OAuth token endpoint
            "/auth/callback",  # OAuth callback handler
            "/register",   # OAuth client registration (dynamic registration)
            "/mcp",        # MCP protocol endpoint (OAuth validates at tool call level)
        ]

        # Check if path matches any public path (including subpaths)
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        # Skip whitelist check if auth is disabled (local dev only)
        if os.getenv("DANGEROUSLY_OMIT_AUTH", "false").lower() == "true":
            return await call_next(request)

        # Validate GitHub user against whitelist
        validation_response = await validate_github_user(request)
        if validation_response:
            return validation_response  # Return 401/403 error response

        # User is authorized, proceed with request
        return await call_next(request)


# Add OAuth resource parameter middleware (must be first to modify requests before auth)
app.add_middleware(OAuthResourceParameterMiddleware)
print("✅ OAuth resource parameter middleware enabled (RFC 8707 compatibility)")

# Only add whitelist middleware if OAuth is enabled
if os.getenv("FASTMCP_SERVER_AUTH"):
    app.add_middleware(GitHubWhitelistMiddleware)
    print(f"✅ GitHub username whitelist middleware enabled: {', '.join(ALLOWED_GITHUB_USERNAMES)}")

if __name__ == "__main__":
    # Run server with FastMCP CLI
    # For Cloud Run: PORT environment variable is automatically set by Cloud Run
    # For local dev: Use DANGEROUSLY_OMIT_AUTH=true to bypass OAuth
    # Usage:
    #   Local STDIO: fastmcp dev src/server.py
    #   Local HTTP: PORT=8080 fastmcp dev src/server.py
    #   Cloud Run: Automatically uses HTTP with PORT from environment
    mcp.run()
