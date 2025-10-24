# Data Model: Token Verification

**Feature**: Token Verification
**Date**: 2025-10-23
**Phase**: 1 (Design & Contracts)

## Overview

Token verification is primarily a stateless operation with no persistent storage. Data models represent in-memory validation results, token claims, and configuration objects. All models use Pydantic v2 for runtime validation and type safety.

## Core Models

### TokenClaims

Represents validated claims extracted from a token (JWT or introspection response).

**Purpose**: Unified representation of token identity and permissions regardless of source (JWT claims vs introspection response)

**Fields**:
```python
class TokenClaims(BaseModel):
    """
    Validated token claims extracted from JWT or introspection response.

    Provides unified interface for authorization decisions regardless of token type.
    """
    # Identity
    subject: str | None = Field(None, description="Subject identifier (sub claim)")
    client_id: str | None = Field(None, description="Client identifier (client_id claim or azp)")
    username: str | None = Field(None, description="Username (username claim, if present)")

    # Token metadata
    issuer: str | None = Field(None, description="Token issuer (iss claim)")
    audience: str | list[str] | None = Field(None, description="Intended audience (aud claim)")
    issued_at: datetime | None = Field(None, description="Token issue timestamp (iat claim)")
    expires_at: datetime | None = Field(None, description="Token expiration timestamp (exp claim)")
    not_before: datetime | None = Field(None, description="Token not valid before timestamp (nbf claim)")

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
```

**Validation Rules**:
- At least one of `subject` or `client_id` MUST be present (validated via `identity` property usage)
- `expires_at` if present MUST be in the future (validated at token verification time)
- `scopes` MUST be a list of non-empty strings
- `audience` can be either single string or list of strings (JWT spec allows both)

**Relationships**:
- Returned by all `TokenVerifier` implementations
- Used by FastMCP auth middleware for authorization decisions
- Passed to request context for tool access control

### ValidationResult

Represents the outcome of a token validation attempt.

**Purpose**: Structured validation result that clearly distinguishes success from various failure modes

**Fields**:
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
    error_code: int | None = Field(None, description="HTTP status code (401 for validation errors, 500 for system errors)")

    @classmethod
    def success_result(cls, claims: TokenClaims) -> "ValidationResult":
        """Create successful validation result"""
        return cls(success=True, claims=claims)

    @classmethod
    def failure_result(cls, error: str, error_description: str, error_code: int = 401) -> "ValidationResult":
        """Create failed validation result"""
        return cls(
            success=False,
            error=error,
            error_description=error_description,
            error_code=error_code
        )

    def raise_if_failed(self) -> None:
        """Raise TokenValidationError if validation failed"""
        if not self.success:
            raise TokenValidationError(self.error_description or "Token validation failed")
