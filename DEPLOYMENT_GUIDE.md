# Deployment Guide: Feature 016 to Production

**Feature**: 016-langchain-postgres-upgrade  
**Deployment Date**: 2025-10-25  
**Status**: Ready for Staging Deployment

---

## Quick Start

### 1. Deploy to Cloud Run (Staging with Legacy Backend)

```bash
# Set project
gcloud config set project skai-fastmcp-cloudrun

# Deploy with legacy backend (safe deployment)
gcloud run deploy hansard-mcp-server \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --service-account=666924716777-compute@developer.gserviceaccount.com \
  --add-cloudsql-instances=skai-fastmcp-cloudrun:us-central1:hansard-db-v2 \
  --vpc-connector=hansard-vpc-connector \
  --vpc-egress=private-ranges-only \
  --set-env-vars=PYTHONPATH=/app/src,VECTOR_BACKEND=legacy \
  --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=github-oauth-client-id:latest,FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=github-oauth-client-secret:latest,JWT_SIGNING_KEY=jwt-signing-key:latest,TOKEN_ENCRYPTION_KEY=token-encryption-key:latest,GITHUB_ALLOWED_USERNAMES=github-allowed-usernames:latest \
  --cpu=2 \
  --memory=2Gi \
  --max-instances=10 \
  --timeout=300 \
  --startup-cpu-boost
```

**What this does:**
- Deploys new code with Feature 016 implementation
- Uses `VECTOR_BACKEND=legacy` to keep existing behavior
- Validates that new code works with legacy backend
- Zero-risk deployment (no database migration yet)

### 2. Run Pre-Migration Data Migration

```bash
# Connect to Cloud SQL via proxy
./cloud_sql_proxy skai-fastmcp-cloudrun:us-central1:hansard-db-v2 &

# Run migration script (DRY RUN first)
python scripts/migrate_to_langchain_postgres.py \
  --dry-run \
  --batch-size 100 \
  --max-workers 4

# Review dry-run output, then run actual migration
python scripts/migrate_to_langchain_postgres.py \
  --batch-size 100 \
  --max-workers 4 \
  --progress
```

**What this does:**
- Copies data from `hansard_speeches` to `langchain_pg_collection`/`langchain_pg_embedding`
- Idempotent (can run multiple times safely)
- Does NOT change active backend (still using legacy)
- Prepares new tables for switch

### 3. Switch to New Backend (Staged Rollout)

```bash
# Switch 10% of traffic to new backend
gcloud run services update-traffic hansard-mcp-server \
  --region us-central1 \
  --to-revisions=LATEST=10

# Monitor for 30 minutes, then 50%
gcloud run services update-traffic hansard-mcp-server \
  --region us-central1 \
  --to-revisions=LATEST=50

# Monitor for 2 hours, then 100%
gcloud run services update-traffic hansard-mcp-server \
  --region us-central1 \
  --to-revisions=LATEST=100
```

Wait, we need to deploy with postgres backend first. Let me correct:

```bash
# Deploy new revision with postgres backend
gcloud run deploy hansard-mcp-server \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --service-account=666924716777-compute@developer.gserviceaccount.com \
  --add-cloudsql-instances=skai-fastmcp-cloudrun:us-central1:hansard-db-v2 \
  --vpc-connector=hansard-vpc-connector \
  --vpc-egress=private-ranges-only \
  --set-env-vars=PYTHONPATH=/app/src,VECTOR_BACKEND=postgres \
  --set-secrets=FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID=github-oauth-client-id:latest,FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET=github-oauth-client-secret:latest,JWT_SIGNING_KEY=jwt-signing-key:latest,TOKEN_ENCRYPTION_KEY=token-encryption-key:latest,GITHUB_ALLOWED_USERNAMES=github-allowed-usernames:latest \
  --cpu=2 \
  --memory=2Gi \
  --max-instances=10 \
  --timeout=300 \
  --startup-cpu-boost \
  --no-traffic  # Deploy but don't send traffic yet
```

