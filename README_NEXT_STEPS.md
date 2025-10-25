# Next Steps: Initialize Database Schema

## Current Status

✅ **Completed:**
1. Configuration constants refactored to [src/config.py](src/config.py)
2. Service accounts created (hansard-db-admin, hansard-db-readonly) with Cloud SQL Client IAM role
3. Fresh PostgreSQL 15 instance (hansard-db-v2, db-f1-micro) with `hansard` database
4. MCP server defined cleanly in [src/server.py](src/server.py) (no duplication)
5. Tools cleanly separated in src/tools/ (search.py, fetch.py, ingest.py)
6. Constitution updated with Configuration Management best practices
7. Documentation created:
   - [init_hansard_schema.sql](init_hansard_schema.sql) - Complete schema SQL
   - [DATABASE_SETUP.md](DATABASE_SETUP.md) - Setup instructions
   - [LANGCHAIN_PGVECTOR_BEST_PRACTICES.md](LANGCHAIN_PGVECTOR_BEST_PRACTICES.md) - 2025 best practices from Google Cloud

❌ **Remaining: One Manual Step**

The database is empty and needs the LangChain schema initialized with the **langchain_id** column (currently missing, causing search failures).

## How to Initialize Schema

### Option 1: Google Cloud Console SQL Editor (Easiest)

1. Go to https://console.cloud.google.com/sql/instances/hansard-db-v2/
2. Click "Open Cloud Shell Editor" or navigate to the SQL editor
3. Copy the contents of [init_hansard_schema.sql](init_hansard_schema.sql)
4. Paste into the SQL editor and execute

### Option 2: Install psql and Run SQL File

```bash
# Install PostgreSQL client (requires sudo)
sudo apt-get update && sudo apt-get install -y postgresql-client

# Execute SQL file
PGPASSWORD=temporarypassword123 psql "host=136.115.241.202 dbname=hansard user=postgres sslmode=require" < init_hansard_schema.sql
```

### Option 3: Copy SQL Commands Manually

Connect to the database and run these commands:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create hansard_speeches table with LangChain schema
CREATE TABLE IF NOT EXISTS hansard_speeches (
    langchain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    langchain_metadata JSONB DEFAULT '{}'::jsonb,
    speaker VARCHAR(200),
    party VARCHAR(100),
    chamber VARCHAR(50),
    date DATE,
    speech_type VARCHAR(100),
    electorate VARCHAR(100),
    speaker_id VARCHAR(20),
    utterance_id VARCHAR(100),
    debate TEXT
);

-- Create HNSW vector index for similarity search
CREATE INDEX IF NOT EXISTS hansard_speeches_embedding_idx
ON hansard_speeches
USING hnsw (embedding vector_cosine_ops)
WITH (m = 24, ef_construction = 100);

-- Create metadata indexes for efficient filtering
CREATE INDEX IF NOT EXISTS idx_hansard_speeches_speaker ON hansard_speeches(speaker);
CREATE INDEX IF NOT EXISTS idx_hansard_speeches_party ON hansard_speeches(party);
CREATE INDEX IF NOT EXISTS idx_hansard_speeches_chamber ON hansard_speeches(chamber);
CREATE INDEX IF NOT EXISTS idx_hansard_speeches_date ON hansard_speeches(date);
```

## After Schema Initialization

### 1. Verify Schema

```sql
\d hansard_speeches
```

You should see the `langchain_id` column listed.

### 2. Test Search Functionality

```bash
PYTHONPATH=src \
GCP_PROJECT_ID=skai-fastmcp-cloudrun \
GCP_REGION=us-central1 \
CLOUDSQL_INSTANCE=hansard-db-v2 \
CLOUDSQL_DATABASE=hansard \
CLOUDSQL_USER=postgres \
DATABASE_PASSWORD=temporarypassword123 \
uv run python3 -c "
import asyncio
from tools.search import search_hansard_speeches

async def test():
    result = await search_hansard_speeches(query='climate', limit=5)
    print(f'Total results: {result.get(\"total_results\", 0)}')
    print('✅ Search working! (0 results expected - database is empty)')

