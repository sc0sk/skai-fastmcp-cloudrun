"""
Example FastMCP server with token verification.

This example demonstrates how to use token verification with FastMCP.
For Claude Code CLI testing, this uses static tokens for simplicity.

To test with Claude Code CLI:
1. Start this server: python3 example_auth_server.py
2. Add to Claude Code CLI with bearer token authentication
"""

import logging
from fastmcp import FastMCP
from src.auth import StaticTokenVerifier
from src.models.auth import StaticTokenVerifierConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP("Hansard API with Token Auth")

# Configure static token verification for testing
# NOTE: In production, use JWTVerifier with real OAuth tokens
verifier_config = StaticTokenVerifierConfig(
    tokens={
        # Admin token with full access
        "admin-token-12345": {
            "client_id": "admin@example.com",
            "scopes": ["read:hansard", "write:hansard", "admin"]
        },
        # Read-only token
        "readonly-token-67890": {
            "subject": "readonly-user",
            "scopes": ["read:hansard"]
        },
        # Guest token with no scopes
        "guest-token-abcde": {
            "client_id": "guest",
            "scopes": []
        }
    },
    required_scopes=["read:hansard"]  # All requests require at least read access
)

verifier = StaticTokenVerifier(verifier_config)


# Middleware to verify bearer tokens
@mcp.middleware
async def auth_middleware(request, next):
    """Verify bearer token before processing request"""
    # Extract Authorization header
    auth_header = request.headers.get("authorization")

    if not auth_header:
        logger.warning("Missing Authorization header")
        return {
            "error": "invalid_request",
            "error_description": "Missing Authorization header"
        }, 401

    # Extract token
    token = verifier.extract_bearer_token(auth_header)
    if not token:
        logger.warning("Invalid Authorization header format")
        return {
            "error": "invalid_request",
            "error_description": "Invalid Authorization header format. Expected: Bearer <token>"
        }, 401

    # Verify token
    result = await verifier.verify(token)

    if not result.success:
        logger.warning(f"Token validation failed: {result.error_description}")
        return {
            "error": result.error,
            "error_description": result.error_description
        }, result.error_code or 401

    # Token valid - add claims to request context
    request.state.claims = result.claims
    logger.info(f"Authenticated request from: {result.claims.identity}")

    # Continue to handler
    return await next(request)


# Example tools that are now protected by token authentication
@mcp.tool()
def get_info() -> dict:
    """Get information about the authenticated user"""
    # Note: In actual FastMCP, request context would be available via dependency injection
    # This is a simplified example
    return {
        "message": "This tool is protected by token authentication",
        "info": "Use Authorization: Bearer <token> header to access this tool",
        "valid_tokens": {
            "admin": "admin-token-12345",
            "readonly": "readonly-token-67890",
            "guest": "guest-token-abcde (will fail - no scopes)"
        }
    }


@mcp.tool()
def search_hansard(query: str, limit: int = 10) -> dict:
    """
    Search Australian Hansard speeches (protected endpoint).

    Requires: read:hansard scope
    """
    return {
        "query": query,
        "limit": limit,
        "results": [
            {"speaker": "Example Speaker", "text": "Example speech text"}
        ],
        "total": 1,
        "note": "This is a protected endpoint - token with 'read:hansard' scope required"
    }


if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*70)
    print("FastMCP Server with Token Verification")
    print("="*70)
    print("\nValid Test Tokens:")
    print("  - admin-token-12345     (admin@example.com, scopes: read:hansard, write:hansard, admin)")
    print("  - readonly-token-67890  (readonly-user, scopes: read:hansard)")
    print("  - guest-token-abcde     (guest, scopes: none - will be rejected)")
    print("\nUsage:")
    print("  curl -H 'Authorization: Bearer admin-token-12345' http://localhost:8000/mcp/")
    print("\nFor Claude Code CLI:")
    print("  1. Start server: python3 example_auth_server.py")
    print("  2. Configure Claude Code CLI with bearer token authentication")
    print("="*70 + "\n")

    # Start server
    uvicorn.run(
        mcp,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