Then gradually shift traffic as described above.

### 4. Quick Rollback (if needed)

```bash
# Instant rollback to legacy backend (<5 minutes)
gcloud run services update hansard-mcp-server \
  --region us-central1 \
  --update-env-vars VECTOR_BACKEND=legacy
```

---

## Full Deployment Procedure

### Phase 1: Pre-Deployment Validation (30 minutes)

```bash
# Run pre-staging quality gates
cd /home/user/skai-fastmcp-cloudrun

# 1. Code quality checks
ruff check .
mypy src/

# 2. Security scan
pip-audit

# 3. Run all tests
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/

# 4. Verify dependencies
uv sync
uv tree | grep -E "(langchain|psycopg|sqlalchemy)"
```

**Acceptance Criteria:**
- ✅ All linting passes
- ✅ All tests pass (108+ test cases)
- ✅ No high/critical security vulnerabilities
- ✅ Dependencies correct: langchain-postgres>=0.0.12, psycopg>=3.1,<3.3

### Phase 2: Staging Deployment with Legacy Backend (1 hour)

**Objective:** Deploy new code, validate it works with legacy backend before migration.

```bash
# 1. Deploy with legacy backend
gcloud run deploy hansard-mcp-server \
  --source . \
  --region us-central1 \
  --set-env-vars=PYTHONPATH=/app/src,VECTOR_BACKEND=legacy \
  [... other flags from Quick Start section 1 ...]

# 2. Wait for deployment to complete
gcloud run services describe hansard-mcp-server --region us-central1

# 3. Test the deployed service
export SERVICE_URL=$(gcloud run services describe hansard-mcp-server --region us-central1 --format='value(status.url)')

# Health check
curl $SERVICE_URL/health

# Test search (should use legacy backend)
# Use your MCP client or test script
```

**Acceptance Criteria:**
- ✅ Deployment succeeds
- ✅ Service responds to health checks
- ✅ Search queries work correctly
- ✅ No errors in Cloud Logging
- ✅ Latency within normal range

### Phase 3: Data Migration (30-60 minutes for 10K+ rows)

**Objective:** Migrate data from legacy to new schema without affecting production traffic.

```bash
# 1. Start Cloud SQL Proxy
./cloud_sql_proxy skai-fastmcp-cloudrun:us-central1:hansard-db-v2 &
PROXY_PID=$!

# 2. Set environment variables
export GCP_PROJECT_ID="skai-fastmcp-cloudrun"
export GCP_REGION="us-central1"
export CLOUDSQL_INSTANCE="hansard-db-v2"
export CLOUDSQL_DATABASE="hansard"
export PGVECTOR_COLLECTION="hansard"

# 3. Dry run first (always!)
python scripts/migrate_to_langchain_postgres.py \
  --dry-run \
  --batch-size 100 \
  --max-workers 4

# Review output carefully:
# - Source record count
# - Estimated batches
# - Estimated time

# 4. Execute migration
python scripts/migrate_to_langchain_postgres.py \
  --batch-size 100 \
  --max-workers 4 \
  --progress

# 5. Validate migration
python scripts/migrate_to_langchain_postgres.py --validate-only

# 6. Stop proxy
kill $PROXY_PID
```

**Acceptance Criteria:**
- ✅ Migration completes successfully
- ✅ Record counts match (source == target)
- ✅ No duplicate custom_id values
- ✅ Spot-check: Random sample of 10 records verified
- ✅ Vector dimensions correct (1536 for Vertex AI embeddings)

### Phase 4: Switch to New Backend - Gradual Rollout (4-6 hours)

**Objective:** Gradually shift traffic to new backend with monitoring.

#### Step 1: Deploy New Revision (no traffic)

