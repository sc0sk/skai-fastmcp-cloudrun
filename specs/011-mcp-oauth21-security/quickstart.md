# Quickstart: MCP OAuth 2.1 Compliance and Security Hardening

**Feature**: 011-mcp-oauth21-security
**Date**: 2025-10-24
**Purpose**: Deployment and configuration guide for OAuth 2.1 token verification

## Overview

This guide provides step-by-step instructions for deploying and configuring the MCP OAuth 2.1 Resource Server with comprehensive security hardening across different environments.

## Prerequisites

- Python 3.11+
- Google Cloud account (for Secret Manager and Cloud Run)
- OAuth 2.1 Identity Provider (Google, Microsoft, Auth0, Okta, etc.)
- Basic understanding of JWT and OAuth 2.0

## Quick Start (5 Minutes)

### 1. Local Development with Static Tokens

**Use Case**: Quick testing without OAuth infrastructure

```bash
# 1. Install dependencies
uv pip install -e .

# 2. Create .env file
cat > .env <<EOF
ENVIRONMENT=development
FASTMCP_SERVER_AUTH_TYPE=static
DANGEROUSLY_OMIT_AUTH=false
EOF

# 3. Create test server
cat > test_server.py <<'PYTHON'
from fastmcp import FastMCP
from src.auth import StaticTokenVerifier, TokenVerifierAuthProvider
from src.models.auth import StaticTokenVerifierConfig

# Configure static tokens for testing
verifier = StaticTokenVerifier(
    StaticTokenVerifierConfig(
        tokens={
            "dev-token-12345": {
                "client_id": "developer@example.com",
                "scopes": ["read:data", "write:data"]
            }
        },
        required_scopes=["read:data"]
    )
)

auth = TokenVerifierAuthProvider(verifier, required_scopes=["read:data"])
mcp = FastMCP("Test Server", auth=auth)

@mcp.tool()
def hello(name: str) -> str:
    """Test tool requiring authentication"""
    return f"Hello, {name}!"
PYTHON

# 4. Run server
fastmcp dev test_server.py

# 5. Test with curl
curl -H "Authorization: Bearer dev-token-12345" \
     http://localhost:6274/tools/call \
     -d '{"name": "hello", "arguments": {"name": "World"}}'
```

**⚠️ Warning**: Static tokens are for development only. Never use in production.

---

## Deployment Scenarios

### Scenario 1: JWT with Google OAuth (Recommended for Production)

**Use Case**: Enterprise deployment with Google Workspace identity

#### Step 1: Configure Google Cloud

```bash
# Set project
export GCP_PROJECT_ID=your-project-id

# Create Secret Manager secrets
echo "https://accounts.google.com" | \
  gcloud secrets create jwt-issuer --data-file=-

echo "your-mcp-server-id" | \
  gcloud secrets create jwt-audience --data-file=-

echo "https://www.googleapis.com/oauth2/v3/certs" | \
  gcloud secrets create jwt-jwks-uri --data-file=-
```

#### Step 2: Grant IAM Permissions

```bash
# Get Cloud Run service account
export SERVICE_ACCOUNT=$(gcloud run services describe your-service \
  --region us-central1 \
  --format 'value(spec.template.spec.serviceAccountName)')

# Grant Secret Manager access
gcloud secrets add-iam-policy-binding jwt-issuer \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding jwt-audience \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding jwt-jwks-uri \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

#### Step 3: Deploy to Cloud Run

```bash
gcloud run deploy your-service \
  --source . \
  --region us-central1 \
  --set-env-vars="ENVIRONMENT=production" \
  --set-env-vars="FASTMCP_SERVER_AUTH_TYPE=jwt" \
  --set-env-vars="FASTMCP_SERVER_AUTH_SECRET_BACKEND=gcp_secret_manager" \
  --set-env-vars="GCP_PROJECT_ID=${GCP_PROJECT_ID}" \
  --set-secrets="FASTMCP_SERVER_AUTH_JWT_ISSUER=jwt-issuer:latest" \
  --set-secrets="FASTMCP_SERVER_AUTH_JWT_AUDIENCE=jwt-audience:latest" \
  --set-secrets="FASTMCP_SERVER_AUTH_JWT_JWKS_URI=jwt-jwks-uri:latest" \
  --set-env-vars="FASTMCP_SERVER_AUTH_JWT_ALGORITHM=RS256" \
  --set-env-vars="FASTMCP_SERVER_AUTH_JWT_REQUIRED_SCOPES=read:data" \
  --no-allow-unauthenticated