asyncio.run(test())
"
```

If you see "✅ Search working!" without errors, the schema is correctly initialized!

### 3. Populate Database

Use the Hansard speeches from `/home/user/sk-hansard-converter/output_md_enhanced/reps/` to populate the database.

## Why This Matters

The **langchain_id** column is required by LangChain's PostgresVectorStore. Without it, all searches fail with:

```
ValueError: Id column, langchain_id, does not exist.
```

Once initialized, the system will be ready for:
- ✅ Vector similarity search
- ✅ Hybrid search (vectors + SQL filters)
- ✅ Data ingestion with automatic embedding generation
- ✅ Production deployment

## Implementation Follows Google Cloud 2025 Best Practices

Our implementation aligns with the latest recommendations:
- ✅ Single-table schema with metadata columns (not JSONB)
- ✅ Native `langchain-google-cloud-sql-pg` integration
- ✅ Async drivers (asyncpg) for performance
- ✅ HNSW indexing for ANN search
- ✅ IAM authentication support
- ✅ Configurable constants (no hardcoded values)

See [LANGCHAIN_PGVECTOR_BEST_PRACTICES.md](LANGCHAIN_PGVECTOR_BEST_PRACTICES.md) for details.

---

# Quality Gates: Pre-Staging Checklist

This checklist must be completed before deploying Feature 016 (langchain-postgres upgrade) to the staging environment.

## Overview

Quality gates ensure code quality, test coverage, and operational readiness before deploying to staging. These automated and manual checks catch issues early and prevent production incidents.

**Gate Status**: All checks must **PASS** before staging deployment.

## 1. Code Quality Gates

### 1.1 Linting (Automated)

**Objective**: Ensure code follows Python style guidelines and catches common errors.

```bash
# Run ruff linter
ruff check .

# Expected output:
# All checks passed!
```

**Pass Criteria**:
- Zero linting errors
- Zero critical warnings
- Acceptable: Style suggestions (non-blocking)

**Failure Actions**:
- Fix errors: `ruff check --fix .`
- Review warnings and address critical ones
- Update `.ruff.toml` if rules need adjustment

### 1.2 Type Checking (Automated)

**Objective**: Validate type annotations and catch type errors.

```bash
# Run mypy type checker (if configured)
mypy src/

# Expected: No errors from production code
```

**Pass Criteria**:
- Zero type errors in `src/` directory
- Test files may have acceptable type issues (fixtures, mocking)

**Failure Actions**:
- Add missing type annotations
- Fix type mismatches
- Add `# type: ignore` comments only for genuine false positives

### 1.3 Security Scan (Automated)

**Objective**: Detect known vulnerabilities in dependencies.

```bash
# Scan dependencies for vulnerabilities
uv pip list --format=json | python3 -m json.tool | grep -E '"name"|"version"'

# Manual check: Review for known CVEs
# Automated: Use safety (if installed)
# pip install safety
# safety check --json
```

**Pass Criteria**:
- No critical or high-severity vulnerabilities in dependencies
- Medium/low vulnerabilities: Document and plan remediation

**Failure Actions**:
- Update vulnerable dependencies to patched versions
- Document exceptions for vulnerabilities without patches
- Consider alternative packages if vulnerability is unresolved

## 2. Test Coverage Gates

### 2.1 Unit Tests (Automated)

**Objective**: Verify all unit tests pass with adequate coverage.

```bash
# Run all unit tests with coverage
pytest tests/unit/ --cov=src --cov-report=term --cov-report=html -v

# Expected output:
# - All tests pass
# - Coverage > 90%
```

**Pass Criteria**:
- 100% unit tests pass
- Coverage ≥ 90% for `src/` directory
- No skipped tests (unless explicitly documented)

**Failure Actions**:
- Fix failing tests immediately
- Add tests for uncovered code paths
- Document legitimate coverage exclusions in `pyproject.toml`

**Coverage Exclusions** (acceptable):
- `if TYPE_CHECKING:` blocks
- `def __repr__():` methods
- Defensive assertions that are never expected to trigger

### 2.2 Integration Tests (Automated)

**Objective**: Verify integration with Cloud SQL and external services.

```bash
# Run integration tests
pytest tests/integration/ -v

# Expected: All tests pass
```

**Pass Criteria**:
- 100% integration tests pass
- Tests run against dev Cloud SQL instance
- Both legacy and postgres backends tested

**Failure Actions**:
- Fix test failures before proceeding
- Verify Cloud SQL connectivity and IAM permissions
- Check for environment-specific issues (dev vs staging config)

### 2.3 Performance Tests (Manual)

**Objective**: Validate performance benchmarks before staging.

```bash
# Run performance tests
pytest tests/performance/ -v -s

# Note: These are slow tests (~10-15 minutes)
```

**Pass Criteria**:
- Migration speed: 10,000 rows < 5 minutes
- Search latency: P95 ≤ 110% of legacy baseline
- Throughput: > 10 searches/second under load

**Failure Actions**:
- Investigate performance regressions
- Profile slow queries using EXPLAIN ANALYZE
- Review connection pooling and indexing configuration
- Consider adjusting batch sizes or query optimization

## 3. Migration Validation Gates

### 3.1 Dry-Run Migration (Manual)

**Objective**: Validate migration script on dev database without committing changes.