```bash
gcloud run deploy hansard-mcp-server \
  --source . \
  --region us-central1 \
  --set-env-vars=PYTHONPATH=/app/src,VECTOR_BACKEND=postgres \
  [... other flags from Quick Start section 1 ...] \
  --no-traffic
```

#### Step 2: 10% Traffic (30 minutes observation)

```bash
# Get revision names
gcloud run revisions list --service=hansard-mcp-server --region=us-central1

# Split traffic: 90% legacy, 10% postgres
gcloud run services update-traffic hansard-mcp-server \
  --region us-central1 \
  --to-revisions=[POSTGRES_REVISION]=10,[LEGACY_REVISION]=90

# Monitor Cloud Logging
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=hansard-mcp-server" \
  --limit 50 \
  --format json \
  --freshness 5m
```

**Monitor for 30 minutes:**
- ✅ No increase in error rate
- ✅ P95 latency ≤110% of legacy
- ✅ No database connection errors
- ✅ Search results parity validated

#### Step 3: 50% Traffic (2 hours observation)

```bash
gcloud run services update-traffic hansard-mcp-server \
  --region us-central1 \
  --to-revisions=[POSTGRES_REVISION]=50,[LEGACY_REVISION]=50
```

**Monitor for 2 hours:**
- ✅ Error rate stable
- ✅ Latency stable
- ✅ No performance degradation
- ✅ Database metrics healthy

#### Step 4: 100% Traffic (24-48 hours observation)

```bash
gcloud run services update-traffic hansard-mcp-server \
  --region us-central1 \
  --to-revisions=[POSTGRES_REVISION]=100
```

**Monitor for 24-48 hours:**
- ✅ System stable
- ✅ No rollback needed
- ✅ User feedback positive
- ✅ All quality gates passed

### Phase 5: Post-Production Stability (30 days)

After 48+ hours of production stability:

```bash
# 1. Remove legacy dependency (T033)
# Edit pyproject.toml, remove langchain-google-cloud-sql-pg
uv sync

# 2. Archive old table (T034)
psql -h 127.0.0.1 -U postgres -d hansard << EOF
ALTER TABLE hansard_speeches RENAME TO hansard_speeches_legacy_archived;
COMMENT ON TABLE hansard_speeches_legacy_archived IS 'Archived on 2025-10-25. Safe to drop after 2025-11-25.';
EOF

# 3. After 30 days, final cleanup (T035)
# Create backup first!
pg_dump -h 127.0.0.1 -U postgres -d hansard -t hansard_speeches_legacy_archived > legacy_table_backup.sql

# Drop archived table
psql -h 127.0.0.1 -U postgres -d hansard -c "DROP TABLE hansard_speeches_legacy_archived;"
```

---

## Monitoring & Validation

### Key Metrics to Monitor

1. **Error Rate**
   ```bash
   # Cloud Logging filter
   resource.type="cloud_run_revision"
   resource.labels.service_name="hansard-mcp-server"
   severity>=ERROR
   ```

2. **Latency (P95)**
   ```bash
   # Cloud Monitoring metric
   run.googleapis.com/request_latencies
   ```

3. **Database Connections**
   ```bash
   # Cloud SQL monitoring
   cloudsql.googleapis.com/database/postgresql/num_backends
   ```

4. **Search Result Count**
   ```bash
   # Application logs
   "search_results_count"
   ```

### Validation Queries

```sql
-- Connect to Cloud SQL
psql -h 127.0.0.1 -U postgres -d hansard

-- Check new tables exist and have data
SELECT 
  c.name as collection,
  COUNT(e.id) as embedding_count
FROM langchain_pg_collection c
LEFT JOIN langchain_pg_embedding e ON e.collection_id = c.uuid
GROUP BY c.name;

-- Verify no duplicate custom_id values
SELECT custom_id, COUNT(*)
FROM langchain_pg_embedding
GROUP BY custom_id
HAVING COUNT(*) > 1;

-- Check vector dimensions
SELECT 
  custom_id,
  array_length(embedding, 1) as dimension
FROM langchain_pg_embedding
LIMIT 5;
```