```

#### Step 4: Test with Google JWT

```bash
# Get Google OAuth token (using gcloud)
export TOKEN=$(gcloud auth print-identity-token \
  --audiences=your-mcp-server-id)

# Test authenticated request
curl -H "Authorization: Bearer ${TOKEN}" \
     https://your-service-url.run.app/mcp/tools/list
```

**Expected Response**: List of available tools (authenticated)

---

### Scenario 2: JWT with Microsoft Entra ID (Azure AD)

**Use Case**: Enterprise deployment with Microsoft 365 identity

#### Step 1: Register Application in Azure

1. Go to [Azure Portal](https://portal.azure.com) → Azure Active Directory → App Registrations
2. Create new registration:
   - Name: "MCP Server Resource"
   - Supported account types: "Accounts in this organizational directory only"
   - No redirect URI needed (we're the resource server)
3. Note the **Application (client) ID** and **Directory (tenant) ID**

#### Step 2: Configure Secrets

```bash
# Create secrets in Google Cloud Secret Manager
echo "https://login.microsoftonline.com/{tenant-id}/v2.0" | \
  gcloud secrets create jwt-issuer --data-file=-

echo "api://{client-id}" | \
  gcloud secrets create jwt-audience --data-file=-

echo "https://login.microsoftonline.com/{tenant-id}/discovery/v2.0/keys" | \
  gcloud secrets create jwt-jwks-uri --data-file=-
```

Replace `{tenant-id}` and `{client-id}` with values from Azure.

#### Step 3: Deploy

```bash
gcloud run deploy your-service \
  --source . \
  --region us-central1 \
  --set-env-vars="ENVIRONMENT=production" \
  --set-env-vars="FASTMCP_SERVER_AUTH_TYPE=jwt" \
  --set-env-vars="FASTMCP_SERVER_AUTH_SECRET_BACKEND=gcp_secret_manager" \
  --set-env-vars="GCP_PROJECT_ID=${GCP_PROJECT_ID}" \
  --set-secrets="FASTMCP_SERVER_AUTH_JWT_ISSUER=jwt-issuer:latest" \
  --set-secrets="FASTMCP_SERVER_AUTH_JWT_AUDIENCE=jwt-audience:latest" \
  --set-secrets="FASTMCP_SERVER_AUTH_JWT_JWKS_URI=jwt-jwks-uri:latest" \
  --set-env-vars="FASTMCP_SERVER_AUTH_JWT_ALGORITHM=RS256" \
  --no-allow-unauthenticated
```

#### Step 4: Test with Azure Token

```powershell
# Get Azure AD token (using Azure CLI)
$token = az account get-access-token `
  --resource "api://{client-id}" `
  --query accessToken `
  --output tsv

# Test authenticated request
curl -H "Authorization: Bearer $token" `
     https://your-service-url.run.app/mcp/tools/list
```

---

### Scenario 3: OAuth Introspection (Auth0, Okta)

**Use Case**: Using authorization server that issues opaque tokens

#### Step 1: Get Introspection Endpoint Details

**Auth0**:
```
Introspection URL: https://{your-domain}.auth0.com/oauth/token/introspection
Client ID: {your-m2m-client-id}
Client Secret: {your-m2m-client-secret}
```

**Okta**:
```
Introspection URL: https://{your-domain}.okta.com/oauth2/v1/introspect
Client ID: {your-service-app-client-id}
Client Secret: {your-service-app-client-secret}
```

#### Step 2: Store Secrets

```bash
# Create secrets
echo "https://{your-domain}.auth0.com/oauth/token/introspection" | \
  gcloud secrets create introspection-url --data-file=-

echo "{your-client-id}" | \
  gcloud secrets create introspection-client-id --data-file=-

echo "{your-client-secret}" | \
  gcloud secrets create introspection-client-secret --data-file=-
