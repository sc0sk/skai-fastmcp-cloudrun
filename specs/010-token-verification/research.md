# Research: Token Verification

**Feature**: Token Verification
**Date**: 2025-10-23
**Phase**: 0 (Outline & Research)

## Overview

This document consolidates research findings for implementing token verification in FastMCP servers. Token verification enables MCP servers to act as OAuth resource servers by validating bearer tokens issued by external authentication systems without participating in user authentication flows.

## Research Areas

### 1. JWT Validation Libraries (Python)

**Decision**: Use PyJWT with cryptography backend

**Rationale**:
- **PyJWT** is the de-facto standard for JWT handling in Python with 7.5k+ GitHub stars and widespread adoption
- Supports all required algorithms: RS256/384/512 (RSA), ES256/384/512 (ECDSA), HS256/384/512 (HMAC)
- Built-in support for JWKS (JSON Web Key Sets) fetching and caching
- Strong security track record with regular updates
- Excellent integration with `cryptography` library for key management
- Type-safe with proper type hints
- Well-documented with clear API patterns

**Alternatives Considered**:
- **python-jose**: Good alternative but less actively maintained (last major update 2021), PyJWT has better community support
- **authlib**: Comprehensive but heavyweight - includes OAuth client/server components we don't need for pure token verification
- **jwcrypto**: Lower-level library requiring more boilerplate, PyJWT provides better developer experience

**Implementation Pattern**:
```python
import jwt
from jwt import PyJWKClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# JWKS endpoint pattern
jwks_client = PyJWKClient("https://auth.example.com/.well-known/jwks.json")
signing_key = jwks_client.get_signing_key_from_jwt(token)
decoded = jwt.decode(token, signing_key.key, algorithms=["RS256"],
                     audience="my-api", issuer="https://auth.example.com")

# Static public key pattern
public_key = serialization.load_pem_public_key(public_key_pem)
decoded = jwt.decode(token, public_key, algorithms=["RS256"],
                     audience="my-api", issuer="https://auth.example.com")

# HMAC symmetric key pattern
decoded = jwt.decode(token, shared_secret, algorithms=["HS256"],
                     audience="my-api", issuer="https://auth.example.com")
```

**Key Dependencies**:
- `PyJWT[crypto]` (version 2.8.0+) - includes cryptography support
- `cryptography` (version 41.0.0+) - RSA/ECDSA key operations
- Python 3.11+ built-in `urllib` for JWKS fetching (PyJWT handles this internally)

### 2. Token Introspection (RFC 7662)

**Decision**: Use httpx for async HTTP introspection with Pydantic response validation

**Rationale**:
- **httpx** is the modern async HTTP client for Python with excellent async/await support
- Native support for timeout configuration, retry logic, and connection pooling
- Type-safe with proper async context manager patterns
- Better performance than `requests` for high-throughput scenarios
- Built-in support for HTTP Basic Auth (required for RFC 7662 client authentication)
- AsyncClient enables non-blocking introspection calls critical for performance
- Existing usage in project (likely) for consistency

**RFC 7662 Protocol Summary**:
- Authorization server provides introspection endpoint (e.g., `/oauth/introspect`)
- Resource server (MCP server) authenticates with client credentials (HTTP Basic Auth)
- POST request with `token` parameter in form-encoded body
- Response includes `active` boolean + token metadata (scopes, expiration, subject)
- Must handle `active=false` for revoked/expired tokens
- Must handle network failures gracefully (deny access on error)

**Alternatives Considered**:
- **requests**: Synchronous only, would require threading or blocking, not suitable for async FastMCP server
- **aiohttp**: More complex API, httpx provides better developer experience with requests-like interface
- **urllib3**: Too low-level, requires significant boilerplate for production use

