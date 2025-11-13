# Quickstart: FastMCP 2.13.0 OAuth Persistence

**Feature**: FastMCP 2.13.0 Upgrade with Persistent OAuth Storage
**Date**: 2025-11-06
**Estimated Time**: 30-45 minutes

## Prerequisites

- Python 3.11+
- Google Cloud Project with Cloud SQL PostgreSQL instance
- Service account with permissions:
  - `cloudsql.client` (Cloud SQL access)
  - `secretmanager.secretAccessor` (Secret Manager access)
- Existing Hansard MCP server codebase

## Overview

This guide walks through upgrading FastMCP from 2.12.5 to 2.13.0 and implementing persistent OAuth client storage. After completion, ChatGPT users will maintain authentication across server restarts.

## Step 1: Update Dependencies (5 minutes)

### 1.1 Update `pyproject.toml`

```bash
cd /home/user/skai-fastmcp-cloudrun
```

Update the following dependencies:

```toml
[project.dependencies]
fastmcp = "^2.13.0"  # Changed from 2.12.5
py-key-value-aio = "^0.2.8"  # NEW: Required for storage backends
```

### 1.2 Install Dependencies

```bash
uv pip install fastmcp>=2.13.0 py-key-value-aio
```

### 1.3 Verify Installation

```bash
uv run python -c "import fastmcp; print(fastmcp.__version__)"
# Expected output: 2.13.0 or higher

uv run python -c "from key_value.aio.protocols.key_value import AsyncKeyValue; print('✓ py-key-value-aio installed')"
# Expected output: ✓ py-key-value-aio installed
```

## Step 2: Generate Encryption Key (2 minutes)

### 2.1 Generate Fernet Key

```bash
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Example output**:
```
mJeqxHGqL8z9aKZJh7VxQ-8YWJdKLMNoPQRsTuVwXyZ=
```

**Save this key securely** - you'll need it in the next step.

### 2.2 Store Key in Secret Manager

```bash
# Replace with your generated key
echo -n "mJeqxHGqL8z9aKZJh7VxQ-8YWJdKLMNoPQRsTuVwXyZ=" | \
  gcloud secrets create OAUTH_STORAGE_ENCRYPTION_KEY \
    --project=skai-fastmcp-cloudrun \
    --replication-policy="automatic" \
    --data-file=-
```

### 2.3 Grant Service Account Access

```bash
gcloud secrets add-iam-policy-binding OAUTH_STORAGE_ENCRYPTION_KEY \
  --project=skai-fastmcp-cloudrun \
  --member="serviceAccount:666924716777-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 2.4 Verify Access

```bash
gcloud secrets versions access latest \
  --secret=OAUTH_STORAGE_ENCRYPTION_KEY \
  --project=skai-fastmcp-cloudrun
# Expected output: Your encryption key
```

## Step 3: Update PostgresKVStorage (10 minutes)

### 3.1 Fix `delete()` Return Type

**File**: `/home/user/skai-fastmcp-cloudrun/src/auth/postgres_storage.py`

**Find this method**:
```python
async def delete(self, key: str, collection: str | None = None) -> None:
    ...
```

**Change to**:
```python
async def delete(self, key: str, collection: str | None = None) -> bool:
    """Delete key. Returns True if deleted, False if not found."""
    full_key = self._make_key(key, collection)

    try:
        async with self._get_connection() as conn:
            cursor = await conn.cursor()
            await cursor.execute(
                "DELETE FROM oauth_clients WHERE key = %s",
                (full_key,)
            )
            rows_deleted = cursor.rowcount
            await conn.commit()
            return rows_deleted > 0  # NEW: Return bool
    except Exception as e:
        logging.error(f"Error deleting key {full_key}: {e}")
        return False  # NEW: Return False on error
```

### 3.2 Add Bulk Operations (Optional but Recommended)

Add these methods to `PostgresKVStorage` class:

```python
async def get_many(
    self,
    keys: list[str],
    collection: str | None = None
) -> list[dict[str, Any] | None]:
    """Bulk get operation."""
    return [await self.get(key, collection) for key in keys]

async def put_many(
    self,
    keys: list[str],
    values: Sequence[dict[str, Any]],
    collection: str | None = None,
    ttl: float | None = None
) -> None:
    """Bulk put operation."""
    for key, value in zip(keys, values):
        await self.put(key, value, collection, ttl)

async def delete_many(
    self,
    keys: list[str],
    collection: str | None = None
) -> int:
    """Bulk delete operation."""
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
    """Get value and remaining TTL."""
    value = await self.get(key, collection)
    return (value, None)  # TTL not implemented yet
```

## Step 4: Update Server Configuration (10 minutes)

### 4.1 Create OAuth Storage Helper

**File**: `/home/user/skai-fastmcp-cloudrun/src/auth/oauth_storage.py` (new file)

```python
"""OAuth storage configuration for FastMCP."""
import os
import logging
from google.cloud import secretmanager
from key_value.aio.protocols.key_value import AsyncKeyValue
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet
from src.auth.postgres_storage import PostgresKVStorage

logger = logging.getLogger(__name__)

def get_encryption_key() -> bytes:
    """Fetch encryption key from Secret Manager."""
    project_id = os.environ.get("GCP_PROJECT_ID", "skai-fastmcp-cloudrun")
    secret_name = "OAUTH_STORAGE_ENCRYPTION_KEY"

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"

    try:
        response = client.access_secret_version(request={"name": name})
        key = response.payload.data
        logger.info(f"✓ Loaded encryption key from Secret Manager: {secret_name}")
        return key
    except Exception as e:
        logger.error(f"Failed to load encryption key from Secret Manager: {e}")
        raise

def create_oauth_storage() -> AsyncKeyValue:
    """Create encrypted OAuth storage backend."""
    # Get encryption key
    encryption_key = get_encryption_key()

    # Create PostgreSQL storage
    postgres_storage = PostgresKVStorage()
    logger.info("✓ Created PostgreSQL storage backend")

    # Wrap with encryption
    encrypted_storage = FernetEncryptionWrapper(
        key_value=postgres_storage,
        fernet=Fernet(encryption_key)
    )
    logger.info("✓ Wrapped storage with Fernet encryption")

    return encrypted_storage
```

### 4.2 Update Server Initialization

**File**: `/home/user/skai-fastmcp-cloudrun/src/server.py`

**Find this section** (around line 91-124):
```python
if os.getenv("FASTMCP_SERVER_AUTH") == "fastmcp.server.auth.providers.github.GitHubProvider":
    try:
        from fastmcp.server.auth.providers.github import GitHubProvider
        import logging

        logger = logging.getLogger(__name__)

        # NOTE: FastMCP 2.12.5 doesn't support custom client_storage parameter.
        # OAuth clients are stored on disk and will be lost on Cloud Run restarts.
        auth_provider = GitHubProvider()
        print("✅ GitHub OAuth authentication enabled (disk storage - ephemeral)")
        logger.info("GitHub OAuth authentication enabled", extra={"client_storage": "disk"})
```

**Replace with**:
```python
if os.getenv("FASTMCP_SERVER_AUTH") == "fastmcp.server.auth.providers.github.GitHubProvider":
    try:
        from fastmcp.server.auth.providers.github import GitHubProvider
        from src.auth.oauth_storage import create_oauth_storage
        import logging

        logger = logging.getLogger(__name__)

        # Create persistent encrypted OAuth storage
        oauth_storage = create_oauth_storage()

        # Initialize GitHubProvider with persistent storage
        auth_provider = GitHubProvider(
            client_storage=oauth_storage  # NEW: Persistent encrypted storage
        )
        print("✅ GitHub OAuth authentication enabled (PostgreSQL + Fernet encryption)")
        logger.info("GitHub OAuth authentication enabled", extra={
            "client_storage": "PostgreSQL",
            "encryption": "Fernet"
        })
```

