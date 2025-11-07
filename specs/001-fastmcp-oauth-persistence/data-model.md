# Data Model: OAuth Client Persistence

**Feature**: FastMCP 2.13.0 Upgrade with Persistent OAuth Storage
**Date**: 2025-11-06

## Entities

### 1. OAuth Client Registration

**Description**: Represents a dynamically registered MCP client (e.g., ChatGPT) that has authenticated via GitHub OAuth.

**Storage**: PostgreSQL `oauth_clients` table, key-value format

**Key Format**: `"oauth_clients:{client_id}"`

**Fields**:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `client_id` | `str` | Yes | Unique OAuth client identifier | `"Ov23liAbcDefGhiJkLmN"` |
| `client_secret` | `str` | Yes | OAuth client secret (encrypted at rest) | `"ghs_16CharacterPrefix..."` |
| `redirect_uris` | `list[str]` | Yes | Allowed OAuth callback URLs | `["https://chatgpt.com/aip/oauth/callback"]` |
| `grant_types` | `list[str]` | Yes | Allowed OAuth grant types | `["authorization_code", "refresh_token"]` |
| `client_name` | `str` | No | Human-readable client name | `"ChatGPT"` |
| `created_at` | `str` (ISO 8601) | Yes | Registration timestamp | `"2025-11-06T10:30:00Z"` |

**Relationships**: None (standalone entity)

**Lifecycle**:
- **Created**: When client registers via `/register` endpoint
- **Read**: On every authenticated request (token validation)
- **Updated**: Never (OAuth clients are immutable after creation)
- **Deleted**: When client explicitly unregisters (rare)

**Validation Rules**:
- `client_id` must be unique across all clients
- `redirect_uris` must contain at least one HTTPS URL
- `grant_types` must include `"authorization_code"`

**State Transitions**: None (immutable after creation)

---

### 2. Encryption Key

**Description**: Fernet symmetric encryption key used to encrypt/decrypt OAuth client secrets at rest.

**Storage**: Google Cloud Secret Manager (`OAUTH_STORAGE_ENCRYPTION_KEY`)

**Format**: Base64-encoded 32-byte key

**Fields**:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `key` | `bytes` | Yes | 32-byte encryption key | `b'...'` (32 bytes) |
| `key_base64` | `str` | Yes | Base64-encoded key for environment | `"mJeqxHGqL8z9aKZJh7VxQ-8YWJdKLMNoPQRsTuVwXyZ="` |

**Relationships**: Used by FernetEncryptionWrapper to encrypt OAuth Client secrets

**Lifecycle**:
- **Created**: One-time setup using `Fernet.generate_key()`
- **Read**: On every server startup (from Secret Manager)
- **Updated**: Only during key rotation (requires all clients to re-register)
- **Deleted**: Never (loss causes all OAuth clients to become invalid)

**Validation Rules**:
- Must be exactly 32 bytes
- Must be valid Fernet key (base64-encoded)
- Must be stored in Secret Manager (not environment variables)

**State Transitions**: None (static key)

---

### 3. Storage Backend (PostgresKVStorage)

**Description**: PostgreSQL implementation of AsyncKeyValue protocol for OAuth client persistence.

**Interface**: `key_value.aio.protocols.key_value.AsyncKeyValue`

**Database**: Cloud SQL PostgreSQL (`hansard` database, `oauth_clients` table)

**Methods**:

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `get` | `key: str, collection: str \| None` | `dict[str, Any] \| None` | Retrieve OAuth client by key |
| `put` | `key: str, value: dict[str, Any], collection: str \| None, ttl: float \| None` | `None` | Store OAuth client |
| `delete` | `key: str, collection: str \| None` | `bool` | Delete OAuth client (returns True if deleted) |
| `get_many` | `keys: list[str], collection: str \| None` | `list[dict[str, Any] \| None]` | Bulk get operation |
| `put_many` | `keys: list[str], values: Sequence[dict[str, Any]], collection: str \| None, ttl: float \| None` | `None` | Bulk put operation |
| `delete_many` | `keys: list[str], collection: str \| None` | `int` | Bulk delete (returns count) |
| `ttl` | `key: str, collection: str \| None` | `tuple[dict[str, Any] \| None, float \| None]` | Get value and TTL |

