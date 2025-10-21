# Data Model: GitHub OAuth Authentication and Docker Deployment

**Feature**: 002-github-oauth-docker
**Date**: 2025-10-21
**Status**: Complete

## Overview

This feature adds GitHub OAuth authentication and Docker containerization to the existing Hansard RAG system. The data model focuses on OAuth-related entities and deployment configuration, as the core RAG data model (speeches, speech_chunks) was defined in feature 001.

---

## OAuth-Related Entities

### OAuth Client Registration

**Purpose**: Stores metadata for dynamically registered MCP clients

**Attributes**:
- `client_id` (string, UUID): Unique identifier for the registered client
- `client_name` (string): Human-readable client name (e.g., "Claude Desktop", "Custom MCP Client")
- `redirect_uris` (list of strings): Allowed redirect URIs for OAuth callback
- `logo_uri` (string, optional): URL to client's logo image
- `scopes` (list of strings): Requested OAuth scopes
- `created_at` (datetime): Registration timestamp
- `approved` (boolean): User consent status

**Validation Rules**:
- `client_id` must be globally unique
- `redirect_uris` must be valid HTTPS URLs (or http://localhost for development)
- At least one `redirect_uri` must be provided
- `client_name` must not be empty

**Storage**: Persisted in Redis (key-value store)
- Key: `oauth:client:{client_id}`
- Value: JSON-serialized client metadata

**State Transitions**:
```
PENDING (initial registration)
  → APPROVED (user grants consent)
  → ACTIVE (tokens issued)
  → REVOKED (user revokes access)
```

---

### Access Token

**Purpose**: Represents authenticated session for MCP client

**Attributes**:
- `token_value` (string): JWT token issued by FastMCP OAuth Proxy
- `token_type` (string): Always "Bearer"
- `expires_at` (datetime): Token expiration timestamp
- `issued_at` (datetime): Token issuance timestamp
- `claims` (dict): JWT payload containing user identity
  - `iss` (string): Issuer (FastMCP server URL)
  - `sub` (string): Subject (GitHub user ID)
  - `aud` (string): Audience (client_id)
  - `exp` (integer): Expiration Unix timestamp
  - `iat` (integer): Issued-at Unix timestamp
  - `login` (string): GitHub username
  - `name` (string): GitHub display name
  - `email` (string): GitHub email address

**Validation Rules**:
- Token signature must be valid (HS256)
- Current time must be before `expires_at`
- `client_id` in `aud` claim must match requesting client

**Storage**: Encrypted in Redis using Fernet encryption
- Key: `oauth:token:{client_id}`
- Value: Encrypted upstream GitHub access token

---

### OAuth Callback Transaction

**Purpose**: Temporary state linking authorization code to client redirect URI

**Attributes**:
- `state` (string): CSRF token (cryptographically random)
- `client_id` (string): Client initiating the OAuth flow
- `redirect_uri` (string): Client's callback URL for final token delivery
- `code_verifier` (string): PKCE code verifier (client-to-proxy)
- `upstream_code_verifier` (string): PKCE code verifier (proxy-to-GitHub)
- `created_at` (datetime): Transaction creation timestamp
- `expires_at` (datetime): Transaction expiration (typically 10 minutes)

**Validation Rules**:
- `state` must be cryptographically random (128+ bits entropy)
- Transaction must not be expired
- `redirect_uri` must match one of the client's registered URIs

**Storage**: In-memory (ephemeral) or Redis with TTL
- Key: `oauth:transaction:{state}`
- TTL: 600 seconds (10 minutes)

---

## Environment Configuration Entity

**Purpose**: Collection of environment variables required for server operation

**Production Configuration**:

```bash
# Authentication (required)
FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.github.GitHubProvider
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=<from-secret-manager>
FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=<from-secret-manager>
FASTMCP_SERVER_AUTH_GITHUB_BASE_URL=https://mcp.simonkennedymp.com.au

# Token persistence (required for production)
JWT_SIGNING_KEY=<from-secret-manager>
TOKEN_ENCRYPTION_KEY=<from-secret-manager>
REDIS_HOST=10.x.x.x  # Internal Cloud SQL Redis instance IP
REDIS_PORT=6379

# Cloud SQL (required)
GCP_PROJECT_ID=<project-id>
GCP_REGION=us-central1
CLOUDSQL_INSTANCE=hansard-db
CLOUDSQL_DATABASE=hansard
CLOUDSQL_USER=postgres
DATABASE_PASSWORD=<from-secret-manager>

# Vertex AI (required)
VERTEX_AI_LOCATION=us-central1

# Server configuration
PORT=8080  # Injected by Cloud Run

# Optional
FASTMCP_SERVER_AUTH_GITHUB_REQUIRED_SCOPES=user,user:email
LOG_LEVEL=INFO
```

**Validation Rules**:
- All `*_SECRET` and `*_PASSWORD` variables must be loaded from Secret Manager (never hardcoded)
- `FASTMCP_SERVER_AUTH_GITHUB_BASE_URL` must match GitHub OAuth App callback URL
- `PORT` must be between 1024 and 65535
- `GCP_PROJECT_ID` must be valid Google Cloud project ID

**Secret Manager Mapping**:
```yaml
# gcloud secrets list
github-client-id:       FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID
github-client-secret:   FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET
jwt-signing-key:        JWT_SIGNING_KEY
token-encryption-key:   TOKEN_ENCRYPTION_KEY
db-password:            DATABASE_PASSWORD
```

---

## Docker Image Entity

**Purpose**: Self-contained deployment artifact with all runtime dependencies

**Attributes**:
- `image_name` (string): gcr.io/PROJECT_ID/hansard-mcp
- `image_tag` (string): Git commit SHA or "latest"
- `size` (integer): Image size in bytes (target: ~270MB)
- `created_at` (datetime): Build timestamp
- `layers` (list): Docker layer digests
- `platform` (string): linux/amd64 or linux/arm64

**Build Metadata**:
```json
{
  "base_image": "python:3.13-slim",
  "build_stage_size": "520MB",
  "runtime_stage_size": "270MB",
  "python_version": "3.13.0",
  "uv_version": "0.5.0",
  "dependencies": [
    "fastmcp==2.12.5",
    "langchain-google-vertexai==2.1.0",
    "langchain-google-cloud-sql-pg==0.15.0"
  ]
}
```

**Validation Rules**:
- Image must pass vulnerability scanning (Cloud Build)
- Must run as non-root user (UID 1000)
- Must expose port 8080
- Must respond to /health endpoint within 10 seconds

---

## Relationships

```
OAuth Client Registration
  ├─ has many → Access Tokens (1:N)
  ├─ has many → OAuth Callback Transactions (1:N, ephemeral)
  └─ belongs to → GitHub User (via upstream GitHub profile)

Access Token
  ├─ belongs to → OAuth Client Registration (N:1)
  └─ contains → Encrypted GitHub Token (1:1)

OAuth Callback Transaction
  ├─ belongs to → OAuth Client Registration (N:1)
  └─ expires after → 10 minutes (TTL)

Environment Configuration
  ├─ references → Secret Manager Secrets (N:N)
  └─ required by → Docker Image runtime

Docker Image
  ├─ contains → Application Code + Dependencies
  ├─ requires → Environment Configuration at runtime
  └─ deployed to → Cloud Run Service
```

---

## Redis Storage Schema

**Key Patterns**:

```redis
# OAuth Client Registrations
oauth:client:{client_id} → JSON {client_name, redirect_uris, logo_uri, scopes, created_at, approved}

# Encrypted Upstream Tokens
oauth:token:{client_id} → Fernet-encrypted GitHub access token

# Ephemeral Callback Transactions (TTL: 600s)
oauth:transaction:{state} → JSON {client_id, redirect_uri, code_verifier, upstream_code_verifier, created_at}
```

**Example Redis Commands**:

```bash
# Store client registration
SET oauth:client:abc123 '{"client_name":"Claude Desktop","redirect_uris":["https://claude.ai/callback"],"scopes":["user"],"approved":true}

# Store encrypted token (binary data)
SET oauth:token:abc123 <binary-fernet-encrypted-token>

# Store transaction with TTL
SETEX oauth:transaction:xyz789 600 '{"client_id":"abc123","redirect_uri":"https://claude.ai/callback","code_verifier":"..."}

# Retrieve client registration
GET oauth:client:abc123

# Check transaction expiry
TTL oauth:transaction:xyz789
```

---

## Security Constraints

### Token Encryption

**Algorithm**: Fernet (AES-128-CBC + HMAC-SHA256)

**Key Derivation**:
```python
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import os

# Derive encryption key from TOKEN_ENCRYPTION_KEY
kdf = HKDF(
    algorithm=hashes.SHA256(),
    length=32,
    salt=os.urandom(16),
    info=b'fastmcp-token-encryption',
)
encryption_key = kdf.derive(os.getenv("TOKEN_ENCRYPTION_KEY").encode())
```

**Storage Format**:
```
<16-byte IV><encrypted-token><32-byte HMAC>
```

### JWT Signing

**Algorithm**: HS256 (HMAC-SHA256)

**Claims Validation**:
- `iss` (issuer) must match `FASTMCP_SERVER_AUTH_GITHUB_BASE_URL`
- `aud` (audience) must match requesting client_id
- `exp` (expiration) must be future timestamp
- `sub` (subject) must be GitHub user ID

**Key Rotation**:
- Production: Rotate `JWT_SIGNING_KEY` annually
- On rotation: Old tokens become invalid, users must re-authenticate

---

## Data Retention

**OAuth Client Registrations**: Indefinite (until user revokes)
**Access Tokens**: 30 days (GitHub default expiration)
**Callback Transactions**: 10 minutes (TTL enforced by Redis)

**Cleanup Strategy**:
```python
# Periodic cleanup job (daily)
async def cleanup_expired_tokens():
    # Remove tokens older than 30 days
    cutoff = datetime.now() - timedelta(days=30)

    async for key in redis.scan_iter("oauth:token:*"):
        token_data = await redis.get(key)
        if token_data.expires_at < cutoff:
            await redis.delete(key)
```

---

## Migration from Feature 001

**No schema changes required** for existing tables:
- `speeches` table: Unchanged
- `speech_chunks` table: Unchanged

**New infrastructure**:
- Redis instance for OAuth state storage
- Secret Manager secrets for OAuth credentials
- Docker image in Artifact Registry
- Cloud Run service configuration

**Backward Compatibility**:
- Existing MCP tools (`search`, `fetch`, `dataset_stats`) unchanged
- Authentication layer wraps existing tools (decorator pattern)
- Local development can bypass OAuth with `DANGEROUSLY_OMIT_AUTH=true`

---

## Summary

This data model adds OAuth authentication and deployment infrastructure without modifying the core Hansard RAG data model from feature 001. OAuth entities are ephemeral (Redis-backed) while the core speech data remains in PostgreSQL.

**Key Design Decisions**:
1. **Redis for OAuth state**: Fast, ephemeral storage for tokens and transactions
2. **Secret Manager for credentials**: Never store secrets in code or environment files
3. **JWT tokens for clients**: FastMCP-issued tokens with GitHub user claims
4. **Encrypted upstream tokens**: GitHub tokens encrypted at rest in Redis
5. **Non-root Docker user**: Security compliance (UID 1000)
