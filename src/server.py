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
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request

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

# Import tool functions (using src. prefix for correct imports)
from src.tools.search import search_hansard_speeches, SEARCH_TOOL_METADATA
from src.tools.fetch import fetch_hansard_speech, FETCH_TOOL_METADATA
from src.tools.ingest import ingest_hansard_speech, INGEST_TOOL_METADATA
# TODO: Re-enable when markdown ingestion tools are fixed
# from src.tools.ingest_markdown_file import ingest_markdown_file
# from src.tools.ingest_markdown_directory import ingest_markdown_directory

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
            import logging

            # Get logger for this module
            logger = logging.getLogger(__name__)

            # GitHubProvider automatically loads configuration from environment variables:
            # FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID
            # FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET
            # FASTMCP_SERVER_AUTH_GITHUB_BASE_URL
            #
            # FastMCP 2.13+ supports custom client_storage parameter for persistent OAuth storage.
            # We use Firestore to persist OAuth clients across Cloud Run deployments.

            # Use Firestore OAuth storage (serverless, persistent, no event loop issues)
            from src.auth.firestore_oauth_storage import FirestoreOAuthStorage

            oauth_storage = FirestoreOAuthStorage(
                project_id=os.getenv('GCP_PROJECT_ID'),
                collection_name='oauth_clients'
            )

            auth_provider = GitHubProvider(client_storage=oauth_storage)
            print("✅ GitHub OAuth authentication enabled (Firestore storage - persistent)")
            logger.info("GitHub OAuth authentication enabled", extra={"client_storage": "firestore"})
        except ImportError as e:
            print(f"⚠️  Warning: GitHub OAuth provider not available: {e}")
    else:
        print("ℹ️  No authentication configured (FASTMCP_SERVER_AUTH not set)")
else:
    print("⚠️  WARNING: Authentication DISABLED (DANGEROUSLY_OMIT_AUTH=true)")

# Create FastMCP server instance with authentication and lifespan
mcp = FastMCP("Hansard MCP Server", auth=auth_provider, lifespan=lifespan)

# GitHub access control middleware will be added after app is created

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

# TODO: Re-enable when markdown ingestion tools are fixed
# # Register markdown file ingestion tool (admin-only)
# mcp.tool(
#     name="ingest_markdown_file",
#     exclude_args=["ctx"],
#     annotations={
#         "destructiveHint": True,  # Write operation
#         "requiresAuth": True,  # Admin authentication required
#         "requiredRole": "admin"
#     }
# )(ingest_markdown_file)
# 
# # Register bulk markdown directory ingestion tool (admin-only)
# mcp.tool(
#     name="ingest_markdown_directory",
#     exclude_args=["ctx"],
#     annotations={
#         "destructiveHint": True,  # Write operation
#         "requiresAuth": True,  # Admin authentication required
#         "requiredRole": "admin"
#     }
# )(ingest_markdown_directory)

# Print startup message
print("✅ Hansard MCP Server initialized with ChatGPT Developer Mode enhancements")
print("   🔍 search_hansard_speeches [read-only]")
print("   📄 fetch_hansard_speech [read-only]")
print("   📝 ingest_hansard_speech [write operation with progress reporting]")
# print("   📂 ingest_markdown_file [admin-only markdown ingestion]")
# print("   📁 ingest_markdown_directory [admin-only bulk directory ingestion]")

# Expose ASGI app for uvicorn (Cloud Run deployment)
app = mcp.http_app()

# Add CORS middleware to allow OAuth flows from browser-based clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for OAuth (including localhost)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add GitHub access control middleware (restrict to allowed usernames/emails)
if auth_provider and not os.getenv("DANGEROUSLY_OMIT_AUTH", "false").lower() == "true":
    from src.auth.github_middleware import GitHubAccessControlMiddleware
    app.add_middleware(GitHubAccessControlMiddleware)
    print("✅ GitHub access control middleware enabled")
else:
    print("⚠️  GitHub access control middleware not enabled (no auth provider or DANGEROUSLY_OMIT_AUTH=true)")

# NOTE: All OAuth endpoints (/.well-known/oauth-authorization-server, /oauth/*, /register)
# are automatically provided by FastMCP's GitHubProvider
# We manually add /.well-known/oauth-protected-resource (RFC 9728) for MCP spec compliance

@app.route("/.well-known/oauth-protected-resource", methods=["GET"])  # type: ignore[misc]
async def oauth_protected_resource(request: Request):
    """
    OAuth 2.0 Protected Resource Metadata (RFC 9728).
    Required by MCP specification 2025-06-18.
    """
    # Get base URL from environment or headers
    base_url = os.getenv('FASTMCP_SERVER_AUTH_GITHUB_BASE_URL', 'https://hansard-mcp-server-666924716777.us-central1.run.app')

    # Detect protocol from proxy headers (Cloud Run uses SSL termination)
    proto = request.headers.get('X-Forwarded-Proto', 'https')
    host = request.headers.get('Host', base_url.replace('https://', '').replace('http://', ''))
    resource_url = f"{proto}://{host}"

    metadata = {
        "resource": resource_url,
        "authorization_servers": [resource_url],
        "scopes_supported": ["user"],
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{resource_url}/docs",
    }

    return JSONResponse(metadata)

# DEBUG endpoint: IAM user detection (temporary, remove after debugging)
@app.route("/debug/iam-user", methods=["GET"])  # type: ignore[misc]
async def debug_iam_user(request: Request):
    """Debug endpoint to show IAM user detection in Cloud Run."""
    import google.auth
    
    info = {
        "env": {
            "USE_IAM_AUTH": os.getenv("USE_IAM_AUTH"),
            "CLOUDSQL_USER": os.getenv("CLOUDSQL_USER", "NOT SET"),
            "K_SERVICE": os.getenv("K_SERVICE", "NOT SET"),
        },
        "detection": {}
    }
    
    # Try google.auth.default()
    try:
        credentials, project = google.auth.default()
        info["detection"]["credentials_type"] = type(credentials).__name__
        info["detection"]["project"] = project
        
        if hasattr(credentials, 'service_account_email'):
            info["detection"]["service_account_email"] = credentials.service_account_email
        elif hasattr(credentials, '_service_account_email'):
            info["detection"]["service_account_email"] = credentials._service_account_email
        else:
            info["detection"]["service_account_email"] = "NOT FOUND"
            info["detection"]["available_attrs"] = [a for a in dir(credentials) if not a.startswith('_')][:20]
    except Exception as e:
        info["detection"]["google_auth_error"] = str(e)
    
    # Try metadata server
    if os.getenv('K_SERVICE'):
        try:
            import requests
            metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email"
            headers = {"Metadata-Flavor": "Google"}
            response = requests.get(metadata_url, headers=headers, timeout=1)
            if response.status_code == 200:
                info["detection"]["metadata_server_email"] = response.text.strip()
            else:
                info["detection"]["metadata_server_error"] = f"HTTP {response.status_code}"
        except Exception as e:
            info["detection"]["metadata_server_error"] = str(e)
    
    return JSONResponse(info)

# The server is ready to be run with:
# DANGEROUSLY_OMIT_AUTH=true fastmcp dev src/server.py (local dev)
# PORT=8080 fastmcp run src/server.py (production with OAuth)
# uvicorn src.server:app --host 0.0.0.0 --port 8080 (Cloud Run with uvicorn)