```bash
# Run migration in dry-run mode
python scripts/migrate_to_langchain_postgres.py --dry-run

# Expected output:
# - Prerequisites check: PASS
# - Validation check: PASS
# - Dry-run complete (no data modified)
```

**Pass Criteria**:
- Prerequisites check passes (tables exist, indexes exist, pgvector enabled)
- Validation shows 100% record count match (after actual migration)
- No errors during dry-run execution

**Failure Actions**:
- Fix prerequisite failures (schema issues, missing extensions)
- Review validation failures (data inconsistencies)
- Address migration script bugs

### 3.2 Dev Migration Execution (Manual)

**Objective**: Execute full migration on dev database and validate results.

```bash
# Execute migration on dev
python scripts/migrate_to_langchain_postgres.py --execute --batch-size=100

# Verify results
python scripts/migrate_to_langchain_postgres.py --validate
```

**Pass Criteria**:
- Migration completes without errors
- Record counts match: source == target
- Spot-check validation passes (10 random records)
- No data loss or corruption

**Failure Actions**:
- Review migration logs for errors
- Check for partial migration (transaction rollback)
- Verify Cloud SQL has sufficient resources (disk space, connections)
- Re-run migration after fixing issues (idempotent design)

### 3.3 Idempotency Test (Manual)

**Objective**: Verify migration can be safely re-run.

```bash
# Run migration twice
python scripts/migrate_to_langchain_postgres.py --execute
python scripts/migrate_to_langchain_postgres.py --execute

# Expected: Second run completes without duplicates
```

**Pass Criteria**:
- Second migration run succeeds
- No duplicate records created (ON CONFLICT DO NOTHING works)
- Record counts remain the same after second run

**Failure Actions**:
- Fix idempotency issues in migration script
- Review ON CONFLICT clause in INSERT statements
- Test with small dataset first, then full migration

## 4. Feature Flag Validation Gates

### 4.1 Backend Switching (Manual)

**Objective**: Validate VECTOR_BACKEND feature flag works correctly.

```bash
# Test legacy backend
export VECTOR_BACKEND=legacy
# Restart application
# Verify searches work

# Test postgres backend
export VECTOR_BACKEND=postgres
# Restart application
# Verify searches work
```

**Pass Criteria**:
- Application starts successfully with both backend values
- Searches return results with both backends
- No errors in logs during backend switching
- Results semantically equivalent between backends

**Failure Actions**:
- Fix backend selection logic in `src/storage/vector_store.py`
- Verify configuration loading
- Check for hardcoded backend references

### 4.2 Invalid Backend Handling (Automated)

**Objective**: Verify misconfiguration fails fast with clear error.

```bash
# Test with invalid backend value
export VECTOR_BACKEND=invalid_value

# Attempt to start application
# Expected: Clear error message, application fails to start
```

**Pass Criteria**:
- Application fails at startup (before accepting requests)
- Error message clearly identifies problem
- Error message lists valid options

**Failure Actions**:
- Enhance validation logic in `get_default_vector_store()`
- Improve error messages
- Add startup validation tests

## 5. Documentation Gates

### 5.1 Documentation Completeness (Manual)

**Objective**: Ensure all operator documentation is complete and accurate.

**Checklist**:
- [ ] Migration procedure documented (`specs/016-langchain-postgres-upgrade/migration-procedure.md`)
- [ ] Quickstart guide updated (`specs/016-langchain-postgres-upgrade/quickstart.md`)
- [ ] IAM authentication procedure documented
- [ ] Staging smoke tests documented
- [ ] Rollback procedure documented
- [ ] Troubleshooting guide complete

**Pass Criteria**:
- All documentation files exist and are up-to-date
- Copy-paste commands work without modification
- Screenshots or example outputs provided where helpful

**Failure Actions**:
- Complete missing documentation
- Test all commands in documentation
- Update outdated sections

### 5.2 Runbook Review (Manual)

**Objective**: Validate operational runbook for staging deployment.

**Checklist**:
- [ ] Deployment steps clearly documented
- [ ] Rollback steps clearly documented
- [ ] Troubleshooting scenarios covered
- [ ] Monitoring and alerting guidance provided
- [ ] Success criteria defined

**Pass Criteria**:
- Operations team can follow runbook without developer assistance
- All commands tested and verified
- Expected outcomes documented for each step

**Failure Actions**:
- Clarify ambiguous steps
- Add missing troubleshooting scenarios
- Include links to relevant logs and dashboards

## 6. Dependency Gates

### 6.1 Dependency Pinning (Automated)

**Objective**: Ensure all dependencies have version constraints.

```bash
# Check pyproject.toml for unpinned dependencies
cat pyproject.toml | grep -E '^\s*[a-z-]+\s*=\s*"[^<>~=]'

# Expected: No results (all dependencies have constraints)
```

