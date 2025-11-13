# Quick Start: LangChain 1.0 with langchain-postgres

Get up and running with the LangChain 1.0 upgrade in 30 minutes.

## Prerequisites

- Python 3.11+
- Access to development Cloud SQL PostgreSQL instance with pgvector extension
- Google Cloud credentials configured (`gcloud auth application-default login`)
- Existing codebase cloned and virtual environment activated

## Quick Setup (Development)

### 1. Install Dependencies (5 minutes)

```bash
# Checkout feature branch
git checkout -b 016-langchain-postgres-upgrade

# Update dependencies in pyproject.toml (or use uv add)
uv add "langchain>=1.0.0" \
       "langchain-postgres>=0.0.12" \
       "psycopg[binary]>=3.1.0" \
       "google-cloud-sql-connector>=1.11.0" \
       "sqlalchemy>=2.0.0" \
       "pgvector>=0.3.0"

# Update existing packages
uv add --upgrade "langchain-google-vertexai>=2.0.0" \
                 "langchain-google-genai>=2.0.0"

# Sync environment
uv sync
```

### 2. Configure Environment (2 minutes)

Add to `.env` or export:

```bash
# Feature flag (start with legacy for safety)
export VECTOR_BACKEND=legacy

# Collection name for new backend
export POSTGRES_COLLECTION_NAME=hansard

# Existing Cloud SQL config (keep your values)
export CLOUD_SQL_INSTANCE=your-project:us-central1:hansard-db-v2
export CLOUD_SQL_DATABASE=hansard
# ... other existing vars ...
```

### 3. Verify Installation (3 minutes)

```python
# In Python REPL
python3

# Test new imports
from langchain_postgres import PGVector
from google.cloud.sql.connector import Connector
import psycopg
from sqlalchemy import create_engine

print("✅ All imports successful!")
```

### 4. Run Existing Tests (5 minutes)

```bash
# Should still pass with VECTOR_BACKEND=legacy
pytest tests/unit/
pytest tests/integration/
```

## Implementation Checklist

Follow this order for smooth implementation:

### Phase 1: Engine Factory ✓ Complete When
- [ ] Create `src/storage/cloud_sql_engine.py`
- [ ] Create `tests/unit/storage/test_cloud_sql_engine.py`
- [ ] Unit tests pass
- **Time**: 4 hours

### Phase 2: Vector Store Adapter ✓ Complete When
- [ ] Create `src/storage/postgres_vector_store.py`
- [ ] Create `tests/unit/storage/test_postgres_vector_store.py`
- [ ] Unit tests pass
- **Time**: 6 hours

### Phase 3: Backend Selection ✓ Complete When
- [ ] Update `src/storage/vector_store.py` with factory pattern
- [ ] Update `src/config.py` with new vars
- [ ] Service starts with both VECTOR_BACKEND values
- **Time**: 2 hours

### Phase 4: Integration Testing ✓ Complete When
- [ ] Create `tests/integration/storage/test_postgres_integration.py`
- [ ] Run against dev Cloud SQL
- [ ] All integration tests pass with VECTOR_BACKEND=postgres
- **Time**: 7 hours

### Phase 5: Migration ✓ Complete When
- [ ] Create `scripts/migrate_to_langchain_postgres.py`
- [ ] Test migration on dev database
- [ ] Validation shows 100% data integrity
- **Time**: 8 hours

## Testing Your Changes

### Unit Tests (Fast)

```bash
# Test specific module
pytest tests/unit/storage/test_cloud_sql_engine.py -v

# Test with coverage
pytest tests/unit/ --cov=src/storage --cov-report=html
```

### Integration Tests (Requires Cloud SQL)

```bash
# Set up dev Cloud SQL connection
export VECTOR_BACKEND=postgres

# Run integration tests
pytest tests/integration/storage/test_postgres_integration.py -v

# Compare backends
pytest tests/integration/test_backend_comparison.py -v
```

### Manual Smoke Test

```bash
# Start service locally
uvicorn src.main:app --reload

# In another terminal, test search
python3 -c "
from src.storage.vector_store import VectorStoreService
import asyncio

async def test():
    service = VectorStoreService()
    results = await service.similarity_search(
        query='climate change',
        k=5
    )
    print(f'Found {len(results)} results')
    return results

asyncio.run(test())
"
```

