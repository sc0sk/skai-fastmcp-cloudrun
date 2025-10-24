# Quickstart: Token Verification

**Feature**: Token Verification
**Date**: 2025-10-23
**Audience**: Developers integrating token verification into FastMCP servers

## Overview

This quickstart guide covers the five main token verification scenarios:

1. **Production JWT with JWKS** - Validate tokens from OAuth providers with automatic key rotation
2. **HMAC Symmetric Keys** - Validate tokens in internal microservices with shared secrets
3. **Static Public Keys** - Validate tokens with fixed RSA/ECDSA keys (testing/constrained environments)
4. **OAuth Token Introspection** - Validate opaque tokens via RFC 7662 introspection endpoint
5. **Development Testing** - Static tokens and test key generation for local development

Each scenario includes setup instructions, code examples, and testing guidance.

---

## Scenario 1: Production JWT with JWKS Endpoint

**Use Case**: Integrate with enterprise OAuth providers (Okta, Auth0, Azure AD, Google) using automatic key rotation

### Step 1: Get OAuth Provider Information

Find your provider's JWKS endpoint and issuer information:

```bash
# Example: Okta (check your Okta admin console)
JWKS_URI=https://your-domain.okta.com/oauth2/default/v1/keys
ISSUER=https://your-domain.okta.com/oauth2/default

# Example: Auth0 (check your Auth0 tenant settings)
JWKS_URI=https://your-tenant.auth0.com/.well-known/jwks.json
ISSUER=https://your-tenant.auth0.com/

# Example: Google
JWKS_URI=https://www.googleapis.com/oauth2/v3/certs
ISSUER=https://accounts.google.com

# Example: Azure AD
JWKS_URI=https://login.microsoftonline.com/{tenant-id}/discovery/v2.0/keys
ISSUER=https://login.microsoftonline.com/{tenant-id}/v2.0
```

### Step 2: Configure Environment Variables

```bash
# .env file (local development)
FASTMCP_SERVER_AUTH_JWT_JWKS_URI=https://auth.yourcompany.com/.well-known/jwks.json
FASTMCP_SERVER_AUTH_JWT_ISSUER=https://auth.yourcompany.com
FASTMCP_SERVER_AUTH_JWT_AUDIENCE=mcp-production-api
FASTMCP_SERVER_AUTH_JWT_REQUIRED_SCOPES=api:read,api:write
FASTMCP_SERVER_AUTH_JWT_CLOCK_SKEW=60
```

### Step 3: Enable JWT Verification in FastMCP Server

```python
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier

# Option A: Explicit configuration
verifier = JWTVerifier(
    jwks_uri="https://auth.yourcompany.com/.well-known/jwks.json",
    issuer="https://auth.yourcompany.com",
    audience="mcp-production-api",
    required_scopes=["api:read", "api:write"]
)

mcp = FastMCP(name="Protected API", auth=verifier)

# Option B: Load from environment (recommended for production)
verifier = JWTVerifier.from_env()
mcp = FastMCP(name="Protected API", auth=verifier)
```

### Step 4: Test with Real Token

```bash
# Get token from your OAuth provider (varies by provider)
# Example: Use OAuth2 client credentials flow

# Test the MCP server
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     http://localhost:8080/mcp/

# Or using MCP Inspector
fastmcp dev src/server.py
# Inspector will prompt for credentials on first request
```

### Step 5: Deploy to Cloud Run

```bash
# Store secrets in Google Secret Manager
echo -n "https://auth.yourcompany.com/.well-known/jwks.json" | \
  gcloud secrets create jwt-jwks-uri --data-file=-

echo -n "https://auth.yourcompany.com" | \
  gcloud secrets create jwt-issuer --data-file=-

echo -n "mcp-production-api" | \
  gcloud secrets create jwt-audience --data-file=-

# Deploy with secrets
gcloud run deploy my-mcp-server \
  --set-secrets=FASTMCP_SERVER_AUTH_JWT_JWKS_URI=jwt-jwks-uri:latest \
  --set-secrets=FASTMCP_SERVER_AUTH_JWT_ISSUER=jwt-issuer:latest \
  --set-secrets=FASTMCP_SERVER_AUTH_JWT_AUDIENCE=jwt-audience:latest \
  --set-env-vars=FASTMCP_SERVER_AUTH_JWT_REQUIRED_SCOPES=api:read,api:write
```