```

**Validation Rules**:
- If `success=True`, `claims` MUST be present
- If `success=False`, `error` and `error_description` MUST be present
- `error_code` MUST be 401 (validation errors) or 500 (system errors)

**Error Categories** (following RFC 6750):
- `"invalid_token"`: Token malformed, expired, wrong signature, wrong audience/issuer
- `"insufficient_scope"`: Token valid but lacks required scopes
- `"invalid_request"`: Malformed Authorization header
- `"server_error"`: Internal system errors (JWKS unreachable, configuration error)

### JWTVerifierConfig

Configuration for JWT verification.

**Purpose**: Type-safe configuration for JWT verification with validation rules

**Fields**:
```python
class JWTVerifierConfig(BaseModel):
    """
    Configuration for JWT token verification.

    Supports JWKS endpoints, static public keys, and HMAC symmetric keys.
    """
    # Key configuration (mutually exclusive: either jwks_uri OR public_key)
    jwks_uri: str | None = Field(None, description="JWKS endpoint URL")
    public_key: str | None = Field(None, description="Static public key (PEM) or HMAC secret")

    # Validation parameters
    issuer: str = Field(description="Expected token issuer (iss claim)")
    audience: str | list[str] = Field(description="Expected audience (aud claim)")
    algorithm: str = Field("RS256", description="JWT signing algorithm (RS256, ES256, HS256, etc.)")

    # Optional settings
    required_scopes: list[str] = Field(default_factory=list, description="Required scopes for access")
    clock_skew: int = Field(60, description="Clock skew tolerance in seconds", ge=0, le=300)
    jwks_cache_ttl: int = Field(3600, description="JWKS cache TTL in seconds", ge=60, le=86400)

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
            if len(self.public_key.encode()) < min_length:
                raise ValueError(
                    f"HMAC key for {self.algorithm} must be at least {min_length} bytes. "
                    f"Current key length: {len(self.public_key.encode())} bytes"
                )
        return self

    @classmethod
    def from_env(cls) -> "JWTVerifierConfig":
        """Load configuration from environment variables"""
        return cls(
            jwks_uri=os.getenv("FASTMCP_SERVER_AUTH_JWT_JWKS_URI"),
            public_key=os.getenv("FASTMCP_SERVER_AUTH_JWT_PUBLIC_KEY"),
            issuer=os.getenv("FASTMCP_SERVER_AUTH_JWT_ISSUER"),
            audience=os.getenv("FASTMCP_SERVER_AUTH_JWT_AUDIENCE"),
            algorithm=os.getenv("FASTMCP_SERVER_AUTH_JWT_ALGORITHM", "RS256"),
            required_scopes=os.getenv("FASTMCP_SERVER_AUTH_JWT_REQUIRED_SCOPES", "").split(","),
            clock_skew=int(os.getenv("FASTMCP_SERVER_AUTH_JWT_CLOCK_SKEW", "60")),
        )
```

**Validation Rules**:
- MUST specify exactly one of `jwks_uri` or `public_key` (mutually exclusive)
- `issuer` is REQUIRED (no default - explicit configuration)
- `audience` is REQUIRED (can be single string or list)
- `algorithm` MUST be a valid JWT algorithm (RS256, RS384, RS512, ES256, ES384, ES512, HS256, HS384, HS512)
- HMAC keys MUST meet minimum length requirements (32/48/64 bytes)
- `clock_skew` MUST be between 0 and 300 seconds
- `jwks_cache_ttl` MUST be between 60 seconds and 24 hours

### IntrospectionVerifierConfig

Configuration for OAuth 2.0 Token Introspection.

**Purpose**: Type-safe configuration for RFC 7662 token introspection

**Fields**:
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
    client_secret: str = Field(description="Client secret for introspection authentication")

    # Optional settings
    required_scopes: list[str] = Field(default_factory=list, description="Required scopes for access")
    timeout: int = Field(10, description="HTTP request timeout in seconds", ge=1, le=60)

    @field_validator("introspection_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate introspection URL is well-formed HTTPS"""
        if not v.startswith("https://") and not v.startswith("http://localhost"):
            raise ValueError("Introspection URL must use HTTPS (or http://localhost for dev)")
        return v

    @classmethod
    def from_env(cls) -> "IntrospectionVerifierConfig":
        """Load configuration from environment variables"""
        return cls(
            introspection_url=os.getenv("FASTMCP_SERVER_AUTH_INTROSPECTION_URL"),
            client_id=os.getenv("FASTMCP_SERVER_AUTH_INTROSPECTION_CLIENT_ID"),
            client_secret=os.getenv("FASTMCP_SERVER_AUTH_INTROSPECTION_CLIENT_SECRET"),
            required_scopes=os.getenv("FASTMCP_SERVER_AUTH_INTROSPECTION_REQUIRED_SCOPES", "").split(","),
            timeout=int(os.getenv("FASTMCP_SERVER_AUTH_INTROSPECTION_TIMEOUT", "10")),
        )
```