---

## Rollback Procedures

### Instant Rollback (<5 minutes)

If issues detected, immediately switch back to legacy:

```bash
# Method 1: Update environment variable (preferred)
gcloud run services update hansard-mcp-server \
  --region us-central1 \
  --update-env-vars VECTOR_BACKEND=legacy

# Method 2: Route all traffic to legacy revision
gcloud run services update-traffic hansard-mcp-server \
  --region us-central1 \
  --to-revisions=[LEGACY_REVISION]=100
```

### Post-Rollback Actions

1. **Investigate root cause**
   - Check Cloud Logging for errors
   - Review monitoring metrics
   - Validate data migration completeness

2. **Document issue**
   - Create incident report
   - Update troubleshooting guide
   - Plan remediation

3. **Re-attempt deployment**
   - Fix identified issues
   - Re-run validation tests
   - Follow deployment procedure again

---

## Testing Commands

### Test Locally Before Deployment

```bash
# 1. Start local server with legacy backend
export VECTOR_BACKEND=legacy
uv run src/main.py

# 2. Test with legacy backend
python test_tools_direct.py

# 3. Switch to postgres backend
export VECTOR_BACKEND=postgres
uv run src/main.py

# 4. Test with postgres backend
python test_tools_direct.py

# 5. Compare results (should be identical)
```

### Test Deployed Service

```bash
# Get service URL
export SERVICE_URL=$(gcloud run services describe hansard-mcp-server --region us-central1 --format='value(status.url)')

# Health check
curl $SERVICE_URL/health

# Check active backend (look for log messages)
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=hansard-mcp-server AND jsonPayload.message:'Using'" \
  --limit 5 \
  --format json

# Run end-to-end test (requires auth token)
python test_via_cloud_run.sh
```

---

## Success Criteria

### Deployment Success
- ✅ Service deployed and healthy
- ✅ No increase in error rate
- ✅ Latency within acceptable range (P95 ≤110% of baseline)
- ✅ All monitoring alerts green

### Migration Success
- ✅ Record counts match (source == target)
- ✅ No duplicate custom_id values
- ✅ Spot-check validation passed (10 random records)
- ✅ Search results parity validated

### Production Success
- ✅ 48+ hours production stability
- ✅ No rollback required
- ✅ User feedback positive
- ✅ All quality gates passed

---

## Support & Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check Cloud SQL instance is running
   - Verify VPC connector configured
   - Confirm IAM permissions set correctly

2. **High Latency**
   - Check database query performance
   - Verify connection pooling working
   - Monitor concurrent request count

3. **Search Result Discrepancies**
   - Validate data migration completeness
   - Check metadata filtering logic
   - Verify embedding dimensions match

### Getting Help

- **Documentation**: `specs/016-langchain-postgres-upgrade/`
- **Migration Guide**: `specs/016-langchain-postgres-upgrade/migration-procedure.md`
- **Quickstart**: `specs/016-langchain-postgres-upgrade/quickstart.md`
- **Quality Gates**: `README_NEXT_STEPS.md` and `FINAL_DEPLOYMENT_TEST_SUMMARY.md`

---

## Summary

**Safe Deployment Path:**
1. Deploy with `VECTOR_BACKEND=legacy` (zero risk)
2. Run data migration (no impact on production)
3. Deploy with `VECTOR_BACKEND=postgres --no-traffic`
4. Gradual traffic rollout: 10% → 50% → 100%
5. Monitor at each step, rollback if needed
6. After 48h stability, proceed with cleanup

**Total Time:** ~7 days active work + 30-day retention period
**Risk Level:** Low (instant rollback capability)
**Rollback Time:** <5 minutes

**Questions?** Review documentation in `specs/016-langchain-postgres-upgrade/`