**Expected Behavior**:
- ✅ Valid tokens with correct issuer/audience → access granted
- ❌ Expired tokens → 401 with "Token has expired"
- ❌ Wrong signature → 401 with "Token signature verification failed"
- ❌ Wrong audience → 401 with "Invalid audience"
- ❌ Missing required scopes → 401 with "Insufficient scope"

---

## Scenario 2: HMAC Symmetric Keys (Internal Microservices)

**Use Case**: Authenticate internal services using shared secrets without complex PKI infrastructure

### Step 1: Generate Strong Shared Secret

```python
# Generate cryptographically secure secret
import secrets

# For HS256: 32 bytes minimum
secret_hs256 = secrets.token_urlsafe(32)
print(f"HS256 Secret: {secret_hs256}")

# For HS384: 48 bytes minimum
secret_hs384 = secrets.token_urlsafe(48)
print(f"HS384 Secret: {secret_hs384}")

# For HS512: 64 bytes minimum
secret_hs512 = secrets.token_urlsafe(64)
print(f"HS512 Secret: {secret_hs512}")
```

### Step 2: Configure Environment Variables

```bash
# .env file
FASTMCP_SERVER_AUTH_JWT_PUBLIC_KEY=your-shared-secret-minimum-32-chars
FASTMCP_SERVER_AUTH_JWT_ALGORITHM=HS256
FASTMCP_SERVER_AUTH_JWT_ISSUER=internal-auth-service
FASTMCP_SERVER_AUTH_JWT_AUDIENCE=mcp-internal-api
```

### Step 3: Configure MCP Server

```python
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier

verifier = JWTVerifier(
    public_key="your-shared-secret-minimum-32-chars",  # Same secret for signing and validation
    issuer="internal-auth-service",
    audience="mcp-internal-api",
    algorithm="HS256"
)

mcp = FastMCP(name="Internal API", auth=verifier)
```

### Step 4: Create Tokens in Other Services

```python
import jwt
from datetime import datetime, timedelta

# In your authentication service or other microservices
secret = "your-shared-secret-minimum-32-chars"

token = jwt.encode(
    {
        "iss": "internal-auth-service",
        "aud": "mcp-internal-api",
        "sub": "service-123",
        "client_id": "billing-service",
        "scope": "api:read api:write",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow()
    },
    secret,
    algorithm="HS256"
)

print(f"Token: {token}")
```

### Step 5: Test the Integration

```bash
# Use the generated token
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
     http://localhost:8080/mcp/
```

**Security Warning**:
- ⚠️ Store shared secrets securely (Secret Manager, not environment files in production)
- ⚠️ Rotate secrets regularly (every 90 days recommended)
- ⚠️ Never commit secrets to version control
- ⚠️ Use HTTPS/TLS for all communication

---

## Scenario 3: Static Public Keys (Fixed RSA/ECDSA)

**Use Case**: Controlled environments where JWKS endpoints aren't available or key rotation isn't needed

### Step 1: Generate RSA Key Pair

```python
from fastmcp.server.auth.providers.jwt import RSAKeyPair

# Generate 2048-bit RSA key pair
key_pair = RSAKeyPair.generate(key_size=2048)

# Export keys
print("Private Key (keep secret):")
print(key_pair.private_key_pem)

print("\nPublic Key (configure in MCP server):")
print(key_pair.public_key_pem)
```

### Step 2: Configure MCP Server with Public Key