**Pass Criteria**:
- All direct dependencies have version constraints (>=, <, ~=)
- Critical dependencies pinned to specific minor versions
- No `*` wildcards for production dependencies

**Failure Actions**:
- Add version constraints to unpinned dependencies
- Pin critical dependencies (psycopg, langchain-postgres, sqlalchemy)
- Run `uv sync` to update lock file

### 6.2 Dependency Audit (Manual)

**Objective**: Review dependency changes for potential issues.

```bash
# Show dependency tree
uv pip list --format=json | python3 -m json.tool

# Compare with main branch
git diff main:pyproject.toml pyproject.toml
```

**Pass Criteria**:
- No unexpected transitive dependencies added
- New dependencies reviewed and approved
- License compatibility verified

**Failure Actions**:
- Remove unnecessary dependencies
- Replace dependencies with problematic licenses
- Document dependency choices in research.md

## 7. Environment Validation Gates

### 7.1 Configuration Completeness (Manual)

**Objective**: Verify all required configuration variables are documented.

**Checklist**:
- [ ] VECTOR_BACKEND documented and has default value
- [ ] POSTGRES_COLLECTION_NAME documented and has default value
- [ ] CLOUD_SQL_INSTANCE documented (required)
- [ ] CLOUD_SQL_DATABASE documented (required)
- [ ] IAM authentication requirements documented
- [ ] Optional configuration variables documented

**Pass Criteria**:
- All configuration variables in `src/config.py` have docstrings
- Required vs optional variables clearly marked
- Default values documented
- Example `.env` file provided

**Failure Actions**:
- Add missing docstrings
- Update configuration documentation
- Create/update `.env.example` file

### 7.2 Staging Environment Setup (Manual)

**Objective**: Verify staging environment is ready for deployment.

**Checklist**:
- [ ] Staging Cloud SQL instance exists and is accessible
- [ ] Staging service account has Cloud SQL IAM permissions
- [ ] Staging database has sufficient resources (CPU, memory, disk)
- [ ] Staging pgvector extension enabled
- [ ] Staging IAM authentication configured
- [ ] Staging monitoring and logging enabled

**Pass Criteria**:
- All infrastructure prerequisites met
- Can connect to staging Cloud SQL using IAM auth
- Sufficient resources for full migration

**Failure Actions**:
- Provision missing infrastructure
- Configure IAM permissions
- Enable required Cloud SQL flags

## Quality Gate Summary

**Total Gates**: 19 checks across 7 categories

**Automation Level**:
- Automated: 8 checks (can run in CI/CD)
- Manual: 11 checks (require human judgment)

**Execution Time**:
- Fast checks (<5 min): Code quality, unit tests, linting
- Slow checks (>5 min): Integration tests, performance tests, migration
- **Total estimated time**: ~45-60 minutes

## Pass/Fail Decision Matrix

| Severity | Category | Action |
|----------|----------|--------|
| **Critical Failure** | Security vulnerability, test failure, migration error | ❌ BLOCK staging deployment |
| **Major Failure** | Coverage <90%, performance regression >20% | ⚠️ Requires approval to proceed |
| **Minor Failure** | Documentation incomplete, non-critical warnings | ⚠️ Create follow-up ticket, proceed |

## Running All Quality Gates

```bash
# Complete quality gate check script
#!/bin/bash
set -e

echo "=== Feature 016 Quality Gates ==="
echo

echo "1. Code Quality..."
ruff check .

echo
echo "2. Unit Tests..."
pytest tests/unit/ --cov=src --cov-report=term --cov-report=html -v

echo
echo "3. Integration Tests..."
pytest tests/integration/ -v

echo
echo "4. Migration Dry-Run..."
python scripts/migrate_to_langchain_postgres.py --dry-run

echo
echo "5. Feature Flag Tests..."
pytest tests/unit/storage/test_vector_store.py -v -k "test_invalid_backend"

echo
echo "=== All Automated Gates Passed ==="
echo "Proceed with manual gates (performance tests, documentation review, staging setup)"
```

**Save as**: `scripts/run_quality_gates.sh`

**Usage**:
```bash
chmod +x scripts/run_quality_gates.sh
./scripts/run_quality_gates.sh
```

## After Passing Quality Gates

Once all quality gates pass:

1. **Create Staging Deployment PR**
   - Include quality gate results
   - Link to test reports
   - Attach migration plan

2. **Schedule Staging Deployment**
   - Choose low-traffic window
   - Have rollback plan ready
   - Assign on-call engineer

3. **Execute Staging Deployment**
   - Follow `migration-procedure.md`
   - Run staging smoke tests
   - Verify monitoring and alerts

4. **Production Readiness Review**
   - After 48 hours of stable staging operation
   - Review metrics and logs
   - Proceed to T028 (production quality gates)

````
