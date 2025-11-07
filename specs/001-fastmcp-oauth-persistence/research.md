# Research: FastMCP 2.13.0 OAuth Persistence Implementation

**Feature**: FastMCP 2.13.0 Upgrade with Persistent OAuth Storage
**Date**: 2025-11-06
**Status**: Complete

## Overview

This research document consolidates technical findings for upgrading FastMCP to 2.13.0 and implementing persistent OAuth client storage using PostgreSQL with encryption.

## 1. py-key-value-aio AsyncKeyValue Protocol

### Decision
**Implement AsyncKeyValue protocol for PostgreSQL storage backend**

### Interface Requirements

```python
from typing import Any, Sequence

class AsyncKeyValue:
    """Protocol for async key-value storage backends."""

    async def get(
        self,
        key: str,
        collection: str | None = None
    ) -> dict[str, Any] | None:
        """Retrieve value by key. Returns None if not found."""
        ...

    async def get_many(
        self,
        keys: list[str],
        collection: str | None = None
    ) -> list[dict[str, Any] | None]:
        """Bulk get operation. Preserves order, returns None for missing keys."""
        ...

    async def put(
        self,
        key: str,
        value: dict[str, Any],
        collection: str | None = None,
        ttl: float | None = None
    ) -> None:
        """Store value under key with optional TTL (seconds)."""
        ...

    async def put_many(
        self,
        keys: list[str],
        values: Sequence[dict[str, Any]],
        collection: str | None = None,
        ttl: float | None = None
    ) -> None:
        """Bulk put operation."""
        ...

    async def delete(
        self,
        key: str,
        collection: str | None = None
    ) -> bool:
        """Delete key. Returns True if deleted, False if not found."""
        ...

    async def delete_many(
        self,
        keys: list[str],
        collection: str | None = None
    ) -> int:
        """Bulk delete. Returns count of deleted keys."""
        ...

    async def ttl(
        self,
        key: str,
        collection: str | None = None
    ) -> tuple[dict[str, Any] | None, float | None]:
        """Get value and remaining TTL in seconds. Returns (None, None) if not found."""
        ...
```

### Key Characteristics

- **All methods are async**: Return coroutines, not synchronous results
- **Collection parameter**: Optional namespace (e.g., "oauth_clients") for multi-tenancy
- **TTL support**: Optional expiration time in seconds (None = no expiration)
- **Bulk operations**: Optimize database round-trips for multiple keys
- **Type safety**: Values must be JSON-serializable `dict[str, Any]`
- **Return types**:
  - `get` returns `None` if key doesn't exist (not exception)
  - `delete` returns `bool` (True if deleted, False if not found)
  - `delete_many` returns `int` count of deleted keys

### Rationale

- **Simple interface**: Minimal methods, focused on key-value operations
- **Namespace isolation**: Collection parameter enables separate logical stores in one backend
- **Performance**: Bulk operations reduce database round-trips
- **TTL built-in**: Automatic expiration support at protocol level
- **Existing compatibility**: Current `/home/user/skai-fastmcp-cloudrun/src/auth/postgres_storage.py` is already compatible (minor signature fix needed for `delete`)

### Alternatives Considered

1. **Dict-like interface**: Synchronous `__getitem__`, `__setitem__` - ❌ Not async-friendly
2. **Generic[K, V] interface**: Support non-string keys - ❌ OAuth clients need string keys only
3. **Custom interface**: Define our own protocol - ❌ Not compatible with py-key-value-aio ecosystem
4. **AsyncKeyValue protocol**: ✅ **Selected** - Standard, well-documented, ecosystem support

## 2. FastMCP 2.13.0 client_storage Parameter

### Decision
**Use official `client_storage` parameter in GitHubProvider**

### API Signature