```

#### Step 3: Deploy

```bash
gcloud run deploy your-service \
  --source . \
  --region us-central1 \
  --set-env-vars="ENVIRONMENT=production" \
  --set-env-vars="FASTMCP_SERVER_AUTH_TYPE=introspection" \
  --set-env-vars="FASTMCP_SERVER_AUTH_SECRET_BACKEND=gcp_secret_manager" \
  --set-env-vars="GCP_PROJECT_ID=${GCP_PROJECT_ID}" \
  --set-secrets="FASTMCP_SERVER_AUTH_INTROSPECTION_URL=introspection-url:latest" \
  --set-secrets="FASTMCP_SERVER_AUTH_INTROSPECTION_CLIENT_ID=introspection-client-id:latest" \
  --set-secrets="FASTMCP_SERVER_AUTH_INTROSPECTION_CLIENT_SECRET=introspection-client-secret:latest" \
  --set-env-vars="FASTMCP_SERVER_AUTH_INTROSPECTION_REQUIRED_SCOPES=read:data" \
  --set-env-vars="FASTMCP_SERVER_AUTH_INTROSPECTION_TIMEOUT=10" \
  --no-allow-unauthenticated
```

---

### Scenario 4: HMAC Symmetric Keys (Internal Services)

**Use Case**: Service-to-service authentication with pre-shared keys

⚠️ **Security Warning**: Only use HMAC for trusted internal services. Use asymmetric (RS256) for external clients.

#### Step 1: Generate Secure HMAC Key

```bash
# Generate 256-bit (32-byte) cryptographically random key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Example output: "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"
```

#### Step 2: Store Key in Secret Manager

```bash
# Store HMAC key
echo "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6" | \
  gcloud secrets create hmac-secret-key --data-file=-

# Store other config
echo "https://internal-auth.example.com" | \
  gcloud secrets create jwt-issuer --data-file=-

echo "internal-mcp-service" | \
  gcloud secrets create jwt-audience --data-file=-
```

#### Step 3: Deploy

```bash
gcloud run deploy your-service \
  --source . \
  --region us-central1 \
  --set-env-vars="ENVIRONMENT=production" \
  --set-env-vars="FASTMCP_SERVER_AUTH_TYPE=jwt" \
  --set-env-vars="FASTMCP_SERVER_AUTH_SECRET_BACKEND=gcp_secret_manager" \
  --set-env-vars="GCP_PROJECT_ID=${GCP_PROJECT_ID}" \
  --set-secrets="FASTMCP_SERVER_AUTH_JWT_PUBLIC_KEY=hmac-secret-key:latest" \
  --set-secrets="FASTMCP_SERVER_AUTH_JWT_ISSUER=jwt-issuer:latest" \
  --set-secrets="FASTMCP_SERVER_AUTH_JWT_AUDIENCE=jwt-audience:latest" \
  --set-env-vars="FASTMCP_SERVER_AUTH_JWT_ALGORITHM=HS256" \
  --no-allow-unauthenticated
```

#### Step 4: Generate Test Token

```python
import jwt
from datetime import datetime, timedelta

# Use same HMAC key
secret_key = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"

# Create token
payload = {
    "sub": "service-123",
    "iss": "https://internal-auth.example.com",
    "aud": "internal-mcp-service",
    "exp": datetime.utcnow() + timedelta(hours=1),
    "scope": "read:data write:data"
}

token = jwt.encode(payload, secret_key, algorithm="HS256")
print(token)
```

---

### Scenario 5: Local Development with Real OAuth (ngrok)

**Use Case**: Testing with real identity provider locally

#### Step 1: Install ngrok

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com

# Start ngrok tunnel
ngrok http 8000
# Note the HTTPS URL: https://abc123.ngrok.io
```

#### Step 2: Configure Identity Provider

Register your ngrok URL as a valid audience/resource in your OAuth provider.

**Example (Google Cloud)**:
```bash
gcloud iap oauth-clients create \
  --display_name="MCP Server Dev" \
  --uri=https://abc123.ngrok.io
```

#### Step 3: Run Local Server

```bash
# Create .env with real OAuth config
cat > .env <<EOF
ENVIRONMENT=development
FASTMCP_SERVER_AUTH_TYPE=jwt
FASTMCP_SERVER_AUTH_SECRET_BACKEND=env
FASTMCP_SERVER_AUTH_JWT_JWKS_URI=https://www.googleapis.com/oauth2/v3/certs
FASTMCP_SERVER_AUTH_JWT_ISSUER=https://accounts.google.com
FASTMCP_SERVER_AUTH_JWT_AUDIENCE=your-client-id
FASTMCP_SERVER_AUTH_JWT_ALGORITHM=RS256
EOF

# Run server
fastmcp run server.py --transport http --port 8000
```