```python
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier

public_key_pem = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----"""

verifier = JWTVerifier(
    public_key=public_key_pem,
    issuer="https://auth.yourcompany.com",
    audience="mcp-production-api"
)

mcp = FastMCP(name="Protected API", auth=verifier)
```

### Step 3: Sign Tokens with Private Key

```python
import jwt
from datetime import datetime, timedelta

private_key_pem = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...
-----END PRIVATE KEY-----"""

token = jwt.encode(
    {
        "iss": "https://auth.yourcompany.com",
        "aud": "mcp-production-api",
        "sub": "user-123",
        "scope": "read write",
        "exp": datetime.utcnow() + timedelta(hours=1),
    },
    private_key_pem,
    algorithm="RS256"
)

print(f"Token: {token}")
```

### Step 4: Test Verification

```bash
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     http://localhost:8080/mcp/
```

**Key Rotation**:
When rotating keys:
1. Generate new key pair
2. Update server configuration with new public key
3. Restart server
4. Update token generation service with new private key
5. Allow grace period for in-flight tokens (consider key overlap period)

---

## Scenario 4: OAuth Token Introspection (Opaque Tokens)

**Use Case**: Enterprise OAuth providers that issue opaque tokens with server-side state and immediate revocation

### Step 1: Get Introspection Endpoint Details

```bash
# Check your OAuth provider documentation
# Example: Okta
INTROSPECTION_URL=https://your-domain.okta.com/oauth2/default/v1/introspect

# Example: Auth0
INTROSPECTION_URL=https://your-tenant.auth0.com/oauth/introspect

# You'll also need client credentials for the MCP server
CLIENT_ID=mcp-resource-server
CLIENT_SECRET=your-client-secret
```

### Step 2: Configure Environment Variables

```bash
# .env file
FASTMCP_SERVER_AUTH_INTROSPECTION_URL=https://auth.yourcompany.com/oauth/introspect
FASTMCP_SERVER_AUTH_INTROSPECTION_CLIENT_ID=mcp-resource-server
FASTMCP_SERVER_AUTH_INTROSPECTION_CLIENT_SECRET=your-client-secret
FASTMCP_SERVER_AUTH_INTROSPECTION_REQUIRED_SCOPES=api:read,api:write
FASTMCP_SERVER_AUTH_INTROSPECTION_TIMEOUT=10
```

### Step 3: Configure MCP Server

```python
from fastmcp import FastMCP
from fastmcp.server.auth.providers.introspection import IntrospectionTokenVerifier

# Option A: Explicit configuration
verifier = IntrospectionTokenVerifier(
    introspection_url="https://auth.yourcompany.com/oauth/introspect",
    client_id="mcp-resource-server",
    client_secret="your-client-secret",
    required_scopes=["api:read", "api:write"]
)

mcp = FastMCP(name="Protected API", auth=verifier)

# Option B: Load from environment (recommended)
verifier = IntrospectionTokenVerifier.from_env()
mcp = FastMCP(name="Protected API", auth=verifier)
```

### Step 4: Test with Opaque Token

```bash
# Get opaque token from your OAuth provider
# (varies by provider - typically OAuth2 client credentials or authorization code flow)

# Test the MCP server
curl -H "Authorization: Bearer opaque-token-string" \
     http://localhost:8080/mcp/
```

### Step 5: Monitor Introspection Performance

```python
import logging

# Enable debug logging to monitor introspection latency
logging.basicConfig(level=logging.DEBUG)

# Expected: ~50-200ms per request (network latency to auth server)
# Consider caching if performance becomes an issue (cache introspection responses)
```

**Expected Behavior**:
- ✅ Active token → introspection returns `active=true` → access granted
- ❌ Revoked token → introspection returns `active=false` → 401 denied
- ❌ Invalid token → introspection returns `active=false` → 401 denied
- ❌ Introspection endpoint unreachable → 500 server error (fail closed)

---

## Scenario 5: Development Testing (Static Tokens & Test Keys)

**Use Case**: Local development and automated testing without external OAuth infrastructure

### Option A: Static Token Verification

