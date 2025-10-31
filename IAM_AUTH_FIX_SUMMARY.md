# IAM Authentication Fix Summary

**Date:** October 31, 2025  
**Issue:** `Failed to create vector extension: control characters forbidden: invalid-encoding`  
**Root Cause:** Password authentication with secrets containing control characters (newlines/encoding issues)  
**Resolution:** Enforce IAM DB authentication end-to-end

---

## Changes Made

### 1. Core Code Fixes

#### `src/storage/vector_store.py`
- **Change:** Respect `USE_IAM_AUTH` environment variable
- **Behavior:**
  - When `USE_IAM_AUTH=true/yes/1`: Forces IAM authentication (no passwords)
  - When `USE_IAM_AUTH` is unset/false AND credentials present: Uses password auth (legacy/local)
  - Default: Prefers IAM authentication
- **Password env vars:** Now reads `DATABASE_PASSWORD` (preferred) with `CLOUDSQL_PASSWORD` fallback
- **Logging:** Added info logs to indicate which auth mode is active

#### `src/storage/cloud_sql_engine.py`
- **Change:** Fixed `enable_iam_auth` parameter type
- **Before:** `kwargs["enable_iam_auth"] = "true"` (string)
- **After:** `kwargs["enable_iam_auth"] = True` (boolean)
- **Why:** Cloud SQL Python Connector + pg8000 expects boolean parameter

#### `src/storage/metadata_store.py`
- **Status:** Already supports `USE_IAM_AUTH` override (no changes needed)
- **Behavior:** When `USE_IAM_AUTH` is truthy, clears user/password to force IAM

### 2. Deployment Helper Scripts

Created three executable scripts in `tools/`:

#### `tools/patch_cloud_run_env_use_iam_auth.sh`
**Purpose:** Set `USE_IAM_AUTH=true` on Cloud Run service and trigger new revision

**Usage:**
```bash
./tools/patch_cloud_run_env_use_iam_auth.sh -s hansard-mcp-server -r us-central1 -p skai-fastmcp-cloudrun
```

**Features:**
- Sets `USE_IAM_AUTH=true` environment variable
- Creates new revision (no image rebuild required)
- Shows current relevant env vars after update
- Includes optional commented block to remove password env vars

#### `tools/remove_db_password_envs.sh`
**Purpose:** Remove legacy password env vars from Cloud Run service

**Usage:**
```bash
./tools/remove_db_password_envs.sh -s hansard-mcp-server -r us-central1 -p skai-fastmcp-cloudrun
```

**What it removes:**
- `CLOUDSQL_USER`
- `CLOUDSQL_PASSWORD`
- `DATABASE_PASSWORD`

**Why:** Prevents accidental fallback to password authentication

#### `tools/check_cloud_run_sa_iam.sh`
**Purpose:** Verify Cloud Run service account has required IAM roles

**Usage:**
```bash
./tools/check_cloud_run_sa_iam.sh -s hansard-mcp-server -r us-central1 -p skai-fastmcp-cloudrun
```

**Checks:**
- Prints service account email
- Verifies `roles/cloudsql.client` (required for Cloud SQL Connector)
- Verifies `roles/cloudsql.instanceUser` (required for IAM DB auth token generation)
- Provides grant commands if roles are missing

---

## Deployment Steps

### Step 1: Set IAM Auth Mode
```bash
./tools/patch_cloud_run_env_use_iam_auth.sh
```

**What this does:**
- Sets `USE_IAM_AUTH=true` on the Cloud Run service
- Creates a new revision with the updated environment
- Traffic is automatically sent to the new revision

### Step 2: Verify IAM Roles (Optional but Recommended)
```bash
./tools/check_cloud_run_sa_iam.sh
```

**If roles are missing, grant them:**
```bash
# Example (replace with your actual service account)
gcloud projects add-iam-policy-binding skai-fastmcp-cloudrun \
  --member=serviceAccount:666924716777-compute@developer.gserviceaccount.com \
  --role=roles/cloudsql.instanceUser
```

### Step 3: Remove Password Env Vars (Optional but Recommended)
```bash
./tools/remove_db_password_envs.sh
```

**Why:** Eliminates any chance of accidental password auth fallback

### Step 4: Verify pgvector Extension

If you get extension creation errors after deployment, the pgvector extension may not be installed. Enable it once as a superuser:

**Option A: Using existing script (requires POSTGRES_PASSWORD env var):**
```bash
export POSTGRES_PASSWORD="your-postgres-password"
python3 enable_pgvector_postgres.py
```