**Implementation Pattern**:
```python
import httpx
from pydantic import BaseModel

class IntrospectionResponse(BaseModel):
    active: bool
    scope: str | None = None
    client_id: str | None = None
    username: str | None = None
    exp: int | None = None
    iat: int | None = None
    sub: str | None = None

async def introspect_token(token: str, introspection_url: str,
                           client_id: str, client_secret: str) -> IntrospectionResponse:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            introspection_url,
            data={"token": token},
            auth=(client_id, client_secret),
            timeout=10.0
        )
        response.raise_for_status()
        return IntrospectionResponse(**response.json())
```

**Key Dependencies**:
- `httpx` (version 0.25.0+) - async HTTP client
- `pydantic` v2 (existing) - response validation
- Standard library `base64` for Basic Auth (httpx handles internally)

### 3. JWKS Key Caching Strategy

**Decision**: Implement time-based cache with automatic refresh and stale-while-revalidate pattern

**Rationale**:
- **Performance**: Fetching JWKS on every request adds 100-500ms latency - unacceptable for <100ms validation target
- **Reliability**: Cached keys enable graceful degradation when JWKS endpoint is unavailable
- **Security**: Key rotation support ensures smooth transitions without request drops
- **RFC 7517 Compliance**: JWKS standard supports key rotation via `kid` (key ID) matching

**Caching Strategy**:
1. **Initial fetch**: On first token validation, fetch JWKS and cache with TTL (default 1 hour)
2. **Hit path**: Use cached key if `kid` matches and cache not expired (< 1ms lookup)
3. **Miss path**: If `kid` not found in cache, fetch fresh JWKS (handles key rotation)
4. **Stale-while-revalidate**: Use expired cache if JWKS endpoint unavailable (graceful degradation)
5. **Concurrent requests**: Single in-flight fetch prevents thundering herd during cache refresh

**Alternative Patterns Considered**:
- **No caching**: Rejected - 100-500ms latency per request violates performance requirements
- **Cache forever**: Rejected - prevents key rotation, security risk
- **Background refresh**: Considered but adds complexity - simpler to refresh on first use after expiration
- **Redis cache**: Overkill for single-server deployments - in-memory cache sufficient, can add Redis later for multi-instance

**Implementation Notes**:
- PyJWT's `PyJWKClient` provides built-in caching with configurable TTL
- Default cache TTL: 3600 seconds (1 hour) - balances performance and freshness
- Override with `lifespan` parameter for testing (shorter TTL) or high-security scenarios
- Use asyncio locks to prevent concurrent JWKS fetches

### 4. Clock Skew Tolerance

**Decision**: 60-second default clock skew tolerance with configuration override

**Rationale**:
- **Industry Standard**: 60 seconds is widely used (Auth0, Okta, AWS Cognito use 60-300s)
- **Operational Reality**: Server clocks drift despite NTP - typical drift is 1-30 seconds
- **Security Balance**: Tight enough to prevent significant replay window expansion, loose enough for operational reliability
- **JWT Standard**: RFC 7519 recommends clock skew tolerance but doesn't mandate specific value

**Clock Skew Application**:
- **exp (expiration)**: Token valid if `current_time < exp + leeway` (accept slightly expired tokens)
- **nbf (not before)**: Token valid if `current_time >= nbf - leeway` (accept slightly future tokens)
- **iat (issued at)**: Optional validation, typically not enforced with strict clock skew

**Alternative Values Considered**:
- **0 seconds (strict)**: Rejected - causes frequent false negatives in production due to clock drift
- **300 seconds (5 minutes)**: Considered but too permissive - expands replay attack window unnecessarily
- **120 seconds (2 minutes)**: Reasonable alternative for high-security scenarios, 60s preferred for balance

**Implementation Pattern**:
```python
# PyJWT built-in support
decoded = jwt.decode(token, public_key, algorithms=["RS256"],
                     audience="my-api",
                     issuer="https://auth.example.com",
                     leeway=60)  # 60-second clock skew tolerance

# Environment configuration
CLOCK_SKEW_SECONDS = int(os.getenv("FASTMCP_SERVER_AUTH_JWT_CLOCK_SKEW", "60"))
```

