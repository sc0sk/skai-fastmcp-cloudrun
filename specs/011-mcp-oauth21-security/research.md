# Research: MCP OAuth 2.1 Compliance and Security Hardening

**Feature**: 011-mcp-oauth21-security
**Date**: 2025-10-24
**Purpose**: Technology research and architecture decisions for OAuth 2.1 Resource Server implementation with security hardening

## Overview

This document captures research findings and technology decisions for implementing MCP 2025-03-26 OAuth 2.1 Resource Server compliance while fixing critical security vulnerabilities in the existing token verification system.

## Technology Decisions

### 1. Rate Limiting Implementation

**Decision**: Token bucket algorithm with in-memory state storage

**Rationale**:
- **Token Bucket Algorithm**: Industry-standard for API rate limiting, allows burst traffic while maintaining long-term rate limits
- **In-Memory Storage**: Simpler than distributed state (Redis, Memcached) for per-instance rate limiting
- **Performance**: <5ms overhead per request, negligible impact on p95 latency
- **Scope**: Per-token-hash limiting prevents one malicious actor from affecting all users

**Alternatives Considered**:
1. **Distributed Rate Limiting (Redis)**: Rejected - adds infrastructure complexity, network latency, and single point of failure. Per-instance limiting is sufficient for Cloud Run's auto-scaling model.
2. **Fixed Window Algorithm**: Rejected - vulnerable to burst attacks at window boundaries
3. **Sliding Window Log**: Rejected - higher memory overhead, unnecessary complexity for this use case

**Implementation Details**:
- Data structure: `dict[str, list[datetime]]` mapping token hash → attempt timestamps
- Automatic cleanup of expired entries (older than window duration)
- Thread-safe with `asyncio.Lock` for concurrent request handling
- Configurable parameters: max attempts (default 10), window duration (default 60s)

### 2. Google Cloud Secret Manager Integration

**Decision**: Use official `google-cloud-secret-manager` Python client with TTL-based caching

**Rationale**:
- **Official Client**: Maintained by Google, follows best practices, automatic auth via service account
- **TTL Caching**: Reduces Secret Manager API calls (cost), improves latency (10ms cached vs 200ms+ API call)
- **Version Support**: Handles "latest" and specific version selection
- **Automatic Rotation**: Detects new versions after cache TTL expiration

**Alternatives Considered**:
1. **Direct REST API Calls**: Rejected - reinventing the wheel, missing automatic authentication, error handling
2. **No Caching**: Rejected - excessive API calls (rate limits, cost), unnecessary latency on every token validation
3. **File-based Secrets**: Rejected - doesn't support automatic rotation, requires manual deployment updates

**Implementation Details**:
- Async wrapper around `SecretManagerServiceClient`
- Cache structure: `dict[str, tuple[str, datetime]]` mapping secret name → (value, cached_at)
- Default TTL: 300 seconds (configurable)
- Fallback chain: Secret Manager → environment variables → raise error
- IAM role required: `roles/secretmanager.secretAccessor`

### 3. Token Hash Logging

**Decision**: SHA-256 hashing for all token log references

**Rationale**:
- **SHA-256**: Industry-standard cryptographic hash, irreversible, collision-resistant
- **Security**: Prevents token exposure in logs, audit trails, error reports
- **Debugging**: Sufficient for correlating requests (same token = same hash) without exposing secret
- **Performance**: Minimal overhead (<1ms per hash operation)

