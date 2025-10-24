"""
FastMCP AuthProvider adapter for token verification.

This module provides an adapter that makes our TokenVerifier implementations
compatible with FastMCP's AuthProvider interface.
"""

import logging
from typing import Any

from fastmcp.server.auth import AuthProvider, AccessToken
from starlette.routing import Route

from src.auth.base import TokenVerifier

logger = logging.getLogger(__name__)


class TokenVerifierAuthProvider(AuthProvider):
    """
    FastMCP AuthProvider adapter for TokenVerifier implementations.

    Wraps any TokenVerifier (JWT, Introspection, Static) to work with FastMCP's
    authentication system.
    """

    def __init__(
        self,
        verifier: TokenVerifier,
        base_url: str | None = None,
        required_scopes: list[str] | None = None,
    ):
        """
        Initialize the auth provider adapter.

        Args:
            verifier: TokenVerifier instance (JWTVerifier, IntrospectionTokenVerifier, etc.)
            base_url: Base URL of the server (optional)
            required_scopes: Required scopes for all requests (optional)
        """
        super().__init__(base_url=base_url, required_scopes=required_scopes)
        self.verifier = verifier
        logger.info(f"Initialized FastMCP auth provider with {verifier.__class__.__name__}")

    async def verify_token(self, token: str) -> AccessToken | None:
        """
        Verify a bearer token and return access info if valid.

        Args:
            token: The token string to validate

        Returns:
            AccessToken object if valid, None if invalid or expired
        """
        # Verify token using our verifier
        result = await self.verifier.verify(token)

        if not result.success:
            logger.debug(f"Token verification failed: {result.error_description}")
            return None

        # Convert to FastMCP AccessToken
        # MCP SDK AccessToken requires: token, client_id, scopes
        access_token = AccessToken(
            token=token,
            client_id=result.claims.client_id or result.claims.subject or "unknown",
            scopes=result.claims.scopes,
            expires_at=int(result.claims.expires_at.timestamp()) if result.claims.expires_at else None,
        )

        logger.debug(f"Token verified successfully for client_id: {access_token.client_id}")
        return access_token

    def get_routes(
        self,
        mcp_path: str | None = None,
        mcp_endpoint: Any | None = None,
    ) -> list[Route]:
        """
        Get custom routes for this authentication provider.

        Token verifiers don't need custom routes - they just validate tokens.

        Returns:
            Empty list (no custom routes needed)
        """
        return []