### 5. Minimum HMAC Key Length

**Decision**: Enforce minimum key lengths based on algorithm: HS256=32 bytes, HS384=48 bytes, HS512=64 bytes

**Rationale**:
- **NIST SP 800-107**: Recommends HMAC key length ≥ hash output size
- **RFC 2104 (HMAC)**: States key should be at least as long as hash output (256 bits = 32 bytes for SHA-256)
- **Security Best Practice**: Shorter keys reduce entropy and enable brute-force attacks
- **Algorithm Alignment**: Key length should match hash algorithm strength
  - HS256 (SHA-256): 32 bytes minimum
  - HS384 (SHA-384): 48 bytes minimum
  - HS512 (SHA-512): 64 bytes minimum

**Enforcement Strategy**:
- Validate key length at configuration time (fail fast on server startup)
- Provide clear error messages with minimum length requirements
- Support base64-encoded keys (decode before length check)
- Allow override for testing (with explicit warning)

**Alternative Approaches Considered**:
- **No validation**: Rejected - weak keys are a security vulnerability
- **Universal 32-byte minimum**: Too weak for HS384/HS512
- **Universal 64-byte minimum**: Too strict for HS256, reduces adoption

**Implementation Pattern**:
```python
def validate_hmac_key(key: str, algorithm: str) -> None:
    min_lengths = {"HS256": 32, "HS384": 48, "HS512": 64}
    min_length = min_lengths.get(algorithm)
    if min_length and len(key.encode()) < min_length:
        raise ValueError(
            f"HMAC key for {algorithm} must be at least {min_length} bytes. "
            f"Current key length: {len(key.encode())} bytes"
        )
```

### 6. Error Handling Patterns

**Decision**: Differentiate between validation errors (401) and system errors (500) with structured error responses

**Rationale**:
- **Security**: Don't leak internal system details in validation errors (e.g., "JWKS endpoint unreachable" → generic "authentication failed")
- **Debugging**: Provide sufficient context for legitimate debugging without exposing attack surface
- **Standards Compliance**: OAuth 2.0 Bearer Token Usage (RFC 6750) defines error response format
- **Client Experience**: Clear error messages enable proper client-side error handling

**Error Categories**:

1. **Validation Errors (401 Unauthorized)**:
   - Expired token (`exp` claim past current time)
   - Invalid signature (token tampered or wrong key)
   - Wrong issuer (`iss` claim doesn't match expected)
   - Wrong audience (`aud` claim doesn't match expected)
   - Insufficient scopes (missing required scopes)
   - Malformed token (cannot parse JWT structure)
   - Invalid bearer token format in header

2. **System Errors (500 Internal Server Error)**:
   - JWKS endpoint unreachable (network failure)
   - Introspection endpoint timeout
   - Configuration error (invalid algorithm, missing keys)
   - Internal key cache failure

**Error Response Format** (RFC 6750):
```
WWW-Authenticate: Bearer error="invalid_token",
                  error_description="Token signature verification failed"
```

**Production Error Masking**:
- Development: Detailed error messages with stack traces
- Production: Generic messages, detailed logs to server logs only
- Never expose: Internal endpoints, key material, system architecture

**Implementation Pattern**:
```python
class TokenValidationError(Exception):
    """Base class for token validation errors (401)"""
    pass

class TokenExpiredError(TokenValidationError):
    """Token has expired"""
    pass

class InvalidSignatureError(TokenValidationError):
    """Token signature is invalid"""
    pass

class SystemAuthError(Exception):
    """Base class for system auth errors (500)"""
    pass

# Error handler in FastMCP server
@app.exception_handler(TokenValidationError)
async def validation_error_handler(request, exc):
    # Generic message for clients, detailed logging internally
    logger.warning(f"Token validation failed: {exc}", extra={"client_ip": request.client.host})
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": f'Bearer error="invalid_token"'},
        content={"error": "invalid_token", "error_description": "Authentication failed"}
    )
```

### 7. Development Testing Utilities

**Decision**: Provide StaticTokenVerifier and RSAKeyPair generator for rapid development without external dependencies

**Rationale**:
- **Development Velocity**: Developers shouldn't need OAuth infrastructure for local testing
- **CI/CD Testing**: Automated tests need deterministic tokens without network calls
- **Learning Curve**: Simple examples help developers understand token verification concepts
- **Rapid Prototyping**: Quick token generation for integration testing

**StaticTokenVerifier Pattern**:
```python
# Simple mapping: token string -> claims dict
verifier = StaticTokenVerifier(
    tokens={
        "dev-alice-token": {
            "client_id": "alice@company.com",
            "scopes": ["read:data", "write:data", "admin"]
        },
        "dev-guest-token": {
            "client_id": "guest",
            "scopes": ["read:data"]
        }
    }
)
```

**RSAKeyPair Generator Pattern**:
```python
# Generate test key pair
key_pair = RSAKeyPair.generate(key_size=2048)

# Get keys in various formats
private_key_pem = key_pair.private_key_pem  # For signing tokens
public_key_pem = key_pair.public_key_pem    # For server configuration
jwks_dict = key_pair.to_jwks()              # For JWKS endpoint mocking

# Create test tokens
test_token = key_pair.create_token(
    subject="test-user-123",
    issuer="https://test.example.com",
    audience="test-api",
    scopes=["read", "write"],
    expiration=3600  # 1 hour
)
```

**Security Warnings**:
- StaticTokenVerifier MUST only be used in development (check environment, fail if production detected)
- Generated key pairs MUST NOT be committed to version control
- Test tokens MUST have short expiration times
- Clear documentation warning against production use

**Alternative Approaches Considered**:
- **Mock OAuth server**: Too complex for simple testing scenarios
- **Hardcoded test tokens**: Brittle, expire over time, require regeneration
- **External test services (auth0-test, etc.)**: Adds external dependency, network latency, rate limiting

### 8. Environment-Based Configuration

**Decision**: Prefix all configuration with `FASTMCP_SERVER_AUTH_` following FastMCP conventions

**Rationale**:
- **Consistency**: Matches existing FastMCP environment variable patterns
- **Namespace Protection**: Avoids conflicts with other environment variables
- **Discovery**: Clear prefix makes configuration discoverable
- **Documentation**: Standard pattern simplifies documentation and examples

**Environment Variable Naming Convention**:
```bash
# Format: FASTMCP_SERVER_AUTH_{PROVIDER}_{SETTING}
FASTMCP_SERVER_AUTH=jwt                                    # Select auth provider
FASTMCP_SERVER_AUTH_JWT_JWKS_URI=https://...              # JWKS endpoint
FASTMCP_SERVER_AUTH_JWT_ISSUER=https://auth.example.com   # Expected issuer
FASTMCP_SERVER_AUTH_JWT_AUDIENCE=my-api                   # Expected audience
FASTMCP_SERVER_AUTH_JWT_ALGORITHM=RS256                   # Algorithm (optional)
FASTMCP_SERVER_AUTH_JWT_PUBLIC_KEY=-----BEGIN PUBLIC...  # Static key (optional)
FASTMCP_SERVER_AUTH_JWT_REQUIRED_SCOPES=read,write        # Comma-separated scopes
FASTMCP_SERVER_AUTH_JWT_CLOCK_SKEW=60                     # Clock skew tolerance (seconds)

# Introspection endpoint configuration
FASTMCP_SERVER_AUTH=introspection
FASTMCP_SERVER_AUTH_INTROSPECTION_URL=https://auth.example.com/introspect
FASTMCP_SERVER_AUTH_INTROSPECTION_CLIENT_ID=mcp-server
FASTMCP_SERVER_AUTH_INTROSPECTION_CLIENT_SECRET=secret123
FASTMCP_SERVER_AUTH_INTROSPECTION_REQUIRED_SCOPES=api:read,api:write
```

**Configuration Priority**:
1. Explicit programmatic configuration (highest priority)
2. Environment variables
3. Default values (lowest priority)

**Validation Strategy**:
- Validate configuration at server startup (fail fast)
- Provide clear error messages for invalid/missing required settings
- Support partial configuration (e.g., JWKS URI without explicit algorithm - auto-detect)

## Dependencies Summary

### Production Dependencies
- `PyJWT[crypto]>=2.8.0` - JWT validation with cryptography support
- `cryptography>=41.0.0` - RSA/ECDSA key operations
- `httpx>=0.25.0` - Async HTTP client for token introspection
- `pydantic>=2.0.0` - Data validation (existing dependency)

### Development Dependencies
- `pytest>=7.4.0` - Testing framework (existing)
- `pytest-asyncio>=0.21.0` - Async test support (existing)
- `pytest-httpx>=0.22.0` - Mock HTTP requests for introspection tests

### Optional Dependencies
- `python-dotenv` - .env file support for local development (likely existing)

## Security Considerations

### OWASP Token Validation Best Practices

1. **Always verify signature** - Never trust unsigned tokens
2. **Validate all standard claims** - `iss`, `aud`, `exp`, `nbf` where present
3. **Use constant-time comparison** - Prevent timing attacks (PyJWT handles this)
4. **Fail closed** - Deny access on validation errors, don't assume success
5. **Log security events** - Track failed validations for monitoring
6. **Rate limit validation** - Prevent brute force attacks on token validation endpoints
7. **Secure key storage** - Never log or expose private keys

### JWT Security Pitfalls (Avoided)

1. **"alg: none" vulnerability** - PyJWT rejects unsigned tokens by default
2. **Key confusion attacks** - Explicitly specify allowed algorithms, never auto-detect
3. **Weak HMAC keys** - Enforce minimum key lengths
4. **Missing audience validation** - Always validate `aud` claim
5. **Excessive clock skew** - Limit to 60 seconds
6. **Key material in logs** - Mask keys in error messages and logs

## Performance Benchmarks (Targets)

Based on research of production JWT validation systems:

- **JWKS cached validation**: 1-5ms (signature verification only)
- **JWKS cache miss (fresh fetch)**: 100-500ms (network + validation)
- **HMAC validation**: 0.5-2ms (symmetric key faster than asymmetric)
- **Token introspection**: 50-200ms (network round-trip to auth server)
- **Static token lookup**: 0.1-0.5ms (dictionary lookup)

**Target**: <50ms overhead for cached JWT validation, <200ms for introspection (p95)

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| JWKS endpoint downtime | HIGH | Implement cache with stale-while-revalidate pattern |
| Key rotation drops requests | MEDIUM | Support multiple simultaneous keys via JWKS `kid` matching |
| Weak HMAC keys in production | HIGH | Enforce minimum key lengths with startup validation |
| Clock skew causes false negatives | MEDIUM | Default 60-second leeway with override option |
| Introspection endpoint latency | MEDIUM | Set aggressive timeouts (10s), consider local caching if needed |
| Static tokens used in production | HIGH | Environment detection with hard failure in production environments |
| Token validation bypass | CRITICAL | Explicit algorithm specification, no auto-detection |
| Sensitive data in logs | MEDIUM | Mask all key material and tokens in logs |

## Next Steps (Phase 1)

1. Generate `data-model.md` with Pydantic models for token claims and validation results
2. Create `quickstart.md` with setup instructions for each verification method
3. Update agent context files (CLAUDE.md) with new dependencies
4. Re-evaluate Constitution Check after design complete