**Validation Rules**:
- `introspection_url` MUST be HTTPS (except localhost for development)
- `client_id` and `client_secret` are REQUIRED
- `timeout` MUST be between 1 and 60 seconds
- `required_scopes` can be empty list (no scope requirements)

### StaticTokenVerifierConfig

Configuration for static token verification (development only).

**Purpose**: Simple token mapping for development and testing without external dependencies

**Fields**:
```python
class StaticTokenVerifierConfig(BaseModel):
    """
    Configuration for static token verification (DEVELOPMENT ONLY).

    Maps token strings to predefined claims for local testing.
    """
    tokens: dict[str, dict[str, Any]] = Field(
        description="Mapping of token strings to claims dictionaries"
    )
    required_scopes: list[str] = Field(default_factory=list, description="Required scopes for access")

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
                    f"Token '{token}' must have either 'client_id' or 'subject' claim"
                )
        return self
```

**Validation Rules**:
- MUST NOT be used when `ENVIRONMENT=production`
- Each token entry MUST have either `client_id` or `subject`
- Token strings MUST be non-empty
- Claims MUST be valid JSON-serializable dictionaries

## Abstract Base Classes

### TokenVerifier

Abstract base for all verifier implementations.

**Purpose**: Common interface for different token verification strategies

**Methods**:
```python
from abc import ABC, abstractmethod

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

    @abstractmethod
    def verify_scopes(self, claims: TokenClaims, required_scopes: list[str]) -> bool:
        """
        Verify token has required scopes.

        Args:
            claims: Extracted token claims
            required_scopes: List of required scopes

        Returns:
            True if all required scopes present, False otherwise
        """
        pass

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
```

**Implementations**:
- `JWTVerifier` - JWT validation with JWKS/static keys/HMAC
- `IntrospectionTokenVerifier` - OAuth 2.0 introspection
- `StaticTokenVerifier` - Static token mapping (development)

## Helper Models

### RSAKeyPair

Helper for generating RSA key pairs and test tokens.

**Purpose**: Development utility for creating test keys and tokens

**Fields**:
```python
class RSAKeyPair(BaseModel):
    """
    RSA key pair for JWT signing and verification.

    DEVELOPMENT USE ONLY - generates test keys and tokens.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    private_key: Any = Field(description="Cryptography RSA private key object")
    public_key: Any = Field(description="Cryptography RSA public key object")
    key_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Key identifier (kid)")

    @property
    def private_key_pem(self) -> str:
        """Export private key as PEM string"""
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()

    @property
    def public_key_pem(self) -> str:
        """Export public key as PEM string"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()

    def to_jwks(self) -> dict[str, Any]:
        """Export public key as JWKS format"""
        # Implementation: Convert RSA public key to JWK format
        pass

    def create_token(
        self,
        subject: str,
        issuer: str,
        audience: str,
        scopes: list[str] | None = None,
        expiration: int = 3600
    ) -> str:
        """
        Create signed JWT token for testing.

        Args:
            subject: Token subject (sub claim)
            issuer: Token issuer (iss claim)
            audience: Token audience (aud claim)
            scopes: Token scopes (scope claim)
            expiration: Token lifetime in seconds

        Returns:
            Signed JWT token string
        """
        pass

    @classmethod
    def generate(cls, key_size: int = 2048) -> "RSAKeyPair":
        """Generate new RSA key pair"""
        from cryptography.hazmat.primitives.asymmetric import rsa

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size
        )
        return cls(
            private_key=private_key,
            public_key=private_key.public_key()
        )
```

## Entity Relationships

