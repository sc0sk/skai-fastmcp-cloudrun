"""FastMCP server for Australian Hansard parliamentary speech search.

This server provides MCP tools optimized for ChatGPT Developer Mode with:
- Enhanced tool descriptions with "Use this when..." guidance
- Tool annotations (readOnlyHint) for better UX
- Parameter enums for Australian political parties and chambers
- ISO 8601 date format specifications
- Tool selection guidance to prefer MCP tools over built-in capabilities
- GitHub OAuth authentication (environment-based configuration)
"""

import os
from fastmcp import FastMCP

# Import tool functions (relative imports for FastMCP)
from tools.search import search_hansard_speeches, SEARCH_TOOL_METADATA
from tools.fetch import fetch_hansard_speech, FETCH_TOOL_METADATA
# Note: ingest tool imported but not registered for MCP (CLI/script access only)
# from tools.ingest import ingest_hansard_speech, INGEST_TOOL_METADATA

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

# Create FastMCP server instance with authentication
mcp = FastMCP("Hansard MCP Server", auth=auth_provider)

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

# Note: ingest_hansard_speech tool is NOT registered for MCP access
# Write operations are restricted to CLI/script access only for security
# To ingest speeches, use: python scripts/ingest_speeches.py

# Print startup message
print("✅ Hansard MCP Server initialized with ChatGPT Developer Mode enhancements")
print("   🔍 search_hansard_speeches [read-only]")
print("   📄 fetch_hansard_speech [read-only]")
print("   ⚠️  ingest_hansard_speech [disabled - CLI/script only]")

# Expose ASGI app for uvicorn (Cloud Run deployment)
# FastMCP's http_app() method returns the Starlette ASGI application
app = mcp.http_app()

# The server is ready to be run with:
# DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py (local dev)
# PORT=8080 fastmcp run src/server.py (production with OAuth)
# uvicorn src.server:app --host 0.0.0.0 --port 8080 (Cloud Run with uvicorn)
