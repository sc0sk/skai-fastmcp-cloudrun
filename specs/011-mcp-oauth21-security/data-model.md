# Data Model: MCP OAuth 2.1 Compliance and Security Hardening

**Feature**: 011-mcp-oauth21-security
**Date**: 2025-10-24
**Purpose**: Pydantic models and data structures for OAuth 2.1 token verification

## Overview

This document defines all Pydantic models, data structures, and their relationships for the OAuth 2.1 Resource Server implementation. All models use Pydantic v2 with comprehensive validation.

## Model Hierarchy

```
TokenClaims                    # Validated token identity/permissions
    ↓ used by
ValidationResult               # Token verification outcome
    ↓ consumed by
TokenVerifier (ABC)            # Base verification interface
    ↓ implemented by
├── JWTVerifier               # JWT with JWKS/static keys/HMAC
├── IntrospectionTokenVerifier # RFC 7662 opaque tokens
└── StaticTokenVerifier        # Development/testing only

TokenVerifierAuthProvider      # FastMCP AuthProvider adapter
    ↓ uses
AccessToken                    # FastMCP authentication result

RateLimiter                    # Token bucket rate limiting
SecretManager                  # Google Cloud Secret Manager client
```

## Core Data Models

### 1. TokenClaims

**Purpose**: Unified representation of validated token identity and permissions

**Source**: Extracted from JWT payload or introspection response

**Lifecycle**: Created during token verification, passed to authorization logic

```python
from pydantic import BaseModel, Field
from datetime import datetime

class TokenClaims(BaseModel):
    """
    Validated token claims extracted from JWT or introspection response.

    Provides unified interface for authorization decisions regardless of token type.
    """

    # Identity
    subject: str | None = Field(None, description="Subject identifier (sub claim)")
    client_id: str | None = Field(None, description="Client identifier (client_id or azp)")
    username: str | None = Field(None, description="Username (username or preferred_username)")

    # Token metadata
    issuer: str | None = Field(None, description="Token issuer (iss claim)")
    audience: str | list[str] | None = Field(None, description="Intended audience (aud claim)")
    issued_at: datetime | None = Field(None, description="Token issue timestamp (iat)")
    expires_at: datetime | None = Field(None, description="Token expiration timestamp (exp)")
    not_before: datetime | None = Field(None, description="Not valid before timestamp (nbf)")

    # Permissions
    scopes: list[str] = Field(default_factory=list, description="Token scopes/permissions")

    # Additional claims
    extra_claims: dict[str, Any] = Field(default_factory=dict, description="Additional custom claims")

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

    def is_expired(self) -> bool:
        """Check if token is expired (considering current time)"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def is_not_yet_valid(self) -> bool:
        """Check if token is not yet valid (nbf claim)"""
        if not self.not_before:
            return False
        return datetime.utcnow() < self.not_before
```