```python
from fastmcp.server.auth.providers.github import GitHubProvider
from key_value.aio.protocols.key_value import AsyncKeyValue

auth_provider = GitHubProvider(
    client_id: str,                     # GitHub OAuth App client ID
    client_secret: str,                 # GitHub OAuth App client secret
    base_url: str,                      # Server base URL (for OAuth callbacks)
    jwt_signing_key: str | None = None, # JWT signing key (recommended for production)
    client_storage: AsyncKeyValue | None = None  # NEW in 2.13.0
)
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `client_id` | `str` | Yes | GitHub OAuth App client ID from environment |
| `client_secret` | `str` | Yes | GitHub OAuth App client secret from environment |
| `base_url` | `str` | Yes | Server base URL for OAuth redirect URIs |
| `jwt_signing_key` | `str \| None` | No | JWT signing key for token security (recommended) |
| `client_storage` | `AsyncKeyValue \| None` | No | Storage backend for OAuth clients (defaults to in-memory) |

### Behavior

- **Without `client_storage`**: Uses in-memory storage (lost on restart) - ❌ Not suitable for Cloud Run
- **With `client_storage`**: Persists OAuth clients to provided backend - ✅ Survives restarts

### Example Usage

```python
from fastmcp.server.auth.providers.github import GitHubProvider
from src.auth.postgres_kv_storage import PostgresKVStorage
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet
import os

# Create PostgreSQL storage backend
postgres_storage = PostgresKVStorage()

# Wrap with encryption
encrypted_storage = FernetEncryptionWrapper(
    key_value=postgres_storage,
    fernet=Fernet(os.environ["OAUTH_STORAGE_ENCRYPTION_KEY"])
)

# Configure GitHubProvider with persistent storage
auth_provider = GitHubProvider(
    client_id=os.environ["FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID"],
    client_secret=os.environ["FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET"],
    base_url=os.environ["FASTMCP_SERVER_AUTH_GITHUB_BASE_URL"],
    jwt_signing_key=os.environ["JWT_SIGNING_KEY"],
    client_storage=encrypted_storage  # NEW: Persistent encrypted storage
)
```

### Rationale

- **Official API**: Part of FastMCP 2.13.0 public interface (not monkey-patching)
- **Pluggable design**: Any `AsyncKeyValue` implementation works
- **Backward compatible**: Optional parameter (defaults to in-memory)
- **Production-ready**: Designed for persistent storage with encryption

### Alternatives Considered

1. **Monkey-patching internal storage**: ❌ Fragile, breaks on FastMCP updates
2. **Forking FastMCP**: ❌ Maintenance burden, no upstream fixes
3. **Environment variable hack**: ❌ Not part of official API
4. **Official `client_storage` parameter**: ✅ **Selected** - Supported API, future-proof

## 3. FernetEncryptionWrapper

### Decision
**Use FernetEncryptionWrapper from py-key-value-aio for transparent encryption**

### Import and Usage

```python
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet
import os

# Generate encryption key (one-time setup):
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Wrap storage backend with encryption
encrypted_storage = FernetEncryptionWrapper(
    key_value=postgres_storage,  # Underlying storage backend
    fernet=Fernet(os.environ["OAUTH_STORAGE_ENCRYPTION_KEY"])  # Fernet instance with key
)
```

### How It Works

1. **Transparent encryption**: Intercepts `put()` calls, encrypts `value` before storing
2. **Transparent decryption**: Intercepts `get()` calls, decrypts `value` after retrieval
3. **Wrapper pattern**: Delegates all operations to underlying storage backend
4. **Symmetric encryption**: Uses Fernet (AES-128-CBC + HMAC-SHA256)
5. **Key format**: Base64-encoded 32-byte key from `Fernet.generate_key()`

### Encryption Details

- **Algorithm**: Fernet (AES-128 in CBC mode with HMAC authentication)
- **Key size**: 32 bytes (base64-encoded to 44 characters)
- **Format**: `version || timestamp || iv || ciphertext || hmac` (Fernet token format)
- **Authentication**: HMAC prevents tampering
- **Timestamp**: Built-in token age verification

### Key Management

**Generate key once**:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Output example: "mJeqxHGqL8z9aKZJh7VxQ-8YWJdKLMNoPQRsTuVwXyZ="
```

