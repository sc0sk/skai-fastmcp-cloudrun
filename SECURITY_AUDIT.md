# Security Audit Report: Token Authentication Implementation

**Date**: 2025-10-24
**Scope**: Token verification and authentication system for FastMCP server
**Auditor**: Claude (Automated Security Review)

## Executive Summary

The token authentication implementation is **generally secure** with good security practices in place. However, there are **several critical issues** and **recommended improvements** that should be addressed before production deployment.

### Risk Rating: 🟡 MODERATE RISK
- ✅ Strong cryptographic implementation (PyJWT with cryptography backend)
- ✅ Proper signature verification enforced
- ✅ Good input validation and error handling
- ⚠️ **CRITICAL**: Algorithm confusion vulnerability exists
- ⚠️ Secret exposure risks in logging and error messages
- ⚠️ Missing rate limiting could enable DoS attacks
- ⚠️ HTTPS enforcement only partially implemented

---

## Critical Security Issues

### 🔴 CRITICAL #1: Algorithm Confusion Vulnerability

**File**: [src/auth/jwt.py:90-96](src/auth/jwt.py#L90-L96)

**Issue**: The JWT verifier accepts the algorithm specified in configuration but doesn't validate it matches the token's header. This enables the "algorithm confusion" attack where an attacker can:
1. Take a valid RS256 JWT signed with a private key
2. Change the algorithm to HS256
3. Use the public key (which they know) as the HMAC secret
4. The server will accept it because it uses the public key to verify HMAC

**Current Code**:
```python
decoded = jwt.decode(
    token,
    verification_key,
    algorithms=[self.config.algorithm],  # ⚠️ Only checks configured algorithm
    audience=self.config.audience,
    issuer=self.config.issuer,
    leeway=self.config.clock_skew,
)
```

**Attack Scenario**:
```python
# Attacker obtains valid RS256 token and public key
# Creates malicious HS256 token using public key as HMAC secret
malicious_token = jwt.encode(
    {"sub": "admin", "scope": "admin"},
    public_key_pem,  # Using public key as HMAC secret
    algorithm="HS256"
)
# Server accepts it if algorithm="HS256" in config
```

**Recommendation**:
```python
# Option 1: Explicitly whitelist safe algorithms
SAFE_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]

@model_validator(mode="after")
def validate_algorithm(self) -> "JWTVerifierConfig":
    if self.algorithm not in SAFE_ALGORITHMS:
        raise ValueError(f"Algorithm {self.algorithm} not allowed. Use: {SAFE_ALGORITHMS}")
    # Never allow HMAC with JWKS
    if self.jwks_uri and self.algorithm.startswith("HS"):
        raise ValueError("HMAC algorithms cannot be used with JWKS endpoints")
    return self

# Option 2: Separate verifier classes for asymmetric vs symmetric
class AsymmetricJWTVerifier(TokenVerifier):
    ALLOWED_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]

class SymmetricJWTVerifier(TokenVerifier):
    ALLOWED_ALGORITHMS = ["HS256", "HS384", "HS512"]
```

**Severity**: 🔴 **CRITICAL** - Could allow complete authentication bypass

---

### 🔴 CRITICAL #2: HMAC Key Length Validation Insufficient

**File**: [src/models/auth.py:153-163](src/models/auth.py#L153-L163)

**Issue**: While HMAC key length is validated, the validation uses byte length of the string, not the actual entropy. A 32-byte string like `"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` passes validation but has very low entropy.

**Current Code**:
```python
if len(self.public_key.encode()) < min_length:
    raise ValueError(f"HMAC key for {self.algorithm} must be at least {min_length} bytes")
```

**Recommendation**:
```python
import secrets

@model_validator(mode="after")
def validate_hmac_key_strength(self) -> "JWTVerifierConfig":
    if self.algorithm.startswith("HS") and self.public_key:
        min_lengths = {"HS256": 32, "HS384": 48, "HS512": 64}
        min_length = min_lengths.get(self.algorithm, 32)

        key_bytes = self.public_key.encode()

        # Check length
        if len(key_bytes) < min_length:
            raise ValueError(f"HMAC key must be at least {min_length} bytes")

        # Warn if key appears to be base64-encoded (common mistake)
        import base64
        try:
            decoded = base64.b64decode(key_bytes)
            if len(decoded) < min_length:
                raise ValueError(
                    f"Base64-decoded HMAC key is only {len(decoded)} bytes. "
                    f"Use a longer base64-encoded key or raw {min_length}+ byte secret"
                )
        except Exception:
            pass  # Not base64, continue

        # Check for obvious weak keys
        weak_patterns = [b'a' * min_length, b'1' * min_length, b'test', b'secret']
        if any(pattern in key_bytes for pattern in weak_patterns):
            raise ValueError("HMAC key appears to be a test/weak value. Use cryptographically random key.")

    return self

# Also add key generation helper
@staticmethod
def generate_hmac_secret(algorithm: str = "HS256") -> str:
    """Generate cryptographically secure HMAC secret"""
    min_lengths = {"HS256": 32, "HS384": 48, "HS512": 64}
    length = min_lengths.get(algorithm, 32)
    return secrets.token_urlsafe(length)
```

**Severity**: 🔴 **CRITICAL** - Weak keys could be brute-forced

---

## High Severity Issues

### 🟠 HIGH #1: Secret Exposure in Logs

**Files**: Multiple locations

**Issue**: Token strings and potentially sensitive claims are logged at INFO level:
- [src/auth/jwt.py:120](src/auth/jwt.py#L120): `logger.info(f"Successfully validated JWT token for identity: {claims.identity}")`
- [src/auth/jwt.py:243](src/auth/jwt.py#L243): `logger.warning(f"Unknown static token: {token[:10]}...")`

**Risk**:
- Tokens in logs could be extracted and replayed
- Log aggregation systems may have weaker security than production
- Partial tokens (`token[:10]`) may still aid attackers

**Recommendation**:
```python
import hashlib

def _hash_token(token: str) -> str:
    """Create non-reversible token hash for logging"""
    return hashlib.sha256(token.encode()).hexdigest()[:16]

# Use in logging
logger.info(f"Successfully validated JWT token (hash: {self._hash_token(token)}) for identity: {claims.identity}")
logger.warning(f"Unknown static token (hash: {self._hash_token(token)})")
```

**Severity**: 🟠 **HIGH** - Could lead to credential theft from logs

---

### 🟠 HIGH #2: No Rate Limiting on Token Verification

**Files**: All verifiers lack rate limiting

**Issue**: No protection against brute-force token guessing or DoS attacks via:
- Repeated JWT verification (CPU-intensive signature checks)
- Introspection endpoint flooding
- Static token enumeration

**Recommendation**:
```python
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

class RateLimiter:
    """Token-bucket rate limiter for authentication attempts"""

    def __init__(self, max_attempts: int = 10, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window = timedelta(seconds=window_seconds)
        self.attempts: dict[str, list[datetime]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check_rate_limit(self, identifier: str) -> bool:
        """Check if identifier is within rate limit"""
        async with self._lock:
            now = datetime.now()
            cutoff = now - self.window

            # Remove old attempts
            self.attempts[identifier] = [
                t for t in self.attempts[identifier] if t > cutoff
            ]

            # Check limit
            if len(self.attempts[identifier]) >= self.max_attempts:
                return False

            self.attempts[identifier].append(now)
            return True

# Add to TokenVerifier base class
class TokenVerifier(ABC):
    def __init__(self):
        self._rate_limiter = RateLimiter(max_attempts=10, window_seconds=60)

    async def verify(self, token: str) -> ValidationResult:
        # Rate limit by token hash
        token_id = hashlib.sha256(token.encode()).hexdigest()[:16]

        if not await self._rate_limiter.check_rate_limit(token_id):
            logger.warning(f"Rate limit exceeded for token hash: {token_id}")
            return ValidationResult.failure_result(
                error="rate_limit_exceeded",
                error_description="Too many authentication attempts. Try again later.",
                error_code=429
            )

        return await self._verify_impl(token)

    @abstractmethod
    async def _verify_impl(self, token: str) -> ValidationResult:
        """Implementation-specific verification logic"""
        pass
```

**Severity**: 🟠 **HIGH** - Enables DoS and brute-force attacks

---

### 🟠 HIGH #3: Missing HTTPS Enforcement for JWKS

**File**: [src/auth/jwt.py:51-56](src/auth/jwt.py#L51-L56)

**Issue**: JWKS URIs are not validated to use HTTPS. An attacker performing MITM could serve malicious public keys.

**Current Code**:
```python
if config.jwks_uri:
    self._jwks_client = PyJWKClient(
        config.jwks_uri,  # ⚠️ No HTTPS validation
        lifespan=config.jwks_cache_ttl,
        cache_keys=True,
    )
```

**Recommendation**:
```python
@field_validator("jwks_uri")
@classmethod
def validate_jwks_uri(cls, v: str | None) -> str | None:
    if v is None:
        return v

    # Require HTTPS except for localhost development
    if not v.startswith("https://"):
        if not (v.startswith("http://localhost") or v.startswith("http://127.0.0.1")):
            raise ValueError(
                "JWKS URI must use HTTPS in production. "
                "Only http://localhost is allowed for development."
            )

        # Warn about localhost usage
        import os
        if os.getenv("ENVIRONMENT", "development") == "production":
            raise ValueError("Cannot use http://localhost JWKS URI in production")

    return v
```

**Severity**: 🟠 **HIGH** - MITM could bypass authentication

---

## Medium Severity Issues

### 🟡 MEDIUM #1: Introspection Credentials in Environment Variables

**File**: [src/models/auth.py:236-259](src/models/auth.py#L236-L259)

**Issue**: Client secrets loaded from environment variables are logged and may appear in error messages.

**Recommendation**:
```python
# Use SecretStr to prevent accidental logging
from pydantic import SecretStr

class IntrospectionVerifierConfig(BaseModel):
    client_secret: SecretStr = Field(...)  # SecretStr instead of str

    @classmethod
    def from_env(cls) -> "IntrospectionVerifierConfig":
        client_secret = os.getenv("FASTMCP_SERVER_AUTH_INTROSPECTION_CLIENT_SECRET")
        if not client_secret:
            raise ValueError("FASTMCP_SERVER_AUTH_INTROSPECTION_CLIENT_SECRET is required")

        return cls(
            client_secret=SecretStr(client_secret),  # Wrap in SecretStr
            ...
        )

# Update introspection.py usage
async def verify(self, token: str) -> ValidationResult:
    response = await client.post(
        self.config.introspection_url,
        data={"token": token},
        auth=(self.config.client_id, self.config.client_secret.get_secret_value()),  # Extract value
        ...
    )
```

**Severity**: 🟡 **MEDIUM** - Credential exposure in logs/errors

---

### 🟡 MEDIUM #2: Clock Skew Too Permissive

**File**: [src/models/auth.py:136-138](src/models/auth.py#L136-L138)

**Issue**: Clock skew allows up to 300 seconds (5 minutes). This is excessive and could allow replay of expired tokens.

**Recommendation**:
```python
clock_skew: int = Field(
    60,
    description="Clock skew tolerance in seconds",
    ge=0,
    le=120  # Reduce from 300 to 120 (2 minutes max)
)
```

**Severity**: 🟡 **MEDIUM** - Extended token replay window

---

### 🟡 MEDIUM #3: No Token Binding

**Issue**: Tokens are not bound to specific clients/sessions. A stolen token can be used from any IP/client.

**Recommendation**:
```python
# Add token binding support
class TokenClaims(BaseModel):
    # ... existing fields ...

    # Token binding (DPoP, mTLS certificate hash, etc.)
    confirmation: dict[str, Any] | None = Field(
        None,
        description="Token binding confirmation (cnf claim for DPoP/mTLS)"
    )

# In verifier
async def verify(self, token: str, client_cert_hash: str | None = None) -> ValidationResult:
    # ... decode token ...

    # Verify certificate binding if present
    if claims.confirmation and "x5t#S256" in claims.confirmation:
        expected_cert_hash = claims.confirmation["x5t#S256"]
        if client_cert_hash != expected_cert_hash:
            return ValidationResult.failure_result(
                error="invalid_token",
                error_description="Token certificate binding validation failed"
            )
```

**Severity**: 🟡 **MEDIUM** - Stolen tokens fully usable

---

## Low Severity Issues

### 🟢 LOW #1: RSAKeyPair Exports Unencrypted Private Keys

**File**: [src/auth/jwt.py:295-301](src/auth/jwt.py#L295-L301)

**Issue**: Private keys exported without encryption. If accidentally logged or stored, they're fully exposed.

**Recommendation**:
```python
@property
def private_key_pem(self) -> str:
    """Export private key as PEM string (UNENCRYPTED - FOR TESTING ONLY)"""
    # Add warning comment and runtime check
    import os
    if os.getenv("ENVIRONMENT") == "production":
        raise RuntimeError(
            "RSAKeyPair.private_key_pem should not be used in production. "
            "This exports unencrypted private keys for testing only."
        )

    return self.private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),  # Still unencrypted for testing
    ).decode()
```

**Severity**: 🟢 **LOW** - Development utility only

---

### 🟢 LOW #2: StaticTokenVerifier Production Check is Bypassable

**File**: [src/models/auth.py:277-285](src/models/auth.py#L277-L285)

**Issue**: Production check relies on `ENVIRONMENT` variable which could be unset or misconfigured.

**Recommendation**:
```python
@model_validator(mode="after")
def prevent_production_use(self) -> "StaticTokenVerifierConfig":
    """Prevent usage in production environments"""
    env = os.getenv("ENVIRONMENT", "development").lower()

    # Multiple signals to detect production
    production_signals = [
        env in ("production", "prod"),
        os.getenv("FASTMCP_SERVER_AUTH_TYPE") == "static",  # Explicit signal
        os.getenv("KUBERNETES_SERVICE_HOST"),  # Running in k8s
        os.getenv("CLOUD_RUN_SERVICE"),  # Cloud Run
    ]

    if any(production_signals):
        raise ValueError(
            "StaticTokenVerifier detected in production environment. "
            "Use JWTVerifier or IntrospectionTokenVerifier instead."
        )

    return self
```

**Severity**: 🟢 **LOW** - Multiple warnings already present

---

## Information Disclosure Issues

### 🟡 MEDIUM #4: Detailed Error Messages

**Files**: Multiple locations

**Issue**: Error messages reveal too much about system internals:
- [src/auth/jwt.py:138](src/auth/jwt.py#L138): `"Invalid issuer. Expected: {self.config.issuer}"`
- [src/auth/jwt.py:132](src/auth/jwt.py#L132): `"Invalid audience. Expected: {self.config.audience}"`

**Risk**: Helps attackers understand expected values for token forgery.

**Recommendation**:
```python
# Generic error messages for clients
except jwt.InvalidIssuerError:
    logger.warning(f"Invalid issuer. Expected: {self.config.issuer}")  # Keep detailed server log
    return ValidationResult.failure_result(
        error="invalid_token",
        error_description="Token validation failed",  # Generic client message
    )

except jwt.InvalidAudienceError:
    logger.warning(f"Invalid audience. Expected: {self.config.audience}")
    return ValidationResult.failure_result(
        error="invalid_token",
        error_description="Token validation failed",  # Don't reveal expected audience
    )
```

**Severity**: 🟡 **MEDIUM** - Information leakage aids attacks

---

## Dependency Security

### ✅ Dependencies Are Secure

**Reviewed**:
- `PyJWT[crypto]>=2.8.0` - Good (includes CVE-2022-29217 fix)
- `cryptography>=41.0.0` - Good (recent version)
- `httpx>=0.25.0` - Good (supports HTTP/2, modern)

**Recommendation**:
```toml
# Pin to specific versions for reproducibility
dependencies = [
    "PyJWT[crypto]~=2.8.0",  # Allow patch updates only
    "cryptography~=41.0.0",
    "httpx~=0.25.0",
]

# Add dependency scanning
[tool.pip-audit]
require-hashes = true
```

---

## Positive Security Findings ✅

The implementation includes many good security practices:

1. ✅ **Signature verification enforced** - `verify_signature: True` explicitly set
2. ✅ **Expiration validation** - `verify_exp: True`
3. ✅ **Audience validation** - `verify_aud: True`
4. ✅ **Issuer validation** - `verify_iss: True`
5. ✅ **Scope-based authorization** - Proper scope checking before granting access
6. ✅ **Comprehensive exception handling** - All JWT exceptions caught and handled
7. ✅ **JWKS caching** - Reduces attack surface for DoS on JWKS endpoint
8. ✅ **Input validation** - Pydantic models validate all configuration
9. ✅ **Secure defaults** - RS256 default algorithm, 60s clock skew
10. ✅ **Introspection uses Basic Auth** - Not bearer token in query string
11. ✅ **No token in URL** - Properly uses Authorization header
12. ✅ **HTTPs validation for introspection** - Lines 229-233 in auth.py
13. ✅ **Timeout on introspection** - Prevents hanging requests
14. ✅ **Production guards** - StaticTokenVerifier warns against production use

---

## Recommended Security Enhancements

### Priority 1 (Critical - Fix Before Production)
1. ✅ Fix algorithm confusion vulnerability
2. ✅ Enhance HMAC key validation
3. ✅ Remove tokens from logs (use hashes)
4. ✅ Add HTTPS validation for JWKS URIs
5. ✅ Implement rate limiting

### Priority 2 (High - Fix Soon)
6. ✅ Use SecretStr for credentials
7. ✅ Reduce max clock skew to 120s
8. ✅ Generic error messages (don't leak config)

### Priority 3 (Medium - Consider for v2)
9. Token binding support (DPoP/mTLS)
10. Token revocation list support
11. Audit logging (separate from debug logs)
12. Monitoring/alerting for auth failures

### Priority 4 (Nice to Have)
13. JWT claim constraints (max scope, max lifetime)
14. Multi-tenancy support (issuer per tenant)
15. Webhook validation for custom auth

---

## Production Readiness Checklist

Before deploying to production:

- [ ] Fix algorithm confusion (CRITICAL)
- [ ] Fix HMAC key validation (CRITICAL)
- [ ] Remove tokens from logs (HIGH)
- [ ] Add HTTPS enforcement (HIGH)
- [ ] Implement rate limiting (HIGH)
- [ ] Use SecretStr for secrets (MEDIUM)
- [ ] Reduce clock skew max (MEDIUM)
- [ ] Generic error messages (MEDIUM)
- [ ] Set `ENVIRONMENT=production` variable
- [ ] Disable `DANGEROUSLY_OMIT_AUTH` flag
- [ ] Configure real JWT/introspection endpoint
- [ ] Test with production auth server
- [ ] Set up monitoring/alerting
- [ ] Document incident response procedures
- [ ] Perform penetration testing

---

## Testing Recommendations

Add security-specific tests:

```python
# tests/security/test_algorithm_confusion.py
async def test_algorithm_confusion_attack():
    """Verify RS256 token cannot be verified as HS256 using public key"""
    key_pair = RSAKeyPair.generate()

    # Create valid RS256 token
    token = key_pair.create_token(...)

    # Try to verify as HS256 using public key as secret
    config = JWTVerifierConfig(
        public_key=key_pair.public_key_pem,  # Using public key as HMAC secret
        algorithm="HS256",  # Changed algorithm
        issuer="test",
        audience="test"
    )

    verifier = JWTVerifier(config)
    result = await verifier.verify(token)

    # Should FAIL - not accept algorithm confusion
    assert result.success is False

# tests/security/test_rate_limiting.py
async def test_brute_force_protection():
    """Verify rate limiting blocks brute force attempts"""
    verifier = StaticTokenVerifier(...)

    # Attempt 11 failed authentications
    for i in range(11):
        result = await verifier.verify("invalid-token")

    # Should be rate limited
    assert result.error == "rate_limit_exceeded"
    assert result.error_code == 429

# tests/security/test_secret_exposure.py
def test_secrets_not_in_repr():
    """Verify secrets don't appear in string representation"""
    config = IntrospectionVerifierConfig(
        client_secret=SecretStr("super-secret"),
        ...
    )

    config_str = str(config)
    assert "super-secret" not in config_str
    assert "**********" in config_str or "SecretStr" in config_str
```

---

## Conclusion

The token authentication implementation demonstrates **strong foundational security** with proper cryptographic validation and good defensive programming practices. However, **critical vulnerabilities exist** (algorithm confusion, weak HMAC keys, no rate limiting) that **must be fixed before production deployment**.

With the recommended fixes applied, this implementation would be suitable for production use in a defense-in-depth security architecture.

**Overall Security Grade**: B- (would be A- with critical fixes applied)