**Validation Rules**:
- At least one of `subject` or `client_id` must be present (validated via `identity` property)
- `scopes` defaults to empty list if not provided
- Timestamps are optional (some token types don't include all claims)
- `audience` can be string or list per OAuth 2.0 spec

**Usage Example**:
```python
claims = TokenClaims(
    subject="user-123",
    client_id="app-xyz",
    issuer="https://auth.example.com",
    audience="my-api",
    scopes=["read:data", "write:data"],
    expires_at=datetime.utcnow() + timedelta(hours=1)
)

if claims.has_all_scopes(["read:data", "write:data"]):
    # Grant access
    pass
```

### 2. ValidationResult

**Purpose**: Encapsulates token verification outcome (success or failure)

**Source**: Returned by all `TokenVerifier.verify()` implementations

**Lifecycle**: Created during verification, consumed by FastMCP adapter

```python
class ValidationResult(BaseModel):
    """
    Result of token validation operation.

    Encapsulates success/failure state and provides detailed error context.
    """

    success: bool = Field(description="Whether validation succeeded")
    claims: TokenClaims | None = Field(None, description="Extracted token claims (if successful)")
    error: str | None = Field(None, description="Error category (if failed)")
    error_description: str | None = Field(None, description="Detailed error message (if failed)")
    error_code: int | None = Field(
        None,
        description="HTTP status code (401 for validation errors, 500 for system errors)"
    )

    @classmethod
    def success_result(cls, claims: TokenClaims) -> "ValidationResult":
        """Create successful validation result"""
        return cls(success=True, claims=claims)

    @classmethod
    def failure_result(
        cls,
        error: str,
        error_description: str,
        error_code: int = 401
    ) -> "ValidationResult":
        """Create failed validation result"""
        return cls(
            success=False,
            error=error,
            error_description=error_description,
            error_code=error_code
        )
```

**Error Codes** (OAuth 2.0 standard):
- `invalid_token`: Token is malformed, expired, or invalid signature
- `insufficient_scope`: Token lacks required scopes
- `server_error`: Internal error during validation (JWKS fetch failure, etc.)
- `rate_limit_exceeded`: Too many authentication attempts

**Usage Example**:
```python
# Success
result = ValidationResult.success_result(claims)

# Failure
result = ValidationResult.failure_result(
    error="invalid_token",
    error_description="Token has expired",
    error_code=401
)
```

### 3. JWTVerifierConfig

**Purpose**: Configuration for JWT token verification with JWKS, static keys, or HMAC

**Source**: Loaded from environment variables or Secret Manager

**Lifecycle**: Created at server startup, immutable during runtime

```python
from pydantic import SecretStr, field_validator, model_validator

class JWTVerifierConfig(BaseModel):
    """
    Configuration for JWT token verification.

    Supports JWKS endpoints, static public keys, and HMAC symmetric keys.
    """

    # Key configuration (mutually exclusive: either jwks_uri OR public_key)
    jwks_uri: str | None = Field(None, description="JWKS endpoint URL")
    public_key: SecretStr | None = Field(
        None,
        description="Static public key (PEM) or HMAC secret"
    )

    # Validation parameters
    issuer: str = Field(description="Expected token issuer (iss claim)")
    audience: str | list[str] = Field(description="Expected audience (aud claim)")
    algorithm: str = Field(
        "RS256",
        description="JWT signing algorithm (RS256, ES256, HS256, etc.)"
    )

    # Optional settings
    required_scopes: list[str] = Field(
        default_factory=list,
        description="Required scopes for access"
    )
    clock_skew: int = Field(
        60,
        description="Clock skew tolerance in seconds",
        ge=0,
        le=120  # Reduced from 300 to 120 per security audit
    )
    jwks_cache_ttl: int = Field(
        3600,
        description="JWKS cache TTL in seconds",
        ge=60,
        le=86400
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
    def validate_algorithm_safety(self) -> "JWTVerifierConfig":
        """Prevent algorithm confusion attacks"""
        SAFE_ASYMMETRIC = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
        SAFE_SYMMETRIC = ["HS256", "HS384", "HS512"]

        if self.jwks_uri:
            # JWKS must use asymmetric algorithms
            if self.algorithm not in SAFE_ASYMMETRIC:
                raise ValueError(
                    f"JWKS endpoints require asymmetric algorithms. "
                    f"Allowed: {SAFE_ASYMMETRIC}, got: {self.algorithm}"
                )
            # Never allow HMAC with JWKS (algorithm confusion vulnerability)
            if self.algorithm in SAFE_SYMMETRIC:
                raise ValueError(
                    "HMAC algorithms cannot be used with JWKS endpoints. "
                    "This prevents algorithm confusion attacks."
                )

        return self

    @model_validator(mode="after")
    def validate_hmac_key_strength(self) -> "JWTVerifierConfig":
        """Validate HMAC key meets minimum security requirements"""
        if not self.algorithm.startswith("HS") or not self.public_key:
            return self

        min_lengths = {"HS256": 32, "HS384": 48, "HS512": 64}
        min_length = min_lengths[self.algorithm]

        key_bytes = self.public_key.get_secret_value().encode()

        # Check minimum length
        if len(key_bytes) < min_length:
            raise ValueError(
                f"HMAC key for {self.algorithm} must be at least {min_length} bytes. "
                f"Current key length: {len(key_bytes)} bytes"
            )

        # Detect weak patterns
        weak_patterns = [
            b'a' * min_length,
            b'1' * min_length,
            b'test',
            b'secret',
            b'password'
        ]
        if any(pattern in key_bytes for pattern in weak_patterns):
            raise ValueError(
                "HMAC key appears to be a weak/test value. "
                "Use cryptographically random key."
            )

        # Check base64-decoded length if applicable
        try:
            import base64
            decoded = base64.b64decode(key_bytes)
            if len(decoded) < min_length:
                raise ValueError(
                    f"Base64-decoded HMAC key is only {len(decoded)} bytes. "
                    f"Use longer base64-encoded key or raw {min_length}+ byte secret."
                )
        except Exception:
            pass  # Not base64, continue

        return self

    @field_validator("jwks_uri")
    @classmethod
    def validate_https_jwks(cls, v: str | None) -> str | None:
        """Enforce HTTPS for JWKS URIs in production"""
        if v is None:
            return v

        if v.startswith("https://"):
            return v

        # Allow localhost for development
        if v.startswith(("http://localhost", "http://127.0.0.1")):
            import os
            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError(
                    "Cannot use HTTP localhost JWKS URI in production. "
                    "Use HTTPS endpoint from production identity provider."
                )
            import logging
            logging.getLogger(__name__).warning(
                f"Using HTTP JWKS URI in development: {v}"
            )
            return v

        raise ValueError(
            f"JWKS URI must use HTTPS (or http://localhost for dev). Got: {v}"
        )
```

**Configuration Example (Environment Variables)**:
```bash
FASTMCP_SERVER_AUTH_JWT_JWKS_URI=https://auth.example.com/.well-known/jwks.json
FASTMCP_SERVER_AUTH_JWT_ISSUER=https://auth.example.com
FASTMCP_SERVER_AUTH_JWT_AUDIENCE=my-mcp-server
FASTMCP_SERVER_AUTH_JWT_ALGORITHM=RS256
FASTMCP_SERVER_AUTH_JWT_REQUIRED_SCOPES=read:data,write:data
```

### 4. IntrospectionVerifierConfig

**Purpose**: Configuration for OAuth 2.0 Token Introspection (RFC 7662)

**Source**: Loaded from environment variables or Secret Manager

**Lifecycle**: Created at server startup, immutable during runtime

```python
class IntrospectionVerifierConfig(BaseModel):
    """
    Configuration for OAuth 2.0 Token Introspection (RFC 7662).

    Validates opaque tokens via authorization server introspection endpoint.
    """

    # Introspection endpoint
    introspection_url: str = Field(description="OAuth introspection endpoint URL")

    # Client credentials (for Basic Auth)
    client_id: str = Field(description="Client identifier for introspection authentication")
    client_secret: SecretStr = Field(description="Client secret for introspection authentication")

    # Optional settings
    required_scopes: list[str] = Field(
        default_factory=list,
        description="Required scopes for access"
    )
    timeout: int = Field(
        10,
        description="HTTP request timeout in seconds",
        ge=1,
        le=60
    )

    @field_validator("introspection_url")
    @classmethod
    def validate_https_introspection(cls, v: str) -> str:
        """Enforce HTTPS for introspection endpoints in production"""
        if v.startswith("https://"):
            return v

        # Allow localhost for development
        if v.startswith(("http://localhost", "http://127.0.0.1")):
            import os
            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError(
                    "Cannot use HTTP localhost introspection URL in production. "
                    "Use HTTPS endpoint from production identity provider."
                )
            import logging
            logging.getLogger(__name__).warning(
                f"Using HTTP introspection URL in development: {v}"
            )
            return v

        raise ValueError(
            f"Introspection URL must use HTTPS (or http://localhost for dev). Got: {v}"
        )
```

### 5. StaticTokenVerifierConfig

**Purpose**: Development/testing static token mappings

**Source**: Hardcoded in test configuration (never production)

**Lifecycle**: Created for local testing only, blocked in production

```python
class StaticTokenVerifierConfig(BaseModel):
    """
    Configuration for static token verification (DEVELOPMENT ONLY).

    Maps token strings to predefined claims for local testing.
    """

    tokens: dict[str, dict[str, Any]] = Field(
        description="Mapping of token strings to claims dictionaries"
    )
    required_scopes: list[str] = Field(
        default_factory=list,
        description="Required scopes for access"
    )

    @model_validator(mode="after")
    def prevent_production_use(self) -> "StaticTokenVerifierConfig":
        """Prevent usage in production environments"""
        import os
        env = os.getenv("ENVIRONMENT", "development").lower()

        # Multiple signals to detect production
        production_signals = [
            env in ("production", "prod"),
            os.getenv("K_SERVICE"),  # Cloud Run
            os.getenv("KUBERNETES_SERVICE_HOST"),  # Kubernetes
        ]

        if any(production_signals):
            raise ValueError(
                "StaticTokenVerifier detected in production environment. "
                "Use JWTVerifier or IntrospectionTokenVerifier instead."
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
```

## Rate Limiting Models

### 6. RateLimitConfig

**Purpose**: Configuration for token bucket rate limiter

**Source**: Environment variables or defaults

**Lifecycle**: Created at server startup

```python
class RateLimitConfig(BaseModel):
    """Configuration for token bucket rate limiting"""

    max_attempts: int = Field(
        10,
        description="Maximum authentication attempts per window",
        ge=1,
        le=1000
    )
    window_seconds: int = Field(
        60,
        description="Time window duration in seconds",
        ge=1,
        le=3600
    )
    enabled: bool = Field(
        True,
        description="Enable/disable rate limiting"
    )
```

### 7. RateLimitBucket

**Purpose**: Per-token-hash attempt tracking

**Source**: Created dynamically during authentication attempts

**Lifecycle**: Stored in-memory, automatically cleaned up after window expiration

```python
from datetime import datetime

class RateLimitBucket(BaseModel):
    """Per-token rate limiting state"""

    token_hash: str = Field(description="SHA-256 hash of token (first 16 chars)")
    attempts: list[datetime] = Field(
        default_factory=list,
        description="Timestamps of recent authentication attempts"
    )
    last_cleanup: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last time expired entries were removed"
    )

    def is_rate_limited(self, window_seconds: int, max_attempts: int) -> bool:
        """Check if token hash has exceeded rate limit"""
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        recent_attempts = [t for t in self.attempts if t > cutoff]
        return len(recent_attempts) >= max_attempts

    def record_attempt(self) -> None:
        """Record new authentication attempt"""
        self.attempts.append(datetime.utcnow())

    def cleanup_expired(self, window_seconds: int) -> None:
        """Remove attempts older than window duration"""
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        self.attempts = [t for t in self.attempts if t > cutoff]
        self.last_cleanup = datetime.utcnow()
```

## Secret Management Models

### 8. SecretConfig

**Purpose**: Configuration for secret retrieval strategy

**Source**: Environment variables

**Lifecycle**: Created at server startup

```python
from enum import Enum

class SecretBackend(str, Enum):
    """Secret storage backend"""
    ENV = "env"  # Environment variables
    GCP_SECRET_MANAGER = "gcp_secret_manager"  # Google Cloud Secret Manager

class SecretConfig(BaseModel):
    """Configuration for secret management"""

    backend: SecretBackend = Field(
        SecretBackend.ENV,
        description="Secret storage backend"
    )
    gcp_project_id: str | None = Field(
        None,
        description="Google Cloud project ID (required for Secret Manager)"
    )
    cache_ttl_seconds: int = Field(
        300,
        description="Secret cache TTL in seconds",
        ge=60,
        le=3600
    )

    @model_validator(mode="after")
    def validate_gcp_config(self) -> "SecretConfig":
        """Ensure GCP project ID provided when using Secret Manager"""
        if self.backend == SecretBackend.GCP_SECRET_MANAGER and not self.gcp_project_id:
            raise ValueError(
                "gcp_project_id required when using Secret Manager backend"
            )
        return self
```

### 9. CachedSecret

**Purpose**: In-memory cached secret value with expiration

**Source**: Retrieved from Secret Manager or environment variables

**Lifecycle**: Created on first access, refreshed after TTL expiration

```python
class CachedSecret(BaseModel):
    """Cached secret value with expiration tracking"""

    name: str = Field(description="Secret name/key")
    value: SecretStr = Field(description="Secret value (protected)")
    cached_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When secret was cached"
    )
    version: str | None = Field(
        None,
        description="Secret version (Secret Manager only)"
    )

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if cached secret has expired"""
        age = (datetime.utcnow() - self.cached_at).total_seconds()
        return age > ttl_seconds

    @property
    def age_seconds(self) -> float:
        """Age of cached secret in seconds"""
        return (datetime.utcnow() - self.cached_at).total_seconds()
```

## FastMCP Integration Models

### 10. AccessToken (FastMCP)

**Purpose**: FastMCP authentication result (defined by FastMCP library)

**Source**: Constructed by `TokenVerifierAuthProvider` from `ValidationResult`

**Lifecycle**: Created during authentication, passed to FastMCP framework

```python
# This is FastMCP's model - shown for reference
# From fastmcp.server.auth import AccessToken

class AccessToken(BaseModel):
    """
    FastMCP access token model (from MCP SDK).

    Reference only - this is defined by FastMCP, not our code.
    """

    token: str  # Raw token string
    client_id: str  # Client identifier
    scopes: list[str]  # Granted scopes
    expires_at: int | None = None  # Expiration Unix timestamp
    resource: str | None = None  # RFC 8707 resource indicator
    claims: dict[str, Any] = {}  # Additional JWT claims
```

**Mapping from ValidationResult**:
```python
# In TokenVerifierAuthProvider.verify_token()
access_token = AccessToken(
    token=token,  # Raw token
    client_id=result.claims.client_id or result.claims.subject or "unknown",
    scopes=result.claims.scopes,
    expires_at=int(result.claims.expires_at.timestamp()) if result.claims.expires_at else None,
    claims=result.claims.extra_claims
)
```

## Model Relationships

### Token Verification Flow

```
1. Client Request
   └─> Authorization: Bearer <token>

2. TokenVerifierAuthProvider.verify_token(token)
   └─> Extract token from header

3. TokenVerifier.verify(token)
   ├─> JWTVerifier
   │   ├─> Fetch JWKS keys (if not cached)
   │   ├─> Verify signature with public key
   │   ├─> Validate claims (iss, aud, exp)
   │   └─> Extract TokenClaims
   │
   ├─> IntrospectionTokenVerifier
   │   ├─> POST to introspection endpoint
   │   ├─> Check active flag
   │   └─> Extract TokenClaims
   │
   └─> StaticTokenVerifier (dev only)
       ├─> Lookup in token mapping
       └─> Return configured TokenClaims

4. ValidationResult
   ├─> Success: contains TokenClaims
   └─> Failure: contains error details

5. AccessToken Construction
   └─> Map TokenClaims → FastMCP AccessToken

6. FastMCP Framework
   └─> Proceed with authenticated request or reject
```

### Rate Limiting Flow

```
1. Authentication Attempt
   └─> token

2. Hash Token
   └─> SHA-256(token)[:16] = token_hash

3. Check Rate Limit
   ├─> Get RateLimitBucket for token_hash
   ├─> Count recent attempts in window
   └─> If >= max_attempts: REJECT (HTTP 429)

4. Record Attempt
   └─> Add timestamp to bucket.attempts

5. Cleanup (periodic)
   └─> Remove attempts older than window
```

### Secret Management Flow

```
1. Configuration Loading
   └─> SecretConfig from environment

2. Secret Request
   ├─> Check cache
   │   ├─> Hit + not expired: return cached value
   │   └─> Miss or expired: fetch new value
   │
   └─> Fetch Strategy
       ├─> Secret Manager
       │   ├─> Call SecretManagerServiceClient
       │   ├─> Get version (latest or specific)
       │   └─> Cache with TTL
       │
       └─> Environment Variables
           ├─> os.getenv(secret_name)
           └─> Cache with TTL

3. CachedSecret
   └─> Protected with SecretStr
```

## Validation Summary

All models enforce security requirements through Pydantic validators:

| Security Requirement | Model | Validator |
|---------------------|-------|-----------|
| Algorithm confusion prevention | JWTVerifierConfig | `validate_algorithm_safety()` |
| HMAC key strength | JWTVerifierConfig | `validate_hmac_key_strength()` |
| HTTPS enforcement (JWKS) | JWTVerifierConfig | `validate_https_jwks()` |
| HTTPS enforcement (introspection) | IntrospectionVerifierConfig | `validate_https_introspection()` |
| Production guards (static tokens) | StaticTokenVerifierConfig | `prevent_production_use()` |
| Secret protection | All configs | SecretStr type |
| Rate limit bounds | RateLimitConfig | Field constraints (ge, le) |
| Clock skew limits | JWTVerifierConfig | Field constraint (le=120) |

## Testing Considerations

### Model Validation Tests

Each model requires tests for:
1. Valid configuration accepted
2. Invalid configuration rejected with clear error message
3. Edge cases (empty scopes, missing fields, boundary values)
4. SecretStr masking in string representations
5. Pydantic serialization/deserialization

### Example Test

```python
import pytest
from pydantic import ValidationError

def test_jwt_config_algorithm_confusion():
    """Test that HMAC algorithms are rejected with JWKS URI"""
    with pytest.raises(ValidationError) as exc_info:
        JWTVerifierConfig(
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            algorithm="HS256",  # HMAC with JWKS - should fail
            issuer="test",
            audience="test"
        )

    assert "HMAC algorithms cannot be used with JWKS" in str(exc_info.value)
```

## Summary

This data model design provides:
- ✅ Type-safe configuration with Pydantic v2
- ✅ Comprehensive validation at startup (fail fast)
- ✅ Secret protection via SecretStr
- ✅ Clear model hierarchy and relationships
- ✅ Security requirements enforced through validators
- ✅ MCP 2025 OAuth 2.1 compliance
- ✅ Backward compatibility with existing FastMCP interface
