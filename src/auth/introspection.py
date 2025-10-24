"""
OAuth 2.0 Token Introspection (RFC 7662) implementation.

This module provides opaque token validation via introspection endpoints.
"""

import logging
from datetime import datetime
from typing import Any

import httpx

from src.auth.base import TokenVerifier, hash_token
from src.models.auth import IntrospectionVerifierConfig, TokenClaims, ValidationResult

logger = logging.getLogger(__name__)


class IntrospectionTokenVerifier(TokenVerifier):
    """
    Opaque token verifier using OAuth 2.0 Token Introspection (RFC 7662).

    Validates tokens by querying an authorization server's introspection endpoint.
    """

    def __init__(self, config: IntrospectionVerifierConfig):
        """
        Initialize introspection token verifier.

        Args:
            config: Introspection verification configuration
        """
        self.config = config
        logger.info(
            f"Initialized introspection verifier with endpoint: {config.introspection_url}"
        )

    async def verify(self, token: str) -> ValidationResult:
        """
        Verify opaque token via introspection endpoint.

        Args:
            token: Opaque token string

        Returns:
            ValidationResult with success/failure status and claims
        """
        token_hash = hash_token(token)
        try:
            # Make introspection request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.introspection_url,
                    data={"token": token},
                    auth=(self.config.client_id, self.config.client_secret.get_secret_value()),
                    timeout=self.config.timeout,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                introspection_data = response.json()

            logger.debug(f"[{token_hash}] Introspection response received")

            # Check if token is active
            if not introspection_data.get("active", False):
                logger.warning(f"[{token_hash}] Token is inactive (revoked or expired)")
                return ValidationResult.failure_result(
                    error="invalid_token",
                    error_description="Invalid token",
                )

            # Extract claims from introspection response
            claims = self._extract_claims(introspection_data)

            # Verify required scopes
            if self.config.required_scopes and not self.verify_scopes(
                claims, self.config.required_scopes
            ):
                logger.warning(
                    f"[{token_hash}] Token missing required scopes. Has: {claims.scopes}, Required: {self.config.required_scopes}"
                )
                return ValidationResult.failure_result(
                    error="insufficient_scope",
                    error_description="Insufficient scope",
                    error_code=403,
                )

            logger.info(
                f"[{token_hash}] Successfully validated opaque token for identity: {claims.identity}"
            )
            return ValidationResult.success_result(claims)

        except httpx.TimeoutException:
            logger.error(
                f"[{token_hash}] Introspection endpoint timeout after {self.config.timeout}s"
            )
            return ValidationResult.failure_result(
                error="server_error",
                error_description="Internal server error",
                error_code=500,
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"[{token_hash}] Introspection endpoint HTTP error: {e.response.status_code}")
            return ValidationResult.failure_result(
                error="server_error",
                error_description="Internal server error",
                error_code=500,
            )
        except httpx.RequestError as e:
            logger.error(f"[{token_hash}] Introspection endpoint request error: {e}")
            return ValidationResult.failure_result(
                error="server_error",
                error_description="Internal server error",
                error_code=500,
            )
        except Exception as e:
            logger.error(
                f"[{token_hash}] Unexpected error during introspection: {e}", exc_info=True
            )
            return ValidationResult.failure_result(
                error="server_error",
                error_description="Internal server error during token introspection",
                error_code=500,
            )

    def _extract_claims(self, introspection_data: dict[str, Any]) -> TokenClaims:
        """
        Extract token claims from introspection response.

        Args:
            introspection_data: RFC 7662 introspection response

        Returns:
            TokenClaims object
        """
        # Extract scopes (can be space-separated string or list)
        scopes = []
        if "scope" in introspection_data:
            scope_value = introspection_data["scope"]
            if isinstance(scope_value, str):
                scopes = scope_value.split()
            elif isinstance(scope_value, list):
                scopes = scope_value

        # Extract timestamps
        issued_at = None
        if "iat" in introspection_data:
            issued_at = datetime.fromtimestamp(introspection_data["iat"])

        expires_at = None
        if "exp" in introspection_data:
            expires_at = datetime.fromtimestamp(introspection_data["exp"])

        not_before = None
        if "nbf" in introspection_data:
            not_before = datetime.fromtimestamp(introspection_data["nbf"])

        return TokenClaims(
            subject=introspection_data.get("sub"),
            client_id=introspection_data.get("client_id"),
            username=introspection_data.get("username"),
            issuer=introspection_data.get("iss"),
            audience=introspection_data.get("aud"),
            issued_at=issued_at,
            expires_at=expires_at,
            not_before=not_before,
            scopes=scopes,
            extra_claims={
                k: v
                for k, v in introspection_data.items()
                if k
                not in {
                    "active",
                    "sub",
                    "client_id",
                    "username",
                    "iss",
                    "aud",
                    "iat",
                    "exp",
                    "nbf",
                    "scope",
                }
            },
        )