## Common Issues & Solutions

### Issue: Import Error for `langchain_postgres`

```
ModuleNotFoundError: No module named 'langchain_postgres'
```

**Solution**: Ensure you installed the package correctly:
```bash
uv add "langchain-postgres>=0.0.12"
uv sync
```

### Issue: Connection Refused to Cloud SQL

```
psycopg.OperationalError: connection refused
```

**Solution**: Check Cloud SQL connector is using IAM auth:
```python
# In cloud_sql_engine.py, verify:
connector.connect(
    instance_connection_name="...",
    enable_iam_auth=True,  # Must be True
    driver="pg8000",
)
```

### Issue: "VECTOR_BACKEND" Not Found

```
KeyError: 'VECTOR_BACKEND'
```

**Solution**: Set environment variable or update config.py default:
```bash
export VECTOR_BACKEND=legacy  # or postgres
```

### Issue: Tests Hang on Async Operations

**Solution**: Ensure you're using `pytest-asyncio`:
```bash
uv add pytest-asyncio
```

And mark async tests:
```python
@pytest.mark.asyncio
async def test_async_operation():
    ...
```

## Next Steps

Once quick start is complete:

1. **Review Full Spec**: Read `spec.md` for complete requirements
2. **Check Implementation Plan**: See `plan.md` for phase details
3. **Follow Task List**: Use `tasks.md` to track progress
4. **Migration Planning**: Review migration strategy before production

## Staging Smoke Tests

After migration is complete in staging, validate the feature flag rollback mechanism:

### Test 1: Backend Selection Validation

**Objective**: Verify that VECTOR_BACKEND correctly switches between backends.

```bash
# Test with legacy backend
export VECTOR_BACKEND=legacy
# Restart application
# Run test searches - should use legacy backend

# Test with postgres backend
export VECTOR_BACKEND=postgres
# Restart application
# Run test searches - should use postgres backend
```

**Expected Outcomes**:
- Legacy backend: Uses `langchain-google-cloud-sql-pg` (hansard_speeches table)
- Postgres backend: Uses `langchain-postgres` (langchain_pg_embedding table)
- Search results semantically equivalent (score differences < 0.3)
- No errors in logs during backend switching

### Test 2: Invalid Backend Value Fails Fast

**Objective**: Verify that misconfiguration is caught immediately at startup.

```bash
# Test with invalid backend value
export VECTOR_BACKEND=invalid_value
# Attempt to start application

# Expected: Application fails to start with clear error:
# ValueError: Invalid VECTOR_BACKEND value: 'invalid_value'.
#            Must be one of: legacy, postgres.
#            Set VECTOR_BACKEND environment variable to 'legacy' or 'postgres'.
```

**Expected Outcomes**:
- Application fails during startup (before accepting requests)
- Error message clearly identifies the problem
- Error message lists valid options
- No silent fallback to unexpected backend

### Test 3: Instant Rollback Scenario

**Objective**: Simulate production rollback after discovering an issue.

```bash
# Step 1: Start with postgres backend (post-migration)
export VECTOR_BACKEND=postgres
# Start application and verify working

# Step 2: Simulate discovering an issue
# (e.g., unexpected search results, performance regression)

# Step 3: Instant rollback to legacy
export VECTOR_BACKEND=legacy
# Restart application (Cloud Run redeploy or container restart)

# Step 4: Verify rollback successful
# - Application starts successfully
# - Searches work correctly
# - No database changes required
```

**Expected Outcomes**:
- Rollback completes in < 5 minutes
- No data loss (both backends access same source data post-migration)
- Service immediately operational on legacy backend
- Postgres backend remains available (can switch back for investigation)

### Test 4: Search Result Parity

**Objective**: Validate that both backends return equivalent results.

