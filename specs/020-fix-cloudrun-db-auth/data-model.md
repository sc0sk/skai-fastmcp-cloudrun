# Data Model: IAM Authentication State

**Feature**: 019-fix-cloudrun-db-auth
**Date**: 2025-11-06
**Purpose**: Define the state model for IAM principal detection and Cloud SQL connection management

---

## Overview

This feature modifies internal connection state management to properly detect and use IAM principals for Cloud SQL authentication. There are no user-facing data model changes - this is purely internal state.

---

## Entities

### 1. IAMPrincipal

**Description**: Represents the detected identity used for database authentication.

**Attributes**:
- `email` (string, required): Service account email or user email
  - Format: `{account}@{project}.iam.gserviceaccount.com` (service account)
  - Format: `{user}@gmail.com` (user account, local dev only)
  - Validation: Must contain `@` symbol, not empty, not `"default"`
- `detection_method` (enum, required): How the principal was detected
  - Values: `METADATA_SERVICE`, `ADC_CREDENTIALS`, `GCLOUD_CONFIG`, `FALLBACK`
- `is_valid` (boolean, required): Whether the principal is usable for auth
  - True: Email is non-empty, non-"default", contains `@`
  - False: Detection failed or returned invalid value

**State Transitions**:
1. Initial: `email=None, detection_method=None, is_valid=False`
2. After metadata check: `email="{sa}@{proj}.iam...", detection_method=METADATA_SERVICE, is_valid=True`
3. After ADC fallback: `email="{detected}", detection_method=ADC_CREDENTIALS, is_valid={validated}`
4. After all failures: `email="postgres", detection_method=FALLBACK, is_valid=False`

**Validation Rules**:
- Email MUST NOT be empty string
- Email MUST NOT be `"default"` (placeholder value)
- Email MUST contain `@` symbol
- If validation fails, `is_valid=False`

**Example Values**:
```python
# Valid - Cloud Run metadata service
IAMPrincipal(
    email="666924716777-compute@developer.gserviceaccount.com",
    detection_method="METADATA_SERVICE",
    is_valid=True
)

# Valid - Local ADC
IAMPrincipal(
    email="fastmcp-server@skai-fastmcp-cloudrun.iam.gserviceaccount.com",
    detection_method="ADC_CREDENTIALS",
    is_valid=True
)

# Invalid - Default placeholder
IAMPrincipal(
    email="default",
    detection_method="ADC_CREDENTIALS",
    is_valid=False
)

# Fallback - No detection succeeded
IAMPrincipal(
    email="postgres",
    detection_method="FALLBACK",
    is_valid=False
)
```

---

### 2. ConnectionConfig

**Description**: Configuration for Cloud SQL connection with resolved IAM user.

**Attributes**:
- `instance_connection_name` (string, required): Cloud SQL instance identifier
  - Format: `{project_id}:{region}:{instance_name}`
  - Example: `skai-fastmcp-cloudrun:us-central1:hansard-db-v2`
- `database` (string, required): Target database name
  - Example: `hansard`
- `iam_principal` (IAMPrincipal, required): Detected IAM user for authentication
- `driver` (string, required): Database driver name
  - Fixed value: `pg8000` (only driver supporting IAM auth)
- `pool_size` (integer, required): Maximum active connections
  - Default: 5 (optimized for Cloud Run)
- `max_overflow` (integer, required): Additional connections under load
  - Default: 2
- `pool_timeout` (integer, required): Seconds to wait for connection
  - Default: 30

**Relationships**:
- Has-one `IAMPrincipal` (composition)
- Used-by `CloudSQLEngine` to create SQLAlchemy engine

**Validation Rules**:
- `instance_connection_name` MUST match format `{proj}:{region}:{instance}`
- `database` MUST NOT be empty
- `iam_principal.is_valid` SHOULD be True (warning if False)
- `pool_size` MUST be > 0
- `max_overflow` MUST be >= 0

**Example Values**:
```python
# Cloud Run configuration
ConnectionConfig(
    instance_connection_name="skai-fastmcp-cloudrun:us-central1:hansard-db-v2",
    database="hansard",
    iam_principal=IAMPrincipal(
        email="666924716777-compute@developer.gserviceaccount.com",
        detection_method="METADATA_SERVICE",
        is_valid=True
    ),
    driver="pg8000",
    pool_size=5,
    max_overflow=2,
    pool_timeout=30
)
```

---

### 3. ConnectionState

**Description**: Runtime state of database connection attempts and health.

**Attributes**:
- `status` (enum, required): Current connection state
  - Values: `INITIALIZING`, `CONNECTED`, `FAILED`, `RETRYING`, `CLOSED`
- `attempt_count` (integer, required): Number of connection attempts
  - Range: 0-3 (max retries from @with_retry decorator)
- `last_error` (string, optional): Most recent error message
  - Populated on FAILED or RETRYING states