#### Step 4: Test with Real Tokens

```bash
# Get real token from Google
TOKEN=$(gcloud auth print-identity-token --audiences=your-client-id)

# Test via ngrok URL
curl -H "Authorization: Bearer ${TOKEN}" \
     https://abc123.ngrok.io/mcp/tools/list
```

---

## Configuration Reference

### Environment Variables

#### Common Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `development` | Environment name (development/production) |
| `FASTMCP_SERVER_AUTH_TYPE` | Yes | - | Authentication type: `jwt` or `introspection` |
| `FASTMCP_SERVER_AUTH_SECRET_BACKEND` | Yes | `env` | Secret storage: `env` or `gcp_secret_manager` |
| `GCP_PROJECT_ID` | If Secret Manager | - | Google Cloud project ID |

#### JWT Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FASTMCP_SERVER_AUTH_JWT_JWKS_URI` | If JWT+JWKS | - | JWKS endpoint URL (https://...) |
| `FASTMCP_SERVER_AUTH_JWT_PUBLIC_KEY` | If JWT+static | - | Public key PEM or HMAC secret |
| `FASTMCP_SERVER_AUTH_JWT_ISSUER` | Yes | - | Expected issuer (iss claim) |
| `FASTMCP_SERVER_AUTH_JWT_AUDIENCE` | Yes | - | Expected audience (aud claim) |
| `FASTMCP_SERVER_AUTH_JWT_ALGORITHM` | No | `RS256` | Signing algorithm |
| `FASTMCP_SERVER_AUTH_JWT_REQUIRED_SCOPES` | No | `` | Comma-separated required scopes |
| `FASTMCP_SERVER_AUTH_JWT_CLOCK_SKEW` | No | `60` | Clock skew tolerance (seconds, max 120) |
| `FASTMCP_SERVER_AUTH_JWT_JWKS_CACHE_TTL` | No | `3600` | JWKS cache duration (seconds) |

#### Introspection Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FASTMCP_SERVER_AUTH_INTROSPECTION_URL` | Yes | - | Introspection endpoint URL (https://...) |
| `FASTMCP_SERVER_AUTH_INTROSPECTION_CLIENT_ID` | Yes | - | Client ID for Basic Auth |
| `FASTMCP_SERVER_AUTH_INTROSPECTION_CLIENT_SECRET` | Yes | - | Client secret for Basic Auth |
| `FASTMCP_SERVER_AUTH_INTROSPECTION_REQUIRED_SCOPES` | No | `` | Comma-separated required scopes |
| `FASTMCP_SERVER_AUTH_INTROSPECTION_TIMEOUT` | No | `10` | HTTP timeout (seconds, max 60) |

#### Rate Limiting Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FASTMCP_SERVER_AUTH_RATE_LIMIT_ENABLED` | No | `true` | Enable rate limiting |
| `FASTMCP_SERVER_AUTH_RATE_LIMIT_MAX_ATTEMPTS` | No | `10` | Max attempts per window |
| `FASTMCP_SERVER_AUTH_RATE_LIMIT_WINDOW_SECONDS` | No | `60` | Time window duration |

#### Secret Manager Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FASTMCP_SERVER_AUTH_SECRET_CACHE_TTL` | No | `300` | Secret cache TTL (seconds) |

---

## Troubleshooting

### Issue: "Algorithm confusion" error at startup

**Symptom**:
```
ValueError: HMAC algorithms cannot be used with JWKS endpoints
```

**Solution**: Don't mix JWKS URIs with HMAC algorithms. Use:
- JWKS + RS256/RS384/RS512/ES256/ES384/ES512 (asymmetric)
- Static key + HS256/HS384/HS512 (symmetric)

### Issue: "HMAC key must be at least X bytes"

**Symptom**:
```
ValueError: HMAC key for HS256 must be at least 32 bytes
```

**Solution**: Generate longer key:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Issue: "Cannot use HTTP localhost in production"

**Symptom**:
```
ValueError: Cannot use HTTP localhost JWKS URI in production
```

