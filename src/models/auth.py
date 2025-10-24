"""
Authentication and token verification models.

This module provides Pydantic models for token verification, including:
- TokenClaims: Validated claims extracted from tokens
- ValidationResult: Token validation outcomes
- Configuration models for different verifier types
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator


# Algorithm safety constants
SAFE_ASYMMETRIC_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
SAFE_SYMMETRIC_ALGORITHMS = ["HS256", "HS384", "HS512"]


class TokenClaims(BaseModel):
    """
    Validated token claims extracted from JWT or introspection response.

    Provides unified interface for authorization decisions regardless of token type.
    """

    # Identity
    subject: str | None = Field(None, description="Subject identifier (sub claim)")
    client_id: str | None = Field(
        None, description="Client identifier (client_id claim or azp)"
    )
    username: str | None = Field(None, description="Username (username claim, if present)")

    # Token metadata
    issuer: str | None = Field(None, description="Token issuer (iss claim)")
    audience: str | list[str] | None = Field(
        None, description="Intended audience (aud claim)"
    )
    issued_at: datetime | None = Field(
        None, description="Token issue timestamp (iat claim)"
    )
    expires_at: datetime | None = Field(
        None, description="Token expiration timestamp (exp claim)"
    )
    not_before: datetime | None = Field(
        None, description="Token not valid before timestamp (nbf claim)"
    )

    # Permissions
    scopes: list[str] = Field(
        default_factory=list, description="Token scopes/permissions"
    )

    # Additional claims
    extra_claims: dict[str, Any] = Field(
        default_factory=dict, description="Additional custom claims"
    )

    @property
    def identity(self) -> str:
        """Primary identity identifier (subject or client_id)"""
        return self.subject or self.client_id or "unknown"

    def has_scope(self, required_scope: str) -> bool:
        """Check if token has specific scope"""
        return required_scope in self.scopes

    def has_any_scope(self, required_scopes: list[str]) -> bool:
        """Check if token has at least one of the required scopes"""
        return any(scope in self.scopes for scope in required_scopes)

    def has_all_scopes(self, required_scopes: list[str]) -> bool:
        """Check if token has all required scopes"""
        return all(scope in self.scopes for scope in required_scopes)

    def is_expired(self, clock_skew: int = 0) -> bool:
        """Check if token is expired (with optional clock skew tolerance)"""
        if not self.expires_at:
            return False  # No expiration claim = doesn't expire
        now = datetime.now(timezone.utc)
        exp_time = self.expires_at.replace(tzinfo=timezone.utc) if self.expires_at.tzinfo is None else self.expires_at
        return now > exp_time + timedelta(seconds=clock_skew)

    def is_not_yet_valid(self, clock_skew: int = 0) -> bool:
        """Check if token is not yet valid (with optional clock skew tolerance)"""
        if not self.not_before:
            return False  # No nbf claim = always valid from time perspective
        now = datetime.now(timezone.utc)
        nbf_time = self.not_before.replace(tzinfo=timezone.utc) if self.not_before.tzinfo is None else self.not_before
        return now < nbf_time - timedelta(seconds=clock_skew)


class ValidationResult(BaseModel):
    """
    Result of token validation operation.

    Encapsulates success/failure state and provides detailed error context.
    """

    success: bool = Field(description="Whether validation succeeded")
    claims: TokenClaims | None = Field(
        None, description="Extracted token claims (if successful)"
    )
    error: str | None = Field(None, description="Error category (if failed)")
    error_description: str | None = Field(
        None, description="Detailed error message (if failed)"
    )
    error_code: int | None = Field(
        None,
        description="HTTP status code (401 for validation errors, 500 for system errors)",
    )

    @classmethod
    def success_result(cls, claims: TokenClaims) -> "ValidationResult":
        """Create successful validation result"""
        return cls(success=True, claims=claims)

    @classmethod
    def failure_result(
        cls, error: str, error_description: str, error_code: int = 401
    ) -> "ValidationResult":
        """Create failed validation result"""
        return cls(
            success=False,
            error=error,
            error_description=error_description,
            error_code=error_code,
        )


class JWTVerifierConfig(BaseModel):
    """
    Configuration for JWT token verification.

    Supports JWKS endpoints, static public keys, and HMAC symmetric keys.
    """

    # Key configuration (mutually exclusive: either jwks_uri OR public_key)
    jwks_uri: str | None = Field(None, description="JWKS endpoint URL")
    public_key: SecretStr | None = Field(
        None, description="Static public key (PEM) or HMAC secret (masked in logs)"
    )

    # Validation parameters
    issuer: str = Field(description="Expected token issuer (iss claim)")
    audience: str | list[str] = Field(description="Expected audience (aud claim)")
    algorithm: str = Field(
        "RS256", description="JWT signing algorithm (RS256, ES256, HS256, etc.)"
    )

    # Optional settings
    required_scopes: list[str] = Field(
        default_factory=list, description="Required scopes for access"
    )
    clock_skew: int = Field(
        60, description="Clock skew tolerance in seconds", ge=0, le=120
    )
    jwks_cache_ttl: int = Field(
        3600, description="JWKS cache TTL in seconds", ge=60, le=86400
    )

    @model_validator(mode="after")
    def validate_key_config(self) -> "JWTVerifierConfig":
        """Ensure exactly one key configuration method is specified"""
        if not self.jwks_uri and not self.public_key:
            raise ValueError("Either jwks_uri or public_key must be specified")
        if self.jwks_uri and self.public_key:
            raise ValueError("Cannot specify both jwks_uri and public_key")
        return self

    @model_validator(mode="after")
    def validate_hmac_key_length(self) -> "JWTVerifierConfig":
        """Validate HMAC key meets minimum length requirements"""
        if self.algorithm.startswith("HS") and self.public_key:
            min_lengths = {"HS256": 32, "HS384": 48, "HS512": 64}
            min_length = min_lengths.get(self.algorithm, 32)
            key_bytes = self.public_key.get_secret_value().encode()
            if len(key_bytes) < min_length:
                raise ValueError(
                    f"HMAC key for {self.algorithm} must be at least {min_length} bytes. "
                    f"Current key length: {len(key_bytes)} bytes"
                )
        return self

    @model_validator(mode="after")
    def validate_algorithm_safety(self) -> "JWTVerifierConfig":
        """Prevent algorithm confusion attacks by enforcing algorithm whitelist"""
        # JWKS endpoints MUST use asymmetric algorithms only
        if self.jwks_uri and self.algorithm not in SAFE_ASYMMETRIC_ALGORITHMS:
            raise ValueError(
                f"JWKS endpoints require asymmetric algorithms. "
                f"Got {self.algorithm}, expected one of {SAFE_ASYMMETRIC_ALGORITHMS}. "
                f"HMAC algorithms (HS256/HS384/HS512) are not allowed with JWKS to prevent "
                f"algorithm confusion attacks."
            )
        return self

    @model_validator(mode="after")
    def validate_hmac_key_strength(self) -> "JWTVerifierConfig":
        """Validate HMAC key strength to prevent weak keys"""
        if self.algorithm.startswith("HS") and self.public_key:
            key = self.public_key.get_secret_value()

            # Check for repeated characters (like "aaaa..." or "11111...")
            if len(set(key)) < max(len(key) / 4, 8):  # At least 25% unique chars or 8 unique
                raise ValueError(
                    f"HMAC key has weak pattern: too many repeated characters. "
                    f"Use a cryptographically random key."
                )

            # Check for repeated patterns (like "testtest..." or "password"*5)
            for pattern_len in range(2, min(len(key) // 3, 20)):
                pattern = key[:pattern_len]
                # Check if key starts with repeated pattern (at least 3 times)
                if len(key) >= pattern_len * 3:
                    repetitions = key.count(pattern)
                    if repetitions >= 3 and len(pattern * repetitions) >= len(key) * 0.5:
                        raise ValueError(
                            f"HMAC key has weak pattern: repeated sequence detected. "
                            f"Use a cryptographically random key."
                        )

        return self

    @model_validator(mode="after")
    def validate_https_jwks(self) -> "JWTVerifierConfig":
        """Enforce HTTPS for JWKS endpoints (except localhost in development)"""
        if self.jwks_uri:
            # Allow http://localhost or http://127.0.0.1 in development
            if self.jwks_uri.startswith("http://"):
                if not (
                    self.jwks_uri.startswith("http://localhost")
                    or self.jwks_uri.startswith("http://127.0.0.1")
                ):
                    # Check if we're in production
                    env = os.getenv("ENVIRONMENT", "development").lower()
                    is_cloud_run = os.getenv("K_SERVICE") is not None
                    is_k8s = os.getenv("KUBERNETES_SERVICE_HOST") is not None

                    if env == "production" or is_cloud_run or is_k8s:
                        raise ValueError(
                            f"JWKS URI must use HTTPS in production. Got: {self.jwks_uri}. "
                            f"HTTP is only allowed for localhost in development."
                        )
        return self

    @classmethod
    def from_env(cls) -> "JWTVerifierConfig":
        """Load configuration from environment variables"""
        jwks_uri = os.getenv("FASTMCP_SERVER_AUTH_JWT_JWKS_URI")
        public_key = os.getenv("FASTMCP_SERVER_AUTH_JWT_PUBLIC_KEY")
        issuer = os.getenv("FASTMCP_SERVER_AUTH_JWT_ISSUER")
        audience_str = os.getenv("FASTMCP_SERVER_AUTH_JWT_AUDIENCE")

        if not issuer:
            raise ValueError("FASTMCP_SERVER_AUTH_JWT_ISSUER is required")
        if not audience_str:
            raise ValueError("FASTMCP_SERVER_AUTH_JWT_AUDIENCE is required")

        # Parse audience (can be comma-separated list)
        audience: str | list[str] = audience_str
        if "," in audience_str:
            audience = [aud.strip() for aud in audience_str.split(",")]

        # Parse scopes (comma-separated)
        scopes_str = os.getenv("FASTMCP_SERVER_AUTH_JWT_REQUIRED_SCOPES", "")
        required_scopes = [s.strip() for s in scopes_str.split(",") if s.strip()]

        return cls(
            jwks_uri=jwks_uri,
            public_key=public_key,
            issuer=issuer,
            audience=audience,
            algorithm=os.getenv("FASTMCP_SERVER_AUTH_JWT_ALGORITHM", "RS256"),
            required_scopes=required_scopes,
            clock_skew=int(os.getenv("FASTMCP_SERVER_AUTH_JWT_CLOCK_SKEW", "60")),
            jwks_cache_ttl=int(os.getenv("FASTMCP_SERVER_AUTH_JWT_JWKS_CACHE_TTL", "3600")),
        )


class IntrospectionVerifierConfig(BaseModel):
    """
    Configuration for OAuth 2.0 Token Introspection (RFC 7662).

    Validates opaque tokens via authorization server introspection endpoint.
    """

    # Introspection endpoint
    introspection_url: str = Field(description="OAuth introspection endpoint URL")

    # Client credentials (for Basic Auth)
    client_id: str = Field(
        description="Client identifier for introspection authentication"
    )
    client_secret: SecretStr = Field(
        description="Client secret for introspection authentication (masked in logs)"
    )

    # Optional settings
    required_scopes: list[str] = Field(
        default_factory=list, description="Required scopes for access"
    )
    timeout: int = Field(
        10, description="HTTP request timeout in seconds", ge=1, le=60
    )

    @field_validator("introspection_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate introspection URL is well-formed HTTPS"""
        if v.startswith("http://"):
            # Allow localhost in development
            if not (
                v.startswith("http://localhost") or v.startswith("http://127.0.0.1")
            ):
                # Check if we're in production
                env = os.getenv("ENVIRONMENT", "development").lower()
                is_cloud_run = os.getenv("K_SERVICE") is not None
                is_k8s = os.getenv("KUBERNETES_SERVICE_HOST") is not None

                if env == "production" or is_cloud_run or is_k8s:
                    raise ValueError(
                        f"Introspection URL must use HTTPS in production. Got: {v}. "
                        f"HTTP is only allowed for localhost in development."
                    )
        return v

    @classmethod
    def from_env(cls) -> "IntrospectionVerifierConfig":
        """Load configuration from environment variables"""
        introspection_url = os.getenv("FASTMCP_SERVER_AUTH_INTROSPECTION_URL")
        client_id = os.getenv("FASTMCP_SERVER_AUTH_INTROSPECTION_CLIENT_ID")
        client_secret = os.getenv("FASTMCP_SERVER_AUTH_INTROSPECTION_CLIENT_SECRET")

        if not introspection_url:
            raise ValueError("FASTMCP_SERVER_AUTH_INTROSPECTION_URL is required")
        if not client_id:
            raise ValueError("FASTMCP_SERVER_AUTH_INTROSPECTION_CLIENT_ID is required")
        if not client_secret:
            raise ValueError("FASTMCP_SERVER_AUTH_INTROSPECTION_CLIENT_SECRET is required")

        # Parse scopes (comma-separated)
        scopes_str = os.getenv("FASTMCP_SERVER_AUTH_INTROSPECTION_REQUIRED_SCOPES", "")
        required_scopes = [s.strip() for s in scopes_str.split(",") if s.strip()]

        return cls(
            introspection_url=introspection_url,
            client_id=client_id,
            client_secret=client_secret,
            required_scopes=required_scopes,
            timeout=int(os.getenv("FASTMCP_SERVER_AUTH_INTROSPECTION_TIMEOUT", "10")),
        )


class StaticTokenVerifierConfig(BaseModel):
    """
    Configuration for static token verification (DEVELOPMENT ONLY).

    Maps token strings to predefined claims for local testing.
    """

    tokens: dict[str, dict[str, Any]] = Field(
        description="Mapping of token strings to claims dictionaries"
    )
    required_scopes: list[str] = Field(
        default_factory=list, description="Required scopes for access"
    )

    @model_validator(mode="after")
    def prevent_production_use(self) -> "StaticTokenVerifierConfig":
        """Prevent usage in production environments"""
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env in ("production", "prod"):
            raise ValueError(
                "StaticTokenVerifier is for DEVELOPMENT ONLY. "
                "Do not use in production environments."
            )
        return self

    @model_validator(mode="after")
    def validate_token_claims(self) -> "StaticTokenVerifierConfig":
        """Ensure all token claims have required fields"""
        for token, claims in self.tokens.items():
            if not claims.get("client_id") and not claims.get("subject"):
                raise ValueError(
                    f"Token '{token[:10]}...' must have either 'client_id' or 'subject' claim"
                )
        return self