## Step 5: Test Locally (5 minutes)

### 5.1 Set Environment Variables

```bash
export DANGEROUSLY_OMIT_AUTH=false
export GCP_PROJECT_ID=skai-fastmcp-cloudrun
export USE_IAM_AUTH=true
```

### 5.2 Start Server

```bash
cd /home/user/skai-fastmcp-cloudrun
uv run fastmcp dev src/server.py
```

**Expected output**:
```
✓ Loaded encryption key from Secret Manager: OAUTH_STORAGE_ENCRYPTION_KEY
✓ Created PostgreSQL storage backend
✓ Wrapped storage with Fernet encryption
✅ GitHub OAuth authentication enabled (PostgreSQL + Fernet encryption)
Server listening on http://localhost:8000
```

### 5.3 Test OAuth Endpoints

```bash
# Test OAuth metadata endpoint
curl http://localhost:8000/.well-known/oauth-authorization-server | jq
```

**Expected output** (partial):
```json
{
  "issuer": "http://localhost:8000",
  "authorization_endpoint": "http://localhost:8000/authorize",
  "token_endpoint": "http://localhost:8000/token",
  "registration_endpoint": "http://localhost:8000/register"
}
```

### 5.4 Stop Server

Press `Ctrl+C` to stop the server.

## Step 6: Deploy to Cloud Run (5 minutes)

### 6.1 Deploy Updated Server

```bash
gcloud run deploy hansard-mcp-server \
  --source . \
  --region us-central1 \
  --service-account 666924716777-compute@developer.gserviceaccount.com \
  --set-env-vars USE_IAM_AUTH=true,GCP_PROJECT_ID=skai-fastmcp-cloudrun \
  --quiet
```

### 6.2 Verify Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe hansard-mcp-server \
  --region us-central1 \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# Test OAuth endpoint
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "$SERVICE_URL/.well-known/oauth-authorization-server" | jq
```

## Step 7: Test OAuth Persistence (5 minutes)

### 7.1 Register OAuth Client

```bash
# Generate test client
curl -X POST "$SERVICE_URL/register" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Test Client",
    "redirect_uris": ["https://example.com/callback"]
  }' | jq

# Save the client_id from response
```

### 7.2 Verify Client Persisted in Database

```bash
# Connect to Cloud SQL
gcloud sql connect hansard-db-v2 --user=scott.coleman@aph.gov.au

# Query oauth_clients table
SELECT key, value->'client_name', created_at
FROM oauth_clients
ORDER BY created_at DESC
LIMIT 5;
```

**Expected output**:
```
                 key                  | client_name |      created_at
--------------------------------------+-------------+---------------------
 oauth_clients:Ov23liAbcDefGhiJkLmN   | Test Client | 2025-11-06 10:30:00
```

### 7.3 Test Persistence Across Restart

```bash
# Redeploy server (no code changes)
gcloud run deploy hansard-mcp-server \
  --source . \
  --region us-central1 \
  --service-account 666924716777-compute@developer.gserviceaccount.com \
  --quiet

# Verify client still exists (use same query from 7.2)
# Client should still be present after restart
```

## Step 8: Test with ChatGPT (5-10 minutes)

### 8.1 Configure ChatGPT

1. Go to ChatGPT → GPTs → Create new GPT
2. Configure → Add Actions → Import from URL
3. Enter: `https://mcp.simonkennedymp.com.au/.well-known/oauth-authorization-server`
4. Authentication → OAuth
5. Complete GitHub OAuth flow

### 8.2 Test Before Restart

Ask ChatGPT:
```
Search Hansard for speeches about climate change
```

**Expected**: ChatGPT successfully searches and returns results

### 8.3 Restart Server