**Solution**: Use HTTPS JWKS endpoint from your identity provider, or set `ENVIRONMENT=development` for local testing.

### Issue: Rate limiting blocking legitimate requests

**Symptom**: HTTP 429 errors for valid tokens

**Solution**: Increase rate limit or disable temporarily:
```bash
export FASTMCP_SERVER_AUTH_RATE_LIMIT_MAX_ATTEMPTS=100
# or
export FASTMCP_SERVER_AUTH_RATE_LIMIT_ENABLED=false
```

### Issue: Secret Manager permission denied

**Symptom**:
```
google.api_core.exceptions.PermissionDenied: 403 Permission denied on secret
```

**Solution**: Grant IAM role to Cloud Run service account:
```bash
gcloud secrets add-iam-policy-binding secret-name \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

### Issue: Token signature verification failed

**Symptom**:
```
HTTP 401: Token signature verification failed
```

**Debugging Steps**:
1. Verify JWKS URI is correct
2. Check issuer matches token's `iss` claim
3. Verify algorithm matches (RS256 vs HS256)
4. Ensure clock sync (NTP configured)
5. Check token hasn't expired

```bash
# Decode JWT to inspect claims (without verification)
echo "YOUR_TOKEN" | cut -d. -f2 | base64 -d | jq .
```

---

## Security Checklist

Before deploying to production, verify:

- [ ] ✅ `ENVIRONMENT=production` set
- [ ] ✅ Using Secret Manager (not environment variables) for secrets
- [ ] ✅ HTTPS enforced for all external endpoints (JWKS, introspection)
- [ ] ✅ Strong HMAC keys (32+ bytes, cryptographically random) if using HS256
- [ ] ✅ Asymmetric algorithms (RS256) preferred over symmetric (HS256)
- [ ] ✅ Rate limiting enabled
- [ ] ✅ Required scopes configured
- [ ] ✅ Clock skew ≤120 seconds
- [ ] ✅ StaticTokenVerifier disabled (production detection working)
- [ ] ✅ Service account has minimal IAM permissions
- [ ] ✅ Cloud Logging enabled for audit trail
- [ ] ✅ Monitoring configured for 401/429 errors
- [ ] ✅ No secrets in git history
- [ ] ✅ JWKS cache TTL appropriate (default 3600s)
- [ ] ✅ Secret cache TTL appropriate (default 300s)
- [ ] ✅ Tested with real OAuth tokens from identity provider

---

## Performance Tuning

### JWKS Cache TTL

- **Low TTL (60s)**: More frequent key fetches, better rotation detection
- **High TTL (86400s)**: Fewer API calls, slower rotation response
- **Recommended**: 3600s (1 hour)

```bash
export FASTMCP_SERVER_AUTH_JWT_JWKS_CACHE_TTL=3600
```

### Secret Cache TTL

- **Low TTL (60s)**: More Secret Manager API calls, faster rotation
- **High TTL (3600s)**: Fewer API calls, cost savings, slower rotation
- **Recommended**: 300s (5 minutes)

```bash
export FASTMCP_SERVER_AUTH_SECRET_CACHE_TTL=300
```

### Rate Limiting

- **Stricter (5 attempts/60s)**: Better DoS protection, may block burst traffic
- **Lenient (50 attempts/60s)**: Allows burst traffic, less protection
- **Recommended**: 10 attempts/60s

```bash
export FASTMCP_SERVER_AUTH_RATE_LIMIT_MAX_ATTEMPTS=10
export FASTMCP_SERVER_AUTH_RATE_LIMIT_WINDOW_SECONDS=60
```

---

## Next Steps

After successful deployment:

1. **Monitor Logs**: Watch for 401/429 errors in Cloud Logging
2. **Set Up Alerts**: Configure alerting for authentication failures
3. **Test Rotation**: Rotate a secret and verify TTL-based refresh works
4. **Load Testing**: Verify rate limiting thresholds are appropriate
5. **Security Audit**: Run security tests to verify all fixes applied
6. **Documentation**: Update team docs with OAuth provider details

## Support

For issues or questions:
- Review [SECURITY_AUDIT.md](../../../SECURITY_AUDIT.md) for security findings
- Check [research.md](research.md) for architecture decisions
- See [data-model.md](data-model.md) for model definitions
- Refer to [MCP 2025 Specification](https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization)
