# Feature 003: Service Account Separation for Read-Only/Read-Write Access

**Status**: Planning
**Priority**: P0 (Security)
**Created**: 2025-10-23

---

## Problem Statement

Currently, both ingestion jobs and MCP query tools use the same service account (`666924716777-compute@developer.gserviceaccount.com`) with full database permissions. This violates the principle of least privilege and creates security risks.

### Current Issues:
1. ❌ MCP search/fetch tools have unnecessary write access to database
2. ❌ No separation between data ingestion and data querying permissions
3. ❌ If MCP server is compromised, attacker can modify/delete all data
4. ❌ No audit trail distinction between read vs. write operations

---

## Solution Overview

Create two separate service accounts with distinct IAM roles:

1. **Read-Write Service Account** (`hansard-ingest@skai-fastmcp-cloudrun.iam.gserviceaccount.com`)
   - Used by: Ingestion Cloud Run jobs
   - Permissions: Can CREATE, INSERT, UPDATE, DELETE on hansard database
   - Use cases: Data ingestion, table schema management

2. **Read-Only Service Account** (`hansard-query@skai-fastmcp-cloudrun.iam.gserviceaccount.com`)
   - Used by: MCP server, search/fetch tools
   - Permissions: Can only SELECT from hansard database
   - Use cases: Semantic search, speech retrieval, query operations

---

## User Stories

### US1: Create Read-Write Service Account (P0)
**As a** data engineer
**I want** a dedicated service account for data ingestion
**So that** I can securely load Hansard speeches without exposing write permissions to query tools

**Acceptance Criteria**:
- Service account created: `hansard-ingest@skai-fastmcp-cloudrun.iam.gserviceaccount.com`
- IAM roles assigned:
  - `roles/cloudsql.client` (Cloud SQL Client)
  - Database role: `readwrite` on `hansard` database
- Used by: `ingest-hansard-jsonb` Cloud Run job
- Credentials stored in Secret Manager: `hansard-ingest-sa-key`

---

### US2: Create Read-Only Service Account (P0)
**As an** API consumer
**I want** MCP search/fetch tools to use read-only database access
**So that** compromised queries cannot modify or delete data

**Acceptance Criteria**:
- Service account created: `hansard-query@skai-fastmcp-cloudrun.iam.gserviceaccount.com`
- IAM roles assigned:
  - `roles/cloudsql.client` (Cloud SQL Client)
  - Database role: `readonly` on `hansard` database (SELECT only)
- Used by: MCP server (`hansard-mcp-server` Cloud Run service)
- Credentials stored in Secret Manager: `hansard-query-sa-key`
- MCP tools (`search_hansard`, `fetch_speech`) use this account

---

### US3: Update Ingestion Jobs to Use Read-Write Account (P0)
**As a** data engineer
**I want** ingestion jobs to authenticate with the read-write service account
**So that** I can load data while maintaining security separation

**Acceptance Criteria**:
- `ingest-hansard-jsonb` job updated to use `hansard-ingest@` service account
- `drop-hansard-table` job updated to use `hansard-ingest@` service account
- Environment variables configured to use correct credentials
- Ingestion succeeds with new service account

---

### US4: Update MCP Server to Use Read-Only Account (P0)
**As a** security engineer
**I want** the MCP server to use read-only database access
**So that** query operations cannot accidentally or maliciously modify data

**Acceptance Criteria**:
- MCP server Cloud Run service updated to use `hansard-query@` service account
- `search_hansard` tool works with read-only account
- `fetch_speech` tool works with read-only account
- Attempts to INSERT/UPDATE/DELETE fail with permission errors (expected behavior)

---

## Technical Design

### Service Account Configuration

#### 1. Create Service Accounts
```bash
# Read-write for ingestion
gcloud iam service-accounts create hansard-ingest \
    --display-name="Hansard Ingestion Service Account" \
    --project=skai-fastmcp-cloudrun

# Read-only for queries
gcloud iam service-accounts create hansard-query \
    --display-name="Hansard Query Service Account (Read-Only)" \
    --project=skai-fastmcp-cloudrun
```

#### 2. Grant Cloud SQL Permissions
```bash
# Both need Cloud SQL Client role
gcloud projects add-iam-policy-binding skai-fastmcp-cloudrun \
    --member="serviceAccount:hansard-ingest@skai-fastmcp-cloudrun.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding skai-fastmcp-cloudrun \
    --member="serviceAccount:hansard-query@skai-fastmcp-cloudrun.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"
```