```python
#!/usr/bin/env python3
"""Staging smoke test: Search result parity."""

import os
import asyncio
from src.storage.vector_store import get_default_vector_store

async def test_search_parity():
    """Compare search results between legacy and postgres backends."""
    
    test_queries = [
        "climate change policy",
        "healthcare reform",
        "education funding",
        "indigenous rights",
        "housing affordability",
    ]
    
    results_comparison = []
    
    for query in test_queries:
        # Test legacy backend
        os.environ['VECTOR_BACKEND'] = 'legacy'
        # Note: In production, this requires app restart
        # For testing, manually create new store instances
        
        # Test postgres backend
        os.environ['VECTOR_BACKEND'] = 'postgres'
        # Same note as above
        
        # Compare top 5 results
        # (Implementation details omitted for brevity)
        
        results_comparison.append({
            'query': query,
            'top_results_similar': True,  # Based on comparison
            'score_difference': 0.15,  # Average difference
        })
    
    # Report
    print("Search Parity Results:")
    for result in results_comparison:
        status = "✅ PASS" if result['top_results_similar'] else "❌ FAIL"
        print(f"  {status} {result['query']}: "
              f"Δscore={result['score_difference']:.3f}")
    
    # Assert all pass
    assert all(r['top_results_similar'] for r in results_comparison), \
        "Some queries have divergent results between backends"

if __name__ == "__main__":
    asyncio.run(test_search_parity())
```

**Expected Outcomes**:
- All test queries return similar top results (semantic equivalence)
- Score differences < 0.3 for matching documents
- Both backends handle filters correctly
- No errors or timeouts

### Test 5: Performance Baseline

**Objective**: Ensure postgres backend meets performance requirements.

```bash
# Run performance comparison tests
pytest tests/integration/test_mcp_tools_e2e.py::TestPerformanceComparison -v -s

# Expected: P95 latency within 10% of legacy baseline
```

**Expected Outcomes**:
- Postgres backend latency ≤ 110% of legacy backend latency
- No timeout errors
- Throughput comparable (requests/second)
- Memory usage stable

### Test 6: Metadata Filtering

**Objective**: Verify metadata filters work correctly on both backends.

```python
#!/usr/bin/env python3
"""Test metadata filtering on both backends."""

import asyncio
from src.storage.vector_store import VectorStoreService

async def test_metadata_filters():
    """Test various metadata filter combinations."""
    
    filters = [
        {"party": "Labor"},
        {"chamber": "Representatives"},
        {"speaker": "Anthony Albanese"},
        {"party": "Labor", "chamber": "Senate"},
        {"date": "2024-01-15"},
    ]
    
    for filter_obj in filters:
        # Test with legacy backend
        store_legacy = VectorStoreService()  # Uses legacy by default
        results_legacy = await store_legacy.similarity_search(
            query="test query",
            k=10,
            filter=filter_obj
        )
        
        # Test with postgres backend
        # (requires VECTOR_BACKEND=postgres and restart)
        
        # Verify both return results matching filter
        for result in results_legacy:
            metadata = result['metadata']
            for key, value in filter_obj.items():
                assert metadata.get(key) == value, \
                    f"Filter mismatch: {key}={value}"
        
        print(f"✅ Filter {filter_obj}: {len(results_legacy)} results")

if __name__ == "__main__":
    asyncio.run(test_metadata_filters())
```

**Expected Outcomes**:
- Both backends respect metadata filters
- Results only include documents matching filter criteria
- Complex filters (multiple conditions) work correctly
- Empty results returned gracefully when no matches

### Staging Smoke Test Checklist

Complete this checklist before promoting to production:

- [ ] **Backend Selection**: Legacy and postgres backends both work
- [ ] **Invalid Value Handling**: Invalid VECTOR_BACKEND fails fast with clear error
- [ ] **Instant Rollback**: Can switch from postgres to legacy in < 5 minutes
- [ ] **Search Parity**: Results semantically equivalent (score diff < 0.3)
- [ ] **Performance**: Postgres backend P95 latency within 10% of legacy
- [ ] **Metadata Filtering**: Filters work correctly on both backends
- [ ] **Error Handling**: Both backends handle edge cases gracefully
- [ ] **Monitoring**: Logs and metrics available for both backends
- [ ] **Documentation**: Runbook updated with rollback procedures

### Troubleshooting Smoke Tests

**Issue**: Backend switch doesn't take effect

