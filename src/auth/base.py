"""
Base token verifier abstract class and exceptions.

This module provides the foundation for all token verification strategies.
"""

import hashlib
from abc import ABC, abstractmethod

from src.models.auth import TokenClaims, ValidationResult


def hash_token(token: str) -> str:
    """
    Hash token using SHA-256 for safe logging.

    Args:
        token: Bearer token string

    Returns:
        First 16 characters of SHA-256 hex digest
    """
    return hashlib.sha256(token.encode()).hexdigest()[:16]


class TokenValidationError(Exception):
    """Base class for token validation errors (401)"""

    pass


class SystemAuthError(Exception):
    """Base class for system auth errors (500)"""

    pass


class TokenVerifier(ABC):
    """
    Abstract base class for token verification.

    Implementations validate tokens using different strategies (JWT, introspection, static).
    """

    @abstractmethod
    async def verify(self, token: str) -> ValidationResult:
        """
        Verify token and extract claims.

        Args:
            token: Bearer token string (without "Bearer " prefix)

        Returns:
            ValidationResult with success/failure status and claims
        """
        pass

    def verify_scopes(self, claims: TokenClaims, required_scopes: list[str]) -> bool:
        """
        Verify token has required scopes.

        Args:
            claims: Extracted token claims
            required_scopes: List of required scopes

        Returns:
            True if all required scopes present, False otherwise
        """
        if not required_scopes:
            return True
        return claims.has_all_scopes(required_scopes)

    def extract_bearer_token(self, authorization_header: str | None) -> str | None:
        """
        Extract token from Authorization header.

        Args:
            authorization_header: Authorization header value (e.g., "Bearer abc123")

        Returns:
            Token string without "Bearer " prefix, or None if invalid
        """
        if not authorization_header:
            return None

        parts = authorization_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        return parts[1]