```
                                  ┌─────────────────┐
                                  │  TokenVerifier  │
                                  │   (abstract)    │
                                  └────────┬────────┘
                                           │
                         ┌─────────────────┼─────────────────┐
                         │                 │                 │
                ┌────────▼────────┐ ┌─────▼──────┐ ┌───────▼────────┐
                │  JWTVerifier    │ │Introspection│ │StaticToken     │
                │                 │ │Verifier     │ │Verifier        │
                └────────┬────────┘ └─────┬──────┘ └───────┬────────┘
                         │                │                 │
                         └────────────────┼─────────────────┘
                                          │
                                          │ verify()
                                          │
                                   ┌──────▼──────┐
                                   │ Validation  │
                                   │   Result    │
                                   └──────┬──────┘
                                          │
                                          │ contains
                                          │
                                   ┌──────▼──────┐
                                   │TokenClaims  │
                                   │             │
                                   └─────────────┘

Configuration Models:
┌──────────────────┐    ┌───────────────────────┐    ┌──────────────────────┐
│JWTVerifierConfig │    │IntrospectionVerifier  │    │StaticTokenVerifier   │
│                  │    │Config                 │    │Config                │
└────────┬─────────┘    └────────┬──────────────┘    └────────┬─────────────┘
         │                       │                            │
         └───────────────────────┼────────────────────────────┘
                                 │
                          configures
                                 │
                          ┌──────▼──────┐
                          │TokenVerifier│
                          │             │
                          └─────────────┘
```

## State Transitions

### Token Validation Flow

```
[Authorization Header]
         │
         ▼
[Extract Bearer Token]
         │
    ┌────┴────┐
    │ Valid?  │──No──► [ValidationResult: invalid_request]
    └────┬────┘
         │ Yes
         ▼
[TokenVerifier.verify(token)]
         │
    ┌────┴────────────────────────────┐
    │  Verification Strategy           │
    │  - JWT: Signature + Claims       │
    │  - Introspection: HTTP Request   │
    │  - Static: Dictionary Lookup     │
    └────┬────────────────────────────┘
         │
    ┌────┴────┐
    │Success? │──No──► [ValidationResult: invalid_token/server_error]
    └────┬────┘
         │ Yes
         ▼
[Extract TokenClaims]
         │
         ▼
[Verify Required Scopes]
         │
    ┌────┴────┐
    │ Has All?│──No──► [ValidationResult: insufficient_scope]
    └────┬────┘
         │ Yes
         ▼
[ValidationResult: success + claims]
         │
         ▼
[Allow Request / Inject Claims into Context]
```

## Storage Requirements

**None** - Token verification is stateless. All validation uses:
- In-memory JWKS key cache (transient, TTL-based)
- No persistent storage required
- No database tables

**Future Considerations**:
- Optional Redis cache for JWKS keys in multi-instance deployments
- Optional token revocation list (if needed beyond OAuth introspection)

## Migration Path

This is a new feature with no existing data to migrate. However, integration considerations:

1. **Existing GitHub OAuth**: Token verification ADDS authentication options, doesn't replace existing GitHub OAuth
2. **Configuration Migration**: Servers using GitHub OAuth can add token verification without disruption
3. **Gradual Rollout**: Servers can support both GitHub OAuth and token verification simultaneously
4. **Client Compatibility**: Existing MCP clients unaffected - auth negotiation happens at connection time

## Validation Summary

| Model | Required Fields | Validation Rules | Error Handling |
|-------|----------------|------------------|----------------|
| TokenClaims | subject OR client_id | Valid datetime objects, non-empty scopes | N/A (passive data) |
| ValidationResult | success, error (if failed) | Claims required if success, error details if failed | Raise TokenValidationError |
| JWTVerifierConfig | issuer, audience, jwks_uri OR public_key | Mutual exclusivity, HMAC key length, URL format | ValueError on construction |
| IntrospectionVerifierConfig | introspection_url, client_id, client_secret | HTTPS URLs, timeout range | ValueError on construction |
| StaticTokenVerifierConfig | tokens dict | Production environment check, required claims | ValueError on construction |
| TokenVerifier | N/A (abstract) | Subclass must implement verify() | NotImplementedError |
| RSAKeyPair | private_key, public_key | Valid cryptography key objects | ValueError on construction |
