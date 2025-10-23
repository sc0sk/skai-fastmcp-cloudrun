"""FastMCP server for Australian Hansard parliamentary speech search.

This server provides MCP tools optimized for ChatGPT Developer Mode with:
- Enhanced tool descriptions with "Use this when..." guidance
- Tool annotations (readOnlyHint) for better UX
- Parameter enums for Australian political parties and chambers
- ISO 8601 date format specifications
- Tool selection guidance to prefer MCP tools over built-in capabilities
- GitHub OAuth authentication (environment-based configuration)
- LangChain + Vertex AI + Cloud SQL PostgreSQL vector search
"""

import os
from contextlib import asynccontextmanager
from fastmcp import FastMCP

# Lifespan context manager for global resources (database connections, embedding models)
@asynccontextmanager
async def lifespan(app: FastMCP):
    """
    Manage global resources (database connections, embedding models).

    Pre-initializes connections on startup to avoid cold-start delays.
    Ensures proper cleanup on shutdown.
    """
    # Startup: Pre-initialize resources
    print("🚀 FastMCP Hansard RAG Server starting...")
    print("🔄 Warming up database connections and embedding models...")

    from storage.metadata_store import get_default_metadata_store
    from storage.vector_store import get_default_vector_store

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
    from storage.metadata_store import _default_metadata_store
    from storage.vector_store import _default_vector_store

    if _default_metadata_store:
        await _default_metadata_store.close()

    if _default_vector_store:
        await _default_vector_store.close()

# Import tool functions (relative imports for FastMCP)
from tools.search import search_hansard_speeches, SEARCH_TOOL_METADATA
from tools.fetch import fetch_hansard_speech, FETCH_TOOL_METADATA
from tools.ingest import ingest_hansard_speech, INGEST_TOOL_METADATA

# GitHub OAuth configuration
# See: https://docs.fastmcp.com/servers/auth/github
#
# Required environment variables:
# - FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID (from Secret Manager)
# - FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET (from Secret Manager)
# - FASTMCP_SERVER_AUTH_GITHUB_BASE_URL (e.g., https://mcp.simonkennedymp.com.au)
#
# For local development without OAuth:
# - DANGEROUSLY_OMIT_AUTH=true

# Configure authentication provider
auth_provider = None
if os.getenv("DANGEROUSLY_OMIT_AUTH", "false").lower() != "true":
    # Check if OAuth is configured via environment
    if os.getenv("FASTMCP_SERVER_AUTH") == "fastmcp.server.auth.providers.github.GitHubProvider":
        try:
            from fastmcp.server.auth.providers.github import GitHubProvider

            # GitHubProvider automatically loads configuration from environment variables:
            # FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID
            # FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET
            # FASTMCP_SERVER_AUTH_GITHUB_BASE_URL
            auth_provider = GitHubProvider()
            print("✅ GitHub OAuth authentication enabled")
        except ImportError:
            print("⚠️  Warning: GitHub OAuth provider not available (fastmcp version too old)")
    else:
        print("ℹ️  No authentication configured (FASTMCP_SERVER_AUTH not set)")
else:
    print("⚠️  WARNING: Authentication DISABLED (DANGEROUSLY_OMIT_AUTH=true)")

# Create FastMCP server instance with authentication and lifespan
mcp = FastMCP("Hansard MCP Server", auth=auth_provider, lifespan=lifespan)

# Register search tool with ChatGPT Developer Mode enhancements
# Note: icon parameter not supported in FastMCP 2.12.5, icons stored in metadata for future use
mcp.tool(
    name=SEARCH_TOOL_METADATA["name"],
    annotations=SEARCH_TOOL_METADATA["annotations"]
)(search_hansard_speeches)

# Register fetch tool with ChatGPT Developer Mode enhancements
mcp.tool(
    name=FETCH_TOOL_METADATA["name"],
    annotations=FETCH_TOOL_METADATA["annotations"]
)(fetch_hansard_speech)

# Register ingest tool with progress reporting
# Note: destructiveHint=True for write operations
mcp.tool(
    name=INGEST_TOOL_METADATA["name"],
    exclude_args=["ctx"],  # Exclude ctx from MCP schema
    annotations={
        "destructiveHint": True,  # Write operation
    }
)(ingest_hansard_speech)

# Print startup message
print("✅ Hansard MCP Server initialized with ChatGPT Developer Mode enhancements")
print("   🔍 search_hansard_speeches [read-only]")
print("   📄 fetch_hansard_speech [read-only]")
print("   📝 ingest_hansard_speech [write operation with progress reporting]")

# Expose ASGI app for uvicorn (Cloud Run deployment)
# FastMCP's http_app() method returns the Starlette ASGI application
app = mcp.http_app()

# The server is ready to be run with:
# DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py (local dev)
# PORT=8080 fastmcp run src/server.py (production with OAuth)
# uvicorn src.server:app --host 0.0.0.0 --port 8080 (Cloud Run with uvicorn)