**Alternatives Considered**:
1. **Token Truncation** (first/last N characters): Rejected - still leaks partial token, aids brute force
2. **UUIDs/Random IDs**: Rejected - loses correlation capability (can't track same token across requests)
3. **HMAC**: Rejected - requires secret key management, unnecessary complexity for one-way hashing

**Implementation Details**:
```python
import hashlib

def hash_token(token: str) -> str:
    """Create non-reversible token hash for logging"""
    return hashlib.sha256(token.encode()).hexdigest()[:16]  # First 16 chars sufficient
```

### 4. Algorithm Confusion Prevention

**Decision**: Enforce algorithm whitelist with Pydantic validators, separate JWKS/HMAC verifier classes

**Rationale**:
- **Whitelist Approach**: Only allow known-safe algorithms (RS256, RS384, RS512, ES256, ES384, ES512)
- **JWKS ≠ HMAC**: Prevent configuration mixing JWKS URI with HMAC algorithms (critical vulnerability)
- **Pydantic Validation**: Configuration errors caught at startup, before any tokens processed
- **Type Safety**: Separate classes for asymmetric (JWTVerifier) vs symmetric (HMACVerifier) if needed

**Alternatives Considered**:
1. **Runtime Algorithm Validation Only**: Rejected - errors occur during request handling, not at startup
2. **Single Verifier Class**: Rejected - easier to accidentally misconfigure, unclear separation
3. **Algorithm Blacklist**: Rejected - insecure (new vulnerable algorithms could emerge)

**Implementation Details**:
```python
SAFE_ASYMMETRIC_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
SAFE_SYMMETRIC_ALGORITHMS = ["HS256", "HS384", "HS512"]

@model_validator(mode="after")
def validate_algorithm_safety(self) -> "JWTVerifierConfig":
    if self.jwks_uri and self.algorithm not in SAFE_ASYMMETRIC_ALGORITHMS:
        raise ValueError(f"JWKS endpoints require asymmetric algorithms: {SAFE_ASYMMETRIC_ALGORITHMS}")
    if self.jwks_uri and self.algorithm in SAFE_SYMMETRIC_ALGORITHMS:
        raise ValueError("HMAC algorithms cannot be used with JWKS endpoints (algorithm confusion attack)")
    return self
```

### 5. HMAC Key Validation

**Decision**: Multi-layer validation - length, entropy estimation, weak pattern detection

**Rationale**:
- **Minimum Length**: 32/48/64 bytes for HS256/HS384/HS512 per OAuth 2.0 security recommendations
- **Weak Pattern Detection**: Reject common test strings, repeated characters
- **Base64 Awareness**: Check decoded length for base64-encoded secrets
- **Startup Validation**: Fail fast on weak keys, never allow weak configuration to production

**Alternatives Considered**:
1. **Length-Only Validation**: Rejected - doesn't catch weak keys like "aaaaaaaaaaaaa..."
2. **Full Entropy Analysis**: Rejected - computationally expensive, false positives on legitimate keys
3. **No Validation**: Rejected - allows weak keys vulnerable to brute force

**Implementation Details**:
```python
@model_validator(mode="after")
def validate_hmac_key_strength(self) -> "JWTVerifierConfig":
    if not self.algorithm.startswith("HS"):
        return self

    min_length = {"HS256": 32, "HS384": 48, "HS512": 64}[self.algorithm]
    key_bytes = self.public_key.encode()

    # Check minimum length
    if len(key_bytes) < min_length:
        raise ValueError(f"{self.algorithm} requires minimum {min_length} bytes")

    # Detect weak patterns
    weak_patterns = [b'a' * min_length, b'test', b'secret', b'password']
    if any(pattern in key_bytes for pattern in weak_patterns):
        raise ValueError("HMAC key appears to be weak/test value")

    # Check base64-decoded length if applicable
    try:
        decoded = base64.b64decode(key_bytes)
        if len(decoded) < min_length:
            raise ValueError(f"Base64-decoded key only {len(decoded)} bytes")
    except Exception:
        pass  # Not base64, continue

    return self
```

### 6. HTTPS Enforcement

**Decision**: Pydantic field validators with environment-aware rules (production vs development)

**Rationale**:
- **Production Safety**: Prevent MITM attacks on JWKS/introspection endpoints
- **Development Flexibility**: Allow localhost HTTP for local testing without security warnings
- **Early Detection**: Configuration errors caught at startup via Pydantic validators
- **Clear Error Messages**: Developers immediately know why http:// URLs are rejected

**Alternatives Considered**:
1. **Runtime Validation Only**: Rejected - errors occur during first token validation, not at startup
2. **Allow HTTP with Warnings**: Rejected - warnings get ignored, security bypasses become permanent
3. **Certificate Pinning**: Rejected - operational complexity, breaks with cert rotation

**Implementation Details**:
```python
@field_validator("jwks_uri")
@classmethod
def validate_https_jwks(cls, v: str | None) -> str | None:
    if v is None:
        return v

    if v.startswith("https://"):
        return v

    # Allow localhost for development
    if v.startswith(("http://localhost", "http://127.0.0.1")):
        import os
        if os.getenv("ENVIRONMENT") == "production":
            raise ValueError("Cannot use HTTP localhost in production")
        logger.warning(f"Using HTTP JWKS URI in development: {v}")
        return v

    raise ValueError(f"JWKS URI must use HTTPS (got: {v})")
```

### 7. Pydantic SecretStr for Credentials

**Decision**: Use `pydantic.SecretStr` for all sensitive configuration values

**Rationale**:
- **String Representation Safety**: `str(secret)` returns `"**********"`, prevents accidental logging
- **Explicit Access**: Requires `.get_secret_value()` to access plaintext, makes credential handling visible
- **Type System Integration**: Pydantic automatically handles SecretStr in model validation
- **Best Practice**: Recommended by Pydantic docs for passwords, API keys, tokens

**Alternatives Considered**:
1. **Plain Strings**: Rejected - easy to accidentally log, no protection against `str()` calls
2. **Custom Wrapper Class**: Rejected - reinventing Pydantic's solution, less ecosystem support
3. **Environment Variables Only**: Rejected - still need protection when loaded into memory

**Implementation Details**:
```python
from pydantic import SecretStr

class IntrospectionVerifierConfig(BaseModel):
    client_secret: SecretStr  # Not str

    # Usage
    async def introspect(self, token: str):
        auth = (self.client_id, self.client_secret.get_secret_value())  # Explicit access
```

### 8. Generic Error Messages (Information Disclosure Prevention)

**Decision**: Two-tier logging - detailed server logs, generic client responses

**Rationale**:
- **Security**: Prevent attackers learning expected issuer, audience, algorithm from error messages
- **Debugging**: Server logs retain full context for ops/security teams
- **Compliance**: Follows OWASP API Security best practices for error handling
- **User Experience**: Clients still get actionable error codes ("invalid_token", "insufficient_scope")

**Alternatives Considered**:
1. **Detailed Client Errors**: Rejected - leaks configuration, aids token forgery attempts
2. **No Logging**: Rejected - impossible to debug authentication issues
3. **Obfuscated Errors**: Rejected - confusing for legitimate users, still leaks info through timing

**Implementation Details**:
```python
except jwt.InvalidIssuerError:
    logger.warning(f"Invalid issuer. Expected: {self.config.issuer}")  # Detailed server log
    return ValidationResult.failure_result(
        error="invalid_token",  # Generic OAuth error code
        error_description="Token validation failed",  # No config details
    )
```

## Performance Considerations

### Latency Budget

| Operation | Target | Rationale |
|-----------|--------|-----------|
| Rate limit check | <5ms | In-memory hash lookup + timestamp comparison |
| Secret cache hit | <10ms | In-memory dict lookup |
| Secret cache miss | <300ms | Secret Manager API call (Google-hosted, low latency) |
| JWT verification (JWKS cached) | <50ms | Cryptographic signature verification |
| JWT verification (JWKS fetch) | <500ms | External HTTPS call to JWKS endpoint |
| Introspection | <200ms | External HTTPS call to introspection endpoint |
| **Total p95 (cached)** | **<100ms** | Sum of common path (rate limit + secret cache + JWT verify) |

### Memory Usage

| Component | Estimated Usage | Cleanup Strategy |
|-----------|-----------------|------------------|
| Rate limiter | ~100 bytes per unique token | Automatic expiration after window duration |
| Secret cache | ~1KB per secret | TTL-based expiration (300s default) |
| JWKS cache | ~5KB per key set | PyJWT library handles caching (3600s TTL) |
| **Per-instance total** | <1MB for 1000 active users | Background cleanup tasks |

## Security Analysis

### Threat Model

| Threat | Mitigation | Verification |
|--------|------------|--------------|
| Algorithm confusion attack | Whitelist validation, JWKS≠HMAC enforcement | Security tests attempt HS256 attack on RS256 config |
| Weak HMAC keys | Multi-layer key validation (length, entropy, patterns) | Startup fails with weak keys, tests verify rejection |
| Token logging exposure | SHA-256 hashing all token references | Audit all log statements, grep for token patterns |
| Brute force attacks | Rate limiting (10 attempts / 60s per token hash) | Load tests verify 11th attempt returns 429 |
| MITM on JWKS/introspection | HTTPS enforcement with certificate validation | Config tests verify HTTP URLs rejected in production |
| Secret exposure in logs | Pydantic SecretStr for all credentials | Tests verify `str(config)` doesn't contain secrets |
| Information disclosure | Generic client errors, detailed server logs | Error message tests verify no config leakage |
| DoS via unbounded caching | TTL-based expiration, automatic cleanup | Memory leak tests over 24 hours |

### Compliance Matrix

| Requirement | Implementation | Verification Method |
|-------------|----------------|---------------------|
| MCP 2025-03-26 OAuth 2.1 | Resource server pattern, bearer token validation | Compliance tests against spec checklist |
| OWASP API Security Top 10 | Rate limiting, strong authentication, no info disclosure | Security audit verification tests |
| OAuth 2.1 Section 5.2 | JWT signature, expiration, audience validation | Token validation tests |
| RFC 7662 (Introspection) | POST with Basic Auth, active flag checking | Introspection mock tests |
| RFC 7517 (JWKS) | Automatic key fetch, rotation handling | JWKS client integration tests |

## Dependency Analysis

### New Dependencies

```toml
[dependencies]
google-cloud-secret-manager = ">=2.16.0"  # Secret Manager integration
python-dotenv = ">=1.0.0"  # .env file support for development

[dev-dependencies]
pytest-httpx = ">=0.22.0"  # Already exists - mock introspection endpoints
```

### Version Constraints

- **google-cloud-secret-manager**: >=2.16.0 for async support and latest security patches
- **python-dotenv**: >=1.0.0 for reliable .env parsing
- **PyJWT**: >=2.8.0 (existing) includes CVE-2022-29217 fix
- **cryptography**: >=41.0.0 (existing) for secure key operations
- **httpx**: >=0.25.0 (existing) for async HTTP with timeout support

## Best Practices Applied

### 1. Defense in Depth
- **Multiple Layers**: Algorithm whitelist + length validation + pattern detection + HTTPS enforcement
- **Fail Secure**: Invalid configuration prevents server startup
- **Least Privilege**: Secret Manager IAM roles grant minimum required access

### 2. Principle of Least Surprise
- **Pydantic Validation**: Configuration errors caught at definition time
- **Type Safety**: SecretStr explicitly marks sensitive data
- **Clear Error Messages**: Developers understand what's wrong and how to fix it

### 3. Operational Excellence
- **Observability**: Detailed server logging with correlation via token hashes
- **Debuggability**: Two-tier logging preserves context for ops teams
- **Testability**: All security controls have dedicated test suites

### 4. Zero Trust
- **Verify Everything**: Signatures, expiration, audience, issuer, scopes
- **No Implicit Trust**: HTTPS required, certificate validation enforced
- **Audit Trail**: All authentication attempts logged with outcomes

## Development Workflow

### Local Development Setup

1. Create `.env` file with test configuration:
```bash
FASTMCP_SERVER_AUTH_TYPE=jwt
FASTMCP_SERVER_AUTH_SECRET_BACKEND=env
FASTMCP_SERVER_AUTH_JWT_JWKS_URI=http://localhost:8080/.well-known/jwks.json
FASTMCP_SERVER_AUTH_JWT_ISSUER=test-issuer
FASTMCP_SERVER_AUTH_JWT_AUDIENCE=test-audience
ENVIRONMENT=development
```

2. Run local OAuth server for testing (optional):
```bash
# Use tools like mock-oauth2-server or keycloak
docker run -p 8080:8080 navikt/mock-oauth2-server
```

3. Test with MCP Inspector:
```bash
fastmcp dev server.py
# Inspector opens automatically at localhost:6274
```

### Production Deployment Checklist

1. ✅ Create secrets in Google Cloud Secret Manager
2. ✅ Grant Cloud Run service account `roles/secretmanager.secretAccessor`
3. ✅ Set `FASTMCP_SERVER_AUTH_SECRET_BACKEND=gcp_secret_manager`
4. ✅ Set `ENVIRONMENT=production`
5. ✅ Verify HTTPS enforcement (no localhost URLs)
6. ✅ Configure real JWKS URI from Identity Provider
7. ✅ Set proper audience value (MCP server resource identifier)
8. ✅ Enable Cloud Logging for audit trail
9. ✅ Monitor rate limiting metrics
10. ✅ Test with production OAuth tokens

## Testing Strategy

### Test Pyramid

```
         ┌─────────────┐
         │  Security   │ ← Algorithm confusion, rate limits, token logging
         │   Tests     │
         ├─────────────┤
         │ Integration │ ← OAuth 2.1 compliance, Secret Manager, JWKS
         │   Tests     │
         ├─────────────┤
         │    Unit     │ ← Token parsing, validation logic, config loading
         │   Tests     │
         └─────────────┘
```

### Coverage Requirements

- **Line Coverage**: 80% minimum (existing standard)
- **Branch Coverage**: 70% minimum
- **Security Tests**: 100% coverage of audit findings
- **Error Paths**: 100% coverage

### Key Test Scenarios

1. **Algorithm Confusion**: Attempt HS256 signature with RS256 public key
2. **Rate Limiting**: 11 consecutive invalid token attempts
3. **Token Logging**: Grep logs for plaintext tokens (should find zero)
4. **Secret Rotation**: Verify cache refresh after TTL
5. **JWKS Rotation**: Handle key ID changes gracefully
6. **HTTPS Enforcement**: Reject http:// URLs in production
7. **Weak Keys**: Startup fails with short/weak HMAC keys
8. **Generic Errors**: Client errors don't leak config details

## Migration Path

### From Existing Implementation

**No breaking changes** - this is enhancement, not replacement:

1. Existing `src/auth/` modules remain functional
2. New security features added via:
   - Enhanced Pydantic validators
   - New `rate_limiter.py` module
   - New `secrets.py` module
3. Backward compatible with existing FastMCP AuthProvider interface
4. Opt-in Secret Manager (environment variable config)
5. Existing test suite continues passing

### Rollout Strategy

1. **Phase 1**: Deploy with Secret Manager disabled (env vars only)
2. **Phase 2**: Enable rate limiting with high limits (monitoring)
3. **Phase 3**: Tune rate limits based on traffic patterns
4. **Phase 4**: Migrate secrets to Secret Manager
5. **Phase 5**: Enable all security hardening features

## Open Questions

**None** - All technical unknowns have been resolved through research. Implementation can proceed.

## References

- [MCP 2025-03-26 Specification](https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization)
- [OAuth 2.1 Draft](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-07)
- [RFC 7662 - Token Introspection](https://datatracker.ietf.org/doc/html/rfc7662)
- [RFC 7517 - JSON Web Key (JWK)](https://datatracker.ietf.org/doc/html/rfc7517)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [Google Cloud Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Pydantic SecretStr Documentation](https://docs.pydantic.dev/latest/api/types/#pydantic.types.SecretStr)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