**Store in Google Cloud Secret Manager**:
```bash
echo -n "mJeqxHGqL8z9aKZJh7VxQ-8YWJdKLMNoPQRsTuVwXyZ=" | \
  gcloud secrets create OAUTH_STORAGE_ENCRYPTION_KEY --data-file=-
```

**Access in Cloud Run**:
```python
from google.cloud import secretmanager

def get_encryption_key() -> bytes:
    """Fetch encryption key from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/OAUTH_STORAGE_ENCRYPTION_KEY/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data
```

### Rationale

- **Security**: OAuth secrets encrypted at rest (defense in depth)
- **Compliance**: Meets security best practices for credential storage
- **Transparency**: No changes to storage backend implementation
- **Standard crypto**: Uses battle-tested `cryptography.fernet` library
- **Wrapper design**: Composable, testable, maintainable

### Alternatives Considered

1. **No encryption**: ❌ Exposes OAuth tokens in plaintext
2. **PostgreSQL encryption**: ✅ Can use in addition (column-level encryption)
3. **Application-level encryption in storage**: ❌ Couples encryption to storage implementation
4. **FernetEncryptionWrapper**: ✅ **Selected** - Clean separation of concerns

## 4. Database Schema

### Decision
**Use simple two-column key-value schema with JSONB**

### Table Structure

```sql
CREATE TABLE IF NOT EXISTS oauth_clients (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS oauth_clients_updated_at_idx
ON oauth_clients(updated_at);
```

### Schema Details

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `key` | `TEXT` | `PRIMARY KEY` | Composite key: `"collection:actual_key"` or just `"key"` |
| `value` | `JSONB` | `NOT NULL` | OAuth client data (encrypted if using FernetEncryptionWrapper) |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Last update time (for cleanup) |

### Key Format

```python
# Without collection
key = "some_key_123"

# With collection (OAuth clients use this)
key = "oauth_clients:client_id_abc123"
```

### Example OAuth Client Data

**Unencrypted (stored in `value` column)**:
```json
{
  "client_id": "Ov23liAbcDefGhiJkLmN",
  "client_secret": "ghs_16CharacterPrefix...",
  "redirect_uris": ["https://chatgpt.com/aip/oauth/callback"],
  "grant_types": ["authorization_code", "refresh_token"],
  "client_name": "ChatGPT",
  "created_at": "2025-11-06T10:30:00Z"
}
```

**Encrypted (with FernetEncryptionWrapper)**:
```json
{
  "_encrypted": true,
  "data": "gAAAAABmSomeFernetEncryptedTokenHere..."
}
```

### Indexes

```sql
-- Index for cleanup queries (delete old unused clients)
CREATE INDEX oauth_clients_updated_at_idx ON oauth_clients(updated_at);
```

### Cleanup Strategy

```python
# Example: Remove OAuth clients inactive for 90 days
DELETE FROM oauth_clients
WHERE updated_at < NOW() - INTERVAL '90 days';
```

### Rationale

- **Simple schema**: Two-column key-value design (minimal complexity)
- **JSONB type**: Efficient storage, enables PostgreSQL JSON queries if needed
- **Timestamps**: Enable cleanup of stale OAuth sessions
- **Single index**: Minimal overhead, optimizes cleanup queries
- **Already exists**: Schema matches existing `/home/user/skai-fastmcp-cloudrun/src/auth/postgres_storage.py` implementation

### Alternatives Considered

1. **Separate columns for OAuth fields**: ❌ More complex, not extensible
2. **JSON (not JSONB)**: ❌ Slower queries, no indexing
3. **Key-value with JSONB**: ✅ **Selected** - Simple, flexible, performant

## 5. Breaking Changes (FastMCP 2.12.5 → 2.13.0)

### Decision
**Upgrade is safe - minimal breaking changes, none affect current codebase**

### Breaking Changes Identified

#### 1. Lifespan Parameter Behavior ⚠️

**Change**: `lifespan` now refers to server lifecycle (not per-client session)

**Impact**: ✅ **None** - Current codebase doesn't use `lifespan` parameter