**Relationships**:
- Uses Cloud SQL PostgreSQL database
- Wrapped by FernetEncryptionWrapper for encryption
- Used by GitHubProvider for OAuth client persistence

**Lifecycle**:
- **Created**: On first server startup
- **Used**: On every OAuth operation (registration, authentication)
- **Closed**: On server shutdown (connection cleanup)

**Validation Rules**:
- All keys must be non-empty strings
- All values must be JSON-serializable dicts
- Collection parameter is optional (defaults to None)

---

## Database Schema

### Table: `oauth_clients`

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

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `key` | `TEXT` | `PRIMARY KEY` | Composite key: `"collection:actual_key"` |
| `value` | `JSONB` | `NOT NULL` | OAuth client data (encrypted) |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Record creation time |
| `updated_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Last update time |

**Indexes**:
- `PRIMARY KEY` on `key` (automatic B-tree index)
- `oauth_clients_updated_at_idx` on `updated_at` (for cleanup queries)

**Sample Data** (unencrypted):

```sql
INSERT INTO oauth_clients (key, value) VALUES (
    'oauth_clients:Ov23liAbcDefGhiJkLmN',
    '{
        "client_id": "Ov23liAbcDefGhiJkLmN",
        "client_secret": "ghs_16CharacterPrefix...",
        "redirect_uris": ["https://chatgpt.com/aip/oauth/callback"],
        "grant_types": ["authorization_code", "refresh_token"],
        "client_name": "ChatGPT",
        "created_at": "2025-11-06T10:30:00Z"
    }'::jsonb
);
```

**Sample Data** (with encryption):

```sql
INSERT INTO oauth_clients (key, value) VALUES (
    'oauth_clients:Ov23liAbcDefGhiJkLmN',
    '{
        "_encrypted": true,
        "data": "gAAAAABmSomeFernetEncryptedTokenHereWithHMACAuthentication..."
    }'::jsonb
);
```

---

## Data Flow

### 1. OAuth Client Registration Flow

```
┌─────────────┐
│   ChatGPT   │
└──────┬──────┘
       │ 1. POST /register
       ▼
┌─────────────────────┐
│  GitHubProvider     │
│  (FastMCP 2.13.0)   │
└──────┬──────────────┘
       │ 2. Generate client_id, client_secret
       ▼
┌─────────────────────────────┐
│  FernetEncryptionWrapper    │
│  (encrypts client_secret)   │
└──────┬──────────────────────┘
       │ 3. put(key="oauth_clients:{client_id}", value={...})
       ▼
┌─────────────────────┐
│  PostgresKVStorage  │
└──────┬──────────────┘
       │ 4. INSERT INTO oauth_clients (key, value)
       ▼
┌─────────────────────┐
│  PostgreSQL DB      │
│  (Cloud SQL)        │
└─────────────────────┘
```

### 2. OAuth Token Validation Flow

```
┌─────────────┐
│   ChatGPT   │
└──────┬──────┘
       │ 1. Request with Authorization: Bearer {token}
       ▼
┌─────────────────────┐
│  GitHubProvider     │
│  (validate token)   │
└──────┬──────────────┘
       │ 2. Extract client_id from token
       │ 3. get(key="oauth_clients:{client_id}")
       ▼
┌─────────────────────────────┐
│  FernetEncryptionWrapper    │
│  (decrypts client_secret)   │
└──────┬──────────────────────┘
       │ 4. SELECT value FROM oauth_clients WHERE key=...
       ▼
┌─────────────────────┐
│  PostgresKVStorage  │
└──────┬──────────────┘
       │ 5. Return OAuth client data
       ▼