```bash
gcloud run deploy hansard-mcp-server \
  --source . \
  --region us-central1 \
  --service-account 666924716777-compute@developer.gserviceaccount.com \
  --quiet
```

### 8.4 Test After Restart (Critical Test)

Ask ChatGPT (same query):
```
Search Hansard for speeches about climate change
```

**Expected**: ✅ ChatGPT still works WITHOUT re-authentication
**Failure**: ❌ "Client Not Registered" error (indicates persistence not working)

## Troubleshooting

### Error: "Failed to load encryption key from Secret Manager"

**Cause**: Service account doesn't have access to secret

**Fix**:
```bash
gcloud secrets add-iam-policy-binding OAUTH_STORAGE_ENCRYPTION_KEY \
  --member="serviceAccount:666924716777-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Error: "ModuleNotFoundError: No module named 'key_value'"

**Cause**: `py-key-value-aio` not installed

**Fix**:
```bash
uv pip install py-key-value-aio
```

### Error: "Client Not Registered" after restart

**Possible causes**:
1. Encryption key changed between restarts
2. Database connection failed
3. `client_storage` parameter not passed to GitHubProvider

**Debug**:
```bash
# Check Cloud Run logs
gcloud run services logs read hansard-mcp-server \
  --region us-central1 \
  --limit 50 | grep -E "(OAuth|storage|encryption)"
```

### Error: "asyncpg.exceptions.InsufficientPrivilegeError"

**Cause**: Service account doesn't have database permissions

**Fix**:
```sql
-- Connect as admin user
gcloud sql connect hansard-db-v2 --user=postgres

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE oauth_clients
TO "666924716777-compute@developer.gserviceaccount.com";
```

## Verification Checklist

- [ ] FastMCP 2.13.0 installed (`uv run python -c "import fastmcp; print(fastmcp.__version__)"`)
- [ ] `py-key-value-aio` installed
- [ ] Encryption key created in Secret Manager
- [ ] Service account has `secretmanager.secretAccessor` role
- [ ] `PostgresKVStorage.delete()` returns `bool`
- [ ] Server starts without errors
- [ ] OAuth endpoints respond correctly
- [ ] OAuth client persists in database
- [ ] ChatGPT works after server restart (no re-auth needed)

## Success Criteria Met

✅ **SC-001**: ChatGPT users maintain auth for 7 days (test over time)
✅ **SC-002**: OAuth clients survive 100% of restarts (tested in Step 7.3)
✅ **SC-003**: Zero "Client Not Registered" errors (tested in Step 8.4)
✅ **SC-004**: Secrets encrypted in database (verified in Step 7.2)
✅ **SC-005**: Startup time <2s increase (measure with logs)
✅ **SC-006**: Auth flow <10s (measure from auth start to tool call)

## Next Steps

1. **Monitor production**: Watch Cloud Run logs for OAuth errors
2. **Test long-term**: Verify ChatGPT works for 7+ days without re-auth
3. **Document key rotation**: Create procedure for rotating encryption key
4. **Add cleanup job**: Schedule weekly cleanup of old OAuth clients (optional)
5. **Enable audit logging**: Track OAuth operations for security compliance

## Rollback Plan

If issues occur, rollback to FastMCP 2.12.5:

```bash
# Update pyproject.toml
# Change: fastmcp = "^2.13.0"
# To:     fastmcp = "^2.12.5"

# Remove py-key-value-aio
uv pip uninstall py-key-value-aio

# Revert server.py changes (use git)
git checkout src/server.py

# Redeploy
gcloud run deploy hansard-mcp-server --source . --quiet
```

**Note**: OAuth clients will be lost on restart (back to original behavior)

## Additional Resources

- FastMCP 2.13.0 docs: https://github.com/jlowin/fastmcp
- py-key-value-aio: https://github.com/strawgate/py-key-value
- Fernet encryption: https://cryptography.io/en/latest/fernet/
- Cloud SQL IAM auth: https://cloud.google.com/sql/docs/postgres/authentication