**Best for**: Rapid prototyping, simple integration tests

```python
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

# Define development tokens and their claims
verifier = StaticTokenVerifier(
    tokens={
        "dev-alice-token": {
            "client_id": "alice@company.com",
            "scopes": ["read:data", "write:data", "admin:users"]
        },
        "dev-bob-token": {
            "client_id": "bob@company.com",
            "scopes": ["read:data"]
        },
        "dev-guest-token": {
            "client_id": "guest-user",
            "scopes": []
        }
    },
    required_scopes=["read:data"]
)

mcp = FastMCP(name="Development Server", auth=verifier)
```

**Testing**:
```bash
# Test as Alice (admin)
curl -H "Authorization: Bearer dev-alice-token" \
     http://localhost:8080/mcp/

# Test as Bob (read-only)
curl -H "Authorization: Bearer dev-bob-token" \
     http://localhost:8080/mcp/

# Test as Guest (no scopes - should fail if scopes required)
curl -H "Authorization: Bearer dev-guest-token" \
     http://localhost:8080/mcp/
```

**Security Warning**:
```python
# StaticTokenVerifier will fail if ENVIRONMENT=production
import os
os.environ["ENVIRONMENT"] = "production"

verifier = StaticTokenVerifier(tokens={...})
# Raises: ValueError("StaticTokenVerifier is for DEVELOPMENT ONLY")
```

### Option B: Test Key Pair Generation

**Best for**: Testing JWT validation logic with real cryptographic signatures

```python
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier, RSAKeyPair

# Generate test key pair
key_pair = RSAKeyPair.generate(key_size=2048)

# Configure server with public key
verifier = JWTVerifier(
    public_key=key_pair.public_key_pem,
    issuer="https://test.yourcompany.com",
    audience="test-mcp-server"
)

mcp = FastMCP(name="Test Server", auth=verifier)

# Generate test tokens
test_token_admin = key_pair.create_token(
    subject="test-admin",
    issuer="https://test.yourcompany.com",
    audience="test-mcp-server",
    scopes=["read", "write", "admin"],
    expiration=3600  # 1 hour
)

test_token_readonly = key_pair.create_token(
    subject="test-readonly",
    issuer="https://test.yourcompany.com",
    audience="test-mcp-server",
    scopes=["read"],
    expiration=3600
)

print(f"Admin token: {test_token_admin}")
print(f"Read-only token: {test_token_readonly}")
```

**Automated Testing**:
```python
import pytest
from fastmcp.testing import test_mcp

@pytest.fixture
def auth_tokens():
    """Generate test tokens for all test cases"""
    key_pair = RSAKeyPair.generate()
    return {
        "key_pair": key_pair,
        "admin": key_pair.create_token("admin", "test", "test", ["admin"]),
        "readonly": key_pair.create_token("readonly", "test", "test", ["read"]),
    }

async def test_tool_with_admin_token(auth_tokens):
    """Test tool execution with admin token"""
    verifier = JWTVerifier(
        public_key=auth_tokens["key_pair"].public_key_pem,
        issuer="test",
        audience="test"
    )
    mcp = FastMCP(name="Test", auth=verifier)

    async with test_mcp(mcp) as client:
        # Set authorization header
        client.headers["Authorization"] = f"Bearer {auth_tokens['admin']}"

        result = await client.call_tool("admin_tool", {})
        assert result.success

async def test_tool_with_insufficient_scopes(auth_tokens):
    """Test tool rejection with insufficient scopes"""
    verifier = JWTVerifier(
        public_key=auth_tokens["key_pair"].public_key_pem,
        issuer="test",
        audience="test",
        required_scopes=["admin"]
    )
    mcp = FastMCP(name="Test", auth=verifier)

    async with test_mcp(mcp) as client:
        client.headers["Authorization"] = f"Bearer {auth_tokens['readonly']}"

        # Should fail with insufficient scope error
        with pytest.raises(Exception, match="Insufficient scope"):
            await client.call_tool("admin_tool", {})
```