┌─────────────────────┐
│  GitHubProvider     │
│  (validates token)  │
└─────────────────────┘
```

### 3. Server Restart Flow (Persistence Test)

```
┌─────────────────────┐
│  Server restarts    │
└──────┬──────────────┘
       │ 1. Load encryption key from Secret Manager
       ▼
┌─────────────────────────────┐
│  FernetEncryptionWrapper    │
│  (initialized with key)     │
└──────┬──────────────────────┘
       │ 2. Wrap PostgresKVStorage
       ▼
┌─────────────────────┐
│  GitHubProvider     │
│  client_storage=... │
└──────┬──────────────┘
       │ 3. ChatGPT sends request with old token
       ▼
┌─────────────────────┐
│  GitHubProvider     │
│  (loads client from │
│   persistent store) │
└──────┬──────────────┘
       │ 4. get(key="oauth_clients:{client_id}")
       ▼
┌─────────────────────┐
│  PostgreSQL DB      │
│  (client still      │
│   exists!)          │
└─────────────────────┘
```

---

## Error Handling

### Error Scenarios

| Scenario | Behavior | Recovery |
|----------|----------|----------|
| Database unavailable during registration | Return HTTP 503 to client | Client retries registration |
| Encryption key not found | Server fails to start | Fix Secret Manager configuration |
| Corrupted encrypted data | Return HTTP 401 (invalid client) | Client must re-register |
| Duplicate client_id | PostgreSQL UNIQUE constraint error | Return HTTP 400 (already registered) |
| Invalid redirect_uri | FastMCP validation error | Return HTTP 400 (invalid request) |
| Database connection timeout | Retry with exponential backoff | Log error, return HTTP 503 |

### Data Integrity

- **Encryption**: All OAuth secrets encrypted with Fernet (AES-128 + HMAC)
- **Transactions**: Single-row operations (atomic by default in PostgreSQL)
- **Constraints**: PRIMARY KEY on `key` prevents duplicates
- **Backup**: Cloud SQL automatic backups (7-day retention)

---

## Performance Considerations

### Query Patterns

| Operation | Query | Frequency | Index Used |
|-----------|-------|-----------|----------|
| Register client | `INSERT INTO oauth_clients (key, value)` | Rare (once per client) | None |
| Validate token | `SELECT value FROM oauth_clients WHERE key = $1` | Every request | PRIMARY KEY |
| List clients | `SELECT * FROM oauth_clients` | Never (not implemented) | Full scan |
| Cleanup old clients | `DELETE FROM oauth_clients WHERE updated_at < $1` | Daily (cron) | `updated_at` index |

### Optimization Strategies

1. **Connection pooling**: Use Cloud SQL Connector connection pooling
2. **Index on key**: PRIMARY KEY provides B-tree index (O(log n) lookups)
3. **JSONB type**: Efficient storage, faster than JSON text
4. **Minimal columns**: Only key, value, timestamps (no redundant data)
5. **No JOINs**: Single-table key-value design (no foreign keys)

### Expected Performance

- **Registration**: <100ms (single INSERT)
- **Token validation**: <50ms (single SELECT with PRIMARY KEY lookup)
- **Cleanup**: <1s (batch DELETE with index scan)
- **Database size**: ~1KB per client (minimal storage impact)

---

## Security

### Encryption at Rest

- **Application-level**: FernetEncryptionWrapper encrypts `client_secret` in `value` column
- **Database-level**: Cloud SQL automatic encryption of data at rest
- **Transport-level**: TLS 1.3 for all database connections

### Access Control

- **Database user**: Service account with IAM authentication (no passwords)
- **Permissions**: `SELECT`, `INSERT`, `UPDATE`, `DELETE` on `oauth_clients` table only
- **Network**: Private IP for Cloud SQL (no public internet access)
- **Secret Manager**: Service account needs `roles/secretmanager.secretAccessor` role

### Audit Trail

- **Cloud SQL logs**: All queries logged (can enable query logging)
- **Application logs**: OAuth registration/validation events logged
- **Secret Manager audit**: Key access logged to Cloud Audit Logs
- **Timestamps**: `created_at`, `updated_at` for forensics