#### 2. MCP Protocol Version (1.16 → 1.17+)

**Change**: Upgraded to MCP 1.17+ with RFC 9728 compliance

**Impact**: ✅ **None** - Protocol changes handled internally by FastMCP

### New Features (Non-Breaking)

1. **Storage backend support**: `client_storage` parameter (opt-in)
2. **Pydantic input validation**: Better type checking for tool parameters
3. **Icon support**: `@mcp.tool(icon="🔍")` for visual indicators
4. **Improved Context API**: Enhanced request context access

### Dependency Updates Required

```toml
[project.dependencies]
fastmcp = "^2.13.0"  # Upgrade from 2.12.5
py-key-value-aio = "^0.2.8"  # NEW: For storage backends
cryptography = "^41.0.0"  # Already installed (no change)
```

### Compatibility Matrix

| Feature | 2.12.5 | 2.13.0 | Change Required? |
|---------|--------|--------|------------------|
| Tool definitions | ✅ | ✅ | No |
| Resource definitions | ✅ | ✅ | No |
| Prompt definitions | ✅ | ✅ | No |
| GitHub OAuth | ✅ | ✅ | No (enhanced) |
| Context API | ✅ | ✅ Enhanced | No (backward compatible) |
| Lifespan parameter | ✅ | ⚠️ Changed | Not used (no impact) |
| Storage backends | ❌ | ✅ NEW | Opt-in (new feature) |
| Icon support | ❌ | ✅ NEW | Opt-in (new feature) |

### Testing Strategy

```bash
# 1. Update dependency
uv pip install fastmcp>=2.13.0 py-key-value-aio

# 2. Run existing tests
uv run pytest tests/ -v

# 3. Test OAuth configuration
uv run pytest tests/test_oauth_config_tdd.py -v

# 4. Test server startup
DANGEROUSLY_OMIT_AUTH=false uv run fastmcp dev src/server.py

# 5. Test OAuth persistence
# - Authenticate with ChatGPT
# - Restart server
# - Verify ChatGPT can still use tools without re-auth
```

### Rationale for Upgrade

✅ **Recommend immediate upgrade**:
1. **Critical feature**: Persistent OAuth storage solves "Client Not Registered" issue
2. **Low risk**: No breaking changes affect current codebase
3. **Better DX**: Pydantic validation, icons, improved Context API
4. **Future-proof**: MCP 1.17+ compliance ensures compatibility

## 6. Implementation Approach

### Decision
**Use existing PostgresKVStorage with minor updates**

### Current Implementation Status

**File**: `/home/user/skai-fastmcp-cloudrun/src/auth/postgres_storage.py`

**Status**: ✅ **90% compatible** with AsyncKeyValue protocol

**Required changes**:
1. Fix `delete()` return type: `None` → `bool`
2. Add missing methods: `get_many()`, `put_many()`, `delete_many()`, `ttl()`
3. Update imports: Use `py-key-value-aio` types

### Minimal Implementation (Phase 1)

```python
from key_value.aio.protocols.key_value import AsyncKeyValue
from typing import Any, Sequence

class PostgresKVStorage(AsyncKeyValue):
    """PostgreSQL-backed key-value storage for OAuth clients."""

    async def get(
        self,
        key: str,
        collection: str | None = None
    ) -> dict[str, Any] | None:
        # Existing implementation (no changes)
        ...

    async def put(
        self,
        key: str,
        value: dict[str, Any],
        collection: str | None = None,
        ttl: float | None = None
    ) -> None:
        # Existing implementation (add TTL support)
        ...

    async def delete(
        self,
        key: str,
        collection: str | None = None
    ) -> bool:  # CHANGE: Return bool instead of None
        # Existing implementation + return True if deleted
        ...

    # NEW: Add bulk operations for performance
    async def get_many(
        self,
        keys: list[str],
        collection: str | None = None
    ) -> list[dict[str, Any] | None]:
        return [await self.get(key, collection) for key in keys]

    async def put_many(
        self,
        keys: list[str],
        values: Sequence[dict[str, Any]],
        collection: str | None = None,
        ttl: float | None = None
    ) -> None:
        for key, value in zip(keys, values):
            await self.put(key, value, collection, ttl)

    async def delete_many(
        self,
        keys: list[str],
        collection: str | None = None
    ) -> int:
        count = 0
        for key in keys:
            if await self.delete(key, collection):
                count += 1
        return count

    async def ttl(
        self,
        key: str,
        collection: str | None = None
    ) -> tuple[dict[str, Any] | None, float | None]:
        value = await self.get(key, collection)
        # TODO: Calculate TTL from updated_at + ttl columns
        return (value, None)  # Return None for TTL (not implemented yet)
```

