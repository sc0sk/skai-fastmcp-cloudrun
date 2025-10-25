# Migration Procedure: Legacy to langchain-postgres Schema

**Feature**: 016-langchain-postgres-upgrade  
**Last Updated**: 2025-10-25  
**Status**: Ready for Production

This document provides step-by-step instructions for migrating from the legacy `hansard_speeches` table (used by `langchain-google-cloud-sql-pg`) to the new `langchain-postgres` schema (`langchain_pg_collection` and `langchain_pg_embedding` tables).

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Migration Checklist](#pre-migration-checklist)
3. [Migration Steps](#migration-steps)
4. [Validation Procedures](#validation-procedures)
5. [Rollback Instructions](#rollback-instructions)
6. [Post-Migration Tasks](#post-migration-tasks)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Environment Requirements

- **Python**: 3.11+
- **Database**: PostgreSQL 15+ with pgvector extension
- **Access**: Cloud SQL IAM authentication configured
- **Permissions**: Database admin privileges (for creating tables)

### Required Configuration

Ensure the following environment variables are set:

```bash
# GCP Configuration
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
export CLOUDSQL_INSTANCE="your-instance-name"
export CLOUDSQL_DATABASE="hansard"

# Migration Configuration
export PGVECTOR_COLLECTION="hansard"  # Target collection name
export VECTOR_BACKEND="legacy"  # Keep as legacy during migration
```

### Dependency Installation

```bash
# Install migration script dependencies
cd /path/to/skai-fastmcp-cloudrun
uv sync  # Ensures all dependencies installed

# Verify imports
python3 -c "
from scripts.migrate_to_langchain_postgres import MigrationExecutor
from src.storage.cloud_sql_engine import CloudSQLEngine
print('✅ All imports successful')
"
```

### Database Preparation

```sql
-- Connect to Cloud SQL database
-- Verify pgvector extension is enabled
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Verify source table exists and has data
SELECT COUNT(*) FROM hansard_speeches;

-- Verify target tables exist (created by langchain-postgres)
SELECT * FROM information_schema.tables 
WHERE table_name IN ('langchain_pg_collection', 'langchain_pg_embedding');
```

---

## Pre-Migration Checklist

Complete this checklist before starting the migration:

### Development Environment

- [ ] **Dry-run completed successfully** in development
- [ ] **Integration tests pass** (`pytest tests/integration/test_migration.py`)
- [ ] **Performance tests pass** (`pytest tests/performance/test_migration_speed.py`)
- [ ] **Unit tests pass** (`pytest tests/unit/`)
- [ ] **All Phase 1-3 tasks complete** in Feature 016

### Staging Environment

- [ ] **Staging database snapshot created** (backup before migration)
- [ ] **Staging dry-run completed** (preview migration plan)
- [ ] **Staging migration executed** successfully
- [ ] **Record counts validated** (source == target)
- [ ] **Spot-check validation passed** (10 random records)
- [ ] **Search parity verified** (legacy vs postgres results)
- [ ] **Performance baseline met** (latency within 10% of legacy)
- [ ] **Rollback tested** (VECTOR_BACKEND=legacy still works)

### Production Environment

- [ ] **Production snapshot created** (full database backup)
- [ ] **Maintenance window scheduled** (if needed)
- [ ] **Stakeholders notified** (migration plan and timeline)
- [ ] **On-call engineer available** (for emergency support)
- [ ] **Rollback plan documented** (steps to revert if needed)
- [ ] **Monitoring configured** (latency, error rates, throughput)

---

## Migration Steps

### Step 1: Create Database Snapshot

**CRITICAL**: Always create a snapshot before migration.

```bash
# Using gcloud CLI
gcloud sql backups create \
  --instance=$CLOUDSQL_INSTANCE \
  --project=$GCP_PROJECT_ID \
  --description="Pre-migration backup for langchain-postgres upgrade"

# Verify backup created
gcloud sql backups list \
  --instance=$CLOUDSQL_INSTANCE \
  --project=$GCP_PROJECT_ID \
  --limit=5
```

**Expected Output**:
```
BACKUP_ID    WINDOW_START_TIME           STATUS
...          2025-10-25T12:00:00Z        SUCCESSFUL
```

### Step 2: Dry-Run Migration

**Purpose**: Preview migration without making changes.

```bash
cd /path/to/skai-fastmcp-cloudrun

# Run dry-run mode
python scripts/migrate_to_langchain_postgres.py --dry-run

# Review output for:
# - Source record count
# - Estimated migration time
# - Batch count
# - No errors reported
```

**Expected Output**:
```
Migration Configuration:
  Mode: DRY RUN
  Project: your-project-id
  Instance: your-instance-name
  Database: hansard
  Collection: hansard
  Batch size: 100

Connected to: PostgreSQL 15.x

[DRY RUN] Would ensure collection 'hansard' exists
[DRY RUN] Would migrate batch at offset 0: 100 records
[DRY RUN] Batch 1 complete: 100 records (0.05s) | Progress: 100/1000 (10.0%)
...
[DRY RUN] Would migrate 1000 records in 5.2s

✅ Dry run completed successfully!
```

### Step 3: Execute Migration

**Warning**: This step modifies the database.

```bash
# Execute migration with default batch size (100)
python scripts/migrate_to_langchain_postgres.py --execute

# OR with custom batch size
python scripts/migrate_to_langchain_postgres.py --execute --batch-size 200

# Monitor output for:
# - Progress updates (percentage complete)
# - Batch processing times
# - ETA (estimated time remaining)
# - Validation results
# - Final status (success/warning)
```

**Expected Output**:
```
Migration Configuration:
  Mode: EXECUTE
  Project: your-project-id
  Instance: your-instance-name
  Database: hansard
  Collection: hansard
  Batch size: 100

Connected to: PostgreSQL 15.x

Validating migration prerequisites...
Source table has 10,000 records

Collection 'hansard' already exists (uuid: abc-123-def)

Starting migration (batch size: 100)...
Batch 1 complete: 100 records (2.1s) | Progress: 100/10,000 (1.0%) | ETA: 0:03:30
Batch 2 complete: 100 records (2.0s) | Progress: 200/10,000 (2.0%) | ETA: 0:03:20
...
Batch 100 complete: 100 records (1.9s) | Progress: 10,000/10,000 (100.0%)

Running final validation...
Migration validation:
  Source records: 10,000
  Target records (before): 0
  Target records (after): 10,000
  Newly migrated: 10,000

Spot-checking 10 random records...
Spot-check results: 10/10 records match

Running ANALYZE for query optimization...

======================================================================
Migration Summary
======================================================================
  status: success
  source_count: 10000
  target_count: 10000
  newly_migrated: 10000
  duration_seconds: 185.3
  spot_check_matches: 10
  spot_check_total: 10
======================================================================
✅ Migration completed successfully!
```

### Step 4: Immediate Validation

Run validation queries immediately after migration:

```sql
-- 1. Verify record counts match
SELECT 
    (SELECT COUNT(*) FROM hansard_speeches) AS source_count,
    (SELECT COUNT(*) FROM langchain_pg_embedding e
     JOIN langchain_pg_collection c ON e.collection_id = c.uuid
     WHERE c.name = 'hansard') AS target_count;

-- Expected: source_count == target_count

-- 2. Verify collection exists
SELECT uuid, name, cmetadata 
FROM langchain_pg_collection 
WHERE name = 'hansard';

-- Expected: 1 row with collection name 'hansard'

-- 3. Spot-check random records
SELECT 
    s.langchain_id::text AS source_id,
    e.custom_id AS target_id,
    LEFT(s.content, 50) AS source_content_preview,
    LEFT(e.document, 50) AS target_content_preview,
    s.speaker = e.cmetadata->>'speaker' AS speaker_match
FROM hansard_speeches s
LEFT JOIN langchain_pg_embedding e ON s.langchain_id::text = e.custom_id
JOIN langchain_pg_collection c ON e.collection_id = c.uuid
WHERE c.name = 'hansard'
ORDER BY RANDOM()
LIMIT 10;

-- Expected: All rows have matching content and metadata
```

---

## Validation Procedures

### Automated Validation (Included in Migration)

The migration script automatically performs:

1. **Record Count Validation**: Compares source vs target counts
2. **Spot-Check Validation**: Randomly samples 10 records for data integrity
3. **ANALYZE Optimization**: Updates query planner statistics

These are reported in the migration summary.

### Manual Validation Steps

#### 1. Search Parity Test

Test that searches return similar results:

```python
import asyncio
from src.storage.vector_store import VectorStoreService

async def test_search_parity():
    # Test with legacy backend
    import os
    os.environ['VECTOR_BACKEND'] = 'legacy'
    legacy_service = VectorStoreService()
    legacy_results = await legacy_service.similarity_search(
        query="climate change",
        k=10
    )
    
    # Test with postgres backend
    os.environ['VECTOR_BACKEND'] = 'postgres'
    postgres_service = VectorStoreService()
    postgres_results = await postgres_service.similarity_search(
        query="climate change",
        k=10
    )
    
    print(f"Legacy results: {len(legacy_results)}")
    print(f"Postgres results: {len(postgres_results)}")
    
    # Compare top results (should be similar)
    for i in range(min(5, len(legacy_results), len(postgres_results))):
        legacy_score = legacy_results[i]['score']
        postgres_score = postgres_results[i]['score']
        diff = abs(legacy_score - postgres_score)
        print(f"Result {i+1}: Legacy={legacy_score:.4f}, Postgres={postgres_score:.4f}, Diff={diff:.4f}")

asyncio.run(test_search_parity())
```

**Expected**: Score differences < 0.3, top results similar

#### 2. Performance Baseline Test

```bash
# Run performance comparison
pytest tests/integration/test_mcp_tools_e2e.py::TestPerformanceComparison -v -s

# Expected: Postgres latency within 10% of legacy
```

#### 3. Integration Test Suite

```bash
# Run full integration test suite
pytest tests/integration/ -v

# All tests should pass with VECTOR_BACKEND=postgres
```

---

## Rollback Instructions

### Immediate Rollback (< 5 minutes)

If issues are detected immediately after migration:

```bash
# 1. Switch backend to legacy (no database changes needed)
export VECTOR_BACKEND=legacy

# 2. Redeploy Cloud Run service with updated env var
gcloud run deploy skai-fastmcp-cloudrun \
  --set-env-vars VECTOR_BACKEND=legacy \
  --region=$GCP_REGION \
  --project=$GCP_PROJECT_ID

# 3. Verify legacy backend operational
# Test a few searches via MCP tools

# 4. Monitor for errors
# Check Cloud Run logs for any issues
```

### Full Rollback (if migration compromised data)

If the migration produced incorrect data:

```bash
# 1. Immediate rollback (above)

# 2. Restore from snapshot
gcloud sql backups restore BACKUP_ID \
  --backup-instance=$CLOUDSQL_INSTANCE \
  --backup-project=$GCP_PROJECT_ID \
  --restore-instance=$CLOUDSQL_INSTANCE \
  --project=$GCP_PROJECT_ID

# 3. Verify restoration
# Check hansard_speeches table still intact

# 4. Remove corrupted target data (if snapshot not used)
# Connect to database and run:
# DELETE FROM langchain_pg_embedding WHERE collection_id IN 
#   (SELECT uuid FROM langchain_pg_collection WHERE name = 'hansard');
# DELETE FROM langchain_pg_collection WHERE name = 'hansard';

# 5. Incident report
# Document what went wrong, root cause, prevention steps
```

---

## Post-Migration Tasks

### Immediate (Day 0)

- [ ] **Switch to postgres backend**: Set `VECTOR_BACKEND=postgres`
- [ ] **Deploy to Cloud Run**: Update environment variables
- [ ] **Monitor error rates**: Check Cloud Run logs for issues
- [ ] **Monitor latency**: Verify P95 latency within 10% of baseline
- [ ] **Test MCP tools**: Run manual smoke tests

### Short-term (Week 1)

- [ ] **Daily monitoring**: Check error rates, latency, throughput
- [ ] **User feedback**: Monitor for any reported issues
- [ ] **Performance optimization**: Tune indexes if needed
- [ ] **Documentation update**: Record any lessons learned

### Long-term (After 1 week stable operation)

- [ ] **Remove feature flag** (Phase 7: Task T033)
- [ ] **Remove legacy dependency** `langchain-google-cloud-sql-pg`
- [ ] **Archive old table**: Rename `hansard_speeches` to `hansard_speeches_legacy`
- [ ] **Final backup**: Create snapshot of production database
- [ ] **Drop legacy table** (after final backup confirmation)

---

## Troubleshooting

### Issue: Migration Script Hangs

**Symptoms**: Migration stops responding, no progress updates

**Diagnosis**:
```sql
-- Check for blocking queries
SELECT pid, state, query, wait_event_type, wait_event
FROM pg_stat_activity
WHERE datname = 'hansard' AND state != 'idle';

-- Check for long-running transactions
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '5 minutes';
```

**Resolution**:
- Terminate blocking queries if safe
- Increase Cloud SQL instance size temporarily
- Reduce batch size (`--batch-size 50`)
- Check network connectivity

### Issue: Record Count Mismatch

**Symptoms**: `source_count != target_count` after migration

**Diagnosis**:
```sql
-- Find missing records
SELECT s.langchain_id::text
FROM hansard_speeches s
LEFT JOIN langchain_pg_embedding e ON s.langchain_id::text = e.custom_id
LEFT JOIN langchain_pg_collection c ON e.collection_id = c.uuid
WHERE c.name = 'hansard' AND e.uuid IS NULL
LIMIT 10;
```

**Resolution**:
- Review migration logs for batch failures
- Re-run migration (idempotent, will skip existing records)
- Check for constraint violations in logs

### Issue: Search Results Differ Significantly

**Symptoms**: Postgres backend returns very different results than legacy

**Diagnosis**:
```python
# Compare embedding dimensions
SELECT array_length(embedding, 1) AS dim FROM hansard_speeches LIMIT 1;
SELECT array_length(embedding, 1) AS dim FROM langchain_pg_embedding LIMIT 1;

# Should both be 768 for text-embedding-005
```

**Resolution**:
- Verify embedding model consistent (`text-embedding-005`)
- Check cmetadata preserved correctly
- Review spot-check validation results
- Consider re-embedding if model version changed

### Issue: Performance Regression

**Symptoms**: P95 latency > 10% higher than legacy

**Diagnosis**:
```sql
-- Check if ANALYZE was run
SELECT last_analyze FROM pg_stat_user_tables 
WHERE relname = 'langchain_pg_embedding';

-- Check index usage
SELECT indexrelname, idx_scan FROM pg_stat_user_indexes 
WHERE relname = 'langchain_pg_embedding';
```

**Resolution**:
```sql
-- Run ANALYZE manually
ANALYZE langchain_pg_embedding;
ANALYZE langchain_pg_collection;

-- Check index configuration
-- Ensure IVFFlat index exists with appropriate lists parameter
```

### Issue: "Collection does not exist" Error

**Symptoms**: Migration fails with collection not found

**Diagnosis**:
```sql
SELECT * FROM langchain_pg_collection WHERE name = 'hansard';
```

**Resolution**:
- The migration script auto-creates collection if missing
- Verify `PGVECTOR_COLLECTION` env var matches collection name
- Check database permissions (CREATE TABLE privilege)

---

## Contact & Support

- **Feature Owner**: Development Team
- **On-Call Engineer**: [Contact info]
- **Incident Channel**: [Slack/Teams channel]
- **Documentation**: `specs/016-langchain-postgres-upgrade/`

---

## Appendix: SQL Queries

### Verify Migration Completeness

```sql
-- Compare all critical columns
WITH source_sample AS (
    SELECT 
        langchain_id::text AS id,
        content,
        speaker,
        party,
        chamber
    FROM hansard_speeches
    ORDER BY RANDOM()
    LIMIT 100
),
target_sample AS (
    SELECT 
        e.custom_id AS id,
        e.document AS content,
        e.cmetadata->>'speaker' AS speaker,
        e.cmetadata->>'party' AS party,
        e.cmetadata->>'chamber' AS chamber
    FROM langchain_pg_embedding e
    JOIN langchain_pg_collection c ON e.collection_id = c.uuid
    WHERE c.name = 'hansard'
)
SELECT 
    s.id,
    s.content = t.content AS content_match,
    s.speaker = t.speaker AS speaker_match,
    s.party = t.party AS party_match,
    s.chamber = t.chamber AS chamber_match
FROM source_sample s
JOIN target_sample t ON s.id = t.id;
```

### Monitor Migration Progress (During Execution)

```sql
-- Real-time count of migrated records
SELECT 
    c.name AS collection,
    COUNT(*) AS migrated_records,
    pg_size_pretty(pg_total_relation_size('langchain_pg_embedding')) AS table_size
FROM langchain_pg_embedding e
JOIN langchain_pg_collection c ON e.collection_id = c.uuid
WHERE c.name = 'hansard'
GROUP BY c.name;
```

### Clean Up Test Collections

```sql
-- Remove test collections (be careful in production!)
DELETE FROM langchain_pg_embedding WHERE collection_id IN (
    SELECT uuid FROM langchain_pg_collection WHERE name LIKE 'test_%'
);
DELETE FROM langchain_pg_collection WHERE name LIKE 'test_%';
```

---

**Document Version**: 1.0  
**Last Reviewed**: 2025-10-25  
**Next Review**: After first production migration
