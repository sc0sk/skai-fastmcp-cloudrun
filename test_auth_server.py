#!/usr/bin/env python3
"""
Simple FastMCP server with token authentication for testing.

This demonstrates token verification integrated with FastMCP.
Uses static tokens for easy testing with Claude Code CLI.

Test tokens:
  - admin-token-12345: Full access (admin@example.com)
  - readonly-token-67890: Read-only access (readonly-user)
  - guest-token-abcde: No scopes (will be rejected)

Run with: PYTHONPATH=. fastmcp run test_auth_server.py --transport http --port 8000
"""

import logging
from fastmcp import FastMCP
from src.auth import StaticTokenVerifier, TokenVerifierAuthProvider
from src.models.auth import StaticTokenVerifierConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Configure static token verification
verifier = StaticTokenVerifier(
    StaticTokenVerifierConfig(
        tokens={
            "admin-token-12345": {
                "client_id": "admin@example.com",
                "scopes": ["read:data", "write:data", "admin"]
            },
            "readonly-token-67890": {
                "subject": "readonly-user",
                "scopes": ["read:data"]
            },
            "guest-token-abcde": {
                "client_id": "guest",
                "scopes": []
            }
        },
        required_scopes=["read:data"]  # Minimum required scope
    )
)

# Wrap verifier in FastMCP adapter
auth = TokenVerifierAuthProvider(verifier, required_scopes=["read:data"])

# Create FastMCP server with authentication
mcp = FastMCP("Token Auth Test Server", auth=auth)


@mcp.tool()
def echo(message: str) -> dict:
    """
    Echo back a message (requires authentication).

    This tool is protected by bearer token authentication.
    Use Authorization: Bearer <token> header to access it.
    """
    return {
        "echo": message,
        "status": "authenticated",
        "note": "You successfully authenticated with a bearer token!"
    }


@mcp.tool()
def get_user_info() -> dict:
    """Get information about valid test tokens"""
    return {
        "valid_tokens": {
            "admin": {
                "token": "admin-token-12345",
                "identity": "admin@example.com",
                "scopes": ["read:data", "write:data", "admin"]
            },
            "readonly": {
                "token": "readonly-token-67890",
                "identity": "readonly-user",
                "scopes": ["read:data"]
            },
            "guest": {
                "token": "guest-token-abcde",
                "identity": "guest",
                "scopes": [],
                "note": "Will be rejected - no read:data scope"
            }
        },
        "required_scopes": ["read:data"],
        "usage": "Add header: Authorization: Bearer <token>"
    }


# Print startup info
print("\n" + "="*70)
print("FastMCP Server with Bearer Token Authentication")
print("="*70)
print("\n📋 Valid Test Tokens:")
print("  ✅ admin-token-12345     → admin@example.com (full access)")
print("  ✅ readonly-token-67890  → readonly-user (read-only)")
print("  ❌ guest-token-abcde     → guest (no scopes - REJECTED)")
print("\n🔒 Required Scope: read:data")
print("\n📡 Run the server with:")
print("  PYTHONPATH=. fastmcp run test_auth_server.py --transport http --port 8000")
print("\n📡 Test with curl (tools/list):")
print("  curl -X POST http://localhost:8000/mcp/ \\")
print("       -H 'Content-Type: application/json' \\")
print("       -H 'Authorization: Bearer admin-token-12345' \\")
print("       -d '{\"jsonrpc\": \"2.0\", \"id\": 1, \"method\": \"tools/list\"}'")
print("\n🤖 For Claude Code CLI:")
print("  1. Start server: PYTHONPATH=. fastmcp run test_auth_server.py --transport http --port 8000")
print("  2. Add MCP server with HTTP transport")
print("  3. Configure bearer token: admin-token-12345")
print("="*70 + "\n")