#### 3. Grant Database-Level Permissions
```sql
-- Connect as postgres user
-- Grant read-write permissions
GRANT CONNECT ON DATABASE hansard TO "hansard-ingest@skai-fastmcp-cloudrun.iam.gserviceaccount.com";
GRANT USAGE ON SCHEMA public TO "hansard-ingest@skai-fastmcp-cloudrun.iam.gserviceaccount.com";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "hansard-ingest@skai-fastmcp-cloudrun.iam.gserviceaccount.com";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "hansard-ingest@skai-fastmcp-cloudrun.iam.gserviceaccount.com";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO "hansard-ingest@skai-fastmcp-cloudrun.iam.gserviceaccount.com";

-- Grant read-only permissions
GRANT CONNECT ON DATABASE hansard TO "hansard-query@skai-fastmcp-cloudrun.iam.gserviceaccount.com";
GRANT USAGE ON SCHEMA public TO "hansard-query@skai-fastmcp-cloudrun.iam.gserviceaccount.com";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "hansard-query@skai-fastmcp-cloudrun.iam.gserviceaccount.com";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO "hansard-query@skai-fastmcp-cloudrun.iam.gserviceaccount.com";
```

#### 4. Store in Secret Manager
```bash
# Create secrets (keys would be generated if using key-based auth)
# With IAM authentication, we just need to reference the service account emails
echo "hansard-ingest@skai-fastmcp-cloudrun.iam.gserviceaccount.com" | \
    gcloud secrets create hansard-ingest-sa-email --data-file=- --project=skai-fastmcp-cloudrun

echo "hansard-query@skai-fastmcp-cloudrun.iam.gserviceaccount.com" | \
    gcloud secrets create hansard-query-sa-email --data-file=- --project=skai-fastmcp-cloudrun
```

### Code Changes

#### Update Ingestion Jobs
```python
# scripts/ingest_hansard_jsonb.py
engine = await PostgresEngine.afrom_instance(
    project_id=os.getenv("GCP_PROJECT_ID"),
    region=os.getenv("GCP_REGION"),
    instance=os.getenv("CLOUDSQL_INSTANCE"),
    database=os.getenv("CLOUDSQL_DATABASE"),
    user=os.getenv("CLOUDSQL_INGEST_USER"),  # hansard-ingest@...
)
```

#### Update MCP Server
```python
# src/storage/vector_store.py
engine = await PostgresEngine.afrom_instance(
    project_id=os.getenv("GCP_PROJECT_ID"),
    region=os.getenv("GCP_REGION"),
    instance=os.getenv("CLOUDSQL_INSTANCE"),
    database=os.getenv("CLOUDSQL_DATABASE"),
    user=os.getenv("CLOUDSQL_QUERY_USER"),  # hansard-query@... (read-only)
)
```

---

## Security Benefits

1. ✅ **Principle of Least Privilege**: Each component has minimum necessary permissions
2. ✅ **Defense in Depth**: Compromised query tool cannot modify data
3. ✅ **Audit Trail**: IAM logs distinguish between read and write operations
4. ✅ **Compliance**: Meets security best practices for data access control
5. ✅ **Production Ready**: Standard pattern for secure database access

---

## Testing Plan

### Test 1: Read-Write Account Works
```bash
# Run ingestion job with new service account
gcloud run jobs execute ingest-hansard-jsonb

# Expected: Successfully ingests data
```

### Test 2: Read-Only Account Can Query
```bash
# Test search tool
curl -X POST http://hansard-mcp-server/search_hansard \
  -d '{"query": "housing affordability"}'

# Expected: Returns search results
```

### Test 3: Read-Only Account Cannot Write
```python
# Attempt INSERT with read-only account
vector_store = await PostgresVectorStore.create(...)
await vector_store.aadd_texts([...], [...])

# Expected: Permission denied error
```

---

## Rollback Plan

If service account separation causes issues:
1. Revert Cloud Run jobs to use original service account
2. Keep new service accounts for future use
3. Document issues for resolution

---

## Dependencies

- Existing: Cloud SQL instance (`hansard-db-v2`) with IAM authentication enabled
- Existing: Secret Manager enabled in project
- Requires: PostgreSQL admin access to grant database-level permissions

---

## Success Metrics

- ✅ Ingestion jobs complete successfully with read-write account
- ✅ MCP search/fetch tools work with read-only account
- ✅ Read-only account receives permission errors on write attempts
- ✅ IAM audit logs show clear distinction between read and write operations

---

## Future Enhancements

### Phase 2: Row-Level Security
- Implement PostgreSQL RLS policies
- Restrict access by party, chamber, or date range
- Enable multi-tenant access patterns

### Phase 3: Query Auditing
- Log all queries with user context
- Track most-accessed speeches
- Monitor query performance

---

## References

- [Cloud SQL IAM Authentication](https://cloud.google.com/sql/docs/postgres/authentication)
- [PostgreSQL GRANT Documentation](https://www.postgresql.org/docs/current/sql-grant.html)
- [Google Cloud IAM Best Practices](https://cloud.google.com/iam/docs/best-practices-service-accounts)