### Production Implementation (Phase 2)

Add encryption wrapper in `src/server.py`:

```python
from src.auth.postgres_storage import PostgresKVStorage
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet
from google.cloud import secretmanager

def get_oauth_storage() -> AsyncKeyValue:
    """Create encrypted OAuth storage backend."""
    # Get encryption key from Secret Manager
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/OAUTH_STORAGE_ENCRYPTION_KEY/versions/latest"
    response = client.access_secret_version(request={"name": name})
    encryption_key = response.payload.data

    # Create PostgreSQL storage
    postgres_storage = PostgresKVStorage()

    # Wrap with encryption
    return FernetEncryptionWrapper(
        key_value=postgres_storage,
        fernet=Fernet(encryption_key)
    )

# Use in GitHubProvider
auth_provider = GitHubProvider(
    client_storage=get_oauth_storage()
)
```

### Rationale

- **Reuse existing code**: PostgresKVStorage already 90% compatible
- **Minimal changes**: Only fix return types and add bulk methods
- **Phased approach**: Phase 1 (basic persistence) → Phase 2 (encryption)
- **Testable**: Can test unencrypted first, add encryption later

### Alternatives Considered

1. **Start from scratch**: ❌ Duplicate work, existing implementation is good
2. **Use different storage**: ❌ PostgreSQL already deployed and working
3. **Update existing PostgresKVStorage**: ✅ **Selected** - Minimal changes, reuse code

## Summary

### Key Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| **Storage backend** | PostgresKVStorage (existing) | Already implemented, uses Cloud SQL |
| **Encryption** | FernetEncryptionWrapper | Standard, transparent, secure |
| **Database schema** | Keep existing `oauth_clients` table | Already compatible, no migration |
| **FastMCP version** | Upgrade to 2.13.0 | Low risk, enables persistence |
| **Interface** | Implement AsyncKeyValue protocol | Standard protocol, ecosystem support |
| **Key management** | Google Cloud Secret Manager | Secure, managed, auditable |

### Files to Modify

1. `/home/user/skai-fastmcp-cloudrun/pyproject.toml` - Update dependencies
2. `/home/user/skai-fastmcp-cloudrun/src/auth/postgres_storage.py` - Fix return types, add bulk methods
3. `/home/user/skai-fastmcp-cloudrun/src/server.py` - Add `client_storage` parameter
4. `/home/user/skai-fastmcp-cloudrun/tests/test_oauth_config_tdd.py` - Add persistence tests

### Dependencies to Add

```toml
py-key-value-aio = "^0.2.8"  # AsyncKeyValue protocol + FernetEncryptionWrapper
```

### Environment Variables to Add

```bash
# Generate once: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
OAUTH_STORAGE_ENCRYPTION_KEY="<32-byte-base64-key>"

# Generate once: openssl rand -base64 32
JWT_SIGNING_KEY="<random-secret>"
```

### Success Criteria Validation

| Criterion | How to Verify |
|-----------|---------------|
| SC-001: 7-day continuous auth | ChatGPT works without re-auth for 7 days |
| SC-002: 100% restart survival | OAuth clients persist across all restarts |
| SC-003: Zero "Client Not Registered" | No errors after deployment |
| SC-004: Encrypted secrets | Inspect database, verify encrypted values |
| SC-005: <2s startup increase | Measure server startup time |
| SC-006: <10s auth flow | Measure OAuth flow from start to tool access |