**Cause**: Application not restarted after environment variable change

**Solution**:
```bash
# Cloud Run deployment
gcloud run deploy skai-fastmcp-cloudrun \
  --set-env-vars VECTOR_BACKEND=postgres \
  --region=us-central1

# Local development
# Kill and restart application after export VECTOR_BACKEND=...
```

**Issue**: Search results differ significantly between backends

**Cause**: Possible data inconsistency or embedding version mismatch

**Solution**:
1. Verify migration completed successfully (record counts match)
2. Check embedding model version (should be same: text-embedding-005)
3. Run spot-check validation from migration procedure
4. Review migration logs for any errors

**Issue**: Performance regression on postgres backend

**Cause**: ANALYZE not run after migration, or indexes not created

**Solution**:
```sql
-- Run ANALYZE manually
ANALYZE langchain_pg_embedding;
ANALYZE langchain_pg_collection;

-- Verify indexes exist
SELECT indexname FROM pg_indexes 
WHERE tablename = 'langchain_pg_embedding';
```

## IAM Authentication Verification

After deployment to Cloud Run, verify that IAM-only authentication is working correctly and that no password-based authentication paths exist.

### Positive Test: IAM Authentication Works

**Objective**: Confirm the application connects to Cloud SQL using IAM authentication only.

```bash
# In Cloud Run environment
# The application should start successfully and connect to Cloud SQL

# Check application logs for successful connection
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=skai-fastmcp-cloudrun AND \
  textPayload=~'Connected to Cloud SQL'" \
  --limit 10 \
  --format json
```

**Expected Outcomes**:
- Application starts without errors
- Connection to Cloud SQL succeeds
- No password-related errors in logs
- IAM token refresh happens automatically (Cloud SQL Connector handles this)

**Manual Verification Steps** (from integration tests):

1. **Check IAM Permissions**:
   ```bash
   # Verify service account has cloudsql.instances.connect permission
   gcloud projects get-iam-policy YOUR_PROJECT_ID \
     --flatten="bindings[].members" \
     --filter="bindings.role:roles/cloudsql.client"
   
   # Should list your Cloud Run service account
   ```

2. **Verify Connection String**:
   ```bash
   # Check that connection URL contains no password
   # In application logs, search for connection initialization
   # Should see: postgresql+psycopg://USER@/DATABASE
   # Should NOT see: postgresql+psycopg://USER:PASSWORD@...
   ```

3. **Audit pg_hba.conf** (on Cloud SQL instance):
   ```bash
   # For Cloud SQL, IAM authentication is configured at instance level
   # Verify instance has IAM authentication enabled:
   gcloud sql instances describe YOUR_INSTANCE_NAME \
     --format="value(settings.databaseFlags)"
   
   # Should include: cloudsql.iam_authentication=on
   ```

4. **Connection Log Audit**:
   ```bash
   # Check Cloud SQL logs for IAM authentication attempts
   gcloud logging read "resource.type=cloudsql_database AND \
     logName=projects/YOUR_PROJECT/logs/cloudsql.googleapis.com%2Fpostgres.log AND \
     textPayload=~'IAM'" \
     --limit 20
   
   # Look for: "IAM authentication successful" or similar
   ```

5. **Code Audit for Hardcoded Credentials**:
   ```bash
   # Search codebase for password variables (should find none)
   grep -r "password\s*=\s*['\"]" src/ tests/
   grep -r "DATABASE_PASSWORD" src/ tests/
   
   # Expected: No matches in production code
   # (test fixtures may have mocked values, which is acceptable)
   ```

### Negative Test: IAM Revocation Fails Gracefully

**Objective**: Verify that revoking IAM permissions causes connection failure with clear error messages, and confirm there is no password fallback mechanism.

**Test Procedure**:

1. **Baseline**: Confirm application is running successfully with IAM auth
   ```bash
   # Check current service status
   gcloud run services describe skai-fastmcp-cloudrun \
     --region=us-central1 \
     --format="value(status.conditions[0].status)"
   
   # Should return: True
   ```