---

## Common Troubleshooting

### Issue: "Token signature verification failed"

**Causes**:
- Wrong public key configured
- Token signed with different private key
- JWKS endpoint returned wrong key

**Solution**:
```bash
# Verify JWKS endpoint is correct
curl https://auth.yourcompany.com/.well-known/jwks.json

# Check token header for key ID (kid)
echo "YOUR_TOKEN" | cut -d. -f1 | base64 -d | jq .

# Verify kid matches a key in JWKS response
```

### Issue: "Token has expired"

**Causes**:
- Token genuinely expired
- Clock skew between systems

**Solution**:
```bash
# Check current time vs token expiration
echo "YOUR_TOKEN" | cut -d. -f2 | base64 -d | jq .

# Increase clock skew tolerance temporarily
export FASTMCP_SERVER_AUTH_JWT_CLOCK_SKEW=120  # 2 minutes

# Long-term: Fix NTP sync on servers
```

### Issue: "Invalid audience"

**Causes**:
- Token issued for different audience
- Misconfigured audience in server

**Solution**:
```bash
# Check token audience claim
echo "YOUR_TOKEN" | cut -d. -f2 | base64 -d | jq .aud

# Verify it matches server configuration
echo $FASTMCP_SERVER_AUTH_JWT_AUDIENCE

# Update server configuration or request tokens with correct audience
```

### Issue: "Insufficient scope"

**Causes**:
- Token lacks required scopes
- Scope claim format mismatch (space-separated vs array)

**Solution**:
```bash
# Check token scopes
echo "YOUR_TOKEN" | cut -d. -f2 | base64 -d | jq .scope

# Verify required scopes
echo $FASTMCP_SERVER_AUTH_JWT_REQUIRED_SCOPES

# Request tokens with additional scopes from OAuth provider
```

### Issue: Introspection endpoint timeout

**Causes**:
- Network latency to auth server
- Auth server overloaded

**Solution**:
```bash
# Increase timeout
export FASTMCP_SERVER_AUTH_INTROSPECTION_TIMEOUT=30

# Test endpoint directly
time curl -X POST https://auth.yourcompany.com/oauth/introspect \
  -u "client_id:client_secret" \
  -d "token=YOUR_TOKEN"

# Consider caching introspection responses (add Redis cache layer)
```

---

## Performance Optimization Tips

### 1. JWKS Key Caching

```python
# Increase JWKS cache TTL to reduce fetches
verifier = JWTVerifier(
    jwks_uri="https://auth.yourcompany.com/.well-known/jwks.json",
    issuer="https://auth.yourcompany.com",
    audience="mcp-api",
    jwks_cache_ttl=7200  # 2 hours (default: 1 hour)
)
```

### 2. Connection Pooling for Introspection

```python
# httpx automatically uses connection pooling
# But you can tune it:
import httpx

introspection_client = httpx.AsyncClient(
    timeout=10.0,
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
)

# Pass to IntrospectionTokenVerifier (if API allows)
```

### 3. Disable Validation in Development

```python
# ONLY for local development, never production
if os.getenv("ENVIRONMENT") == "development":
    verifier = StaticTokenVerifier(tokens={...})
else:
    verifier = JWTVerifier.from_env()
```

---

## Next Steps

1. **Choose your scenario** based on your deployment architecture
2. **Set up environment variables** or programmatic configuration
3. **Test locally** using MCP Inspector or curl
4. **Write integration tests** using pytest with test tokens
5. **Deploy to Cloud Run** with secrets management
6. **Monitor** validation failures and latency

**Further Reading**:
- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519)
- [OAuth 2.0 Token Introspection RFC 7662](https://tools.ietf.org/html/rfc7662)
- [OAuth 2.0 Bearer Token Usage RFC 6750](https://tools.ietf.org/html/rfc6750)
- [FastMCP Authentication Documentation](https://github.com/jlowin/fastmcp)