**Option B: Manual SQL via Cloud SQL Proxy:**
```bash
# Start proxy (in background or separate terminal)
./cloud_sql_proxy skai-fastmcp-cloudrun:us-central1:hansard-db-v2 &

# Connect and enable extension
psql "host=127.0.0.1 port=5432 dbname=hansard user=postgres" \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Step 5: Test in MCP Inspector
1. Open MCP Inspector in browser (refresh OAuth token if needed)
2. Run `search_hansard_speeches` tool
3. Verify no "control characters forbidden" error
4. Check logs show "Vector store using IAM DB authentication via Cloud SQL Connector"

---

## Technical Details

### Why This Fixes the Error

**Original Error:**
```
Failed to create vector extension: control characters forbidden: invalid-encoding
```

**Root Cause:**
- Password authentication used `CLOUDSQL_PASSWORD` secret
- Secret value contained control characters (e.g., trailing newline: `"password\n"`)
- pg8000 driver rejected the password due to invalid encoding

**Resolution:**
- IAM authentication bypasses password entirely
- Cloud SQL Connector automatically manages IAM tokens
- No opportunity for encoding/control character issues

### IAM DB Authentication Flow

1. **Cloud Run service** runs with service account: `666924716777-compute@developer.gserviceaccount.com`
2. **CloudSQLEngine** detects `user=None, password=None` → triggers IAM mode
3. **Cloud SQL Connector** automatically:
   - Detects service account from environment
   - Requests short-lived DB auth token
   - Passes token to pg8000 driver
4. **PostgreSQL** verifies token and grants connection as IAM user

### IAM User Resolution Priority

The code attempts to resolve the IAM user in this order:

1. Service account email from default credentials (`google.auth.default()`)
2. Metadata service (Cloud Run: `http://metadata.google.internal/...`)
3. `gcloud config get-value account` (local development)
4. Fallback: `"postgres"` (will fail if postgres has password auth)

### Environment Variables Reference

| Variable | Purpose | IAM Mode | Password Mode |
|----------|---------|----------|---------------|
| `USE_IAM_AUTH` | Force IAM when set to `true`/`yes`/`1` | Required | N/A |
| `CLOUDSQL_USER` | Database user | Ignored | Required |
| `DATABASE_PASSWORD` | DB password (preferred) | Ignored | Required |
| `CLOUDSQL_PASSWORD` | DB password (fallback) | Ignored | Optional |
| `GCP_PROJECT_ID` | GCP project ID | Required | Required |
| `GCP_REGION` | Cloud SQL region | Required | Required |
| `CLOUDSQL_INSTANCE` | Cloud SQL instance name | Required | Required |
| `CLOUDSQL_DATABASE` | Database name | Required | Required |

---

## Verification Checklist

- [x] Code changes committed
- [ ] `USE_IAM_AUTH=true` set on Cloud Run service
- [ ] Service account has `roles/cloudsql.client`
- [ ] Service account has `roles/cloudsql.instanceUser`
- [ ] Service account granted database privileges in PostgreSQL
- [ ] pgvector extension enabled in target database
- [ ] Password env vars removed from Cloud Run (optional but recommended)
- [ ] MCP Inspector tool calls succeed
- [ ] Logs show "Vector store using IAM DB authentication"

---

## Rollback Plan

If IAM authentication fails and you need to temporarily revert:

```bash
# Revert to password auth
gcloud run services update hansard-mcp-server \
  --region us-central1 \
  --project skai-fastmcp-cloudrun \
  --update-env-vars USE_IAM_AUTH=false

# Or completely remove the variable
gcloud run services update hansard-mcp-server \
  --region us-central1 \
  --project skai-fastmcp-cloudrun \
  --remove-env-vars USE_IAM_AUTH
```

**Note:** Ensure `CLOUDSQL_USER` and `DATABASE_PASSWORD`/`CLOUDSQL_PASSWORD` are present if reverting.

---

## Additional Resources

- **Cloud SQL IAM Database Authentication:** https://cloud.google.com/sql/docs/postgres/authentication
- **Cloud SQL Python Connector:** https://github.com/GoogleCloudPlatform/cloud-sql-python-connector
- **pg8000 Driver:** https://github.com/tlocke/pg8000
- **langchain-postgres:** https://python.langchain.com/docs/integrations/vectorstores/pgvector/

---

## Commit Reference

**Commit:** `d953061`  
**Message:** "Fix IAM DB auth: enforce USE_IAM_AUTH, correct enable_iam_auth flag, add deployment helpers"

**Files Changed:**
- `src/storage/vector_store.py`
- `src/storage/cloud_sql_engine.py`
- `tools/patch_cloud_run_env_use_iam_auth.sh` (new)
- `tools/remove_db_password_envs.sh` (new)
- `tools/check_cloud_run_sa_iam.sh` (new)
