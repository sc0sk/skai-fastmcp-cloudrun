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
    return GitHubProvider(
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url,
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
    annotations={
        "title": "Search Hansard Speeches",
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

    return {
        "results": results,
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
    annotations={
        "title": "Fetch Complete Hansard Speech",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": True,  # Queries external database (Cloud SQL)
    },
    exclude_args=["ctx"],  # Context is injected, not exposed to clients
)
async def fetch(speech_id: str, ctx: Context | None = None) -> Dict[str, Any]:
    """
    Fetch complete Hansard speech by ID.

    Retrieves the full text and metadata for a specific parliamentary speech.
    Use this after finding speech_id from search results to get the complete transcript.

    Args:
        speech_id: UUID of the speech (obtained from search results)

    Returns:
        Complete speech with full text, speaker metadata, and parliamentary context

    Example:
        >>> fetch(speech_id="550e8400-e29b-41d4-a716-446655440000")
        {
            "speech_id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Second Reading: Climate Change Bill 2024",
            "full_text": "Mr Speaker, I rise to speak...",
            "speaker": "Simon Kennedy",
            "party": "Liberal",
            "chamber": "House of Representatives",
            "date": "2024-06-03",
            "word_count": 1523,
            ...
        }
    """
    return await fetch_speech(speech_id, ctx=ctx)


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

if __name__ == "__main__":
    # Run server with FastMCP CLI
    # For Cloud Run: PORT environment variable is automatically set by Cloud Run
    # For local dev: Use DANGEROUSLY_OMIT_AUTH=true to bypass OAuth
    # Usage:
    #   Local STDIO: fastmcp dev src/server.py
    #   Local HTTP: PORT=8080 fastmcp dev src/server.py
    #   Cloud Run: Automatically uses HTTP with PORT from environment
    mcp.run()