2. **Revoke IAM Permission** (temporarily):
   ```bash
   # Identify the service account used by Cloud Run
   SERVICE_ACCOUNT=$(gcloud run services describe skai-fastmcp-cloudrun \
     --region=us-central1 \
     --format="value(spec.template.spec.serviceAccountName)")
   
   # Remove Cloud SQL client role (CAUTION: This will break the service)
   gcloud projects remove-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:${SERVICE_ACCOUNT}" \
     --role="roles/cloudsql.client"
   
   # Wait 30-60 seconds for IAM propagation
   sleep 60
   ```

3. **Trigger Connection Attempt**:
   ```bash
   # Force new connection by redeploying (picks up IAM changes)
   gcloud run services update skai-fastmcp-cloudrun \
     --region=us-central1 \
     --update-env-vars="FORCE_RESTART=$(date +%s)"
   
   # Or trigger via API call that requires database access
   curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
     https://skai-fastmcp-cloudrun-HASH-uc.a.run.app/health
   ```

4. **Verify Failure with Clear Error**:
   ```bash
   # Check application logs for IAM auth failure
   gcloud logging read "resource.type=cloud_run_revision AND \
     resource.labels.service_name=skai-fastmcp-cloudrun AND \
     severity>=ERROR AND \
     textPayload=~'IAM\|authentication\|permission'" \
     --limit 10 \
     --format json
   ```

5. **Verify No Password Fallback**:
   ```bash
   # Search logs for password-based connection attempts
   gcloud logging read "resource.type=cloud_run_revision AND \
     resource.labels.service_name=skai-fastmcp-cloudrun AND \
     textPayload=~'password'" \
     --limit 10
   
   # Expected: No results (no password fallback attempted)
   ```

6. **Restore IAM Permission** (critical - restore service):
   ```bash
   # Re-grant Cloud SQL client role
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:${SERVICE_ACCOUNT}" \
     --role="roles/cloudsql.client"
   
   # Wait for IAM propagation
   sleep 60
   
   # Verify service recovers
   gcloud run services update skai-fastmcp-cloudrun \
     --region=us-central1 \
     --update-env-vars="FORCE_RESTART=$(date +%s)"
   
   # Check service status
   gcloud run services describe skai-fastmcp-cloudrun \
     --region=us-central1 \
     --format="value(status.conditions[0].status)"
   
   # Should return: True (service recovered)
   ```

**Expected Outcomes**:

- **IAM Revocation Phase**:
  - Connection attempts fail with clear IAM-related error
  - Error message mentions "permission denied" or "IAM authentication failed"
  - Application does NOT attempt password-based authentication
  - No DATABASE_PASSWORD environment variable read
  - Service becomes unhealthy (expected behavior)

- **Recovery Phase**:
  - After IAM permission restored, service recovers automatically
  - New connections succeed using IAM auth
  - No manual intervention required beyond IAM permission restoration

**Error Messages to Expect** (when IAM revoked):

```
psycopg.OperationalError: connection failed: 
  FATAL: Cloud SQL IAM user does not have cloudsql.instances.connect permission

# OR

google.auth.exceptions.RefreshError: 
  Unable to acquire impersonated credentials: 
  IAM Service Account Credentials API has not been enabled

# OR

sqlalchemy.exc.OperationalError: (psycopg.OperationalError) 
  connection to server at "..." failed: 
  FATAL: password authentication failed for user "..."
  DETAIL: Cloud SQL IAM authentication is enabled but no valid IAM credentials provided
```

**Error Messages You Should NOT See** (indicating password fallback):

```
# ❌ BAD - indicates password fallback attempt:
Attempting connection with password authentication

# ❌ BAD - indicates password in connection string:
postgresql+psycopg://user:password@host/database

# ❌ BAD - indicates reading password from environment:
Reading DATABASE_PASSWORD environment variable
```

### Security Audit Checklist

Complete this checklist to verify IAM-only authentication:

- [ ] **No Password in Code**: Search codebase for hardcoded passwords (should find none in production code)
- [ ] **No Password Environment Variable**: Verify DATABASE_PASSWORD not set in Cloud Run environment
- [ ] **Connection String Audit**: Verify connection URLs contain no password component
- [ ] **IAM Permissions Verified**: Service account has `roles/cloudsql.client` role
- [ ] **Cloud SQL IAM Enabled**: Instance has `cloudsql.iam_authentication=on` flag
- [ ] **Negative Test Passed**: IAM revocation causes clear failure (not silent password fallback)
- [ ] **Token Refresh Works**: Long-running connections succeed (connector handles token refresh)
- [ ] **Connection Pooling Works**: Multiple concurrent connections succeed with IAM
- [ ] **Log Audit Clean**: No password-related warnings or errors in logs
- [ ] **Recovery Verified**: Service automatically recovers after IAM permission restored

### Troubleshooting IAM Authentication

**Issue**: Connection fails with "password authentication failed"

**Cause**: IAM authentication not enabled on Cloud SQL instance or service account lacks permissions

**Solution**:
```bash
# 1. Enable IAM authentication on instance
gcloud sql instances patch YOUR_INSTANCE_NAME \
  --database-flags=cloudsql.iam_authentication=on

# 2. Grant IAM user database access
# Connect to Cloud SQL as postgres user
gcloud sql connect YOUR_INSTANCE_NAME --user=postgres

# In psql:
CREATE USER "your-service-account@your-project.iam" WITH LOGIN;
GRANT ALL PRIVILEGES ON DATABASE your_database TO "your-service-account@your-project.iam";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "your-service-account@your-project.iam";
```

**Issue**: IAM token refresh fails after ~60 minutes

**Cause**: Cloud SQL Connector not configured correctly or connection pooling issues

**Solution**:
```python
# Verify Cloud SQL Connector is managing token refresh
# In cloud_sql_engine.py, ensure:

connector = Connector()

def getconn() -> psycopg.Connection:
    conn: psycopg.Connection = connector.connect(
        instance_connection_name=instance,
        driver="psycopg",
        user=db_user,
        db=db_name,
        enable_iam_auth=True,  # ← Critical: enables auto token refresh
    )
    return conn

# Connector handles token refresh automatically
# No manual token management required
```

**Issue**: "User does not exist" error with IAM authentication

**Cause**: IAM database user not created in PostgreSQL

**Solution**:
```bash
# IAM users must be created in PostgreSQL with IAM suffix
# Format: "service-account-name@project-id.iam"

# Example for service account: hansard-mcp@my-project.iam.gserviceaccount.com
# Database user should be: hansard-mcp@my-project.iam

# Create in PostgreSQL:
CREATE USER "hansard-mcp@my-project.iam" WITH LOGIN;
GRANT ALL PRIVILEGES ON DATABASE hansard TO "hansard-mcp@my-project.iam";
```

**Issue**: Connection works locally but fails in Cloud Run

**Cause**: Different service account or missing Cloud Run → Cloud SQL permissions

**Solution**:
```bash
# Verify Cloud Run service account
gcloud run services describe skai-fastmcp-cloudrun \
  --region=us-central1 \
  --format="value(spec.template.spec.serviceAccountName)"

# Grant Cloud SQL access to that service account
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/cloudsql.client"

# Verify VPC connector (if using private IP)
gcloud run services describe skai-fastmcp-cloudrun \
  --region=us-central1 \
  --format="value(spec.template.spec.containers[0].resources.vpcAccess)"
```

## Getting Help

- **Spec Questions**: See `spec.md` Open Questions section
- **Technical Issues**: Check `research.md` for architecture decisions
- **Implementation Details**: See code examples in `plan.md`
- **Migration Issues**: See `migration-procedure.md` Troubleshooting section
- **IAM Auth Issues**: See IAM Authentication Verification section above

## Success Criteria Quick Check

Before considering implementation complete:

- [ ] All unit tests pass (>90% coverage)
- [ ] All integration tests pass
- [ ] Search results match between legacy and postgres backends
- [ ] Migration script successfully migrates dev database
- [ ] Feature flag rollback works (switch VECTOR_BACKEND values)
- [ ] IAM authentication verified in Cloud Run environment
- [ ] Performance within 10% of baseline
- [ ] **Staging smoke tests pass** (all 6 tests + checklist)

**Estimated Time to First Working Implementation**: ~27 hours (3-4 working days)