- `connected_at` (datetime, optional): When connection succeeded
  - Populated on CONNECTED state
- `token_refreshed_at` (datetime, optional): Last OAuth2 token refresh
  - Used to track token expiry (tokens valid ~1 hour)

**State Transitions**:
```
INITIALIZING (attempt_count=0)
    ↓ (connection attempt)
    ├─→ CONNECTED (attempt_count=1, connected_at=now)
    ├─→ RETRYING (attempt_count=1, last_error="timeout")
    │     ↓ (retry attempt)
    │     ├─→ CONNECTED (attempt_count=2)
    │     └─→ FAILED (attempt_count=3, last_error="max retries")
    └─→ FAILED (attempt_count=1, last_error="permanent error")

CONNECTED
    ↓ (token expiry or maintenance)
    ├─→ RETRYING (token refresh failed)
    └─→ CONNECTED (token refreshed, token_refreshed_at=now)

CLOSED (application shutdown)
```

**Validation Rules**:
- `attempt_count` MUST be 0-3
- `last_error` SHOULD be set when `status=FAILED` or `status=RETRYING`
- `connected_at` SHOULD be set when `status=CONNECTED`
- `token_refreshed_at` SHOULD be recent (<1 hour) when `status=CONNECTED`

**Example Values**:
```python
# Successful connection
ConnectionState(
    status="CONNECTED",
    attempt_count=1,
    last_error=None,
    connected_at=datetime(2025, 11, 6, 14, 30, 0),
    token_refreshed_at=datetime(2025, 11, 6, 14, 30, 0)
)

# Failed after retries
ConnectionState(
    status="FAILED",
    attempt_count=3,
    last_error="FATAL: role \"default\" does not exist",
    connected_at=None,
    token_refreshed_at=None
)

# Retrying transient error
ConnectionState(
    status="RETRYING",
    attempt_count=2,
    last_error="OperationalError: connection timeout",
    connected_at=None,
    token_refreshed_at=None
)
```

---

## Relationships

```
CloudSQLEngine
    ├─ has-one ConnectionConfig
    │     └─ has-one IAMPrincipal
    └─ maintains ConnectionState
```

**Lifecycle**:
1. `CloudSQLEngine.__init__()`: Creates ConnectionConfig with detected IAMPrincipal
2. `getconn()`: Initializes ConnectionState, attempts connection
3. Retry loop: Updates ConnectionState on each attempt
4. Success: ConnectionState.status = CONNECTED
5. Failure: ConnectionState.status = FAILED, raises exception
6. `close()`: ConnectionState.status = CLOSED

---

## No Database Schema Changes

**Important**: This feature does NOT modify database tables. The entities above are runtime state only (in-memory Python objects).

Existing database schema remains unchanged:
- `langchain_pg_collection`: Vector collection metadata
- `langchain_pg_embedding`: Vector embeddings with JSONB metadata
- `speeches`: Speech metadata (speaker, date, chamber, etc.)

---

## Logging Schema

**Connection Attempt Log** (INFO level):
```json
{
  "event": "CloudSQLEngine connecting",
  "instance": "skai-fastmcp-cloudrun:us-central1:hansard-db-v2",
  "database": "hansard",
  "driver": "pg8000",
  "iam_auth": true,
  "iam_user": "666924716777-compute@developer.gserviceaccount.com",
  "detection_method": "METADATA_SERVICE",
  "attempt": 1
}
```

**Connection Success Log** (INFO level):
```json
{
  "event": "CloudSQLEngine connected",
  "instance": "skai-fastmcp-cloudrun:us-central1:hansard-db-v2",
  "database": "hansard",
  "duration_ms": 234,
  "iam_user": "666924716777-compute@developer.gserviceaccount.com"
}
```

**Connection Failure Log** (ERROR level):
```json
{
  "event": "CloudSQLEngine connection failed",
  "instance": "skai-fastmcp-cloudrun:us-central1:hansard-db-v2",
  "database": "hansard",
  "error": "FATAL: role \"default\" does not exist",
  "iam_user_attempted": "default",
  "detection_method": "ADC_CREDENTIALS",
  "suggestion": "Ensure database user matches service account email. Check IAM permissions."
}
```

---

## Success Validation

Connection is considered successful when:
1. ✅ `IAMPrincipal.is_valid == True`
2. ✅ `IAMPrincipal.email` matches PostgreSQL database user
3. ✅ `ConnectionState.status == CONNECTED`
4. ✅ `ConnectionState.attempt_count <= 3`
5. ✅ Test query succeeds: `SELECT 1`

Connection is considered failed when:
1. ❌ `IAMPrincipal.is_valid == False` and no fallback works
2. ❌ `ConnectionState.attempt_count >= 3` with `status=FAILED`
3. ❌ PostgreSQL returns authentication error
4. ❌ Cloud SQL Connector raises exception

---

**Data Model Complete** - Ready for quickstart.md and contracts generation.
